# Finder 风格 · 材质（vibrancy）配方

> 材质是这套风格的灵魂：半透明系统灰 + backdrop blur + 发丝边 + 柔和双影。
> 所有 `backdrop-filter` 必须同时写 `-webkit-` 前缀。
> 完整变量块见 `assets/styles/finder/tokens.css` 的材质段。

## 通用规则

1. **发丝边框**：一律 1px，透明度 0.08-0.14；禁止厚边框与卡片感。
2. **柔和双影**：一大一小两层投影；禁止硬投影、禁止彩色发光。
3. **暗色抬不透明度**：暗色底透字更明显，材质不透明度比亮色抬高 0.02-0.06，
   阴影加深保证深底上"浮起"可辨。
4. **blur 都配 saturate**：blur 把背后颜色糊淡，saturate(140-180%) 拉回饱和。
5. **性能**：backdrop-filter 形成层叠上下文（见 patterns.md 工程坑）；同屏大面积
   材质层 ≤ 2-3 张。

## 七张表面

### 1. 窗口 chrome（标题栏/工具栏条/状态栏）

```css
background: var(--finder-chrome);            /* 亮 rgba(255,255,255,.76) / 暗 rgba(40,40,42,.92) */
backdrop-filter: saturate(180%) blur(18px);
border-bottom: 1px solid var(--finder-divider);
```

### 2. 侧边栏浮层卡片（与主内容形成高低层级）

```css
background: var(--finder-sidebar);           /* 亮 rgba(248,248,250,.90) / 暗 rgba(34,34,38,.92) */
backdrop-filter: saturate(150%) blur(20px);
border: 1px solid var(--finder-sidebar-border);   /* 亮 rgba(0,0,0,.10) / 暗 rgba(255,255,255,.10) */
border-radius: 14px;
box-shadow: var(--finder-sidebar-shadow);    /* 见 tokens.md 阴影表 */
overflow: hidden;                            /* 内容必须被圆角裁剪 */
```

配套：dock 容器与窗口左/上/下边缘内缩 10px；与主内容**不画硬竖线**，分割只靠阴影与留白。

### 3. 工具栏浮动胶囊（控件托盘）

```css
background: var(--finder-capsule-bg);        /* 亮 rgba(255,255,255,.72) / 暗 rgba(52,52,55,.72) */
backdrop-filter: blur(20px) saturate(160%);
border: 1px solid var(--finder-capsule-border);    /* 亮 rgba(0,0,0,.08) / 暗 rgba(255,255,255,.10) */
border-radius: 18px;                         /* 36px 高即全圆端 */
box-shadow: var(--finder-capsule-shadow);
padding: 3px;
```

工具栏条本身**透明**（无底色无底边框）；每组控件一枚胶囊，组间留白 ≥10px。

### 4. 锚定 Popover（标签总览/下拉面板类）

```css
background: var(--finder-popover-bg);        /* 亮 rgba(248,248,250,.94) / 暗 rgba(42,42,44,.96) */
backdrop-filter: blur(20px) saturate(150%);
border: 1px solid var(--finder-popover-border);    /* 亮 rgba(0,0,0,.12) / 暗 rgba(255,255,255,.14) */
border-radius: 12px;
box-shadow: var(--finder-popover-shadow);
```

要点：不透明度 ≥0.94，**底层内容透过时不可辨认**（防穿透）。

### 5. NSMenu（右键菜单，所有层级一致）

```css
background: var(--menu-bg);                  /* 亮 rgba(250,250,252,.80) / 暗 rgba(44,44,48,.72) */
backdrop-filter: blur(28px) saturate(1.8);
border: 1px solid var(--menu-border);
border-radius: 12px;
box-shadow: var(--menu-shadow);              /* 双影，见 tokens.md */
padding: 5px 0;
```

### 6. Quick Look 材质窗（空格预览浮窗）

```css
background: var(--quicklook-bg);             /* 亮 rgba(248,248,250,.94) / 暗 rgba(40,40,42,.94) */
backdrop-filter: blur(20px) saturate(150%);
border: 1px solid var(--quicklook-border);   /* 亮 rgba(0,0,0,.12) / 暗 rgba(255,255,255,.14) */
border-radius: 12px;
box-shadow: var(--quicklook-shadow);
```

要点：头部/内容/状态栏同属**一张材质**——窗内实色底全部透明化（`background: transparent`）。

### 7. 媒体半透明控件（视频播放器控制条，暗色系专用）

```css
background: rgba(35, 35, 37, 0.72);
backdrop-filter: blur(20px) saturate(140%);
border: 1px solid rgba(255, 255, 255, 0.10);
border-radius: 12px;
```

宽度 = 视频宽 - 16px；内边距 7-8px；右上加 10px 圆角小工具片同材质。

## 表面选择决策

| 要做的界面 | 用哪张 |
| --- | --- |
| 常驻 chrome（标题/工具/状态条） | 1 chrome |
| 侧边导航 | 2 侧边卡片 |
| 工具栏上的控件分组 | 3 胶囊 |
| 点击锚点弹出的面板 | 4 popover |
| 右键菜单/上下文菜单 | 5 NSMenu（必须，不用 popover 冒充） |
| 空格预览/快速查看浮窗 | 6 QuickLook |
| 媒体播放控件 | 7 媒体控件 |
