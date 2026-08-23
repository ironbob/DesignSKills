"""阶段卡注册表（九阶段全量注册）。

StageCard = 网页工具的编排单元（SKILL.md 工具化映射）：
  阶段卡 = 一次有界 AI 调用；gate = L1 脚本 + L2 评审判据卡；decision_type = 界面确认控件形态；
  human_decision = auto 模式下是否仍必停人工（答案/品味/豁免类 True，事实类 False）。
卡文本快照在 stages/cards/（防 skill 升级导致 prompt 突变）；rubric-0N.md 为 L2 判据卡快照；
check_artifacts.py 为 L1 HTML gate 的工具内快照（与 skill scripts/ 逐字节同步，测试锁定）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..workspace import WorkspaceManager

CARDS_DIR = Path(__file__).parent / "cards"

Canvas = tuple[int, int]  # (width, height) = 项目锁端画布


@dataclass(frozen=True)
class GateResult:
    ok: bool
    problems: list[str] = field(default_factory=list)


def _parse_criteria(rubric_file: Path) -> frozenset[str]:
    """从判据卡表格行抽判据号（| R2-1 | … |）。覆盖完整性校验的数据源。"""
    if not rubric_file.exists():
        return frozenset()
    ids = re.findall(r"^\|\s*(R\d+-\d+)\s*\|", rubric_file.read_text(encoding="utf-8"), re.M)
    return frozenset(ids)


@dataclass(frozen=True)
class StageCard:
    stage: int
    name: str
    decision_type: str  # question_form | gallery | crit | confirm | none
    artifact_paths: list[str]
    artifact_map: dict[str, str]
    mock_dir: Path | None
    decision_data_path: str | None
    prompt_file: Path
    rubric_file: Path | None = None       # L2 判据卡快照（None=无 L2）
    human_decision: bool = True           # auto 模式下必停人工（答案/品味/豁免类）

    @property
    def criterion_ids(self) -> frozenset[str]:
        return _parse_criteria(self.rubric_file) if self.rubric_file else frozenset()

    def build_prompt(self, ctx: dict[str, Any]) -> str:
        card_text = self.prompt_file.read_text(encoding="utf-8")
        w, h = ctx["canvas_w"], ctx["canvas_h"]
        return (
            f"你在执行「AI 设计工作台」九阶段工作流的阶段 {self.stage}（{self.name}）。\n"
            f"当前项目：{ctx['product_name']} · {ctx['project_name']}（{ctx['platform']}，画布 {w}×{h}）。\n"
            f"硬约束（项目目标画布，逐字执行）：本阶段一切 HTML 产物的 .frame 必须精确 "
            f"width:{w}px; height:{h}px（锁宽锁高，box-sizing:border-box）；长内容用 flex:1 + overflow:hidden "
            f"内容区内部滚动，禁止整屏长高；浮层用居中覆盖层；单文件自包含。\n"
            f"工作目录即项目工作区；需求文档在 00-requirement.md。\n\n"
            f"阶段任务卡（严格按此执行）：\n---\n{card_text}\n---\n\n"
            f"产出要求：写 {'、'.join(self.artifact_paths)}"
            + (f"，决策数据写 {self.decision_data_path}（JSON，供界面表单消费）" if self.decision_data_path else "")
            + "。\n只写本阶段产物，不越阶段。产物内容用真实感样例数据，不用占位文案。"
        )

    def run_gate(self, ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
        return GATES[self.stage](ws, project_dir, canvas)


# ---------- 决策数据派生（gallery/crit 的界面选项与 advance 校验共用） ----------

def gallery_items(card: StageCard, project_dir: Path) -> list[dict[str, Any]]:
    """gallery 型决策选项：从已产出文件派生（阶段 4=屏×变体，阶段 5=方向 tile）。"""
    if card.stage == 4:
        d = project_dir / "04-wireframes"
        screens = sorted({p.name.split("-v")[0] for p in d.glob("*-v1.html")}) if d.is_dir() else []
        return [
            {
                "id": s,
                "text": f"{s} · 线框变体（结构级二选一，可混搭）",
                "options": [
                    {"label": "V1", "preview": f"04-wireframes/{s}-v1.html"},
                    {"label": "V2", "preview": f"04-wireframes/{s}-v2.html"},
                ],
                "mixable": True,
            }
            for s in screens
        ]
    if card.stage == 5:
        d = project_dir / "05-style-tiles"
        tiles = sorted(d.glob("tile-*.html")) if d.is_dir() else []
        return [
            {
                "id": "style-direction",
                "text": "视觉方向（三选一，可指定混搭如「A 为基底但核心区纯白」）",
                "options": [
                    {"label": p.stem.replace("tile-", "").upper(), "preview": str(p.relative_to(project_dir))}
                    for p in tiles
                ],
                "mixable": True,
            }
        ]
    return []


def crit_decision_items(data: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """crit 型决策项 =（🟡 findings 处置, U-x 倾向确认）。🔴 已由 L1 gate 强制清零。"""
    yellows = [f for f in data.get("findings", []) if f.get("severity") == "yellow"]
    return yellows, list(data.get("u_items", []))


# ---------- gate 实现 ----------

def _gate_stage01(ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
    problems: list[str] = []
    memo = project_dir / "01-需求消化.md"
    if not memo.exists() or len(memo.read_text(encoding="utf-8").strip()) < 200:
        problems.append("01-需求消化.md 缺失或过短（<200 字）")
    qpath = project_dir / ".stage1-questions.json"
    if not qpath.exists():
        return GateResult(False, problems + [".stage1-questions.json 缺失（决策数据未产出）"])
    try:
        data = json.loads(qpath.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        return GateResult(False, problems + [f".stage1-questions.json 不可解析：{e}"])
    blocking = data.get("blocking") or []
    if not blocking:
        problems.append("blocking 为空——阶段 1 至少要有一个阻塞性问题（A-x）")
    for q in blocking:
        if not q.get("id") or not q.get("text"):
            problems.append("存在缺 id/text 的阻塞问题")
            break
        rec = [o for o in q.get("options", []) if o.get("recommend")]
        if not rec:
            problems.append(f"{q.get('id')} 无推荐选项（零裸问）")
        for o in q.get("options", []):
            if not o.get("claim") or not o.get("consequence"):
                problems.append(f"{q.get('id')} 选项 {o.get('label')} 缺主张或后果（三件套不全）")
                break
    return GateResult(not problems, problems)


_MERMAID_FENCE = re.compile(r"```mermaid\r?\n(.*?)```", re.S)
_LABEL = re.compile(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|\|[^|]*\|")
_IDENT = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*\b")
_ARROW = re.compile(r"--?>|-->|-\..*?\.->|-\.->|==>")
_SKIP_LINE = ("flowchart", "graph", "%%", "direction", "classDef", "class ", "style ", "end", "click")


def _mermaid_block_problems(block: str, idx: int) -> list[str]:
    """结构化检查：有边（无断链）、无孤儿节点（声明但无任何边连接）。"""
    edge_nodes: set[str] = set()
    def_nodes: set[str] = set()
    edge_count = 0
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith(_SKIP_LINE) or line.startswith("subgraph"):
            continue
        stripped = _LABEL.sub("", line)
        ids = _IDENT.findall(stripped)
        if not ids:
            continue
        if _ARROW.search(stripped) or "--" in stripped:
            if ids:
                edge_count += 1
                edge_nodes.update((ids[0], ids[-1]))
        elif re.search(r"\[|\(|\{", line):
            def_nodes.update(i for i in ids if i not in ("end",))
    if edge_count == 0:
        return [f"第 {idx} 个 mermaid 块无边（流程必须从触发走到出口，无断链）"]
    orphans = sorted(def_nodes - edge_nodes)
    return [f"第 {idx} 个 mermaid 块存在孤儿节点 {n}（声明了但无任何边连接）" for n in orphans]


def _gate_stage02(ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
    fpath = project_dir / "02-流程草图.md"
    if not fpath.exists():
        return GateResult(False, ["02-流程草图.md 缺失"])
    text = fpath.read_text(encoding="utf-8")
    fences = _MERMAID_FENCE.findall(text)
    if not fences:
        return GateResult(False, ["未找到 mermaid 代码块（流程草图必须用 Mermaid，任务卡约定）"])
    problems: list[str] = []
    for i, block in enumerate(fences, 1):
        problems.extend(_mermaid_block_problems(block, i))
    return GateResult(not problems, problems)


# ---- 阶段 3 共用：屏幕盘点 / 关键屏 ----

_SCREEN_ROW = re.compile(r"^\|\s*(S\d+)\s*\|", re.M)


def _screen_inventory(project_dir: Path) -> list[str]:
    f = project_dir / "03-屏幕与IA.md"
    if not f.exists():
        return []
    return sorted(set(_SCREEN_ROW.findall(f.read_text(encoding="utf-8"))))


def _key_screens(project_dir: Path) -> list[str]:
    """阶段 3 提名的关键屏（「关键屏提名」小节里的 S#）；无 03 时回退到 04 的 v1 文件名。"""
    f = project_dir / "03-屏幕与IA.md"
    if f.exists():
        text = f.read_text(encoding="utf-8")
        m = re.search(r"关键屏提名.*", text)
        if m:
            tail = text[m.start():]
            ids = re.findall(r"\bS\d+\b", tail[:600])
            if ids:
                return sorted(set(ids))
    d = project_dir / "04-wireframes"
    if d.is_dir():
        return sorted({p.name.split("-v")[0] for p in d.glob("*-v1.html")})
    return []


