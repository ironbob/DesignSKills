# EPPS → 可点击 HTML 原型渲染规范

> 配合 Checklist 第 5、8、9 步。HTML 是 EPPS 的机械投影：不新增页面、不新增 zone、不新增跳转。交付前必须运行 `scripts/audit_html_projection.py prototype.md prototype.html`。

---

## 一、硬性原则

1. **单一自包含文件**：所有 CSS/JS 内联，双击即可打开。
2. **手机框优先**：默认 390×844 移动端框；桌面需求另行声明。
3. **严格投影**：每个 `<section>` 对应一个 `page.id`；每个 `.zone` 对应一个 `density.zones[]`；每个辅助元素对应一个 `assistive_elements[]`；每个 `data-target` / `data-host` / `data-behavior` 对应 spec 中的 primary、secondary、assistive、jump、back 或 tab。
4. **示例数据同源**：页面文案从 `sample_state` 投影；不要在 HTML 中临时发明另一套年级、课程、进度。
5. **原型非视觉稿**：使用中性灰 + 单一强调色，只表达结构和跳转。

---

## 二、EPPS 字段 → HTML 标记

| EPPS 字段 | HTML 标记 | 要求 |
|-----------|-----------|------|
| `page.id` | `<section class="screen" id="<id>">` | 普通页面必须是 section |
| `page.level` / `page.type` | `data-level` / `data-type` | 值必须等于 spec |
| `navigation.tab_bar` | `data-tabbar="true|false"` | `tab_bar_mode: hidden` 时全部 false |
| `density.zones[]` | `.zone[data-zone-id][data-zone-kind]` | 数量、顺序、id、kind 必须与 spec 一致 |
| `assistive_elements[]` | `[data-assistive-id][data-assistive-kind]` | 引导/帮助不得渲染为主内容 `.zone`；按 `element_contract.surface` 渲染为 coachmark/bottom_sheet/inline/modal |
| `primary_action.target` | `.btn-primary[data-target]` 或 `data-behavior` | target 为 page/host/behavior 时分别使用正确属性 |
| `secondary_actions[]` | `.btn-sec` / content 内按钮 / inline 按钮 | 按 `placement` 只渲染一处 |
| `navigation.back_target` | `.back[data-target]` 或 `.back[data-host]` | host_anchor 用 `data-host`，不调用 `go()` |
| `jumps[]` | 对应元素的 `data-target` / `data-host` / `data-behavior` | 不得出现 spec 外跳转 |
| `type==modal` | `.modal-mask#<page.id>` 或 `<section id="<page.id>">` | 必须能关闭，且也要投影 modal 的 zones |

---

## 三、zone.kind → HTML 模板

| kind | 投影为 | 内容来源 |
|------|--------|----------|
| `hero_card` | `.continue-card` / `.today-card` | `primary_action` + `sample_state` |
| `quick_entries` | `.quick-row > .quick` | `secondary_actions` 或显式入口 |
| `badge_strip` | `.progress-row > .badge` | `progress.elements` + `sample_state` |
| `word_card` | `.word-head` + `.gloss` + `.ex` | `sample_state.example_word` |
| `option_list` | `.q-stem` + `.opt` + `.feedback-panel` | 题干、选项、即时反馈 |
| `input_block` | `.text-in` + `.feedback-panel` | 输入题 |
| `row_list` | `.row` 列表 | 列表项 |
| `chapter_tree` | `.chapter` / `.row` | 章节、状态 |
| `mastery_bar` | `.mastery` | 掌握度 |
| `score_ring` | `.score-ring` | 成绩百分比 |
| `stat_grid` | `.stat-grid` | 统计值 |
| `progress_strip` | `.bar-track` | 完成度 |
| `hint_block` | `.placeholder` | 提示文本 |
| `text_block` | `.placeholder` | 通用文本 |

新增 kind 前必须同步 `epps-schema.md`、`validation-rules.md`、本表和页面库示例。

### element_contract.surface → HTML 承载

