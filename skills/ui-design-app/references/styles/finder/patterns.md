# Finder 风格 · 布局与交互模式

> 窗口解剖、降级、失活、浮层、键盘、反模式、工程坑。做任何新界面前先读对应节。

## 1. 窗口解剖

```text
┌──────────────────────────────────────────────────────┐
│ 标题栏 48px（chrome 材质）· 内嵌标签栏 · 红绿灯       │  z:30
├──────────┬───────────────────────────────────────────┤
│ dock 内缩 │ 工具栏条 min56px（透明）· [胶囊][路径][搜索胶囊] │
│ ┌──────┐ ├───────────────────────────────────────────┤
│ │侧边栏 │ │  内容画布 canvas（列表/预览/编辑器）        │
│ │卡片14 │ │                                           │
│ │圆角   │ │                                           │
│ └──────┘ ├───────────────────────────────────────────┤
│  10px    │ 状态栏 min24px（chrome 材质 + 上发丝线）    │
└──────────┴───────────────────────────────────────────┘
```

- 标题栏：`hiddenInset` 式（Electron `titleBarStyle`）或自绘等价；chrome 材质 +
  blur(18px) saturate(180%)；标签栏**共享标题栏**，不另起一行（内嵌区 44px）。
- 侧边栏：dock 容器与窗口左/上/下边缘内缩 10px；卡片 12-16px 圆角材质浮于主内容之上；
  宽 240-360 可拖；**与主内容不画硬竖线**；分割器 10px 热区、视觉仅 1px 低对比线
  （上下 14px 内缩），hover/拖拽转 55% 蓝一线。
- 工具栏：条透明，控件成组入胶囊（materials §3），组间 ≥10px；三段式
  左=位置/返回，中=主输入（搜索/路径），右=视图切换/动作/更多。
- 内容画布：`--finder-canvas`；列表/预览/编辑器都坐同一画布。

## 2. 响应式降级（阈值表）

| 窗宽 | 行为 |
| --- | --- |
| < 980px | 工具栏次要文字操作收进"更多"菜单 |
| < 900px | 侧边栏整卡转 absolute **浮层覆盖**（不压缩主内容；与任务抽屉同语义） |
| < 840px | 搜索收为图标，点开覆盖式搜索框 |

任何宽度下控件不得重叠、换行、截断。

## 3. 窗口失活语义（Finder 关键行为）

监听窗口 focus/blur，根节点挂 `is-window-inactive`：

- 侧边栏选中行：蓝底白字 → **灰底（`sidebar-inactive-sel`）+ 蓝字蓝图标**（暗色蓝提亮 `#7cb4ff`）。
- 文本选区/光标：降饱和灰蓝；光标停闪、转灰空心（行定位保持可辨）。
- 原则：**降级不消失**——失焦时仍能看清"哪里被选中"，只是不再宣示焦点所有权。

## 4. 选中态语言（全 app 一致）

- 图标底浅灰 + 文字底系统蓝（components §3）；列表/网格/分栏三视图同一套。
- 拖拽悬停目标 ≠ 选中：独立高亮语言（蓝色内描边 + 微光）。
- 元数据列不参与高亮。

## 5. NSMenu 交互

- 键盘：`↑↓` 同层移动（跳过分隔线与禁用项）；`→` 进子菜单；`←` 收起当前层（父项保持
  高亮）；`Enter` 激活；`Esc` 关整个菜单。菜单打开期间在**捕获阶段**消费按键，优先于
  全局快捷键。
- 悬停 = 键盘焦点 = 高亮，同一状态，同一蓝底白字。
- 子菜单与父行顶部对齐，与父项重叠 6px（鼠标横穿无死区）；未展开的子菜单不进 DOM。
- 定位：渲染后自测量钳制在视口内（8px 边距）；右侧空间不足时所有层级向左弹。
- 弹出动效 0.09s scale(0.97) translateY(-2px)。

## 6. 浮层家族

