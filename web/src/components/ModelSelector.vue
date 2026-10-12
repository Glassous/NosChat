<template>
  <div class="model-selector" ref="rootRef">
    <button
      class="model-trigger"
      :class="{ open: open }"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click="toggle"
    >
      <span class="model-avatar" :style="{ background: current.color }">{{ current.icon }}</span>
      <span class="model-meta">
        <span class="model-name">{{ current.name }}</span>
        <span class="model-sub">{{ current.provider }} · {{ current.context }} · {{ current.released }}</span>
      </span>
      <span class="chevron" :class="{ up: open }">⌄</span>
    </button>

    <Transition name="panel">
      <div v-if="open" class="model-panel" role="listbox" :aria-label="panelLabel">
        <div class="panel-head">
          <input
            v-model.trim="keyword"
            class="panel-search"
            type="search"
            placeholder="搜索模型 / 厂商 / 发布日期…"
            aria-label="搜索模型"
            @keydown.esc="close"
          />
          <span class="panel-count">{{ filtered.length }}/{{ models.length }}</span>
        </div>

        <div class="panel-tools">
          <span class="tools-label">排序</span>
          <div class="tools-group" role="group" aria-label="模型排序方式">
            <button
              v-for="opt in sortOptions"
              :key="opt.value"
              type="button"
              class="sort-pill"
              :class="{ on: sort === opt.value }"
              :aria-pressed="sort === opt.value"
              @click="sort = opt.value"
            >{{ opt.label }}</button>
          </div>
          <span class="tools-hint">{{ sortHint }}</span>
        </div>

        <ul class="model-list">
          <li v-if="filtered.length === 0" class="model-empty">没有匹配的模型</li>
          <li v-for="model in filtered" :key="model.id">
            <button
              class="model-option"
              :class="{ selected: model.id === current.id }"
              role="option"
              :aria-selected="model.id === current.id"
              @click="pick(model)"
            >
              <span class="model-avatar" :style="{ background: model.color }">{{ model.icon }}</span>
              <span class="option-body">
                <span class="option-top">
                  <span class="option-name">{{ model.name }}</span>
                  <span v-if="model.badge" class="option-badge">{{ model.badge }}</span>
                  <span
                    v-if="model.released"
                    class="option-date"
                    :title="`发布日期：${model.released}`"
                  >{{ model.released }}</span>
                </span>
                <span class="option-desc">{{ model.desc }}</span>
                <span class="option-tags">
                  <span class="tag" v-for="t in model.tags" :key="t">{{ t }}</span>
                  <span class="tag muted">上下文 {{ model.context }}</span>
                  <span v-if="model.released" class="tag muted">{{ relRelease(model.released) }}</span>
                </span>
                <span class="option-bars">
                  <span class="bar-label">速度</span>
                  <span class="bar"><i :style="{ width: model.speed * 20 + '%' }"></i></span>
                  <span class="bar-label">能力</span>
                  <span class="bar"><i class="alt" :style="{ width: model.intelligence * 20 + '%' }"></i></span>
                </span>
              </span>
              <span v-if="model.id === current.id" class="option-check">✓</span>
            </button>
          </li>
        </ul>

        <div class="panel-foot">
          <span class="foot-tip">回复为本地模拟，切换模型会改变话术与延迟；发布日期为演示数据</span>
        </div>
      </div>
    </Transition>

    <div v-if="open" class="panel-backdrop" @click="close"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { relRelease, sortModels } from '../data/models.js'

const props = defineProps({
  models: { type: Array, required: true },
  modelValue: { type: String, required: true },
  panelLabel: { type: String, default: '选择模型' }
})

const emit = defineEmits(['update:modelValue', 'change'])

const rootRef = ref(null)
const open = ref(false)
const keyword = ref('')
const sort = ref('default')

const sortOptions = [
  { value: 'default', label: '推荐' },
  { value: 'newest', label: '最新' },
  { value: 'oldest', label: '最早' }
]

