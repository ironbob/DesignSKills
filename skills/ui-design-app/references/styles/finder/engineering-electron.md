# Finder 风格 · Electron 与浮层工程手册

> 只在弹层裁剪、fixed 定位异常、Teleport、Electron 拖拽区、虚拟列表或 Chromium
> 渲染问题出现时加载。普通布局和组件实现不要读取本文件。

## 章节索引

- §1 锚定弹层四条硬规则
- §2 Electron 与 Chromium 工程坑

## 1. 锚定弹层四条硬规则

锚定菜单会同时受到祖先裁剪、fixed 包含块和视口越界影响。统一使用锚定弹层组件：

1. **Teleport 到 shell 级浮层层**：把 `#popover-layer` 放在应用根容器首子节点，使用
   `position: fixed; inset: 0; z-index: <最高浮层>; pointer-events: none`，子元素恢复
   `pointer-events: auto`。浮层留在 shell 内以保留样式作用域，同时离开裁剪祖先。
2. **测量锚点并翻转**：用 `anchor.getBoundingClientRect()` 测锚点，用
   `offsetWidth/offsetHeight` 测弹层自身。下方不足时翻到上方；两侧都不足时选择空间较大
   的一侧，压缩高度并启用内部滚动。
3. **钳制子菜单**：子菜单挂载后测量 bottom，越界时整体上移；仍高于视口时设置
   `max-height` 和 `overflow-y: auto`。
4. **补充外点判定**：Teleport 后宿主的 `contains(target)` 不再覆盖弹层。维护存续弹层
   `Set<HTMLElement>`，在外点关闭判断中调用 `isInsideAnchoredPopover(node)`。

Teleport 根组件必须使用 `defineOptions({ inheritAttrs: false })` 并把 `$attrs` 显式绑定到
内部 DOM。窗口 resize 要重新定位；ResizeObserver 只检测尺寸，不检测锚点位置变化。

## 2. Electron 与 Chromium 工程坑

1. **app-region 吞事件**：`-webkit-app-region: drag` 区域的 pointerdown/click 不进入渲染
   进程。弹层打开期间给 `<html>` 加标记，将 `.app-drag` 临时改为 `no-drag`，用引用计数还原。
2. **backdrop-filter 建立层叠上下文和包含块**：菜单应 Teleport 到 shell 浮层层；标题栏
   显式使用 `z-index: 30`。祖先的 `transform`、`filter`、`backdrop-filter`、
   `perspective`、`will-change: transform`、`contain: paint|layout`、`container-type`
   都可能改变 fixed 定位基准。
3. **container-type 劫持 fixed**：把浮层移出 containment 容器再使用 fixed。
4. **浮窗宽度不用 vw**：多窗或分栏场景按遮罩区实测尺寸使用百分比、`min()` 或 `clamp()`。
5. **自绘滚动条需实测**：Chromium 版本可能忽略部分 `::-webkit-scrollbar` 规则。
6. **统一 reduced motion**：全局收口 `prefers-reduced-motion` 降级。
7. **字体平滑分工**：正文使用 auto，图标字体使用 antialiased。
8. **虚拟列表由数据驱动状态**：固定行高；挂载行只呈现数据状态；框选只查询已挂载项。
9. **Teleport attrs 透传**：显式绑定 class、data-testid 和 aria；外点判定同时查询弹层注册表。
10. **动画期间测布局尺寸**：弹层自身使用 offsetWidth/offsetHeight，锚点才使用 rect，避免
    scale 动画导致测量偏差。
