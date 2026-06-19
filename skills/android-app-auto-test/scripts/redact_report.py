#!/usr/bin/env python3
import argparse
import pathlib
import re


PATTERNS = [
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(access[_-]?token['\"=:\s]+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(refresh[_-]?token['\"=:\s]+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(cookie:\s*)[^\n]+"), r"\1[REDACTED]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL_REDACTED]"),
    (re.compile(r"(?<!\d)(?:\+?\d[\d -]{8,}\d)(?!\d)"), "[PHONE_REDACTED]"),
]


def redact(text: str) -> str:
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Redact secrets and personal data from Android test reports.")
    parser.add_argument("paths", nargs="+", help="Files to redact in place")
    args = parser.parse_args()

    for raw_path in args.paths:
        path = pathlib.Path(raw_path)
        text = path.read_text(encoding="utf-8")
        path.write_text(redact(text), encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
