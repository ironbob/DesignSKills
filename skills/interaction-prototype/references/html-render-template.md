# EPPS → 可点击 HTML 原型渲染规范

> 配合 interaction-prototype skill 的 Checklist 第 5 步（逐页草渲）与第 8 步（组装）。
> 把校验通过的 EPPS 规范，渲染成**单个自包含** `prototype.html`：手机框、多屏、按跳转图可点击演示。
>
> 前置：EPPS 规范必须已通过校验（ERROR 清零、WARNING ≥ 80%）。HTML 只是把规范「画」出来，不增删跳转、不发明页面。

---

## 一、设计原则

1. **单一自包含文件** —— 所有 CSS/JS 内联，双击即开，无需依赖、无需构建。
2. **规范即事实源（完整契约 + 严格投影）** —— HTML 里每个可点元素都必须对回规范里的 `jump` / `primary_action` / `navigation.back` / `tab`；**每个内容区都必须对回 `density.zones[]` 的一条声明**。**不得出现规范里没有的跳转，也不得渲染 spec 未声明的 zone**（连「学习提示」这种「善意补充」也不行——要加就先回 spec 声明）。渲染 = `for zone in page.zones: emit 模板[zone.kind]`，机械投影，不创作。
3. **单一内容源** —— 所有示例值（年级/单元/今日数/streak/示例词/百分比）从原型级 `sample_state` 插值，spec 的 `status` 与 HTML 同源；**禁止各页各自硬编码**（否则同数据跨页漂移：四年级 vs 五年级）。
4. **原型非视觉稿** —— 中性灰 + 单一强调色，不堆砌品牌视觉。组件样式服务于「看清结构与跳转」，不服务「好看」。
5. **手机框优先** —— 教育类 App 多为移动端，用 390×844 手机框；桌面端需求另行说明。
6. **演示友好** —— 提供「页面地图」浮层，方便 review 时快速跳到任意屏。

---

## 二、组件映射表（EPPS 字段 → HTML）

| EPPS 字段 | HTML 结构 | 说明 |
|-----------|-----------|------|
| `page.id` | `<section class="screen" id="<id>">` | 每页一个 section；`go(id)` 切换可见 |
| `level`/`type` | section 的 `data-level` / `data-type` | 用于决定是否渲染 tabbar/back |
| `primary_action` | `.action-bar > button.btn-primary[data-target]` | 底部固定，全宽，最强视觉 |
| `primary_action.status` | `.btn-primary .status` | 主按钮下/内的状态副文案 |
| `secondary_actions[]` | `.sec-row > button.btn-sec[data-target]`（`placement: action_bar`） | 图标+文案，弱化样式，最多 4 个；`placement: content` 者渲染进对应 zone，`inline` 者行内——**一处** |
| `navigation.has_back` / `back_target` | `.topbar > .back[data-target]` | 左上返回箭头 |
| `navigation.tab_bar` | `.tabbar > .tab[data-target]`（× Tab 数） | 底部 Tab，3–5 个（仅 `tab_bar_mode==inherit`；`hidden` 时不渲染，`.action-bar` 贴底） |
| `progress.elements` | `.topbar .locator` + `.progress-row` 的徽章 | overall/streak/today_minutes/chapter_locator 各一徽章 |
| `feedback.type == immediate`（quiz） | 提交后原地展开 `.feedback-panel` + 主按钮重标为「下一题」 | 二段式 |
| `feedback.next_action` | 主按钮/反馈面板的引导文案 | 语义指向下一步 |
| `density.zones[]` | 内容区按 zone **逐项投影**（`for zone: emit 模板[zone.kind]`，见 §四） | 严格按声明顺序与数量；**不渲染未声明的 zone**（R6.2 + 对账兜底） |
| `sample_state` | `{{sample_state.*}}` 插值到 status / 徽章 / 示例词 / 百分比 | 原型级单一内容源；spec 与 HTML 同源，不硬编码 |
| `jumps[]`（非 primary/back/tab） | 对应触发元素加 `data-target` | 如章节条目、卡片点击 |
| `target == host_anchor.id`（`feature_flow` 出口/入口） | 元素带 `data-host="<id>"` | 点击**不** `go()`（宿主页未原型化），弹出「↩ 回到宿主App：<label>」提示；如首屏 back、结果页「返回App」 |