const sortHint = computed(() => {
  if (sort.value === 'newest') return '按发布日期倒序'
  if (sort.value === 'oldest') return '按发布日期正序'
  return '默认顺序，可切到发布日期'
})

const current = computed(
  () => props.models.find(m => m.id === props.modelValue) || props.models[0]
)

/** 发布日期（ISO）→ 可比较的时间戳；缺失或非法排到最后 */
function releaseTs(model) {
  const ts = Date.parse(`${model.released || ''}T00:00:00`)
  return Number.isNaN(ts) ? -Infinity : ts
}

const sorted = computed(() => {
  if (sort.value === 'default') return props.models
  const list = [...props.models]
  list.sort((a, b) =>
    sort.value === 'newest'
      ? releaseTs(b) - releaseTs(a)
      : releaseTs(a) - releaseTs(b)
  )
  return list
})

const filtered = computed(() => {
  const kw = keyword.value.toLowerCase()
  if (!kw) return sorted.value
  return sorted.value.filter(m =>
    [m.name, m.provider, m.desc, ...(m.tags || []), m.released, relRelease(m.released)]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(kw)
  )
})

function toggle() {
  open.value = !open.value
  if (open.value) document.addEventListener('keydown', onKey)
}

function close() {
  open.value = false
  keyword.value = ''
  document.removeEventListener('keydown', onKey)
}

function onKey(e) {
  if (e.key === 'Escape') close()
}

function pick(model) {
  if (model.id !== props.modelValue) {
    emit('update:modelValue', model.id)
    emit('change', model)
  }
  close()
}

watch(current, m => {
  if (!open.value) keyword.value = ''
})

onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<style scoped>
.model-selector {
  position: relative;
}

.model-trigger {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #1e293b;
  min-height: 44px;
  max-width: 240px;
}

.model-trigger:hover,
.model-trigger.open {
  background: #f8fafc;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.model-avatar {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  border-radius: 0.5rem;
  display: grid;
  place-items: center;
  font-size: 0.95rem;
  color: #fff;
}

.model-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  flex: 1;
  min-width: 0;
  line-height: 1.2;
}

.model-name {
  font-size: 0.8rem;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}

.model-sub {
  font-size: 0.65rem;
  color: #64748b;
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chevron {
  font-size: 0.85rem;
  color: #94a3b8;
  transition: transform 0.2s ease;
}

.chevron.up {
  transform: rotate(180deg);
}

.panel-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: transparent;
}

.model-panel {
  position: absolute;
  z-index: 50;
  top: calc(100% + 8px);
  right: 0;
  width: 380px;
  max-width: calc(100vw - 24px);
  background: #fff;
  border-radius: 1rem;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.28);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 0.85rem;
  border-bottom: 1px solid #eef2f7;
}

.panel-search {
  flex: 1;
  min-width: 0;
  padding: 0.45rem 0.7rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.6rem;
  font-size: 0.8rem;
  color: #1e293b;
  outline: none;
}

.panel-search:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.12);
}

.panel-count {
  font-size: 0.7rem;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}

/* 排序工具条：默认顺序 / 按发布日期 */
.panel-tools {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.85rem;
  border-bottom: 1px solid #eef2f7;
  background: #fbfcfe;
}

.tools-label {
  font-size: 0.66rem;
  color: #94a3b8;
  white-space: nowrap;
}

.tools-group {
  display: flex;
  gap: 0.2rem;
  padding: 2px;
  background: #eef2f7;
  border-radius: 999px;
}

.sort-pill {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 0.66rem;
  font-weight: 600;
  font-family: inherit;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s ease, color 0.15s ease;
}

.sort-pill:hover {
  color: #334155;
}

.sort-pill:focus-visible {
  outline: 2px solid #667eea;
  outline-offset: 1px;
}

.sort-pill.on {
  background: #fff;
  color: #4f46e5;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
}

