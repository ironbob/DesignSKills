# EPPS → 可点击 HTML 原型渲染规范

> 配合 interaction-prototype skill 的 Checklist 第 8 步。
> 把校验通过的 EPPS 规范，渲染成**单个自包含** `prototype.html`：手机框、多屏、按跳转图可点击演示。
>
> 前置：EPPS 规范必须已通过校验（ERROR 清零、WARNING ≥ 80%）。HTML 只是把规范「画」出来，不增删跳转、不发明页面。

---

## 一、设计原则

1. **单一自包含文件** —— 所有 CSS/JS 内联，双击即开，无需依赖、无需构建。
2. **规范即事实源** —— HTML 里每个可点元素都必须对回规范里的 `jump` / `primary_action` / `navigation.back` / `tab`；**不得出现规范里没有的跳转**。
3. **原型非视觉稿** —— 中性灰 + 单一强调色，不堆砌品牌视觉。组件样式服务于「看清结构与跳转」，不服务「好看」。
4. **手机框优先** —— 教育类 App 多为移动端，用 390×844 手机框；桌面端需求另行说明。
5. **演示友好** —— 提供「页面地图」浮层，方便 review 时快速跳到任意屏。

---

## 二、组件映射表（EPPS 字段 → HTML）

| EPPS 字段 | HTML 结构 | 说明 |
|-----------|-----------|------|
| `page.id` | `<section class="screen" id="<id>">` | 每页一个 section；`go(id)` 切换可见 |
| `level`/`type` | section 的 `data-level` / `data-type` | 用于决定是否渲染 tabbar/back |
| `primary_action` | `.action-bar > button.btn-primary[data-target]` | 底部固定，全宽，最强视觉 |
| `primary_action.status` | `.btn-primary .status` | 主按钮下/内的状态副文案 |
| `secondary_actions[]` | `.sec-row > button.btn-sec[data-target]` | 图标+文案，弱化样式，最多 4 个 |
| `navigation.has_back` / `back_target` | `.topbar > .back[data-target]` | 左上返回箭头 |
| `navigation.tab_bar` | `.tabbar > .tab[data-target]`（× Tab 数） | 底部 Tab，3–5 个 |
| `progress.elements` | `.topbar .locator` + `.progress-row` 的徽章 | overall/streak/today_minutes/chapter_locator 各一徽章 |
| `feedback.type == immediate`（quiz） | 提交后原地展开 `.feedback-panel` + 主按钮重标为「下一题」 | 二段式 |
| `feedback.next_action` | 主按钮/反馈面板的引导文案 | 语义指向下一步 |
| `density.zones` | 内容区按 zone 垂直堆叠 `.zone` | ≤ 4 个 |
| `jumps[]`（非 primary/back/tab） | 对应触发元素加 `data-target` | 如章节条目、卡片点击 |

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

    <!-- ============ 屏 1 · home（示例，按规范填） ============ -->
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
    if(!el){ console.warn('未定义页:',id); return; }   // R4.2 悬空 target 的运行时保护
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

## 四、各页面类型填充配方

> 骨架不变，按 type 填内容区与操作栏。下面给出每类的最小填充要点。

### `home`
- 顶部：问候 + `progress-row` 放 streak / today_minutes 徽章。
- 主区：**继续学习大卡**（`continue-card`），点击直达核心活动页（满足 R2.1/R2.2）。
- `action-bar`：primary = 继续学习（带 status 进度）。
- `tabbar`：设 `data-tabbar="true"`，放 3–5 个 Tab。

### `course_detail`
- `topbar` 带 back（`back_target`）。
- 内容区：封面 + 简介 + **章节树**（`chapter` 行，标 done/now/lock）。
- `action-bar`：单一 primary「开始/继续学习」；次要收藏/分享用 `btn-sec` 图标行，**不与 primary 等大**（R1.4）。

### `learning`
- `topbar`：back + 章节定位 locator（`chapter_locator`，满足 R7.2）。
- 主区：媒体播放区（占视觉中心）+ 要点；**不塞推荐/广告**。
- `action-bar`：primary「完成并继续」+ 笔记/目录 `btn-sec`。

### `quiz`
- 一次一题：`.q-stem` + 若干 `.opt`。
- `action-bar` primary 为二段式：`data-behavior="submit"` → 提交后展开 `.feedback-panel`（对错+解析）→ 重标「下一题」→ 最后一题 `go('result_page')`。
- 满足 R5.1（immediate）、R5.2（next_action）。

### `result`
- `score-ring`（`--p`=百分比）+ 掌握情况区。
- `action-bar`：**primary「继续下一节」（正向出口，绝不可省，R4.3）** + 重做/返回 `btn-sec`。

### `profile`
- `topbar` 无 back（level1）；`data-tabbar="true"`。
- 头部数据 + 成就区 + 列表（我的课程/错题本/统计），条目 `data-target` 到子页。

### `list`（course_list / my_courses / mistake_book）
- `topbar` 带 back。
- 内容区：列表条目，每条 `data-target` → 对应详情/重做页。
- `action-bar` primary = 进入/继续。

### `modal`（note_modal / chapter_drawer / hint_modal）
- 用 `.modal-mask` + `.modal-sheet`；**必须有关闭**（✕ 或 `data-target` 回原页），满足 R4.4。
- 触发它的元素 `onclick="openModal('id')"`。

---

## 五、渲染检查清单（交付前过一遍）

- [ ] 每个规范里的 `page.id` 都有对应 `<section id="...">`；反之无多余屏。
- [ ] 每个 `primary_action.target`、`jumps[].target`、`back_target`、tab `data-target` 都指向已存在的屏（悬空会触发 JS 的 `console.warn`）。
- [ ] primary 全宽最强，secondary 降权为图标行（无等大并排）。
- [ ] `level≠1` 的屏都有 back；`level==1` 的屏都有 tabbar。
- [ ] quiz 是二段式即时反馈；result 有正向出口 primary。
- [ ] `target==null` 的行为按钮用 `data-behavior`，不误加 `data-target`。
- [ ] 页面地图能跳到任意屏；Tab 高亮随当前屏切换。