> `target == null`（如「提交答案」「收藏」）的按钮：不加 `data-target`，改为 `data-behavior="submit|bookmark|..."`，由 JS 处理（提交触发二段式，收藏仅切图标态）。

---

## 三、手机框骨架（可复用模板）

以下是完整可运行骨架。**照此结构填**：每个页面一个 `<section class="screen">`，把示例 home 屏替换/扩展为你的页面集合。CSS/JS 无需改动。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>交互原型 · <主题></title>
<style>
  :root{
    --bg:#f2f3f5; --surface:#fff; --text:#1d2129; --muted:#86909c;
    --line:#e5e6eb; --accent:#165dff; --accent-weak:#e8f3ff;
    --ok:#00b42a; --warn:#ff7d00; --danger:#f53f3f;
    --radius:14px;
  }
  *{box-sizing:border-box; -webkit-tap-highlight-color:transparent;}
  html,body{margin:0;background:#0f1115;font-family:-apple-system,"PingFang SC",system-ui,sans-serif;color:var(--text);}
  body{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px;}

  /* 手机框 */
  .device{position:relative;width:390px;height:844px;background:var(--bg);border-radius:44px;
    overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.5);border:10px solid #1b1d21;}
  .notch{position:absolute;top:0;left:50%;transform:translateX(-50%);width:150px;height:26px;
    background:#1b1d21;border-radius:0 0 18px 18px;z-index:50;}

  /* 屏幕：默认隐藏，.active 显示 */
  .screen{display:none;flex-direction:column;height:100%;background:var(--bg);}
  .screen.active{display:flex;}

  /* 顶部栏 */
  .topbar{display:flex;align-items:center;gap:10px;padding:40px 16px 12px;background:var(--surface);}
  .topbar .back{font-size:20px;color:var(--text);cursor:pointer;width:28px;text-align:center;visibility:hidden;}
  .screen[data-level="2"] .back, .screen[data-level="3"] .back, .screen[data-level="modal"] .back{visibility:visible;}
  .topbar .title{font-weight:600;font-size:16px;flex:1;}
  .topbar .locator{font-size:12px;color:var(--muted);}

  /* 进度行 */
  .progress-row{display:flex;gap:8px;padding:8px 16px;background:var(--surface);flex-wrap:wrap;}
  .badge{font-size:11px;color:var(--muted);background:var(--bg);border:1px solid var(--line);
    padding:4px 8px;border-radius:20px;}

  /* 内容区 */
  .content{flex:1;overflow-y:auto;padding:12px 16px 100px;}
  .zone{background:var(--surface);border-radius:var(--radius);padding:14px;margin-bottom:12px;}
  .zone h4{margin:0 0 8px;font-size:13px;color:var(--muted);font-weight:500;}
  .placeholder{color:var(--muted);font-size:13px;line-height:1.6;}

  /* home: 继续学习大卡 */
  .continue-card{background:linear-gradient(135deg,var(--accent),#0e42d2);color:#fff;border-radius:var(--radius);
    padding:18px;margin-bottom:12px;cursor:pointer;}
  .continue-card .k{font-size:12px;opacity:.85;}
  .continue-card .v{font-size:18px;font-weight:700;margin:6px 0;}
  .continue-card .s{font-size:12px;opacity:.9;}

  /* course_detail: 章节树 */
  .chapter{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);cursor:pointer;}
  .chapter:last-child{border-bottom:none;}
  .chapter .st{font-size:12px;width:20px;text-align:center;}
  .chapter .st.done{color:var(--ok);} .chapter .st.now{color:var(--accent);} .chapter .st.lock{color:var(--muted);}

  /* quiz: 单题 + 选项 */
  .q-stem{font-size:15px;line-height:1.6;margin-bottom:14px;}
  .opt{display:block;width:100%;text-align:left;padding:12px 14px;margin-bottom:10px;border:1px solid var(--line);
    background:var(--surface);border-radius:10px;font-size:14px;cursor:pointer;}
  .opt.sel{border-color:var(--accent);background:var(--accent-weak);}
  .opt.correct{border-color:var(--ok);background:#e8ffea;}
  .opt.wrong{border-color:var(--danger);background:#ffece8;}
  .feedback-panel{display:none;margin-top:4px;padding:12px;border-radius:10px;font-size:13px;line-height:1.6;}
  .feedback-panel.show{display:block;}
  .feedback-panel.ok{background:#e8ffea;color:#0f6b27;}
  .feedback-panel.no{background:#ffece8;color:#a8261a;}

  /* result: 环形分 */
  .score-ring{width:120px;height:120px;border-radius:50%;background:conic-gradient(var(--accent) calc(var(--p)*1%),#e5e6eb 0);
    display:flex;align-items:center;justify-content:center;margin:8px auto;}
  .score-ring span{width:96px;height:96px;background:var(--surface);border-radius:50%;display:flex;
    align-items:center;justify-content:center;font-size:26px;font-weight:700;}

  /* 底部操作栏 */
  .action-bar{position:absolute;left:0;right:0;bottom:0;background:var(--surface);padding:10px 16px 22px;
    border-top:1px solid var(--line);box-shadow:0 -4px 16px rgba(0,0,0,.04);}
  .btn-primary{display:block;width:100%;padding:14px;border:none;border-radius:12px;background:var(--accent);
    color:#fff;font-size:16px;font-weight:600;cursor:pointer;}
  .btn-primary .status{display:block;font-size:11px;font-weight:400;opacity:.9;margin-top:2px;}
  .sec-row{display:flex;gap:8px;margin-bottom:10px;}
  .btn-sec{flex:1;padding:10px;border:1px solid var(--line);background:var(--surface);border-radius:10px;
    font-size:12px;color:var(--text);cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:4px;}
  .btn-sec .ic{font-size:16px;}

  /* 底部 Tab */
  .tabbar{position:absolute;left:0;right:0;bottom:0;height:62px;background:var(--surface);border-top:1px solid var(--line);
    display:none;justify-content:space-around;align-items:center;padding-bottom:8px;}
  .screen[data-tabbar="true"] .tabbar{display:flex;}
  .screen[data-tabbar="true"] .action-bar{bottom:62px;}
  .tab{display:flex;flex-direction:column;align-items:center;font-size:10px;color:var(--muted);cursor:pointer;gap:2px;}
  .tab .ic{font-size:18px;} .tab.active{color:var(--accent);}

  /* 弹窗 */
  .modal-mask{display:none;position:absolute;inset:0;background:rgba(0,0,0,.4);z-index:40;align-items:flex-end;}
  .modal-mask.active{display:flex;}
  .modal-sheet{width:100%;background:var(--surface);border-radius:18px 18px 0 0;padding:16px;max-height:70%;overflow:auto;}

  /* 页面地图浮层（review 用） */
  .map-fab{position:fixed;right:24px;bottom:24px;z-index:100;background:#1d2129;color:#fff;border:none;
    width:44px;height:44px;border-radius:50%;font-size:18px;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.4);}
  .map-panel{position:fixed;right:24px;bottom:78px;z-index:100;background:#fff;border-radius:12px;padding:8px;
    max-height:60vh;overflow:auto;display:none;box-shadow:0 10px 40px rgba(0,0,0,.3);}
  .map-panel.show{display:block;}
  .map-panel a{display:block;padding:8px 14px;font-size:13px;color:var(--text);text-decoration:none;border-radius:8px;cursor:pointer;}
  .map-panel a:hover{background:var(--bg);}
  .map-panel a small{color:var(--muted);margin-left:6px;}
</style>
</head>
<body>
  <div class="device">
    <div class="notch"></div>

    <!-- ============ 屏 1 · home（scope==whole_app 示例，按规范填） ============ -->
    <!-- 注意：feature_flow 无 home 屏，也无 level1/Tab；其流入口屏 level=2、data-tabbar 不设、back 用 data-host 指向入口 host_anchor -->
    <section class="screen active" id="home" data-level="1" data-type="home" data-tabbar="true">
      <div class="topbar">
        <span class="back">‹</span>
        <span class="title">学习中心</span>
      </div>
      <div class="progress-row">
        <span class="badge">🔥 连续 12 天</span>
        <span class="badge">⏱ 今日 18 分钟</span>
      </div>
      <div class="content">
        <!-- 主区：继续学习大卡 = primary_action，点击直达 learning_page（R2.1/R2.2） -->
        <div class="continue-card" onclick="go('learning_page')">
          <div class="k">继续学习</div>
          <div class="v">《XX课程》第3章</div>
          <div class="s">进度 65% · 上次学到 05:32</div>
        </div>
        <div class="zone"><h4>推荐课程</h4><div class="placeholder">课程卡片列表…</div></div>
      </div>
      <div class="action-bar">
        <button class="btn-primary" data-target="learning_page">继续学习<span class="status">《XX课程》第3章 · 65%</span></button>
      </div>
      <!-- Tab Bar（全局 3–5 个） -->
      <nav class="tabbar">
        <div class="tab active" data-target="home"><span class="ic">🏠</span>首页</div>
        <div class="tab" data-target="course_list"><span class="ic">📚</span>课程</div>
        <div class="tab" data-target="profile"><span class="ic">👤</span>我的</div>
      </nav>
    </section>

    <!-- ============ 屏 2 · learning_page（示例，心流页） ============ -->
    <section class="screen" id="learning_page" data-level="3" data-type="learning">
      <div class="topbar">
        <span class="back" data-target="course_detail">‹</span>
        <span class="title">第3章 · 知识点</span>
        <span class="locator">3/8 章 · 65%</span>
      </div>
      <div class="content">
        <div class="zone" style="height:200px;display:flex;align-items:center;justify-content:center;">
          <span class="placeholder">▶ 视频播放区（继续观看 05:32）</span>
        </div>
        <div class="zone"><h4>本节要点</h4><div class="placeholder">知识点提纲…</div></div>
      </div>
      <div class="action-bar">
        <div class="sec-row">
          <button class="btn-sec" data-target="note_modal"><span class="ic">✏️</span>笔记</button>
          <button class="btn-sec" data-target="chapter_drawer"><span class="ic">📋</span>目录</button>
        </div>
        <button class="btn-primary" data-target="result_page">完成并继续<span class="status">本节即将完成</span></button>
      </div>
    </section>

    <!-- ============ 屏 3 · quiz_page（示例，即时反馈二段式） ============ -->
    <section class="screen" id="quiz_page" data-level="3" data-type="quiz">
      <div class="topbar">
        <span class="back" data-target="course_detail">‹</span>
        <span class="title">练习</span>
        <span class="locator">3/10 题</span>
      </div>
      <div class="content">
        <div class="zone">
          <div class="q-stem">以下哪项是「单一主行动点」原则的正确做法？</div>
          <button class="opt">A. 底部放四个等大按钮</button>
          <button class="opt">B. 一个最强 primary + 其余降权</button>
          <button class="opt">C. 把收藏和主按钮并排</button>
          <div class="feedback-panel" id="qfb"></div>
        </div>
      </div>
      <div class="action-bar">
        <div class="sec-row">
          <button class="btn-sec" data-target="hint_modal"><span class="ic">💡</span>提示</button>
        </div>
        <button class="btn-primary" id="quiz-submit" data-behavior="submit">提交</button>
      </div>
    </section>

    <!-- ============ 屏 4 · result_page（示例，必有正向出口） ============ -->
    <section class="screen" id="result_page" data-level="3" data-type="result">
      <div class="topbar">
        <span class="back" data-target="course_detail">‹</span>
        <span class="title">练习结果</span>
      </div>
      <div class="content">
        <div class="zone" style="text-align:center;">
          <div class="score-ring" style="--p:80"><span>80</span></div>
          <div class="placeholder">正确率 80% · 答对 8 / 10</div>
        </div>
        <div class="zone"><h4>掌握情况</h4><div class="placeholder">错题 2 · 薄弱点：原则1</div></div>
      </div>
      <div class="action-bar">
        <div class="sec-row">
          <button class="btn-sec" data-target="quiz_page"><span class="ic">🔁</span>重做错题</button>
          <button class="btn-sec" data-target="course_detail"><span class="ic">↩</span>返回课程</button>
        </div>
        <button class="btn-primary" data-target="learning_page">继续下一节</button>
      </div>
    </section>

    <!-- ============ 弹窗 · note_modal（必须可关闭，R4.4） ============ -->
    <div class="modal-mask" id="note_modal">
      <div class="modal-sheet">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <b>笔记</b><span style="cursor:pointer;" onclick="closeModal('note_modal')">✕</span>
        </div>
        <div class="placeholder">在此记录本节笔记…</div>
      </div>
    </div>
  </div>

  <!-- 页面地图（review 用，列出所有屏） -->
  <button class="map-fab" onclick="toggleMap()">☰</button>
  <div class="map-panel" id="mapPanel"></div>

<script>
  /* 切换屏幕 */
  function go(id){
    document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
    const el=document.getElementById(id);
    if(!el){ console.warn('未定义页(可能是应改用 data-host 的 host_anchor):',id); return; }   // R4.2 悬空 target 的运行时保护
    el.classList.add('active');
    // tab 高亮
    document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active', t.dataset.target===id));
    el.scrollTop=0;
    document.getElementById('mapPanel').classList.remove('show');
  }
  /* 所有带 data-target 的可点元素 → go() */
  document.addEventListener('click',e=>{
    const t=e.target.closest('[data-target]');
    if(t){ go(t.dataset.target); }
  });
  /* feature_flow 的出口/入口 host_anchor：不 go()（宿主页未原型化），弹提示 */
  document.addEventListener('click',e=>{
    const h=e.target.closest('[data-host]');
    if(!h) return;
    const label=h.dataset.hostLabel||h.dataset.host||'宿主App';
    hostToast('↩ 回到宿主App：'+label);
  });
  function hostToast(msg){
    let t=document.getElementById('hostToast');
    if(!t){
      t=document.createElement('div'); t.id='hostToast';
      t.style.cssText='position:absolute;left:50%;bottom:120px;transform:translateX(-50%);background:#1d2129;color:#fff;padding:10px 16px;border-radius:10px;font-size:13px;z-index:200;opacity:0;transition:opacity .2s;pointer-events:none;max-width:80%;text-align:center;';
      document.querySelector('.device').appendChild(t);
    }
    t.textContent=msg; t.style.opacity='1';
    clearTimeout(t._timer); t._timer=setTimeout(()=>t.style.opacity='0',1600);
  }
  /* 弹窗 */
  function openModal(id){ document.getElementById(id).classList.add('active'); }
  function closeModal(id){ document.getElementById(id).classList.remove('active'); }
  /* quiz 二段式：提交 → 出解析 → 重标「下一题」 */
  document.getElementById('quiz-submit').addEventListener('click',function(){
    if(this.dataset.behavior==='submit'){
      const fb=document.getElementById('qfb');
      fb.className='feedback-panel show ok';
      fb.textContent='✓ 答对了！B 正确：单一主行动点要求一个最强 primary，其余降权。';
      this.textContent='下一题'; this.dataset.behavior='next';
    }else{
      go('result_page');   // 最后一题进结果页（feedback.next_action）
    }
  });
  /* 页面地图 */
  function buildMap(){
    const p=document.getElementById('mapPanel');
    p.innerHTML='';
    document.querySelectorAll('.screen').forEach(s=>{
      const a=document.createElement('a');
      a.innerHTML=`${s.id} <small>${s.dataset.type}·L${s.dataset.level}</small>`;
      a.onclick=()=>go(s.id); p.appendChild(a);
    });
  }
  function toggleMap(){ const p=document.getElementById('mapPanel'); p.classList.toggle('show'); }
  buildMap();
</script>
</body>
</html>
```

---

## 四、渲染投影：zone.kind → HTML 模板（严格投影，非配方）

> **渲染是机械投影，不是创作。** 内容区 = `for zone in page.zones: emit 模板[zone.kind]`，**按 zones 声明顺序**逐个投影。**只渲染声明的 zone，不渲染任何未声明的 zone**（堵住「学习提示」凭空多出一区——S1/S2 源头修复）。要加一个区，先回 spec 的 `density.zones` 声明它（kind 取下表枚举值），再回这里投影；不得在渲染时临场发明。
>
> 所有文本值（年级/单元/今日数/streak/示例词/百分比）从 `sample_state` **插值**，不硬编码（S3）。

### zone.kind → 模板（闭环 14 种，与 `epps-schema.md` 一一对应）

| kind | 投影为（HTML 锚点） | 内容来源 |
|------|---------------------|----------|
| `hero_card` | `.today-card`/`.continue-card`（渐变大卡，可点→ primary target） | `primary_action.label/status` + `sample_state` |
| `quick_entries` | `.quick-row > .quick`×N（图标快捷入口） | `secondary_actions`（`placement: content` 的那些）或显式入口 |
| `badge_strip` | `.progress-row > .badge`×N（streak/今日/定位） | `progress.elements` + `sample_state` |
| `word_card` | `.zone` 含 `.word-head`+`.gloss`+`.ex`（+可选 play-btn） | `sample_state.example_word` |
| `option_list` | `.q-stem` + `.opt`×N + `.feedback-panel` | 题干 + 选项（`data-k`） |
| `input_block` | `.text-in`（`id`）+ `.feedback-panel` | 题干 + 输入框 |
| `row_list` | `.row`×N（`.st`/`.t`/`.arr`，可点→ target） | 列表项 |
| `chapter_tree` | `.seg`（分段）+ `.row`×N（状态 done/now/lock） | 分层结构 + 状态 |
| `mastery_bar` | `.mastery > i`×N + `.legend` | 掌握度分布 |
| `score_ring` | `.score-ring[--p] > span` | 正确率（`sample_state`/结果） |
| `stat_grid` | `.stat-grid > .stat`×N | 统计数字 |
| `progress_strip` | `.bar-track > i[width]` | 完成度 |
| `hint_block` | `.zone > h4[label] + .placeholder` | 提示文案（**非可点**；「学习提示」属此类，须先声明） |
| `text_block` | `.placeholder` / `.zone .placeholder` | 说明/占位文本 |

### 各 type 的典型 zone 组合（声明参考，非渲染时发明）

spec 作者从下表**挑选**该页要声明的 `zones`（可调，但每个必须取枚举 kind）。这只是「通常这样组」，不是硬性规定——**最终以 spec 声明为准，渲染器只投影声明值**。

| type | 典型 zones（kind） |
|------|--------------------|
| `home`（whole_app） | `hero_card`, `badge_strip`, `quick_entries` |
| `course_detail` | `progress_strip`, `chapter_tree` 或 `hero_card`, `mastery_bar`, `row_list` |
| `learning` | `word_card`, `hint_block` |
| `quiz`（选择） | `option_list` |
| `quiz`（拼写） | `input_block` |
| `result` | `score_ring`, `mastery_bar` |
| `profile` | `stat_grid`, `row_list` |
| `list` | `chapter_tree` 或 `row_list` |
| `misc` | `stat_grid`, `progress_strip`, `hint_block` |

### behavior affordance 落点（placement，单点渲染）

`target==null` 的行为（发音/提示/保存）按 `placement` 渲染**且只在一处**：
- `action_bar`（默认）→ `.sec-row > .btn-sec[data-behavior]`
- `content` → 渲染进对应 zone（如发音进 `word_card` 的 `.play-btn`）
- `inline` → 行内小图标

> 反例（须杜绝）：`learning` 页同时在 `word_card` 内画一个 `.play-btn`、又在 `action-bar` 画一个「发音」`btn-sec`——同一 affordance 两处。给「发音」定 `placement: content`，只留卡内那个。

### modal

- 用 `.modal-mask` + `.modal-sheet`；**必须有关闭**（✕ 或 `data-target` 回原页），满足 R4.4。
- 触发它的元素 `onclick="openModal('id')"`。modal 内 zone 同样按声明投影。

---

## 五、渲染检查清单（交付前过一遍）

- [ ] 每个规范里的 `page.id` 都有对应 `<section id="...">`；反之无多余屏。
- [ ] 每个 `primary_action.target`、`jumps[].target`、`back_target`、tab `data-target` 都指向已存在的屏，**或**指向已声明 `host_anchor`（后者用 `data-host`，见下）。
- [ ] primary 全宽最强，secondary 降权为图标行（无等大并排）。
- [ ] `level≠1` 的屏都有 back；`scope==whole_app` 时 `level==1` 的屏都有 tabbar；`tab_bar_mode==hidden` 时全原型无任何 tabbar（`.action-bar` 贴底）。
- [ ] quiz 是二段式即时反馈；result 有正向出口 primary。
- [ ] `target==null` 的行为按钮用 `data-behavior`，不误加 `data-target`。
- [ ] 所有 `data-host` 指向已声明的 `host_anchor`；点击**不**触发 `go()`、不报 `console.warn`，而是弹出「↩ 回到宿主App」提示。
- [ ] 页面地图能跳到任意屏；Tab 高亮随当前屏切换（`hidden` 模式下无 Tab，此项跳过）。

### 机械化对账（HTML ↔ spec，硬拦截——兜底防线）

把每屏 HTML 反解析回 zone/action 列表，与 spec **逐项 diff**。任一不匹配即就地修（修 spec 或修 HTML，二选一回到一致），不得放行：

- [ ] **zone 数量与顺序**：HTML 每屏的内容区 == `page.zones[]`，**一个不多一个不少**。（catch：「学习提示」多出一区）
- [ ] **zone.kind 可回溯**：每个 HTML 区都能对回声明的 `zone.kind`（枚举内）；枚举外的 kind 即拦截。（catch：未登记的 `study_tip`）
- [ ] **示例数据同源**：HTML 里的年级/单元/今日数/streak/示例词/百分比，全部能在 `sample_state` 找到同一值；无跨页矛盾。（catch：四年级 vs 五年级）
- [ ] **affordance 单点**：每个 `target==null` 行为（发音/提示/保存）只在一个 `placement` 渲染，无「卡内 + 操作栏」双份。（catch：两个发音按钮）
- [ ] **无未声明跳转**：HTML 每个 `data-target`/`data-host`/`data-behavior` 都对回 spec 的 `jump`/`primary`/`secondary`/`back`/`tab`；规范里没有的不存在。

> 这一步是**源头优化之后的兜底**：闭环枚举 + 严格投影 + sample_state 已让上面大多数情况无法产生；对账负责抓漏网的、以及人手改 HTML 时引入的回退。它是 `SKILL.md` 第 9 步「自审」的机械化主体。
