# 编码路径评估契约

在 blueprint 通过后、任何代码写入前生成 `change-assessment.json`，并运行
`scripts/validate_change_assessment.py`。repair 模式先完成差异审计，再基于真实 mismatch 评估。

```json
{
  "meta": {
    "mode": "repair",
    "target_screen": "OrderDetail",
    "stage": "pre_code",
    "revision": 1,
    "user_forced_arch_first": false
  },
  "estimate": {
    "production_files": 2,
    "change_size": "small",
    "ui_only": true,
    "logic_change": "none"
  },
  "evidence": [
    "OrderDetailView.swift: only spacing/color/icon mappings differ",
    "repair-audit.json: MISMATCH-01..04"
  ],
  "risk_flags": {
    "navigation_change": false,
    "state_ownership_change": false,
    "data_flow_change": false,
    "api_or_persistence_change": false,
    "new_dependency": false,
    "cross_layer_change": false,
    "shared_component_or_token_change": false,
    "multiple_screens": false,
    "architecture_role_change": false
  },
  "decision": {
    "path": "direct_ui",
    "rationale": "目标屏内纯样式和资源映射修复，无逻辑或共享影响"
  }
}
```

## 判定规则

`change_size` 按预计生产代码文件数确定：`small=1..3`、`medium=4..7`、`large>=8`。
素材文件和 pic-to-ui 交付 JSON 不计入 production_files。

只有同时满足下列条件才走 `direct_ui`：

1. 九个 `risk_flags` 全为 false；
2. `logic_change` 为 `none|local_wiring`，不得包含业务规则、状态所有权或数据流变化；
3. `change_size=small`，或者 `ui_only=true`；
4. `ui_only=true` 时 `logic_change` 必须为 `none`；
5. 用户没有显式强制使用 `$arch-first-code-gen`。

否则必须写 `path=arch_first`。用户显式要求 `$arch-first-code-gen` 时，设置
`user_forced_arch_first=true`，同时在 meta 写非空 `force_evidence`。

直接编码只允许修改评估中覆盖的目标屏局部 UI、资源和局部样式。若实现中发现文件数跨档，
或新增任一 risk flag，立即停止写入、递增 revision、重跑评估；新结论为 arch_first 时，请用户
显式调用 `$arch-first-code-gen` 后再继续。
