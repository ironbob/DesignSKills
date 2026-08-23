"""判据卡（rubric）结构校验：评审器可用的前提是判据离散、覆盖可数、快照齐。"""

from __future__ import annotations

import re
from pathlib import Path

from backend.stages.registry import CARDS_DIR, REGISTRY

RUBRIC_IDS = re.compile(r"^\|\s*(R\d+-\d+)\s*\|", re.M)


def test_all_nine_rubric_snapshots_exist():
    for n in range(1, 10):
        p = CARDS_DIR / f"rubric-{n:02d}.md"
        assert p.exists(), f"缺判据卡快照：{p.name}"
        ids = RUBRIC_IDS.findall(p.read_text(encoding="utf-8"))
        assert len(ids) >= 3, f"rubric-{n:02d} 判据过少（{len(ids)} 条）"
        assert len(ids) == len(set(ids)), f"rubric-{n:02d} 判据号重复"


def test_rubric_criteria_parse_into_cards():
    for stage, card in REGISTRY.items():
        assert card.criterion_ids, f"阶段 {stage} 判据未解析"
        assert all(re.fullmatch(r"R\d+-\d+", c) for c in card.criterion_ids)
        # 判据号前缀与阶段一致（rubric-01 → R1-x）
        assert all(c.startswith(f"R{stage}-") for c in card.criterion_ids)


def test_registered_cards_carry_decision_meta():
    from backend.stages.registry import DECISION_META

    for stage, card in REGISTRY.items():
        meta = DECISION_META[stage]
        assert card.human_decision == meta["human_decision"], f"阶段 {stage} human_decision 与决策类别不一致"
        # 品味/答案/豁免类必须停人工（auto 模式安全前提）
        if meta["category"] in ("answer", "taste", "exemption"):
            assert card.human_decision


def test_review_conventions_snapshot_exists():
    p = CARDS_DIR / "review-conventions.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert '"severity"' in text and "禁止打分" in text  # findings 契约 + 离散判定约束在公约里


def test_all_nine_stage_card_snapshots_exist():
    for n in range(1, 10):
        assert (CARDS_DIR / f"stage{n:02d}.md").exists(), f"缺任务卡快照 stage{n:02d}.md"


def test_check_artifacts_snapshot_in_sync_with_skill():
    """HTML gate 用工具内快照（不运行时依赖 skill 源文件），快照必须与 skill 侧逐字节一致。"""
    skill_copy = Path(__file__).resolve().parents[4] / "skills" / "ui-prototype-gen" / "scripts" / "check_artifacts.py"
    assert skill_copy.exists(), f"skill 侧 gate 脚本不存在：{skill_copy}"
    ours = (CARDS_DIR.parent / "check_artifacts.py").read_text(encoding="utf-8")
    assert ours == skill_copy.read_text(encoding="utf-8"), "check_artifacts.py 与 skill 侧漂移，需重新快照"
