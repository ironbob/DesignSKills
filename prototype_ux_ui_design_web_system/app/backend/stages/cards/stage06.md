# 阶段 6：设计系统（任务卡）

把选中方向落成完整 token + 最小组件集 + 规则。等价 Figma 的 variables+组件库搭建。**完成标志：搭一个新屏不需要新组件。**

输入：阶段 5 选中的 tile + 阶段 4 结构决策 + 当前项目画布。

## 产出

**1. `06-tokens.json`（★机器可读契约，高保真与规格导出直接消费）：**

```json
{
  "name": "<方向名>", "version": "1.0",
  "canvas": {"width": <项目画布宽>, "height": <项目画布高>, "note": "=项目目标画布，全流程唯一画布来源；长内容内部滚动，禁止整屏长高"},
  "color": {"bg": "", "surface": "", "line": "", "ink": "", "ink_weak": "",
            "accent": "", "accent_ink": "", "focus_surface": "", "danger": ""},
  "semantic": {"<态>": {"color": "", "symbol": "", "label": ""}},
  "type": {"family_title": "", "family_body": "", "family_focus": "",
           "scale": {"caption": 12, "body": 14, "body_l": 16, "title": 20, "display": 28},
           "focus_size": 32},
  "space": [8, 16, 24, 32, 48],
  "radius": {"small": 6, "card": 8, "panel": 12},
  "touch": {"min_height": 48, "min_width": 56, "primary_min_width": 88, "max_keys_per_bar": 5},
  "rules": ["…十二条底版见下…"]
}
```

- `focus_surface`=核心内容专用底（全 App 唯一最亮，只给核心内容区）；
- `semantic`=领域语义态（每个 {color, symbol, label} 三元组，**符号+文字强制**）；
- **rules 十二条底版**（逐条保留）：核心区恒亮／一屏一强调／语义色只干语义／符号+文字不只靠色／标题族只做标题／8 倍数留白／画布锁定=项目目标画布／触控高宽下限+主键宽+每行键数上限／核心内容字号下限／"无信号"态≠"坏"态（不进语义三色）／危险操作深色+二次确认／浮层居中覆盖层。

**2. `06-design-system.html`（给人看的规范样张）**：色板（含语义色）→ 刻度表 → 组件族样例（按钮 3–4 式/列表行/分组头/分段/字段/面板/卡片/**核心内容族**/顶栏/徽章）→ 原则。

## 完成标志（L1 gate）

tokens schema 校验（必填键/三元组完整/规则十二条齐/canvas=项目画布）；样张含组件族章节且过 HTML gate。

## 工具化要点

- 决策类型=confirm（重点盯：语义色可辨度、危险色区分、密度规则）。事实类：auto 过双层 gate 自动推进。
- **落库时机：tokens.json = 项目的 token 表**，后续所有高保真任务的只读输入。
