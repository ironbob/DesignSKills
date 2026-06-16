# HTML 渲染规范：EPPS → 自包含可点击多屏原型

> 用途：指导把 `epps.json` 渲染成**单一自包含** HTML。HTML 是 EPPS 的**机械投影**：不新增页面、不新增 zone、不新增跳转。视觉由主题 token 单一源驱动。
> 蓝本：`sample_data/prototype.html`（已验证的 HTML 范式）。组件结构见 `component-mapping.md`；投影标记契约见 `projection.manifest.yaml`。交付前必须跑 `scripts/audit_projection.py`。

---

## 一、硬性原则

1. **单一自包含文件**：所有 CSS/JS 内联，双击即可打开。
2. **手机框优先**：默认 390×844 移动端框；桌面需求另行声明。
3. **严格投影**：每个 `<section class="screen">` 对应一个 `page.id`；每个 `.zone` 对应一条 `density.zones[]`；每个辅助元素对应一条 `assistive_elements[]`；每个 `data-target`/`data-host`/`data-behavior` 对应 spec 的 primary/secondary/assistive/jump/back。
4. **示例数据同源**：页面文案从 `sample_state` 插值（`{{sample_state.x}}` 在生成时解析为真实值）；不在 HTML 里发明另一套年级/课程/进度。
5. **token 单一源**：`:root` 变量从所选主题预设（`presets/*.json`）发射；换预设即换 `:root`。

---

## 二、Token 注入（:root）

从预设 JSON 发射为 CSS 变量（颜色/圆角/间距直接用，字号/字重来自 typography）：

```css
:root{
  /* color.* → --<name> */
  --primary:#165dff; --onPrimary:#fff; --secondary:#722ed1;
  --surface:#fff; --background:#eef1f4;
  --onSurface:#1d2129; --onSurfaceVariant:#86909c; --outline:#e5e6eb;
  --success:#00b42a; --warning:#ff7d00; --danger:#f53f3f;
  /* shape.* */
  --shape-small:8px; --shape-medium:12px; --shape-large:16px;
  /* elevation.* */
  --elev-1:0 1px 2px rgba(0,0,0,.06); --elev-2:0 3px 8px rgba(0,0,0,.08); --elev-3:0 8px 24px rgba(0,0,0,.12);
  /* spacing.* */
  --sp-xs:4px; --sp-sm:8px; --sp-md:12px; --sp-lg:16px; --sp-xl:24px;
}
```

> typography 不进 `:root`，直接落在各 class 的 `font-size`/`font-weight`（headline 22/700、title 17/600、body 15/400、label 13/500、caption 11/400）。

---

## 三、EPPS 字段 → HTML 标记

| EPPS 字段 | HTML 标记 | 要求 |
|-----------|-----------|------|
| `page.id` | `<section class="screen" id="<id>">` | 普通页必须是 section |
| `page.level`/`page.type` | `data-level`/`data-type` | 值必须等于 spec |
| `navigation.tab_bar` | `data-tabbar="true\|false"` | `tab_bar_mode: hidden` 时全 false |
| `density.zones[]` | `.zone[data-zone-id][data-zone-kind]` | 数量、顺序、id、kind 必须与 spec 一致 |
| `assistive_elements[]` | `[data-assistive-id][data-assistive-kind]` | guidance 不得渲染为 `.zone` |
| `primary_action.target` | `.btn-primary[data-target]` 或 `data-behavior` | target 为 page/host/behavior 时用对应属性 |
| `secondary_actions[]` | `.btn-sec`/content 内按钮/inline 按钮 | 按 `placement` 只渲染一处 |
| `navigation.back_target` | `.back[data-target]` 或 `.back[data-host]` | host_anchor 用 `data-host`，不跳屏 |
| `jumps[]` | 对应元素 `data-target`/`data-host`/`data-behavior` | 不得出现 spec 外跳转 |
| `type==modal` | `.screen.modal-mask#<id>` | 必须能关闭；也要投影 modal 的 zones |

---

## 四、zone.kind → HTML

见 `component-mapping.md` §一（14 种全覆盖）。要点：每个 `.zone` 必须带 `data-zone-id` + `data-zone-kind`；内容从 `sample_state`/spec 投影，不发明。

---

## 五、主次层级（核心）

按 `component-mapping.md` §二：
- `primary_action` → 唯一满宽 `.btn-primary`（`--primary` 填充）。
- `secondary_actions`（`placement: action_bar`）→ `.sec-row > .btn-sec`（描边降权），置于 `.btn-primary` 之上。
- `placement: content`/`inline` → 行内 `.icon-btn`，只一处。
- zone `priority` → 大卡/普通卡/弱化（见 component-mapping §三）。

---

## 六、投影标记契约（对账锚点，不可删）

为让 `audit_projection.py`（`projection.manifest.yaml`）机械化对账，HTML 必须保留：

