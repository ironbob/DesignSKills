# 文本 UI 图契约与确认门

文本 UI 图是 pic-to-ui 的第一份产物。它可由截图、用户口述，或两者混合生成；目标是在蓝图、架构和代码之前，让用户确认“理解的页面是不是同一个页面”。它不替代后续 `blueprint.json`。

## 一、一个输入状态对应一个文件

先把输入拆为可独立确认的屏幕或可见状态。每项输入必须有且只有一个独立 `.txt` 或 `.md` 文本图文件：截图使用 `SHOT-##`，口述使用 `DESC-##`。同一屏的不同状态也不能合并。

```text
pic-to-ui/2026-08-12-order/
├── text-ui-manifest.json
└── text-ui/
    ├── SHOT-01-default.txt
    └── DESC-01-empty.txt
```

## 二、文本图画法

使用等宽字符表达空间关系，而不是 prose 或元素清单：

```text
┌──────────────────────────────┐
│ [icon:back]    订单详情       │
├──────────────────────────────┤
│ ┌──────────────────────────┐ │
│ │ [bitmap:商品主图]         │ │
│ └──────────────────────────┘ │
│ 商品名称                     │
│ ¥ 128.00                     │
├──────────────────────────────┤
│        [ 立即支付 ]          │
└──────────────────────────────┘
```

- 用方框、分隔线、缩进和空白表达容器、层级、对齐与大致占比；输入框、按钮、Tab 必须画出边界。
- 截图中可辨识文字按原文写；无法可靠辨识时写 `[text: unreadable]`。
- 口述中明确说出的文字按原文写；未说出的文字、尺寸、颜色、图标、状态写 `[unspecified: <what>]`，不得脑补为事实。
- 图标写 `[icon:<语义>]`，位图写 `[bitmap:<语义>]`；系统栏、底栏、浮层与滚动边界仅在输入明确可见或明确描述时绘制。
- 图后可用少量 `Notes:` 标明推断、冲突或待确认项；Notes 不能代替空间图，也不能藏入未说明的产品需求或实现细节。

口述模式应直接根据用户当前消息作图，不应先索要截图、技术栈或实现方案。描述含多个可独立确认的屏幕/状态时，先拆为多个 `DESC-##` 文本图；不能可靠拆分时，先按一个 `DESC-01` 作图并在 Notes 标明边界不确定。

## 三、`text-ui-manifest.json`

```json
{
  "meta": {
    "screen": "订单详情",
    "input_mode": "mixed",
    "input_count": 2,
    "text_ui_count": 2
  },
  "inputs": [
    {
      "id": "SHOT-01",
      "input_type": "screenshot",
      "source": "order-default.png",
      "state_label": "default",
      "text_ui_file": "text-ui/SHOT-01-default.txt",
      "revision": 1,
      "confirmation": {"status": "pending", "confirmed_by": null, "evidence": null}
    },
    {
      "id": "DESC-01",
      "input_type": "verbal",
      "verbal_input": "空状态：顶部标题订单，中央是空盒子图标和暂无订单，底部有去逛逛按钮",
      "state_label": "empty",
      "text_ui_file": "text-ui/DESC-01-empty.txt",
      "revision": 1,
      "confirmation": {"status": "pending", "confirmed_by": null, "evidence": null}
    }
  ]
}
```

约束：

- `input_mode` 只能为 `screenshot | verbal | mixed`，并且必须与 `inputs[].input_type` 一致；
- `input_count == text_ui_count == inputs.length`；id 和 `text_ui_file` 均唯一，文件必须在 artifact root 内真实存在；
- screenshot 输入需要非空 `source` 且 id 为 `SHOT-##`；verbal 输入需要逐字保留的非空 `verbal_input` 且 id 为 `DESC-##`；
- `revision` 为正整数。用户要求调整时递增 revision、重置确认状态为 `pending`；
- `confirmation.status` 为 `pending | user_confirmed | rejected`。`user_confirmed` 必须有 `confirmed_by: user` 和能指向用户原话的非空 `evidence`，模型不得代签。

## 四、两阶段校验和交互硬门

```bash
python3 <skill-dir>/scripts/validate_text_ui.py text-ui-manifest.json --phase draft --artifact-root <artifact-root>
```

draft 通过后，逐项展示文本图和路径并停止当前工作轮次，等待明确确认；不得继续蓝图、repair audit、架构或代码。确认后填写 evidence 并运行：

```bash
python3 <skill-dir>/scripts/validate_text_ui.py text-ui-manifest.json --phase confirmed --artifact-root <artifact-root>
```

只有 confirmed phase exit 0 才可进入后续流程。部分确认仍阻断；被否决的项只修订对应文本图、递增 revision、重新展示。口述模式中，`[unspecified:*]` 的存在不是失败，但它们必须在确认或后续蓝图中保持可追溯，不能默默变成既定视觉细节。