def _gate_stage03(ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
    f = project_dir / "03-屏幕与IA.md"
    if not f.exists():
        return GateResult(False, ["03-屏幕与IA.md 缺失"])
    text = f.read_text(encoding="utf-8")
    problems: list[str] = []
    fences = _MERMAID_FENCE.findall(text)
    if not fences:
        problems.append("未找到 mermaid IA 图（任务卡约定 IA 用 Mermaid）")
    for i, block in enumerate(fences, 1):
        problems.extend(_mermaid_block_problems(block, i))
    inventory = sorted(set(_SCREEN_ROW.findall(text)))
    if len(inventory) < 3:
        problems.append(f"屏幕盘点表行过少（{len(inventory)} 屏，需 ≥3）")
    if "闭环" not in text:
        problems.append("缺闭环检查表（每条流程 → 覆盖屏幕 → ✅）")
    elif "✅" not in text:
        problems.append("闭环检查表无 ✅ 结论")
    keys = _key_screens(project_dir)
    if not 2 <= len(keys) <= 3:
        problems.append(f"关键屏提名应为 2–3 个（当前 {len(keys)}）")
    for s in keys:
        if s not in inventory:
            problems.append(f"关键屏 {s} 不在盘点表中")
    # 孤儿屏：盘点表屏必须在 IA 图或闭环检查中出现（≥2 次）
    orphans = [s for s in inventory if text.count(s) < 2]
    if orphans:
        problems.append(f"存在孤儿屏（盘点表声明但 IA/闭环未触达）：{orphans}")
    if len(inventory) > 12:
        problems.append(f"屏幕数 {len(inventory)} 超上限 12（超限拆工作区）")
    return GateResult(not problems, problems)


# ---- HTML gate（工具内快照，防运行时依赖 skill 源文件） ----

def _html_problems(files: list[Path], canvas: Canvas | None) -> list[str]:
    """HTML 阶段的 L1 三查。canvas 缺失=配置错误：不允许静默回退默认 390×844。"""
    from .check_artifacts import check_file

    problems: list[str] = []
    for f in files:
        if canvas is None:
            problems.append(f"[CANVAS] {f.name}: 未提供项目画布（HTML gate 不允许回退默认 390×844）")
        else:
            problems.extend(check_file(f, canvas[0], canvas[1]))
    return problems


def _frames_of(html: str) -> int:
    return html.count('class="frame"') + html.count("class='frame'")


def _gate_stage04(ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
    d = project_dir / "04-wireframes"
    if not d.is_dir():
        return GateResult(False, ["04-wireframes/ 缺失"])
    problems: list[str] = []
    for s in _key_screens(project_dir):
        for v in ("v1", "v2"):
            if not (d / f"{s}-{v}.html").exists():
                problems.append(f"关键屏 {s} 缺 {v} 变体文件")
    idx = d / "index.html"
    if not idx.exists():
        problems.append("04-wireframes/index.html 缺失（变体对照板）")
    else:
        itext = idx.read_text(encoding="utf-8")
        if not re.search(r"[？?]", itext):
            problems.append("index.html 未写明要决策的问题（每对变体一句「X 放哪：贴 A 还是固定 B？」）")
    files = sorted(d.glob("*.html"))
    problems.extend(_html_problems(files, canvas))
    for f in files:
        if f.name == "index.html":
            continue
        t = f.read_text(encoding="utf-8")
        if _frames_of(t) < 2:
            problems.append(f"{f.name} 状态帧 <2（一帧一态，覆盖该屏模式×状态）")
        elif not re.search(r"空|中断|错误|异常", t):
            problems.append(f"{f.name} 未覆盖异常态（空/中断/错误——异常态画错是后期 🔴 最大来源）")
    return GateResult(not problems, problems)


def _gate_stage05(ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
    d = project_dir / "05-style-tiles"
    if not d.is_dir():
        return GateResult(False, ["05-style-tiles/ 缺失"])
    problems: list[str] = []
    tiles = sorted(d.glob("tile-*.html"))
    if len(tiles) < 3:
        problems.append(f"风格方向 tile 应为 3 个（当前 {len(tiles)}）")
    idx = d / "index.html"
    if not idx.exists():
        problems.append("05-style-tiles/index.html 缺失（三方向对照表）")
    else:
        itext = idx.read_text(encoding="utf-8")
        for t in tiles:
            if t.stem not in itext:
                problems.append(f"index.html 对照表未提及 {t.stem}")
    problems.extend(_html_problems(tiles + ([idx] if idx.exists() else []), canvas))
    return GateResult(not problems, problems)


_TOKEN_COLOR_KEYS = {"bg", "surface", "line", "ink", "ink_weak", "accent", "accent_ink", "danger"}
_TOKEN_TOUCH_KEYS = {"min_height", "min_width", "primary_min_width", "max_keys_per_bar"}


def _gate_stage06(ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
    problems: list[str] = []
    tpath = project_dir / "06-tokens.json"
    if not tpath.exists():
        return GateResult(False, ["06-tokens.json 缺失（★契约：机器可读 token 数据源）"])
    try:
        tokens = json.loads(tpath.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        return GateResult(False, [f"06-tokens.json 不可解析：{e}"])
    cv = tokens.get("canvas") or {}
    if not (isinstance(cv.get("width"), int) and isinstance(cv.get("height"), int)):
        problems.append("canvas.width/height 缺失或非整数（项目目标画布是全流程唯一画布来源）")
    elif canvas is not None and (cv["width"], cv["height"]) != canvas:
        problems.append(f"canvas {cv['width']}×{cv['height']} 与项目画布 {canvas[0]}×{canvas[1]} 不一致")
    missing = _TOKEN_COLOR_KEYS - set((tokens.get("color") or {}))
    if missing:
        problems.append(f"color 缺键：{sorted(missing)}")
    semantic = tokens.get("semantic") or {}
    if not semantic:
        problems.append("semantic 为空（领域语义态：{color,symbol,label} 三元组）")
    for k, v in semantic.items():
        if not (isinstance(v, dict) and v.get("color") and v.get("symbol") and v.get("label")):
            problems.append(f"semantic[{k}] 三元组不全（color/symbol/label）")
            break
    scale = (tokens.get("type") or {}).get("scale") or {}
    if len(scale) < 5:
        problems.append(f"type.scale 刻度不足（{len(scale)} 级，需 ≥5）")
    if len(tokens.get("space") or []) < 4:
        problems.append("space 留白刻度不足（≥4 档）")
    if not tokens.get("radius"):
        problems.append("radius 缺失")
    touch = tokens.get("touch") or {}
    tmiss = _TOKEN_TOUCH_KEYS - set(touch)
    if tmiss:
        problems.append(f"touch 缺键：{sorted(tmiss)}")
    if len(tokens.get("rules") or []) < 12:
        problems.append(f"rules 规则十二条不全（当前 {len(tokens.get('rules') or [])} 条）")
    html = project_dir / "06-design-system.html"
    if not html.exists():
        problems.append("06-design-system.html 缺失（给人看的规范样张）")
    else:
        ht = html.read_text(encoding="utf-8")
        if "按钮" not in ht or "列表" not in ht:
            problems.append("样张缺组件族章节（按钮/列表行）")
        problems.extend(_html_problems([html], canvas))
    return GateResult(not problems, problems)


def _gate_stage07(ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
    d = project_dir / "07-hifi"
    if not d.is_dir():
        return GateResult(False, ["07-hifi/ 缺失"])
    problems: list[str] = []
    inventory = _screen_inventory(project_dir)
    if not inventory:
        problems.append("读不到 03 屏幕盘点（阶段 7 铺全量的基准）")
    for s in inventory:
        f = d / f"{s}.html"
        if not f.exists():
            problems.append(f"盘点屏 {s} 在 07-hifi/ 无对应文件")
            continue
        if _frames_of(f.read_text(encoding="utf-8")) < 1:
            problems.append(f"{s}.html 无状态帧（每屏含状态变体）")
    idx = d / "index.html"
    if not idx.exists():
        problems.append("07-hifi/index.html 缺失（全屏索引+契约执行情况）")
    problems.extend(_html_problems(sorted(d.glob("*.html")), canvas))
    return GateResult(not problems, problems)


def _gate_stage08(ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
    problems: list[str] = []
    for name in ("08-交互说明.md", "08-prototype.html", "08-findings.md"):
        if not (project_dir / name).exists():
            problems.append(f"{name} 缺失")
    itext = (project_dir / "08-交互说明.md")
    if itext.exists():
        t = itext.read_text(encoding="utf-8")
        if "转场" not in t:
            problems.append("08-交互说明.md 缺转场标注表")
        if "状态" not in t or "模式" not in t:
            problems.append("08-交互说明.md 缺核心屏模式×状态矩阵")
    proto = project_dir / "08-prototype.html"
    if proto.exists():
        pt = proto.read_text(encoding="utf-8")
        if "定位" not in pt:
            problems.append("08-prototype.html 缺流程定位条（右上角随时显示走到哪步）")
        problems.extend(_html_problems([proto], canvas))
    jpath = project_dir / ".stage8-findings.json"
    if not jpath.exists():
        problems.append(".stage8-findings.json 缺失（crit 决策数据）")
        return GateResult(not problems, problems)
    try:
        data = json.loads(jpath.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        return GateResult(False, problems + [f".stage8-findings.json 不可解析：{e}"])
    dims = {d.get("dim") for d in data.get("dims", []) if isinstance(d, dict)}
    dim_missing = set(range(1, 11)) - dims
    if dim_missing:
        problems.append(f"十维度结论不全（沉默即违规）：缺维度 {sorted(dim_missing)}")
    for d in data.get("dims", []):
        if d.get("verdict") not in ("finding", "pass", "na"):
            problems.append(f"维度 {d.get('dim')} 结论非法（finding/pass/na）：{d.get('verdict')}")
            break
    for f in data.get("findings", []):
        if f.get("severity") == "red" and not f.get("fix_record"):
            problems.append(f"{f.get('id')}（🔴）无修复记录——🔴 清零才能定稿")
        if f.get("severity") == "yellow" and f.get("proposed") not in ("fix", "spec", "exempt"):
            problems.append(f"{f.get('id')}（🟡）无处置建议（fix/spec/exempt）")
    for u in data.get("u_items", []):
        if not u.get("proposal"):
            problems.append(f"{u.get('id')} 未决项无倾向方案")
    return GateResult(not problems, problems)


_SPEC_SECTIONS = ("消费者", "设计前提", "IA 与导航", "领域语义", "逐屏规格", "矩阵", "设计系统契约", "实现注意", "未决", "验收")


def _gate_stage09(ws: WorkspaceManager, project_dir: Path, canvas: Canvas | None = None) -> GateResult:
    problems: list[str] = []
    spath = project_dir / "09-spec.md"
    if not spath.exists():
        return GateResult(False, ["09-spec.md 缺失（★交付契约）"])
    text = spath.read_text(encoding="utf-8")
    hit = [k for k in _SPEC_SECTIONS if k in text]
    if len(hit) < 8:
        problems.append(f"spec 十节不全（命中 {len(hit)}/10：{hit}）")
    for contract in ("06-tokens.json", "07-hifi"):
        if contract not in text:
            problems.append(f"spec 未声明契约件 {contract}")
        if not (project_dir / contract).exists():
            problems.append(f"契约件缺失：{contract}")
    # 引用帧存在性：spec 里点名的 07-hifi/S*.html 必须真实存在
    for ref in sorted(set(re.findall(r"07-hifi/[\w-]+\.html", text))):
        if not (project_dir / ref).exists():
            problems.append(f"spec 引用的参照帧不存在：{ref}")
    return GateResult(not problems, problems)


GATES = {
    1: _gate_stage01,
    2: _gate_stage02,
    3: _gate_stage03,
    4: _gate_stage04,
    5: _gate_stage05,
    6: _gate_stage06,
    7: _gate_stage07,
    8: _gate_stage08,
    9: _gate_stage09,
}


# ---------- 注册 ----------

def _card(
    stage: int,
    name: str,
    decision_type: str,
    artifacts: list[str],
    amap: dict[str, str] | None = None,
    decision_path: str | None = None,
    human_decision: bool = True,
) -> StageCard:
    return StageCard(
        stage=stage,
        name=name,
        decision_type=decision_type,
        artifact_paths=artifacts,
        artifact_map=amap or {a.split("/")[-1]: a for a in artifacts},
        mock_dir=CARDS_DIR / "mock" / f"stage{stage:02d}",
        decision_data_path=decision_path,
        prompt_file=CARDS_DIR / f"stage{stage:02d}.md",
        rubric_file=CARDS_DIR / f"rubric-{stage:02d}.md",
        human_decision=human_decision,
    )


REGISTRY: dict[int, StageCard] = {
    1: _card(
        1, "需求消化", "question_form",
        ["01-需求消化.md"],
        {"01-需求消化.md": "01-需求消化.md", "stage1-questions.json": ".stage1-questions.json"},
        ".stage1-questions.json",
        human_decision=True,   # 答案类：A-x 只有用户能答
    ),
    2: _card(
        2, "流程草图", "confirm",
        ["02-流程草图.md"],
        None, None,
        human_decision=False,  # 事实类：auto 过双层 gate 自动推进
    ),
    3: _card(
        3, "屏幕与IA", "confirm",
        ["03-屏幕与IA.md"],
        None, None,
        human_decision=False,
    ),
    4: _card(
        4, "关键屏灰框", "gallery",
        ["04-wireframes"],
        None, None,
        human_decision=True,   # 品味类：挑变体必停人工
    ),
    5: _card(
        5, "视觉方向", "gallery",
        ["05-style-tiles"],
        None, None,
        human_decision=True,   # 品味类：挑方向必停人工
    ),
    6: _card(
        6, "设计系统", "confirm",
        ["06-tokens.json", "06-design-system.html"],
        None, None,
        human_decision=False,
    ),
    7: _card(
        7, "高保真", "confirm",
        ["07-hifi"],
        None, None,
        human_decision=False,
    ),
    8: _card(
        8, "交互与crit", "crit",
        ["08-交互说明.md", "08-prototype.html", "08-findings.md"],
        {"08-交互说明.md": "08-交互说明.md", "08-prototype.html": "08-prototype.html",
         "08-findings.md": "08-findings.md", "stage8-findings.json": ".stage8-findings.json"},
        ".stage8-findings.json",
        human_decision=True,   # 豁免类：crit 处置必停人工
    ),
    9: _card(
        9, "规格导出", "confirm",
        ["09-spec.md"],
        None, None,
        human_decision=False,
    ),
}

# 阶段 3-9 常量（阶段轨展示）
NINE_STAGES = ["需求消化", "流程草图", "屏幕与IA", "关键屏灰框", "视觉方向", "设计系统", "高保真", "交互与crit", "规格导出"]

# 决策类别（SKILL.md 阶段总表）：auto 模式的停走规格，前端向导与阶段轨共用
DECISION_META = {
    1: {"category": "answer", "label": "答案类", "human_decision": True},
    2: {"category": "fact", "label": "事实类", "human_decision": False},
    3: {"category": "fact", "label": "事实类", "human_decision": False},
    4: {"category": "taste", "label": "品味类", "human_decision": True},
    5: {"category": "taste", "label": "品味类", "human_decision": True},
    6: {"category": "fact", "label": "事实类", "human_decision": False},
    7: {"category": "fact", "label": "事实类", "human_decision": False},
    8: {"category": "exemption", "label": "豁免类", "human_decision": True},
    9: {"category": "fact", "label": "事实类", "human_decision": False},
}
