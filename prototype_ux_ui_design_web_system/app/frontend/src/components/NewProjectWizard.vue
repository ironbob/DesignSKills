<script setup lang="ts">
// S2 新建向导（参照 07-hifi/s2-new-wizard.html 两帧）：步1 产品+需求文档 → 步2 端与画布锁定（R8）
import { ref } from 'vue'
import { PLATFORM_PRESETS, type Platform } from '@/api/client'
import { useProductsStore } from '@/stores/products'
import { useUiStore } from '@/stores/ui'

const emit = defineEmits<{ close: [] }>()
const products = useProductsStore()
const ui = useUiStore()

const step = ref<1 | 2>(1)
const name = ref('')
const doc = ref('')
const docName = ref('')
const platform = ref<Platform>('mobile_app')
const projectName = ref('')
const submitting = ref(false)
const error = ref('')

function pickFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  docName.value = file.name
  const reader = new FileReader()
  reader.onload = () => (doc.value = String(reader.result ?? ''))
  reader.readAsText(file)
}

function choosePlatform(p: Platform) {
  platform.value = p
  projectName.value = PLATFORM_PRESETS[p].label
}

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const product = await products.createProduct({
      name: name.value.trim(),
      requirement_doc: doc.value,
      project: { name: projectName.value || PLATFORM_PRESETS[platform.value].label, platform: platform.value },
    })
    emit('close')
    ui.openWorkbench(product.projects[0].id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="overlay">
    <div class="dialog">
      <div class="steps">
        <span class="st" :class="step === 1 ? 'on' : 'did'">
          <span class="num">{{ step === 1 ? '1' : '✓' }}</span>产品与需求文档
        </span>
        <span class="bar"></span>
        <span class="st" :class="step === 2 ? 'on' : ''"><span class="num">2</span>端与画布</span>
      </div>

      <template v-if="step === 1">
        <h3>新建产品</h3>
        <p class="sub">一个产品可挂多个端项目，共用同一份需求文档——先建产品，端项目下一步选。</p>
        <label class="f-label">产品名称</label>
        <input v-model="name" class="in focus" placeholder="如：二胡练习伴侣" />
        <label class="f-label">需求文档（产品级共享）</label>
        <label class="drop" :class="{ ok: !!docName }">
          <template v-if="docName"><span class="okmark">✓ 已接收</span> <b>{{ docName }}</b><br />可重新选择文件（markdown / 文本）</template>
          <template v-else>选择或拖入需求文档：markdown / 文本<br />文档越全（用户／场景／规则），阶段 1 的问题越少</template>
          <input type="file" accept=".md,.txt,.markdown" @change="pickFile" />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="dfoot">
          <button class="btn" @click="emit('close')">取消</button>
          <span class="sp"></span>
          <button class="btn pri" :disabled="!name.trim() || !doc" @click="step = 2">下一步 · 选端 →</button>
        </div>
      </template>

      <template v-else>
        <h3>新建端项目 · {{ name }}</h3>
        <p class="sub">一项目锁一端（R8）：画布、HTML 公约、gate 参数随端锁定，之后不可改（要改=新建端项目）。</p>
        <div class="devs">
          <button
            v-for="(preset, key) in PLATFORM_PRESETS"
            :key="key"
            class="dev"
            :class="{ sel: platform === key }"
            @click="choosePlatform(key as Platform)"
          >
            {{ preset.label }}
            <span class="cv">{{ preset.width }} × {{ preset.height }}</span>
          </button>
        </div>
        <label class="f-label">项目名（默认=端名）</label>
        <input v-model="projectName" class="in" />
        <div class="dfoot">
          <button class="btn" @click="step = 1">← 上一步</button>
          <span class="sp"></span>
          <button class="btn pri" :disabled="submitting" @click="submit">
            {{ submitting ? '创建中…' : '创建并开始阶段 1' }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
  z-index: 40;
}
.dialog {
  width: 640px;
  background: #fff;
  border-radius: var(--r-panel);
  padding: 26px 30px;
  box-shadow: 0 12px 40px rgba(25, 27, 31, 0.18);
}
.steps { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--ink-weak); margin-bottom: 18px; }
.steps .st { display: flex; gap: 7px; align-items: center; }
.steps .num {
  width: 20px; height: 20px; border-radius: 50%;
  border: 1px solid #c7cbd3; text-align: center; line-height: 20px; font-size: 11px;
}
.steps .on { color: var(--accent); font-weight: 700; }
.steps .on .num { background: var(--accent); border-color: var(--accent); color: #fff; }
.steps .did .num { background: var(--ink); border-color: var(--ink); color: #fff; }
.steps .bar { width: 40px; height: 1px; background: #d6dae1; }
h3 { margin: 0 0 4px; font-size: 18px; font-weight: 800; }
.sub { font-size: 12px; color: var(--ink-weak); margin: 0 0 18px; line-height: 1.7; }
.f-label { display: block; font-size: 12px; color: #4b5563; font-weight: 700; margin: 12px 0 6px; }
.in {
  width: 100%;
  border: 1px solid #c7cbd3;
  border-radius: var(--r-small);
  padding: 10px 13px;
  font-size: var(--fs-body);
  background: #fff;
}
.in.focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-surface); }
.drop {
  display: block;
  border: 1.5px dashed #c7cbd3;
  border-radius: var(--r-card);
  padding: 22px;
  text-align: center;
  font-size: var(--fs-body);
  color: var(--ink-weak);
  background: var(--surface);
  line-height: 1.9;
  cursor: pointer;
}
.drop.ok { border-style: solid; border-color: var(--sem-pass-line); background: var(--sem-pass-surface); }
.drop b { color: #374151; }
.okmark { color: var(--sem-pass); font-weight: 700; }
.drop input { display: none; }
.devs { display: flex; gap: 14px; margin: 6px 0 4px; }
.dev {
  flex: 1;
  border: 1.5px solid var(--line);
  border-radius: 10px;
  padding: 14px;
  text-align: center;
  font-size: var(--fs-body);
  color: #4b5563;
  background: #fff;
  cursor: pointer;
}
.dev .cv { display: block; font-size: 11px; color: #9ca3af; margin-top: 5px; }
.dev.sel { border-color: var(--accent); background: var(--accent-surface); font-weight: 700; }
.dev.sel .cv { color: var(--accent); }
.error { color: var(--danger); font-size: 12px; }
.dfoot { display: flex; gap: 10px; margin-top: 20px; align-items: center; }
.sp { flex: 1; }
.btn {
  border: 1px solid #c7cbd3;
  border-radius: var(--r-small);
  padding: 10px 18px;
  font-size: var(--fs-ui);
  background: #fff;
  color: #374151;
  cursor: pointer;
}
.btn.pri {
  background: var(--accent);
  color: #fff;
  font-weight: 700;
  border-color: var(--accent);
  min-width: 150px;
}
.btn.pri:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
