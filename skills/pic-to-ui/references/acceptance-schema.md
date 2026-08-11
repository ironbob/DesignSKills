# acceptance.json 契约

`acceptance.json` 是三重验收的机器可读事实源，`report.md` 是它的人读解释。两者都必须存在，
并通过 `scripts/validate_acceptance.py <acceptance.json> <delivery.json> <artifact-root>
[--repair-audit <repair-audit.json>]`（Gate 3）。

```json
{
  "meta": {"mode": "create", "report": "report.md"},
  "gates": [
    {"name": "text-ui-confirmation", "status": "passed", "evidence": "Gate 0 confirmed exit 0; user confirmation recorded"},
    {"name": "blueprint", "status": "passed", "evidence": "Gate 1 exit 0"},
    {"name": "coding-path", "status": "passed", "evidence": "direct_ui revision 1; actual scope rechecked"},
    {"name": "delivery", "status": "passed", "evidence": "Gate 2 exit 0"}
  ],
  "render_diff": {
    "status": "executed",
    "reference": "evidence/reference.png",
    "after": "evidence/after.png",
    "comparison": "evidence/diff.png",
    "result": "matched"
  },
  "self_check": [
    {"dimension": "structure", "status": "passed", "evidence": "N1-N8 对齐"},
    {"dimension": "entries", "status": "passed", "evidence": "ENTRY-01..04 对账"},
    {"dimension": "dimensions", "status": "passed", "evidence": "DIM-01..03 对账"},
    {"dimension": "style", "status": "passed", "evidence": "字体/颜色/描边复核"},
    {"dimension": "icons", "status": "passed", "evidence": "ICON-01..03 语义复核"},
    {"dimension": "states", "status": "passed", "evidence": "STATE-01 复核"},
    {"dimension": "a11y", "status": "passed", "evidence": "标签与触控区域复核"}
  ],
  "proportion_check": {
    "reference_viewport": {"width_px": 390, "height_px": 844},
    "rendered_viewport": {"width_px": 390, "height_px": 844},
    "items": [
      {"dimension_id": "DIM-01", "reference": {"numerator_px": 44, "denominator_px": 72},
       "rendered": {"numerator_px": 43, "denominator_px": 72}, "deviation_pct": 2.27,
       "tolerance_pct": 5, "status": "passed", "evidence": "同设备截图量取主按钮高/底栏高"}
    ]
  },
  "tests": [
    {"command": "xcodebuild ...", "result": "passed", "evidence": "exit 0"}
  ],
  "flags": [],
  "waivers": []
}
```

## 约束

- repair 模式的 `gates` 还必须含 `repair-audit` 与 `repair-closure`。
- 所有模式必须含 `text-ui-confirmation`，evidence 回链 Gate 0 confirmed 与真实用户确认；模型不能自行确认。
- 所有模式必须含 `coding-path`，记录 assessment revision、direct_ui|arch_first 和实现后范围复核。
- `render_diff.status=executed` 时，reference/after/comparison 必须是 artifact-root 内真实文件，
  result 为 `matched|improved|flagged`。
- 无法渲染时写 `status=unavailable + reason + result=unverified`，不得声称 matched。
- `self_check` 必须恰实覆盖 structure/entries/dimensions/style/icons/states/a11y 七维，逐项有证据。
- `proportion_check` 是控件比例验收的硬性记录：必须包含 reference/rendered viewport，且 `items[]` 必须与 `delivery.dimensions[]` 的 `DIM-##` 一一对应。每项使用同类参照物记录 `numerator_px / denominator_px`，并写出脚本可复算的 `deviation_pct`。
- 默认 `tolerance_pct=5`；受系统安全区、动态字体或文字换行影响时可逐项放宽至最多 8%，并在 evidence 说明。`status=passed` 时偏差不得超过容差；`flagged|unverified` 必须关联真实 `flag_ids[]`。不得因为控件“看起来差不多”省略或通过比例项。
- diff 为 unavailable/improved/flagged，或某项自检为 improved/flagged 时，必须用 `flag_ids[]`
  关联到 `flags[]` 的真实 id。
- `tests` 非空；失败测试阻断交付，未运行项写 `not_run` 及证据/原因。
- `flags[]` 每项含唯一 id、priority、reason、next_action；任何未关闭 P0 flag 阻断 Gate 3。
- delivery 和 repair-audit 中所有 flagged id 必须出现在 `flags[]`；所有 waived id 必须出现在
  `waivers[]`，并保留 reason/evidence。模型不得在最终报告中漏掉或洗掉标红与用户豁免。
- 所有文件路径均相对 artifact-root，禁止越界引用或伪造证据。
