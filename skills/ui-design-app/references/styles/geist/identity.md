# Geist 风格 · 迁移身份

> 证据边界：本包是完整 Geist 设计系统中的 Vercel-dashboard monochrome profile；官方 Geist 还有多组语义色阶。具体离线 Token 为 derived。详见 `evidence.md`。

## 风格命题

以中性骨架、精确细线、黑白反转主操作配置和受控等宽点缀表达冷静开发者工具感；不是复制 Vercel 部署后台，也不代表完整 Geist 只有黑白灰。

## invariant

- monochrome profile 的界面骨架保持中性黑白灰；亮色细线与暗色真黑/近黑层级承担主要分区。
- 本 profile 的主操作使用黑白反转；蓝给链接、选中、焦点和进行中。其他 Geist profile 可按官方语义色阶配置。
- 卡片和面板靠细边框、轻描边影组织，不使用毛玻璃、暖灰和营销渐变。
- 等宽字体只用于代码、ID、分支、数值等机器信息，不覆盖正文。
- 状态 pill 可使用淡彩底并配文字/图标；完整 Geist 允许语义色用于其他合适组件，但本 profile 不扩展成彩色卡片体系。

## adaptive

- 表格行高、卡片密度和页面宽度按目标数据量调整，但保持冷静、中等密度和清楚细线。
- 没有技术数据的产品减少 mono 使用，不为风格感伪造代码气质。
- 主操作数量由功能层级决定，不强行保证每页出现按钮。

## archetype-bound

- 侧栏 + 页头 + 设置卡/表格适合管理后台和开发者工具。
- 状态 pill、部署表格、用量条和键值设置行只在目标有同类数据时采用。
- 普通内容页保留其结构，用 Geist 表面、主次层级和排版重绘。

## source-specific

- 部署、分支、commit、域名和用量等 Vercel 对象不是风格要求。
- 不添加无功能的页头描述、右上 CTA 或技术状态。

## 未覆盖组件推导

在本 monochrome profile 中使用中性骨架、1px 边框、6-8px 圆角、32px 控件和 120-150ms 反馈。先用排版与细线分层，再考虑阴影；语义色只用于明确状态或交互。

## 还原验收权重

`color 20 / material 20 / typography 15 / geometry 10 / spacing-density 10 / component-states 15 / motion-feedback 5 / layout-motif 5`
