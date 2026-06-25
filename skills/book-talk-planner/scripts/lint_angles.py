#!/usr/bin/env python3
# coding: utf-8
"""
讲书角度库结构校验（契约门）。
保证 references/angle-library.md 里的每条视角能稳定作为 skill 引用：
  - 每条视角标题 `### <kebab-id> · <中文名>` 逐字格式正确
  - 四个必备 slot 齐全：看什么 / 何时强 / 钩子倾向 / 示例
  - id 唯一、kebab-case
  - 钩子倾向取值合法（低/中/高/最高）
  - 无 banned 词
  - 视角数量 ≥ 基线（10）—— 低于只警告（尊重可扩展：删减是人为决定）

用法:
  python3 scripts/lint_angles.py                          # 校验自带 angle-library.md
  python3 scripts/lint_angles.py references/angle-library.md   # 校验指定文件
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

# 与 angle-library.md 第四节一致
BANNED_RE = re.compile(r"体验好|功能完善|功能强大|适当处理|待定|待补|后续再说|良好体验|非常重要|很关键|等等|TBD|TODO")

ANGLE_HEAD = re.compile(r"^### ([a-z][a-z0-9-]*) · (.+?)\s*$")
SLOTS = ["看什么", "何时强", "钩子倾向", "示例"]
HOOK_LEVELS = {"低", "中", "高", "最高"}
MIN_ANGLES = 10  # 文档声明基线；低于只警告


def parse_angles(text: str):
    """返回 [(id, name, lineno, section_lines), ...]，跳过代码块。"""
    angles = []
    in_fence = False
    cur = None
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = ANGLE_HEAD.match(stripped)
        if m:
            if cur:
                angles.append(cur)
            cur = {"id": m.group(1), "name": m.group(2), "lineno": i, "lines": []}
        elif cur and stripped.startswith("## "):
            # 进入新的二级标题，结束当前视角
            angles.append(cur)
            cur = None
        elif cur:
            cur["lines"].append((i, line))
    if cur:
        angles.append(cur)
    return angles


def slot_value(section_lines, label):
    """找 `- <label>：xxx` 或 `- <label>: xxx`，返回值文本（去 label 与冒号）。"""
    for _, line in section_lines:
        m = re.match(rf"^\s*-\s*{re.escape(label)}\s*[：:]\s*(.+?)\s*$", line)
        if m:
            return m.group(1)
    return None


def validate(path: Path):
    errs, warns, passed = [], [], []

    if not path.exists():
        print(f"❌ 文件不存在: {path}")
        return 1
    text = path.read_text(encoding="utf-8")

    # 注意：banned 词只扫「视角内容」，不扫文档说明（第四节本就在列 banned 词）
    angles = parse_angles(text)
    if not angles:
        errs.append("[A-PARSE] 未解析到任何视角（`### <id> · <name>` 格式是否正确？）")
    else:
        seen = {}
        for a in angles:
            tag = f"[A-SLOT] {a['id']}"
            ok = True
            for s in SLOTS:
                if slot_value(a["lines"], s) is None:
                    errs.append(f"{tag} 缺 slot: - {s}")
                    ok = False
            # 钩子倾向取值（去掉强调星号与中文/英文括号后的说明）
            hl = slot_value(a["lines"], "钩子倾向")
            if hl is not None:
                core = re.split(r"[（(]", hl)[0].replace("*", "").strip()
                if core not in HOOK_LEVELS:
                    errs.append(f"{tag} 钩子倾向取值非法: {hl}（应为 低/中/高/最高）")
            # banned 词只扫本视角的 slot 内容
            for ln, line in a["lines"]:
                hits = BANNED_RE.findall(line)
                if hits:
                    errs.append(f"[A-BANNED] {a['id']} L{ln} banned 词命中 {hits}: {line.strip()}")
            if a["id"] in seen:
                errs.append(f"[A-UNIQ] id 重复: {a['id']}（L{seen[a['id']]} 与 L{a['lineno']}）")
            else:
                seen[a["id"]] = a["lineno"]
            if ok:
                passed.append(f"[A-SLOT] {a['id']} · {a['name']} slot 齐全")

        # 数量基线（警告，不阻断）
        if len(angles) < MIN_ANGLES:
            warns.append(f"[A-COUNT] 视角数 {len(angles)} < 基线 {MIN_ANGLES}（可扩展，但建议补齐）")
        else:
            passed.append(f"[A-COUNT] 视角数 {len(angles)} ≥ {MIN_ANGLES}")

    # 输出
    print(f"── 校验: {path}")
    for p in passed:
        print(f"  ✅ {p}")
    for w in warns:
        print(f"  🟡 {w}")
    for e in errs:
        print(f"  🔴 {e}")
    print(f"\nERROR: {len(errs)}  WARNING: {len(warns)}  PASSED: {len(passed)}")
    return 1 if errs else 0


def main(argv):
    here = Path(__file__).resolve().parent
    lib = here.parent / "references" / "angle-library.md"
    if len(argv) > 1:
        a = Path(argv[1])
        lib = a if a.is_absolute() else (Path.cwd() / a)
    code = validate(lib)
    sys.exit(code)


if __name__ == "__main__":
    main(sys.argv)