- 每屏：`<section class="screen" id="<page.id>" data-level data-type data-tabbar>`
- 每内容区：`<div class="zone" data-zone-id data-zone-kind>`
- 每辅助元素：`data-assistive-id data-assistive-kind`
- 页内跳转：`data-target="<page.id>"`
- 宿主入口/出口：`data-host="<host_anchor.id>" data-host-label="<label>"`
- 行为动作：`data-behavior="<behavior>"`（`behavior ∈ {next_question, previous_question, submit_answer, retry_quiz, play_audio, toggle_bookmark, share, close_modal}`）
- 主按钮：唯一 `.btn-primary`（每页 ≤ 1，对账 `PRIMARY.unique` 按 class `btn-primary` 计数）

HTML 可有视觉样式，但**不得删除这些标记**。

---

## 七、可点击：delegated listener（无 go()）

用一个**事件委托**监听器处理所有可点元素（蓝本 `sample_data/prototype.html`，无具名 `go()` 函数）：

```js
function showScreen(id){ document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active')); document.getElementById(id)?.classList.add('active'); }
function openModal(id){ document.getElementById(id)?.classList.add('active'); }
function closeModal(){ document.querySelectorAll('.modal-mask.active').forEach(m=>m.classList.remove('active')); }
function toast(msg){ const t=document.getElementById('toast'); t.textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),1400); }
document.addEventListener('click',e=>{
  const t=e.target.closest('[data-target],[data-host],[data-behavior]');
  if(!t) return;
  const beh=t.getAttribute('data-behavior');
  const host=t.getAttribute('data-host');
  const tgt=t.getAttribute('data-target');
  if(beh){ /* 行为占位反馈，预览级不接真实逻辑 */ toast('行为：'+beh); return; }
  if(host){ toast('↩ 回到宿主 App：'+(t.getAttribute('data-host-label')||host)); return; }
  if(tgt){ (document.getElementById(tgt)?.classList.contains('modal-mask') ? openModal(tgt) : showScreen(tgt)); }
});
```

> 行为目标（`data-behavior`）只做**占位反馈**（toast），不接真实发音/提交/评分逻辑——预览级。

---

## 八、闭合 HTML 骨架示例

