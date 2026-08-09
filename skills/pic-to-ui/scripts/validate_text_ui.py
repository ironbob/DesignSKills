#!/usr/bin/env python3
"""Gate 0: validate one text-drawn UI file per screenshot and user confirmation."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _report import Report, emit  # noqa: E402

VALID_PHASES = {"draft", "confirmed"}
VALID_CONFIRMATIONS = {"pending", "user_confirmed", "rejected"}
SHOT_ID_RE = re.compile(r"^SHOT-\d+$")
DRAWING_RE = re.compile(r"[┌┐└┘├┤┬┴┼│─+|\[\]]")


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _resolve_inside(root: Path, relative: str) -> Path | None:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def validate(document: dict[str, Any], phase: str, artifact_root: Path) -> Report:
    report = Report()
    report.add("TXT.phase", "ERROR", phase in VALID_PHASES,
               f"phase 非法：{phase}" if phase not in VALID_PHASES else f"phase={phase}")

    meta = document.get("meta")
    screenshots = document.get("screenshots")
    meta_ok = isinstance(meta, dict) and _nonempty(meta.get("screen"))
    report.add("TXT.meta", "ERROR", meta_ok,
               "meta 须含非空 screen" if not meta_ok else "meta 完整")
    list_ok = isinstance(screenshots, list) and bool(screenshots)
    report.add("TXT.screenshots", "ERROR", list_ok,
               "screenshots 须为非空数组" if not list_ok else f"截图 {len(screenshots)} 张")
    if not list_ok:
        return report

    count = len(screenshots)
    counts_ok = (
        isinstance(meta, dict)
        and meta.get("source_count") == count
        and meta.get("text_ui_count") == count
    )
    report.add("TXT.count", "ERROR", counts_ok,
               "source_count/text_ui_count 必须等于 screenshots.length（一图一文本图）"
               if not counts_ok else f"一一对应数量={count}")

    ids: list[str] = []
    sources: list[str] = []
    files: list[str] = []
    for index, item in enumerate(screenshots):
        ctx = f"screenshots[{index}]"
        if not isinstance(item, dict):
            report.add("TXT.item", "ERROR", False, f"{ctx} 须为对象")
            continue
        shot_id = item.get("id")
        source = item.get("source")
        text_file = item.get("text_ui_file")
        fields_ok = (
            isinstance(shot_id, str) and bool(SHOT_ID_RE.match(shot_id))
            and _nonempty(source)
            and _nonempty(item.get("state_label"))
            and _nonempty(text_file)
            and isinstance(item.get("revision"), int) and item["revision"] > 0
        )
        report.add("TXT.item", "ERROR", fields_ok,
                   f"{ctx} 须含 SHOT-<n> id/source/state_label/text_ui_file/正整数 revision"
                   if not fields_ok else f"{shot_id}: 字段完整")
        if isinstance(shot_id, str):
            ids.append(shot_id)
        if isinstance(source, str):
            sources.append(source)
        if isinstance(text_file, str):
            files.append(text_file)

        confirmation = item.get("confirmation")
        status = confirmation.get("status") if isinstance(confirmation, dict) else None
        confirmation_ok = isinstance(confirmation, dict) and status in VALID_CONFIRMATIONS
        report.add("TXT.confirmation.fields", "ERROR", confirmation_ok,
                   f"{shot_id or ctx}: confirmation.status 须为 {sorted(VALID_CONFIRMATIONS)}"
                   if not confirmation_ok else f"{shot_id}: confirmation={status}")
        if phase == "draft":
            report.add("TXT.confirmation.draft", "ERROR", status != "rejected",
                       f"{shot_id}: rejected 后须修订并重置 pending" if status == "rejected" else f"{shot_id}: 可展示确认")
        elif phase == "confirmed":
            user_confirmed = (
                status == "user_confirmed"
                and confirmation.get("confirmed_by") == "user"
                and _nonempty(confirmation.get("evidence"))
            ) if isinstance(confirmation, dict) else False
            report.add("TXT.confirmation.user", "ERROR", user_confirmed,
                       f"{shot_id}: 未获用户明确确认（须 user_confirmed/confirmed_by=user/evidence）"
                       if not user_confirmed else f"{shot_id}: 用户已确认")

        if isinstance(text_file, str):
            suffix_ok = Path(text_file).suffix.lower() in {".txt", ".md"}
            report.add("TXT.file.extension", "ERROR", suffix_ok,
                       f"{shot_id}: text_ui_file 须为 .txt 或 .md" if not suffix_ok else f"{shot_id}: 扩展名合法")
            resolved = _resolve_inside(artifact_root, text_file)
            inside_ok = resolved is not None
            report.add("TXT.file.inside", "ERROR", inside_ok,
                       f"{shot_id}: text_ui_file 越出 artifact root" if not inside_ok else f"{shot_id}: 路径在 root 内")
            exists = bool(resolved and resolved.is_file())
            report.add("TXT.file.exists", "ERROR", exists,
                       f"{shot_id}: 文本图文件不存在：{text_file}" if not exists else f"{shot_id}: 文件存在")
            if exists and resolved:
                try:
                    content = resolved.read_text(encoding="utf-8")
                except OSError as exc:
                    report.add("TXT.file.read", "ERROR", False, f"{shot_id}: 无法读取：{exc}")
                else:
                    lines = [line for line in content.splitlines() if line.strip()]
                    drawing_marks = len(DRAWING_RE.findall(content))
                    drawn = len(lines) >= 4 and drawing_marks >= 8
                    report.add("TXT.file.drawing", "ERROR", drawn,
                               f"{shot_id}: 必须是至少 4 行、含边框/控件字符的文本 UI 图，不是 prose"
                               if not drawn else f"{shot_id}: 文本图结构有效")

    unique_ok = (
        len(ids) == count == len(set(ids))
        and len(sources) == count == len(set(sources))
        and len(files) == count == len(set(files))
    )
    report.add("TXT.one_to_one", "ERROR", unique_ok,
               "每张截图必须有唯一 id/source/text_ui_file，且不同截图不能共用文本图"
               if not unique_ok else "截图与独立文本图一一对应")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate 0: screenshot-to-text-UI parity and confirmation")
    parser.add_argument("manifest", type=Path, help="Path to text-ui-manifest.json")
    parser.add_argument("--phase", required=True, choices=sorted(VALID_PHASES))
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取 text-ui manifest：{exc}", file=sys.stderr)
        return 2
    if not isinstance(document, dict):
        print("text-ui manifest 顶层须为对象", file=sys.stderr)
        return 2
    return emit(validate(document, args.phase, args.artifact_root), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
