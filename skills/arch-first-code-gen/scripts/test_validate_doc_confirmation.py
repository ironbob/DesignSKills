#!/usr/bin/env python3
"""Regression tests for the mandatory user-confirmation audit section."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_doc import validate


class DocumentConfirmationTests(unittest.TestCase):
    def _validate(self, confirmation: str):
        document = f"""---
feature: sample
title: Sample
stack: JVM
design_profile: light
analyzed_at: 2026-08-14
roles_count: 1
process_steps: 0
verdict: go
open_questions: 0
---
{confirmation}
## 一、模块结构图
```mermaid
flowchart TD
  A[A]
```
## 二、业务流程图
```mermaid
flowchart TD
  A[A]
```
## 三、角色职责清单
| 角色 | 职责 |
|---|---|
| A | 执行用例 |
## 四、质量属性与方案取舍
质量属性可测试；候选 ALT-1；选择 ALT-1。
## 五、设计依据
A 依据 SRP 原则。
## 六、关键接口契约
无跨角色接口。
## 七、验证证据
测试通过。
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "arch.md"
            path.write_text(document, encoding="utf-8")
            return validate(path)

    def test_missing_confirmation_section_fails(self) -> None:
        report = self._validate("")
        self.assertTrue(any("R-C1" in error for error in report.errors))

    def test_complete_confirmation_section_passes(self) -> None:
        report = self._validate(
            "## 零、用户确认记录\n"
            "- 等级：用户选择 light。\n"
            "- 方案版本：1。\n"
            "- 确认：用户在方案展示后的后续消息中确认 ALT-1。\n"
        )
        self.assertFalse(any("R-C1" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