| 浮层 | 规格 |
| --- | --- |
| 锚定 Popover | popover 材质、12px 圆角、视口钳制；底层透过不可辨 |
| Sheet（保存/确认） | 实色感 popover 材质卡 + 居中模态遮罩；标题说结果（"保存标注后的图片"）；主按钮文案随操作（"存储副本"）；取消/主钮右对齐 32px；高级项 disclosure 展开；默认安全操作，覆盖需二次确认 |
| Quick Look 浮窗 | 空格预览：媒体 70%×70% 实色画布；**文本窗**=材质窗（materials §6），宽 `min(90%, 1200px)`、高 `clamp(420px, 遮罩区70%, 760px)`、内层 chrome 全透明、只读默认+显式编辑、⌘F 收纳搜索；打开不滚动背后列表 |
| 快速跳转/命令面板 | 键盘优先（⌘⇧P/⌘K）；居中小浮层，popover 材质；最近项列表 + 输入过滤；外点/Esc 关闭 |
| 任务抽屉 | 右侧展开 320-360（280-440 可调）；窄窗转 overlay；空态自动关闭 |

外点关闭是所有浮层默认行为；弹层打开期间如宿主有窗口拖拽区，需临时放行点击
（见工程坑 §10.1）。

### 6.1 锚定弹层防裁剪范式（2026-08-19，列表底部/卡片内菜单被裁的根治）

任何「锚在按钮/行上向下弹的菜单」都受三重威胁：祖先 `overflow: hidden` 裁剪、
祖先形成包含块使 fixed 失效（见 §10.2/10.3 的完整诱因清单）、弹层自身无钳制
越出视口。统一解法是**锚定弹层组件**（本项目 `AnchoredPopover`），四条硬规则：

1. **Teleport 到 shell 级浮层层**：`#popover-layer` 挂在应用根容器首子节点，
   `position: fixed; inset: 0; z-index: <最高浮层>; pointer-events: none`（子元素
   恢复 auto）。层在 shell 内（shell 前缀的全局样式仍然命中）、在一切裁剪/包含块
   祖先之外。QuickLook 卡片、工具栏容器、双面板 pane 都不再裁剪或劫持坐标。
   勿 teleport 到 `body`——会脱离 `.shell` 样式作用域。
2. **锚点测量定位 + 翻转**：挂载后 `anchor.getBoundingClientRect()` + 自身
   `offsetWidth/Height` 计算坐标（**勿用 getBoundingClientRect 量自身**——入场
   scale 动画期间量到的是缩放中间态）；默认锚点下方弹，下方余量不足翻上方；
   两侧都不够取空间大的一侧压缩高度 + 内滚。
3. **子菜单垂直钳制**：右键菜单的子菜单默认顶部对齐父项行，展开在菜单底部时
   必然越出视口——挂载后（函数 ref + rAF）测 `bottom`，越界上移整层；高于视口
   时 `max-height + overflow-y: auto`。
4. **外点关闭补判**：teleport 后弹层不在宿主子树内，宿主的 `rootEl.contains(target)`
   判定必须加「存续弹层注册表」查询（组件模块级 `Set<el>` + 导出
   `isInsideAnchoredPopover(node)`），否则点菜单内容被误判外点直接收起——
   capture 阶段监听拦不住，必须在判定处补。

配套细节：组件根若是 `<Teleport>`，**fallthrough attrs（class/testid/aria）不会
落到内部 div**，必须 `defineOptions({ inheritAttrs: false })` + `v-bind="$attrs"`；
高度可变的菜单自带 `max-h + overflow-auto`（翻转按压缩后高度算）；窗口 resize
要重定位（锚点 rect 随窗移动，RO 只看尺寸不看位置，需补 resize 监听）。

## 7. 键盘与焦点惯例

- 全局键盘处理用**捕获阶段拦截器，LIFO**（最后打开的浮层先消费；返回 true 才算消费）。
  子组件不要挂冒泡阶段 document keydown 与全局处理器抢。
- Esc 链按层归属：最顶层浮层先吃（输入框内清除→关浮层→关闭预览），一层一次。
- `:focus-visible` only；焦点环配方见 components §4。
- 全 app `user-select: none`（桌面感），仅输入框/可复制内容显式豁免 `user-select: text`。

