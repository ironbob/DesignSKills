<script setup lang="ts">
// S1 产品列表（参照 07-hifi/s1-products.html 两帧：卡片墙 + 空态）
import { onMounted, ref } from 'vue'
import TopBar from '@/components/TopBar.vue'
import NewProjectWizard from '@/components/NewProjectWizard.vue'
import { useProductsStore } from '@/stores/products'
import { useUiStore } from '@/stores/ui'
import { PLATFORM_PRESETS, type Platform } from '@/api/client'

const products = useProductsStore()
const ui = useUiStore()
const wizardOpen = ref(false)

onMounted(() => products.fetchAll())

function stageLine(p: { current_stage: number; stage_status: Record<string, string> }): { text: string; cls: string } {
  const st = p.stage_status[String(p.current_stage)] ?? 'locked'
  if (st === 'done') return { text: '✓ 九阶段全部完成', cls: 'done' }
  if (st === 'awaiting_decision') return { text: `▸ 阶段 ${p.current_stage} · 待拍板`, cls: 'wait' }
  if (st === 'running') return { text: `● 阶段 ${p.current_stage} · 进行中`, cls: 'run' }
  if (st === 'failed') return { text: `✕ 阶段 ${p.current_stage} · 受阻`, cls: 'fail' }
  return { text: `阶段 ${p.current_stage} · 未发起`, cls: 'idle' }
}
</script>

<template>
  <div class="page">
    <TopBar />
    <div class="pagehead">
      <h1>产品</h1>
      <span class="cnt" v-if="products.loaded">{{ products.products.length }} 个产品 · {{ products.totalProjects }} 个端项目</span>
      <span class="sp"></span>
      <button class="primary" @click="wizardOpen = true">＋ 新建产品</button>
    </div>

    <!-- 有数据：卡片墙 -->
    <div v-if="products.loaded && products.products.length" class="grid">
      <div v-for="p in products.products" :key="p.id" class="pcard">
        <h3>{{ p.name }}<span class="act">{{ p.updated_at }}</span></h3>
        <div v-for="proj in p.projects" :key="proj.id" class="proj">
          <span class="dev">{{ PLATFORM_PRESETS[proj.platform as Platform]?.label ?? proj.platform }}</span>
          <span class="st2" :class="stageLine(proj).cls">{{ stageLine(proj).text }}</span>
          <span class="go" :class="{ main: stageLine(proj).cls !== 'done' }" @click="ui.openWorkbench(proj.id)">
            {{ stageLine(proj).cls === 'done' ? '查看 →' : '进入 →' }}
          </span>
        </div>
        <div class="meta">
          <span>需求文档 <template v-if="p.requirement_doc">✓ {{ p.requirement_doc }}</template><template v-else>—</template></span>
        </div>
      </div>
      <div class="newcard" @click="wizardOpen = true">
        <span>＋ 新建产品</span>
        <span class="plus">一份需求文档 + 至少一个端项目<br />手机App（390×844）／ 桌面App（1280×800）／ Web系统（1440×900）</span>
      </div>
    </div>

    <!-- 空态：教育 + 不阻塞配置（09-spec S1 帧②） -->
    <div v-else-if="products.loaded" class="empty">
      <h2>从一份需求文档，到专家级设计稿</h2>
      <p>
        上传需求文档，AI 按九阶段推进：<b>它生成，你拍板，gate 守质量</b>。<br />
        需求文档写得越全（用户／场景／规则），阶段 1 的问题就越少。
      </p>
      <button class="primary big" @click="wizardOpen = true">＋ 新建第一个产品</button>
      <div class="hint">
        <span class="led"></span>
        <span>还没接入 AI 账号——不拦你：先建产品、传需求，发起第一个生成任务前配置即可</span>
        <span class="act">现在配置（约 2 分钟）</span>
      </div>
    </div>

    <div v-else class="empty">
      <p>{{ products.error ? `连接后端失败：${products.error}` : '加载中…' }}</p>
    </div>

    <NewProjectWizard v-if="wizardOpen" @close="wizardOpen = false" />
  </div>
</template>

<style scoped>
.page { height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.pagehead { display: flex; align-items: center; padding: var(--sp-4) 28px 6px; }
.pagehead h1 { margin: 0; font-size: var(--fs-display); font-weight: 800; }
.cnt { font-size: var(--fs-caption); color: var(--ink-weak); margin-left: 14px; }
.sp { flex: 1; }
.primary {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--r-small);
  padding: 11px 26px;
  font-size: var(--fs-body);
  font-weight: 700;
  cursor: pointer;
}
.primary.big { padding: 13px 36px; font-size: 15px; }
.grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px;
  padding: var(--sp-3) 28px 28px;
  align-content: start;
  overflow: auto;
}
.pcard {
  border: 1px solid var(--line);
  border-radius: var(--r-panel);
  padding: 18px 20px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pcard h3 { margin: 0; font-size: 18px; font-weight: 800; display: flex; align-items: baseline; gap: 12px; }
.pcard .act { font-size: 11px; color: #9ca3af; font-weight: 400; }
.proj {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-card);
  padding: 12px 14px;
  background: #fff;
  font-size: var(--fs-ui);
}
.proj:hover { border-color: var(--accent); }
.proj .dev {
  border: 1px solid #9aa0ac;
  border-radius: 5px;
  font-size: 11px;
  padding: 2px 8px;
  color: #4b5563;
  background: var(--surface);
}
.proj .st2 { font-weight: 700; }
.st2.run { color: var(--accent); }
.st2.wait { color: var(--sem-warn); }
.st2.fail { color: var(--danger); }
.st2.done { color: #374151; }
.st2.idle { color: var(--ink-weak); font-weight: 400; }
.proj .go {
  margin-left: auto;
  font-size: 12px;
  border: 1px solid #c7cbd3;
  border-radius: var(--r-small);
  padding: 7px 14px;
  color: #4b5563;
  background: #fff;
  cursor: pointer;
}
.proj .go.main { background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 700; }
.meta { font-size: var(--fs-caption); color: var(--ink-weak); }
.newcard {
  border: 2px dashed #c9cdd6;
  border-radius: var(--r-panel);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: #9ca3af;
  font-size: var(--fs-body);
  cursor: pointer;
  min-height: 160px;
}
.newcard .plus { font-size: 12px; color: var(--ink-weak); line-height: 1.8; text-align: center; }
.empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--sp-4);
  text-align: center;
  padding: var(--sp-3);
}
.empty h2 { margin: 0; font-size: var(--fs-display); font-weight: 800; }
.empty p { margin: 0; color: var(--ink-weak); font-size: var(--fs-body); line-height: 1.9; max-width: 560px; }
.empty p b { color: #374151; }
.hint {
  border: 1px solid var(--line);
  border-radius: var(--r-card);
  background: var(--surface);
  padding: 13px 20px;
  font-size: var(--fs-ui);
  color: #4b5563;
  display: flex;
  gap: 14px;
  align-items: center;
}
.hint .led { width: 9px; height: 9px; border-radius: 50%; background: #c9cdd6; flex: 0 0 auto; }
.hint .act {
  border: 1px solid #c7cbd3;
  border-radius: var(--r-small);
  padding: 7px 14px;
  font-size: 12px;
  background: #fff;
  flex: 0 0 auto;
  color: #374151;
  cursor: pointer;
}
</style>
