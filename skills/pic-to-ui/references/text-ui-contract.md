# 文本 UI 图契约与确认门

文本 UI 图是 pic-to-ui 的第一份产物。它把每张截图的可见空间结构画成等宽字符图，让用户在蓝图、架构和代码之前确认“看懂的页面是不是同一个页面”。它不替代后续 `blueprint.json`。

## 一、一张截图对应一个文件

先枚举本次全部输入截图。每张截图必须有且只有一个独立的 `.txt` 或 `.md` 文本图文件：

```text
pic-to-ui/2026-08-09-checkout/
├── text-ui-manifest.json
└── text-ui/
    ├── SHOT-01-default.txt
    └── SHOT-02-error.txt
```

即使多张截图属于同一屏的不同状态，也不能合并到同一文本图。文件名使用稳定 screenshot id 和状态名；不要覆盖原截图。

## 二、文本图画法

使用等宽字符表达真实空间关系，而不是写一段 prose 或元素清单：

```text
┌──────────────────────────────┐
│ 09:41                  100%  │
├──────────────────────────────┤
│ [icon:back]    订单详情      │
├──────────────────────────────┤
│ ┌──────────────────────────┐ │
│ │ [bitmap:商品主图]         │ │
│ └──────────────────────────┘ │
│ 商品名称                     │
│ ¥ 128.00                     │
│                              │
├──────────────────────────────┤
│        [ 立即支付 ]          │
└──────────────────────────────┘
```

必须遵守：

- 用方框、分隔线、缩进和空白表达容器、层级、对齐和大致占比；
- 可辨识文字按截图写出；无法可靠辨识时写 `[text: unreadable]`，不得脑补；
- 图标写 `[icon:<语义>]`，位图写 `[bitmap:<语义>]`，输入框/按钮/Tab 要画出边界；
- 系统栏、底部栏、浮层、滚动边界和截图可见状态按实际存在绘制；
- 不写 SwiftUI/Compose/CSS 等实现细节，不把推断出的隐藏页面或交互画成截图事实；
- 图后可用少量 `Notes:` 标记不确定项，但 Notes 不能代替空间图。

文本图的宽高是相对表达，不要求逐像素等比例；关键是结构、顺序、层级、主要对齐和可见入口不丢失。

## 三、`text-ui-manifest.json`

```json
{
  "meta": {
    "screen": "checkout",
    "source_count": 2,
    "text_ui_count": 2
  },
  "screenshots": [
    {
      "id": "SHOT-01",
      "source": "checkout-default.png",
      "state_label": "default",
      "text_ui_file": "text-ui/SHOT-01-default.txt",
      "revision": 1,
      "confirmation": {
        "status": "pending",
        "confirmed_by": null,
        "evidence": null
      }
    },
    {
      "id": "SHOT-02",
      "source": "checkout-error.png",
      "state_label": "error",
      "text_ui_file": "text-ui/SHOT-02-error.txt",
      "revision": 1,
      "confirmation": {
        "status": "pending",
        "confirmed_by": null,
        "evidence": null
      }
    }
  ]
}
```

约束：

- `source_count == text_ui_count == screenshots.length`；
- screenshot id、source、text_ui_file 均唯一；每个文件真实存在且不能越出 artifact root；
- `revision` 为正整数；用户要求改图后递增，并把确认重置为 `pending`；
- `confirmation.status` 为 `pending | user_confirmed | rejected`；
- `user_confirmed` 时必须同时有 `confirmed_by: user` 和能指向用户原话/本轮消息的非空 `evidence`；不得由模型自行代签。

## 四、两阶段校验和交互硬门

生成所有文本图后运行草稿检查：

```bash
python3 <skill-dir>/scripts/validate_text_ui.py text-ui-manifest.json --phase draft --artifact-root <artifact-root>
```

通过后，在回复中逐张展示文本图并给出对应文件路径，请用户确认。此时必须结束当前工作轮次；不得继续生成 blueprint、repair audit、架构设计或代码。

用户明确确认全部文本图后，逐条写入 `user_confirmed` 与 evidence，再运行：

```bash
python3 <skill-dir>/scripts/validate_text_ui.py text-ui-manifest.json --phase confirmed --artifact-root <artifact-root>
```

只有 confirmed phase exit 0 才能进入后续流程。部分确认时，已确认项可保留，未确认项仍阻断；用户否决时只修改对应文本图、递增 revision、重新展示并等待确认。
