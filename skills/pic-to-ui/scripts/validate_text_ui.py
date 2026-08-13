#!/usr/bin/env python3
"""Gate 0: validate one text-drawn UI file per screenshot/verbal input and confirmation."""
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
INPUT_ID_RE = re.compile(r"^(SHOT|DESC)-\d+$")
DRAWING_RE = re.compile(r"[┌┐└┘├┤┬┴┼│─+|\[\]]")
VALID_INPUT_MODES = {"screenshot", "verbal", "mixed"}
VALID_INPUT_TYPES = {"screenshot", "verbal"}


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
    inputs = document.get("inputs")
    input_mode = meta.get("input_mode") if isinstance(meta, dict) else None
    meta_ok = (
        isinstance(meta, dict)
        and _nonempty(meta.get("screen"))
        and input_mode in VALID_INPUT_MODES
    )
    report.add("TXT.meta", "ERROR", meta_ok,
               "meta 须含非空 screen 和合法 input_mode" if not meta_ok else "meta 完整")
    list_ok = isinstance(inputs, list) and bool(inputs)
    report.add("TXT.inputs", "ERROR", list_ok,
               "inputs 须为非空数组" if not list_ok else f"输入 {len(inputs)} 项")
    if not list_ok:
        return report

    count = len(inputs)
    counts_ok = (
        isinstance(meta, dict)
        and meta.get("input_count") == count
        and meta.get("text_ui_count") == count
    )
    report.add("TXT.count", "ERROR", counts_ok,
               "input_count/text_ui_count 必须等于 inputs.length（一输入一文本图）"
               if not counts_ok else f"一一对应数量={count}")

    ids: list[str] = []
    input_types: list[str] = []
    files: list[str] = []
    for index, item in enumerate(inputs):
        ctx = f"inputs[{index}]"
        if not isinstance(item, dict):
            report.add("TXT.item", "ERROR", False, f"{ctx} 须为对象")
            continue
        shot_id = item.get("id")
        input_type = item.get("input_type")
        text_file = item.get("text_ui_file")
        fields_ok = (
            isinstance(shot_id, str) and bool(INPUT_ID_RE.match(shot_id))
            and input_type in VALID_INPUT_TYPES
            and _nonempty(item.get("state_label"))
            and _nonempty(text_file)
            and isinstance(item.get("revision"), int) and item["revision"] > 0
        )
        report.add("TXT.item", "ERROR", fields_ok,
                   f"{ctx} 须含 SHOT|DESC-<n> id/input_type/state_label/text_ui_file/正整数 revision"
                   if not fields_ok else f"{shot_id}: 字段完整")
        source_ok = (
            input_type == "screenshot" and isinstance(shot_id, str) and shot_id.startswith("SHOT-") and _nonempty(item.get("source"))
        ) or (
            input_type == "verbal" and isinstance(shot_id, str) and shot_id.startswith("DESC-") and _nonempty(item.get("verbal_input"))
        )
        report.add("TXT.input.source", "ERROR", source_ok,
                   f"{shot_id or ctx}: screenshot 需 SHOT id + source；verbal 需 DESC id + verbatim verbal_input"
                   if not source_ok else f"{shot_id}: {input_type} 输入可追溯")
        if isinstance(shot_id, str):
            ids.append(shot_id)
        if isinstance(input_type, str):
            input_types.append(input_type)
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

    expected_types = set(input_types)
    mode_ok = (
        len(input_types) == count
        and ((input_mode == "mixed" and expected_types == VALID_INPUT_TYPES)
             or (input_mode == "screenshot" and expected_types == {"screenshot"})
             or (input_mode == "verbal" and expected_types == {"verbal"}))
    )
    report.add("TXT.input.mode", "ERROR", mode_ok,
               "input_mode 必须与 inputs[].input_type 一致；mixed 必须同时含 screenshot 和 verbal"
               if not mode_ok else f"输入模式={input_mode}")
    unique_ok = len(ids) == count == len(set(ids)) and len(files) == count == len(set(files))
    report.add("TXT.one_to_one", "ERROR", unique_ok,
               "每项输入必须有唯一 id/text_ui_file，且不同输入不能共用文本图"
               if not unique_ok else "输入与独立文本图一一对应")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate 0: input-to-text-UI parity and confirmation")
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