| surface | HTML 承载 |
|---------|-----------|
| `main_content` | `.zone[data-zone-id][data-zone-kind]` |
| `coachmark` | `.coachmark[data-assistive-id][data-assistive-kind]` |
| `bottom_sheet` | `.sheet[data-assistive-id][data-assistive-kind]` |
| `inline` | `.inline-help[data-assistive-id][data-assistive-kind]` 或行内按钮 |
| `modal` | `.modal-mask#<id>` 或 modal screen |
| `badge` | `.badge` |
| `top_bar` | `.topbar` |
| `action_bar` | `.action-bar` |
| `toast` | `.toast` |
| `menu` | `.menu` / `.drawer` |

`intent: guidance` 禁止用 `.zone` 承载；默认用 coachmark、bottom sheet、inline help 或 modal。

---

## 四、闭合 HTML 骨架示例

下面是最小 `feature_flow` 投影示例。它假设 spec 声明了两个 host anchors：`host_learning_center`（entry）与 `host_learning_center_exit`（exit），并声明了 `course_detail`、`learning_page`、`result_page` 三个页面。所有 target 都有去处；所有 zone 都带 `data-zone-id` / `data-zone-kind`。

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>交互原型</title>
<style>
  :root{--bg:#f2f3f5;--surface:#fff;--text:#1d2129;--muted:#86909c;--line:#e5e6eb;--accent:#165dff}
  *{box-sizing:border-box} body{margin:0;min-height:100vh;display:grid;place-items:center;background:#101217;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;color:var(--text)}
  .device{position:relative;width:390px;height:844px;overflow:hidden;background:var(--bg);border:10px solid #1b1d21;border-radius:44px}
  .screen{display:none;height:100%;flex-direction:column}.screen.active{display:flex}
  .topbar{display:flex;gap:10px;align-items:center;padding:40px 16px 12px;background:var(--surface)}.back{cursor:pointer}.title{font-weight:600;flex:1}.locator{font-size:12px;color:var(--muted)}
  .progress-row{display:flex;gap:8px;padding:8px 16px;background:var(--surface)}.badge{font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:99px;padding:4px 8px}
  .content{flex:1;overflow:auto;padding:12px 16px 104px}.zone{background:var(--surface);border-radius:12px;padding:14px;margin-bottom:12px}.zone h4{margin:0 0 8px;font-size:13px;color:var(--muted)}
  .action-bar{position:absolute;left:0;right:0;bottom:0;background:var(--surface);border-top:1px solid var(--line);padding:10px 16px 22px}.btn-primary{width:100%;border:0;border-radius:12px;background:var(--accent);color:white;padding:14px;font-weight:600}.sec-row{display:flex;gap:8px;margin-bottom:10px}.btn-sec{flex:1;border:1px solid var(--line);background:white;border-radius:10px;padding:10px}
</style>
</head>
<body>
<div class="device">
  <section class="screen active" id="course_detail" data-level="2" data-type="course_detail" data-tabbar="false">
    <div class="topbar"><button class="back" data-host="host_learning_center" data-host-label="学习中心">‹</button><div class="title">{{sample_state.course_title}}</div></div>
    <div class="progress-row"><span class="badge">{{sample_state.chapter}}/{{sample_state.chapter_total}}</span><span class="badge">{{sample_state.progress_percent}}%</span></div>
    <div class="content">
      <div class="zone" data-zone-id="course_progress" data-zone-kind="progress_strip"><h4>进度</h4><div>{{sample_state.progress_percent}}%</div></div>
      <div class="zone" data-zone-id="chapters" data-zone-kind="chapter_tree"><h4>章节</h4><button data-target="learning_page">{{sample_state.chapter}} · {{sample_state.unit}}</button></div>
    </div>
    <div class="action-bar">
      <div class="sec-row"><button class="btn-sec" data-behavior="toggle_bookmark">收藏</button><button class="btn-sec" data-behavior="share">分享</button></div>
      <button class="btn-primary" data-target="learning_page">继续学习</button>
    </div>
  </section>

  <section class="screen" id="learning_page" data-level="3" data-type="learning" data-tabbar="false">
    <div class="topbar"><button class="back" data-target="course_detail">‹</button><div class="title">{{sample_state.chapter}}</div><span class="locator">{{sample_state.progress_percent}}%</span></div>
    <div class="content">
      <div class="zone" data-zone-id="word" data-zone-kind="word_card"><h4>{{sample_state.example_word.w}}</h4><button data-behavior="play_audio">发音</button><p>{{sample_state.example_word.gloss}}</p><p>{{sample_state.example_word.ex}}</p></div>
      <div class="coachmark" data-assistive-id="learning_guidance" data-assistive-kind="hint_block">先理解例句，再进入练习。</div>
    </div>
    <div class="action-bar">
      <button class="btn-primary" data-target="result_page">完成学习</button>
    </div>
  </section>

  <section class="screen" id="result_page" data-level="3" data-type="result" data-tabbar="false">
    <div class="topbar"><button class="back" data-target="learning_page">‹</button><div class="title">学习结果</div></div>
    <div class="content">
      <div class="zone" data-zone-id="score" data-zone-kind="score_ring"><h4>成绩</h4><strong>{{sample_state.score_percent}}%</strong></div>
      <div class="zone" data-zone-id="mastery" data-zone-kind="mastery_bar"><h4>掌握情况</h4><p>继续巩固 {{sample_state.unit}}</p></div>
    </div>
    <div class="action-bar">
      <button class="btn-primary" data-host="host_learning_center_exit" data-host-label="学习中心">返回学习中心</button>
    </div>
  </section>
</div>
<script>
function go(id){document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));document.getElementById(id)?.classList.add('active')}
document.addEventListener('click',e=>{const t=e.target.closest('[data-target]');if(t)go(t.dataset.target);const h=e.target.closest('[data-host]');if(h)alert('回到宿主 App：'+(h.dataset.hostLabel||h.dataset.host));});
</script>
</body>
</html>
```

---

## 五、交付前对账清单

运行：

```bash
python skills/interaction-prototype/scripts/validate_epps.py prototype/YYYY-MM-DD-<主题>/prototype.md
python skills/interaction-prototype/scripts/audit_html_projection.py prototype/YYYY-MM-DD-<主题>/prototype.md prototype/YYYY-MM-DD-<主题>/prototype.html
```

任一失败都必须修复后重跑。脚本机械化检查的范围（其余仍靠人工自审）：

- 每个普通 page 有且仅有一个 `<section id="page.id">`；不多不少。
- 每个 modal 有 `.modal-mask#page.id` 或 `<section id="page.id">`，且有关闭路径。
- HTML zones 与 spec 的 `density.zones[]` 数量、顺序、id、kind 完全一致。
- HTML assistive 与 spec 的 `assistive_elements[]` 数量、顺序、id、kind 完全一致；`guidance` 不得出现在 `.zone`。
- **ACTION.declared**：每个 `data-target`/`data-host`/`data-behavior` 都对回 spec 的 primary/secondary/assistive/jump/back/tab，HTML 里没有规范之外的跳转。
- **ACTION.rendered**：spec 声明的 primary、back（非 modal）、secondary、assistive 目标，必须在该屏 HTML 里有一处对应的 `data-target`/`data-host`/`data-behavior`（堵住「spec 声明了但 HTML 漏画」）。jump 目标因常由 behavior 间接实现（如 `next_question`），不纳入此项。
- **BEHAVIOR.single_point**：同一屏同一 `data-behavior` 渲染次数不得超过 spec 声明次数（堵住「卡内 + 操作栏双份发音」）。
- **SAMPLE_STATE**：HTML 中不得残留未解析的 `{{sample_state.*}}`；grade 字面量（如「四年级」）不得与 `sample_state.grade` 矛盾；chapter 字面量（「第N章」）不得与 `sample_state.chapter` 矛盾。其他自由文本（百分比、词例）同源仍靠人工自审。
- host anchor 一律用 `data-host`，不用 `go()`。
