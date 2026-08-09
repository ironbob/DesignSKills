# repair-audit.json 契约

`repair-audit.json` 只用于 `blueprint.meta.mode = repair`。`validate_repair.py` 在编辑前后分两个
phase 校验同一份文件；必须传 `--blueprint blueprint.json --code-root <root>`，同时验证 target_ids
与真实代码锚点。

## 顶层

```json
{
  "meta": {
    "mode": "repair",
    "target_screen": "OrderDetail",
    "reference_screenshots": ["reference/order-detail.png"],
    "implementation_root": ".",
    "baseline": {
      "status": "captured",
      "evidence": "evidence/before.png"
    }
  },
  "mismatches": []
}
```

`meta.baseline.status` 只能为：

- `captured`：已有当前实现截图，`evidence` 必填。
- `provided`：用户提供了当前效果图，`evidence` 必填。
- `unavailable`：无法渲染或没有当前效果图，`reason` 必填。此时可以做静态审计，但不能声称视觉 `matched`。

## mismatches[]

每个差异使用稳定 id，并关联目标 blueprint：

```json
{
  "id": "MISMATCH-01",
  "category": "dimension",
  "priority": "P1",
  "target_ids": ["DIM-03", "N4"],
  "screenshot_evidence": "shot#1:bottom CTA height about 0.14x screen width",
  "current_evidence": "evidence/before.png: bottom CTA is visibly shorter",
  "diagnosis": "ButtonStyle applies compact vertical padding",
  "current_code_anchor": {
    "file": "OrderDetailView.swift",
    "widget": "CheckoutButtonStyle"
  },
  "status": "open"
}
```

必填字段：

| 字段 | 约束 |
|---|---|
| `id` | 唯一、非空，建议 `MISMATCH-##` |
| `category` | `structure \| entry \| icon \| dimension \| style \| state \| bitmap` |
| `priority` | `P0 \| P1 \| P2` |
| `target_ids[]` | 至少一个 blueprint id；若属于全局环境差异，可用 `META` |
| `screenshot_evidence` | 截图锚点和目标描述，不能只写“看起来不对” |
| `current_evidence` | 当前渲染或代码证据 |
| `diagnosis` | 可操作的根因判断，不是修复方案口号 |
| `current_code_anchor` 或 `anchor_reason` | 找到现有落点就写 `{file, widget}`；找不到就解释 |
| `status` | 审计阶段为 `open`；闭环阶段为 `resolved \| flagged` |

## resolved

```json
{
  "status": "resolved",
  "resolution": {
    "summary": "Increase shared CTA vertical padding and preserve loading binding",
    "code_anchor": {
      "file": "OrderDetailView.swift",
      "widget": "CheckoutButtonStyle"
    }
  },
  "verification": {
    "method": "render_diff",
    "result": "matched",
    "evidence": "evidence/after.png + evidence/diff.png"
  }
}
```

`verification.method`：

- `render_diff`：同配置 before/after 与参考图比较，证据最强。
- `visual_inspection`：有 after 渲染并人工/模型逐项比较。
- `static_inspection`：只检查代码。只能支持行为/结构事实；视觉差异不得用它声明 `matched`，应标红为未验证。

`verification.result`：

- `matched`：证据显示该项已对齐。

`improved` 仍表示存在残差，不能写成 resolved；继续迭代，或改为 `flagged` 并写明 reason、impact、
next_action。闭环 Gate 不接受 unverified 作为 resolved。

## flagged

```json
{
  "status": "flagged",
  "reason": "Simulator toolchain unavailable; code was adjusted but no after render can verify spacing",
  "impact": "CTA vertical spacing may still differ",
  "next_action": "Run screenshot comparison on iPhone 16 simulator"
}
```

`reason` 必填；`impact` 和 `next_action` 强烈建议填写，并汇总到 `report.md`。

## 证据纪律

- 路径必须指向真实存在的产物；如果证据是文字检查，明确写为文字，不伪造文件路径。
- 基线为 `unavailable` 时，所有纯视觉 mismatch 都不能用 `static_inspection + matched` 关闭。
- 一项修改可关闭多个 mismatch，但每项都要独立记录验证结果。
- after 截图的设备、主题、字体缩放、语言或系统栏与参考图不同，要把环境差异写进证据和 report。
