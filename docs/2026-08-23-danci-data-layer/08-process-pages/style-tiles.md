---
title: 主题档位对比 · Danci 数据层方案
---

<script setup>
import { ref, onUnmounted } from 'vue'
import { perfImprovement } from '../../.vitepress/data/danci.charts'

const preset = ref('brief')
const apply = (p) => {
  preset.value = p
  if (typeof document !== 'undefined') document.body.dataset.docPreset = p
}
apply('brief')
onUnmounted(() => {
  if (typeof document !== 'undefined') delete document.body.dataset.docPreset
})
</script>

<style>
.tile-switch {
  display: flex;
  gap: 10px;
  align-items: center;
  margin: 0.6rem 0 1.6rem;
  padding: 12px 16px;
  border: 1px solid var(--doc-line);
  border-radius: 12px;
  background: #f8fafc;
}
.tile-switch .q { font-size: 14px; color: var(--doc-muted); margin-right: auto; }
.tile-switch button {
  font: inherit;
  font-weight: 700;
  font-size: 14px;
  padding: 7px 18px;
  border-radius: 999px;
  border: 1.5px solid var(--doc-line);
  background: #fff;
  color: var(--doc-muted);
  cursor: pointer;
}
.tile-switch button.on {
  border-color: var(--doc-accent);
  color: var(--doc-accent);
  background: var(--doc-accent-weak);
}
</style>

<div class="tile-switch">
  <span class="q">评审会混合场合（会前细读 + 会上投屏），选哪个档位？点按钮切换，正文即整页换档——差异看气质：字阶 / 版心 / 衬线标题 / 密度 / 卡片感。</span>
  <button :class="{ on: preset === 'brief' }" @click="apply('brief')">A · 简报档</button>
  <button :class="{ on: preset === 'editorial' }" @click="apply('editorial')">B · 编辑档</button>
</div>

## 预研证据·存储性能

<p class="lead">真机同口径实测：五项核心指标全面改善，不是某项赢，是全面赢。</p>

<KpiRow :items="[
  { num: '310', unit: 'ms', label: '冷启动首次加载', delta: '-62%', deltaType: 'down-good' },
  { num: '1.8', unit: 's', label: '批量写入 1 万条', delta: '-61%', deltaType: 'down-good' },
  { num: '34', unit: 'ms', label: '复杂查询（SRS 调度）', delta: '-65%', deltaType: 'down-good' },
  { num: '148', unit: 'MB', label: '内存峰值', delta: '-30%', deltaType: 'down-good' },
]" />

<FigureChart
  :option="perfImprovement"
  caption="五项核心指标全面改善：查询 -65%、冷启动 -62%"
  source="iPhone 13 真机 · iOS 17.4 · Release · 5 万单词 + 120 万条学习记录 · 用户提供预研报告口径（评审前复核）"
  fallback="GRDB 相比 Core Data：查询 -65%、冷启动 -62%、写入 -61%、内存 -30%、体积 -17%"
  :height="260" />

<CompareMatrix
  :columns="['候选', '关键短板', '可翻案条件']"
  :rows="[
    { cells: ['SwiftData', '@Model 非 Sendable 限制多线程写入；iCloud 同步行为黑盒；无法精细控制迁移', '苹果放开并发模型与迁移控制'] },
    { cells: ['CloudKit', '同步冲突策略不可控；无法支持 Android 端未来规划', '冲突策略可配置且跨端纳入规划'] },
    { cells: ['Protobuf', '包体积 -38%，但需维护双端 schema，学习成本高于收益', '双端团队扩容、schema 工具链成熟'] },
  ]" />

<Callout type="conclusion">官方方案的便利买不回控制权——落选不是印象分，是三条硬伤与一个成本不等式。</Callout>

```mermaid
sequenceDiagram
    participant C as 客户端（GRDB）
    participant S as 服务端
    C->>C: 离线写入并记录操作（断网 24h 累积 2,300 条）
    C->>S: 恢复联网，按 updated_at 游标上行批量推送
    S-->>C: 返回服务端最新数据与时间戳
    alt 存在冲突（0.4%）
        C->>C: 服务端时间戳优先，自动覆盖本地
    end
    C->>C: 完成全量上行合并（3.2 s）
```