.tools-hint {
  margin-left: auto;
  font-size: 0.62rem;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-list {
  list-style: none;
  overflow-y: auto;
  max-height: 56vh;
  padding: 0.35rem;
  -webkit-overflow-scrolling: touch;
}

.model-empty {
  padding: 1.5rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.8rem;
}

.model-option {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.65rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 0.75rem;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.model-option:hover {
  background: #f6f8fb;
}

.model-option.selected {
  background: linear-gradient(135deg, #667eea12, #764ba212);
  border-color: #667eea55;
}

.option-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.option-top {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.option-name {
  font-size: 0.83rem;
  font-weight: 600;
  color: #1e293b;
}

.option-badge {
  font-size: 0.6rem;
  font-weight: 700;
  color: #667eea;
  background: #667eea18;
  padding: 0.1rem 0.35rem;
  border-radius: 999px;
  white-space: nowrap;
}

/* 发布日期：右对齐，等宽数字便于纵向比较 */
.option-date {
  margin-left: auto;
  font-size: 0.63rem;
  font-weight: 600;
  color: #94a3b8;
  background: #f1f5f9;
  border-radius: 0.35rem;
  padding: 0.08rem 0.35rem;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  flex: 0 0 auto;
}

.model-option.selected .option-date {
  color: #667eea;
  background: #667eea14;
}

.option-desc {
  font-size: 0.72rem;
  color: #64748b;
  line-height: 1.45;
}

.option-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.tag {
  font-size: 0.62rem;
  color: #475569;
  background: #f1f5f9;
  border-radius: 999px;
  padding: 0.1rem 0.4rem;
}

.tag.muted {
  color: #94a3b8;
  background: transparent;
  border: 1px dashed #e2e8f0;
}

.option-bars {
  display: grid;
  grid-template-columns: auto 1fr auto 1fr;
  align-items: center;
  gap: 0.35rem;
}

.bar-label {
  font-size: 0.6rem;
  color: #94a3b8;
}

.bar {
  height: 4px;
  background: #eef2f7;
  border-radius: 999px;
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 999px;
  transition: width 0.35s ease;
}

.bar i.alt {
  background: linear-gradient(90deg, #10b981, #38bdf8);
}

.option-check {
  color: #667eea;
  font-weight: 700;
  font-size: 0.9rem;
  margin-top: 0.2rem;
}

.panel-foot {
  padding: 0.5rem 0.85rem;
  border-top: 1px solid #eef2f7;
  background: #fbfcfe;
}

.foot-tip {
  font-size: 0.65rem;
  color: #94a3b8;
}

.panel-enter-active,
.panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}

/* 平板：下拉面板收窄 */
@media (max-width: 860px) {
  .model-panel {
    width: 320px;
  }
}

/* 手机：改为底部弹层，避免面板被裁切 */
@media (max-width: 640px) {
  .model-trigger {
    max-width: 168px;
    padding: 0.35rem 0.5rem;
  }

  .model-sub {
    display: none;
  }

  .model-panel {
    position: fixed;
    top: auto;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    max-width: none;
    border-radius: 1.25rem 1.25rem 0 0;
    padding-bottom: env(safe-area-inset-bottom, 0px);
    max-height: 82vh;
  }

  .panel-backdrop {
    background: rgba(15, 23, 42, 0.45);
  }

  /* 弹层顶部加拖拽提示条，明确是可下滑关闭的抽屉 */
  .model-panel::before {
    content: '';
    display: block;
    width: 36px;
    height: 4px;
    border-radius: 999px;
    background: #e2e8f0;
    margin: 0.5rem auto -0.25rem;
  }

  .model-list {
    max-height: 58vh;
  }

  .model-option {
    padding: 0.75rem 0.6rem;
    border-bottom: 1px solid #f1f5f9;
    border-radius: 0;
  }

  .option-bars {
    display: none;
  }

  .panel-tools {
    padding: 0.45rem 0.7rem;
  }

  .panel-enter-from,
  .panel-leave-to {
    opacity: 0;
    transform: translateY(24px);
  }
}

@media (max-width: 420px) {
  .tools-hint {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .model-panel,
  .chevron,
  .bar i {
    transition: none !important;
  }
}
</style>