## 8. 反模式清单（审计/评审即查此表）

1. 渐变按钮/渐变选中底 —— 一律实色。
2. 彩色发光阴影（glow）、硬投影。
3. hover 缩放/位移动画（transform）。
4. 导航图标上彩色（彩色只给标签圆点/状态点；导航=单色深灰线性）。
5. 列表整行高亮选中；选中态三视图不一致。
6. 开关/菜单打开态长蓝实底（违反单蓝规则）。
7. Web 风 dropdown/卡片菜单冒充 NSMenu。
8. 侧边栏与主内容之间画硬竖线；"分区卡片化"的侧边栏。
9. 移动端式底部圆形导航/大 FAB。
10. 移动端式全屏模态代替 Sheet。
11. 大写文本滥用（只允许 10px 微标题级）。
12. `background` 简写用于组件类（gradient 遮蔽 background-color，scoped 无法覆盖；用 background-color）。
13. 只靠颜色表达状态（无文字/图标补充）。
14. 禁用项用低对比度冒充（应整体降透明度 + 原因提示）。

## 9. 主题实现

- 根节点 `data-theme="dark|light"` + `color-scheme`；暗色为默认值写在 `:root`，
  亮色覆写 `[data-theme="light"]`。
- 组件**只消费语义 token**，禁止组件内写死色值/主题分支。
- 图标暗色反转用 `filter: invert(1)` 挂主题作用域。

## 10. macOS / Electron 工程坑（每条都花过真实代价）

1. **app-region 拖拽区整片吞事件**：`-webkit-app-region: drag` 区域的 pointerdown/click
   不进渲染进程，document 级外点关闭收不到标题栏点击。方案：弹层打开期间给 `<html>`
   挂标记，全局规则把 `.app-drag` 临时改 `no-drag`，引用计数归零还原。
2. **backdrop-filter 形成层叠上下文 + 包含块**：标题栏一开 blur，其内的菜单浮层伸不
   去且其后代 fixed 的定位基准变成标题栏。方案：菜单 teleport 到 shell 级浮层层
   （§6.1），或给标题栏显式 z-index:30 压过 main。**fixed 失效的完整诱因清单**：
   祖先带 `transform` / `filter` / `backdrop-filter` / `perspective` / `will-change:
   transform` / `contain: paint|layout` / `container-type` 任一即成包含块——不只
   overflow:hidden 一种，审计时逐层查。
3. **`container-type` 劫持 fixed 后代**：容器一开 containment，其内 fixed 浮层的定位基准
   变成该容器。方案：浮层移出该容器再 fixed（或统一走 §6.1 浮层层）。
4. **浮窗宽度勿用 vw**：多窗/分栏下 90vw 会溢出主区；用遮罩区实测百分比 + min()/clamp() 封顶。
5. **自绘滚动条**：必须自定义 `::-webkit-scrollbar`（原生 web 滚动条破坏观感）；
   自绘即无箭头。注意新 Chromium 可能忽略部分 ::-webkit 规则，交付前肉眼验证。
6. **动画尊重 prefers-reduced-motion**，全局降级规则收口。
7. **字体平滑**：正文 auto、图标字体 antialiased（tokens.md §2）；混用错位会"Web 味"。
8. **虚拟长列表**：行高固定（几何由 token 决定）；选中态只作用于挂载行，滚动回收后
   状态由数据层驱动；框选只查挂载项（`[data-*]` 属性）。
9. **Teleport 根组件的 attrs 透传失效**：组件根是 `<Teleport>` 时 class/data-testid/
   aria 不会落到内部元素，必须 `inheritAttrs: false` + `v-bind="$attrs"` 显式透传；
   同因，宿主外点关闭的 `contains` 判定要补弹层注册表（§6.1 第 4 条）。
10. **入场动画期间量自身尺寸**：带 scale 的 pop 动画会让 `getBoundingClientRect`
    量到缩放中间态（钳制差出几像素）；量自身用 `offsetWidth/offsetHeight`（布局
    尺寸不受 transform 影响），量锚点才用 rect。
