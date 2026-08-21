# Linear 风格 · 迁移身份

> 证据边界：以 2024 foundational redesign 为视觉基线，并用当前官方交互文档交叉验证；具体 px/hex 为 derived。详见 `evidence.md`。

## 风格命题

以中性实色、单一可配置 accent、紧凑密度和即时键盘反馈表达高频效率；不是复制 Linear 的项目管理结构。

## invariant

- 实色分层与细边框优先，无 vibrancy、毛玻璃和常驻大阴影。
- 同一主题只使用一个主 accent 承担主操作、选中、链接、焦点和进行中；默认可用 Linear-inspired 紫，常规 hover 保持中性灰。
- 控件与列表保持紧凑、低圆角、快速动效，不使用消费型大圆角和大留白。
- 高频操作具有可发现的键盘入口；命令、菜单与按钮状态保持一致。
- 彩色业务状态收敛为小图标、圆点或文字，不铺大面积彩色底。

## adaptive

- 行高和控件高度按真实信息密度在紧凑值域内调整，不能以挤压可读性换相似度。
- kbd 提示只给真正存在的快捷键；没有快捷键时不伪造装饰 chip。
- accent 可随 Linear 的主题生成模型形成已声明变体，但必须保持单强调色纪律和足够对比。

## archetype-bound

- 图标栏 + 列表栏 + 主内容三栏仅适合高频导航/详情产品。
- `⌘K` 只有在目标已有全局动作、导航或搜索集合时采用。
- 目标为表格、树或检查器结构时保留结构，用 Linear 密度和状态语言重绘。

## source-specific

- issue、cycle、project 等领域对象及其导航不是风格要求。
- 不为了 Linear 感新增无功能的命令、快捷键或三栏结构。

## 未覆盖组件推导

使用 L0/L1/L2 实色层、1px 边框、4-8px 圆角、26-32px 高度和 100-120ms 反馈组合。默认/hover/pressed 保持灰阶，选中弱紫不反白，主操作每屏克制出现。

## 还原验收权重

`color 15 / material 15 / typography 10 / geometry 10 / spacing-density 20 / component-states 20 / motion-feedback 5 / layout-motif 5`