最小 `feature_flow` 投影示例（假设 spec 声明了 host anchor `host_entry`/`host_exit`，页面 `course_detail`/`learning`/`result`）：

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>多平台渲染 · HTML</title>
<style>
  :root{--primary:#165dff;--onPrimary:#fff;--secondary:#722ed1;--surface:#fff;--background:#eef1f4;
    --onSurface:#1d2129;--onSurfaceVariant:#86909c;--outline:#e5e6eb;--success:#00b42a;--warning:#ff7d00;--danger:#f53f3f;
    --shape-small:8px;--shape-medium:12px;--shape-large:16px;--elev-1:0 1px 2px rgba(0,0,0,.06);--elev-2:0 3px 8px rgba(0,0,0,.08);}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0f1115;padding:24px;
    font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;color:var(--onSurface)}
  .wrap{display:flex;flex-direction:column;align-items:center;gap:12px}
  .caption{color:#c9ced6;font-size:13px}
  .device{position:relative;width:390px;height:844px;overflow:hidden;background:var(--background);
    border:11px solid #20232a;border-radius:46px;box-shadow:0 30px 80px rgba(0,0,0,.5)}
  .screen{display:none;height:100%;flex-direction:column}.screen.active{display:flex}
  .topbar{display:flex;gap:10px;align-items:center;padding:40px var(--sp-lg) 12px;background:var(--surface)}
  .back{cursor:pointer;font-size:22px;color:var(--onSurface);background:none;border:0}
  .title{font-size:17px;font-weight:600;flex:1}
  .locator{font-size:11px;color:var(--onSurfaceVariant)}
  .content{flex:1;overflow:auto;padding:12px var(--sp-lg) 104px}
  .zone{background:var(--surface);border:1px solid var(--outline);border-radius:var(--shape-medium);
    padding:14px;margin-bottom:12px;box-shadow:var(--elev-1)}
  .zone h4{margin:0 0 8px;font-size:13px;color:var(--onSurfaceVariant);font-weight:500}
  .zone.hero{background:linear-gradient(135deg,#eaf1ff,#f6efff);border:0;padding:18px;box-shadow:none}
  .zone.hero .h{font-size:22px;font-weight:700}.zone.hero .s{font-size:13px;color:var(--onSurfaceVariant);margin-top:4px}
  .badge-row{display:flex;gap:8px}.badge{font-size:11px;color:var(--onSurfaceVariant);border:1px solid var(--outline);border-radius:99px;padding:4px 8px}
  .action-bar{position:absolute;left:0;right:0;bottom:0;background:var(--surface);border-top:1px solid var(--outline);padding:10px var(--sp-lg) 22px}
  .sec-row{display:flex;gap:8px;margin-bottom:9px}
  .btn-sec{flex:1;border:1px solid var(--outline);background:var(--surface);border-radius:11px;padding:11px;font-size:14px;cursor:pointer;color:var(--onSurface)}
  .btn-primary{width:100%;border:0;border-radius:var(--shape-medium);background:var(--primary);color:var(--onPrimary);padding:15px;font-size:16px;font-weight:600;cursor:pointer}
  .btn-primary .st{display:block;font-size:11px;font-weight:400;opacity:.85;margin-top:3px}
  .modal-mask{display:none;background:rgba(0,0,0,.5);place-items:center}.modal-mask.active{display:grid}
  .toast{position:absolute;left:50%;bottom:120px;transform:translateX(-50%);background:rgba(0,0,0,.8);color:#fff;padding:8px 14px;border-radius:8px;font-size:13px;opacity:0;transition:opacity .2s}.toast.show{opacity:1}
</style>
</head>
<body>
<div class="wrap">
  <div class="caption">多平台渲染 · HTML 预览（{{preset.label}}）</div>
  <div class="device">
    <section class="screen active" id="course_detail" data-level="2" data-type="course_detail" data-tabbar="false">
      <div class="topbar"><button class="back" data-host="host_entry" data-host-label="宿主入口">‹</button><div class="title">{{sample_state.lesson}}</div></div>
      <div class="content">
        <div class="zone hero" data-zone-id="today_task" data-zone-kind="hero_card">
          <div class="h">{{sample_state.lesson}}</div><div class="s">已完成 {{sample_state.progress_percent}}%</div>
        </div>
      </div>
      <div class="action-bar">
        <button class="btn-primary" data-target="learning">开始学习<span class="st">{{sample_state.example_word.w}}</span></button>
      </div>
    </section>

    <section class="screen" id="learning" data-level="3" data-type="learning" data-tabbar="false">
      <div class="topbar"><button class="back" data-target="course_detail">‹</button><div class="title">{{sample_state.example_word.w}}</div></div>
      <div class="content">
        <div class="zone" data-zone-id="word" data-zone-kind="word_card"><h4>学习项</h4>
          <div style="font-size:22px;font-weight:700">{{sample_state.example_word.w}}</div>
          <div style="font-size:11px;color:var(--onSurfaceVariant)">{{sample_state.example_word.ph}} · {{sample_state.example_word.pos}}</div>
          <div style="margin-top:8px">{{sample_state.example_word.gloss}}</div>
          <div style="color:var(--onSurfaceVariant);font-size:13px">{{sample_state.example_word.ex}}</div>
        </div>
      </div>
      <div class="action-bar">
        <button class="btn-primary" data-behavior="next_question">下一个学习项</button>
      </div>
    </section>

    <section class="screen" id="result" data-level="3" data-type="result" data-tabbar="false">
      <div class="topbar"><button class="back" data-target="learning">‹</button><div class="title">结果</div></div>
      <div class="content">
        <div class="zone" data-zone-id="score" data-zone-kind="score_ring"><h4>正确率</h4>
          <div style="font-size:40px;font-weight:700;color:var(--success)">{{sample_state.accuracy_percent}}%</div>
        </div>
      </div>
      <div class="action-bar">
        <button class="btn-primary" data-host="host_exit" data-host-label="宿主首页">完成</button>
      </div>
    </section>

    <div class="toast" id="toast"></div>
  </div>
</div>
<script>
function showScreen(id){document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));document.getElementById(id)?.classList.add('active')}
function closeModal(){document.querySelectorAll('.modal-mask.active').forEach(m=>m.classList.remove('active'))}
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),1400)}
document.addEventListener('click',e=>{const t=e.target.closest('[data-target],[data-host],[data-behavior]');if(!t)return;
  const beh=t.getAttribute('data-behavior'),host=t.getAttribute('data-host'),tgt=t.getAttribute('data-target');
  if(beh){toast('行为：'+beh);return} if(host){toast('↩ 回到宿主：'+(t.getAttribute('data-host-label')||host));return}
  if(tgt){document.getElementById(tgt)?.classList.contains('modal-mask')?document.getElementById(tgt).classList.add('active'):showScreen(tgt)}});
</script>
</body>
</html>
```

---

## 九、交付前对账

```bash
python skills/epps-render/scripts/audit_projection.py <epps.json> <render-dir> --platform html
```

重点：每个普通 page 有且仅有一个 `<section id="page.id">`；modal 有 `.screen.modal-mask#page.id` 且可关闭；HTML zones 与 spec `density.zones[]` 数量/顺序/id/kind 完全一致；assistive 与 spec 一致且 `guidance` 不在 `.zone`；所有 `data-target` 指向已定义 page 或 legal behavior；`target==null` 行为只在一个 `placement` 渲染。
