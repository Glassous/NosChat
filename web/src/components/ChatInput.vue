<template>
  <div class="chat-input">
    <!-- 额度用尽：后端会直接拒绝请求，这里同步锁定输入并说明重置时间 -->
    <div v-if="quotaExceeded" class="quota-bar" role="status">
      <span class="quota-ic">🔒</span>
      <span class="quota-text">
        今日输出 token 已达上限（{{ quotaLimitText }}），将于 {{ quotaResetLabel || '次日' }} 重置
      </span>
    </div>

    <div v-else-if="model" class="input-model-bar">
      <span class="im-avatar" :style="{ background: model.color }">{{ model.icon }}</span>
      <span class="im-name">{{ model.name }}</span>
      <span class="im-tags">
        <span class="im-tag" v-for="t in model.tags.slice(0, 2)" :key="t">{{ t }}</span>
      </span>
      <span v-if="model.reasoning" class="im-think">回复含深度思考</span>
      <span v-if="model.released" class="im-release">发布于 {{ model.released }}</span>
      <span class="im-latency">模拟响应 {{ (model.latency[0] / 1000).toFixed(1) }}–{{ (model.latency[1] / 1000).toFixed(1) }}s</span>
    </div>

    <div class="input-container">
      <div class="input-actions">
        <button class="action-btn" title="附加文件" aria-label="附加文件" :disabled="quotaExceeded">📎</button>
        <button class="action-btn" title="表情符号" aria-label="表情符号" :disabled="quotaExceeded">😊</button>
      </div>

      <div class="input-wrapper">
        <textarea
          ref="textareaRef"
          v-model="localValue"
          :placeholder="placeholderText"
          :disabled="disabled"
          maxlength="4000"
          rows="1"
          class="message-textarea"
          aria-label="消息输入框"
          @keydown.enter.prevent="handleEnter"
          @input="adjustHeight"
        />

        <div class="input-hints">
          <span class="hint-text desktop-only">按 Enter 发送，Shift + Enter 换行</span>
          <span class="hint-text mobile-only">点击右下角发送</span>
          <span class="char-count" :class="countClass">{{ localValue.length }}/4000</span>
        </div>
      </div>

      <div class="send-actions">
        <button
          class="send-btn"
          :disabled="!canSend || disabled"
          :class="{ loading }"
          @click="handleSend"
          title="发送消息"
          aria-label="发送消息"
        >
          <span v-if="loading" class="send-loading">⏳</span>
          <span v-else>🚀</span>
        </button>
      </div>
    </div>

    <div v-if="showQuickActions && !quotaExceeded" class="quick-actions">
      <button class="quick-action-btn" @click="insertSuggestion('你好！')">👋 打招呼</button>
      <button class="quick-action-btn" @click="insertSuggestion('谢谢！')">🙏 表示感谢</button>
      <button class="quick-action-btn" @click="insertSuggestion('请详细说明')">💡 请求解释</button>
      <button class="quick-action-btn" @click="insertSuggestion('举个例子')">🔍 请求示例</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '输入消息…'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  model: {
    type: Object,
    default: null
  },
  // 当日输出 token 额度是否已用尽（由后端判定，前端只做锁定与提示）
  quotaExceeded: {
    type: Boolean,
    default: false
  },
  quotaLimit: {
    type: Number,
    default: 0
  },
  // 后端给出的重置时刻文案（已按其时区格式化）
  quotaResetLabel: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'send'])

const textareaRef = ref(null)
const localValue = ref(props.modelValue)
const showQuickActions = ref(true)

// 单条消息上限与后端 ChatStreamRequest.content max_length 保持一致
const MAX_LENGTH = 4000

const quotaLimitText = computed(() =>
  props.quotaLimit > 0 ? props.quotaLimit.toLocaleString('en-US') : '已用尽'
)

/** 额度用尽时给出明确原因，而不是笼统的禁用态 */
const placeholderText = computed(() => {
  if (!props.quotaExceeded) return props.placeholder
  return props.quotaResetLabel
    ? `今日输出 token 已达上限，将于 ${props.quotaResetLabel} 重置`
    : '今日输出 token 已达上限，请等待重置'
})

const canSend = computed(() => {
  if (props.quotaExceeded) return false
  return localValue.value.trim().length > 0 && localValue.value.length <= MAX_LENGTH
})

const countClass = computed(() => {
  const len = localValue.value.length
  if (len >= MAX_LENGTH) return 'error'
  if (len >= MAX_LENGTH * 0.85) return 'warning'
  return ''
})

// 父级清空/填充输入框时同步（发送后重置、点击快捷建议）
watch(
  () => props.modelValue,
  value => {
    if (value === localValue.value) return
    localValue.value = value
    adjustHeight()
  }
)

function adjustHeight() {
  nextTick(() => {
    const el = textareaRef.value
    if (!el) return

    el.style.height = 'auto'
    const scrollHeight = el.scrollHeight
    const maxHeight = 160

    if (scrollHeight > maxHeight) {
      el.style.height = `${maxHeight}px`
      el.style.overflowY = 'auto'
    } else {
      el.style.height = `${scrollHeight}px`
      el.style.overflowY = 'hidden'
    }

    emit('update:modelValue', localValue.value)
    showQuickActions.value = localValue.value.trim().length === 0
  })
}

function handleEnter(event) {
  if (event.shiftKey) {
    const cursorPosition = textareaRef.value.selectionStart
    const text = localValue.value
    localValue.value = `${text.slice(0, cursorPosition)}\n${text.slice(cursorPosition)}`

    nextTick(() => {
      const el = textareaRef.value
      if (!el) return
      el.selectionStart = el.selectionEnd = cursorPosition + 1
      adjustHeight()
    })
  } else if (canSend.value && !props.disabled) {
    handleSend()
  }
}

function handleSend() {
  if (!canSend.value || props.disabled) return
  emit('send', localValue.value.trim())
  // 父级通常会把 modelValue 置空；这里兜底清空，避免文字残留
  localValue.value = ''
  adjustHeight()
}

function insertSuggestion(text) {
  localValue.value = text
  adjustHeight()
  nextTick(() => {
    textareaRef.value?.focus()
    showQuickActions.value = false
  })
}

onMounted(() => {
  adjustHeight()
})
</script>

<style scoped>
.chat-input {
  padding: clamp(0.75rem, 2.5vw, 1.5rem);
  padding-bottom: calc(clamp(0.75rem, 2.5vw, 1.5rem) + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid #e2e8f0;
  background: white;
  flex: 0 0 auto;
}

.input-model-bar {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.6rem;
  font-size: 0.72rem;
  color: #64748b;
}

/* 额度用尽提示条：替换模型信息条位置，保持输入区高度稳定 */
.quota-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.6rem;
  padding: 0.55rem 0.75rem;
  border-radius: 0.6rem;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  color: #92400e;
  font-size: 0.75rem;
  line-height: 1.4;
}

.quota-ic {
  flex: 0 0 auto;
  font-size: 0.85rem;
}

.quota-text {
  min-width: 0;
}

.im-avatar {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  border-radius: 0.3rem;
  display: grid;
  place-items: center;
  font-size: 0.7rem;
}

.im-name {
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
}

.im-tags {
  display: flex;
  gap: 0.25rem;
  overflow: hidden;
}

.im-tag {
  font-size: 0.62rem;
  background: #f1f5f9;
  border-radius: 999px;
  padding: 0.05rem 0.35rem;
  white-space: nowrap;
}

.im-latency {
  margin-left: auto;
  font-size: 0.62rem;
  color: #94a3b8;
  white-space: nowrap;
}

.im-think {
  font-size: 0.62rem;
  color: #4f46e5;
  background: #667eea14;
  border-radius: 999px;
  padding: 0.05rem 0.4rem;
  white-space: nowrap;
}

.im-release {
  font-size: 0.62rem;
  color: #94a3b8;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.input-container {
  display: flex;
  align-items: flex-end;
  gap: 0.6rem;
}

.input-actions {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.action-btn {
  width: 42px;
  height: 42px;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 0.75rem;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.action-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-wrapper {
  flex: 1;
  position: relative;
  min-width: 0;
}

.message-textarea {
  width: 100%;
  padding: 0.9rem 0.9rem 2rem;
  border: 2px solid #e2e8f0;
  border-radius: 1rem;
  font-family: inherit;
  /* 移动端保持 16px，避免 iOS 聚焦时自动放大页面 */
  font-size: 16px;
  line-height: 1.5;
  resize: none;
  outline: none;
  transition: border-color 0.2s ease;
  background: white;
  color: #1e293b;
  max-height: 160px;
}

@media (min-width: 769px) {
  .message-textarea {
    font-size: 0.875rem;
  }
}

.message-textarea:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.message-textarea:disabled {
  background: #f8fafc;
  cursor: not-allowed;
  opacity: 0.7;
}

.message-textarea::placeholder {
  color: #94a3b8;
}

.input-hints {
  position: absolute;
  bottom: 0.5rem;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  padding: 0 0.9rem;
  pointer-events: none;
}

.hint-text {
  font-size: 0.68rem;
  color: #94a3b8;
}

.mobile-only {
  display: none;
}

.char-count {
  font-size: 0.68rem;
  color: #94a3b8;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.char-count.warning {
  color: #f59e0b;
}

.char-count.error {
  color: #ef4444;
}

.send-actions {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.send-btn {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 1rem;
  font-size: 1.25rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  padding: 0;
}

.send-btn:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn.loading {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.send-loading {
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.quick-actions {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.75rem;
  flex-wrap: wrap;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.quick-action-btn {
  padding: 0.4rem 0.85rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 9999px;
  font-size: 0.72rem;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-family: inherit;
  min-height: 34px;
}

.quick-action-btn:hover {
  background: #e2e8f0;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

@media (max-width: 768px) {
  .input-container {
    flex-wrap: wrap;
  }

  .input-wrapper {
    order: 1;
    flex: 1 1 auto;
  }

  .send-actions {
    order: 2;
  }

  .input-actions {
    order: 3;
    width: 100%;
    flex-direction: row;
    justify-content: flex-start;
  }

  .action-btn {
    width: 40px;
    height: 40px;
    font-size: 0.9rem;
  }

  .send-btn {
    width: 46px;
    height: 46px;
    font-size: 1.1rem;
  }

  .desktop-only {
    display: none;
  }

  .mobile-only {
    display: inline;
  }

  .quick-actions {
    gap: 0.3rem;
  }

  .quick-action-btn {
    padding: 0.35rem 0.7rem;
    font-size: 0.68rem;
  }

  .im-latency,
  .im-tags,
  .im-release {
    display: none;
  }
}

@media (max-width: 420px) {
  .input-hints {
    padding: 0 0.75rem;
  }

  .message-textarea {
    padding: 0.75rem 0.75rem 1.9rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .send-btn,
  .quick-action-btn,
  .action-btn {
    transition: none;
  }

  .send-btn.loading,
  .send-loading {
    animation: none;
  }

  .quick-actions {
    animation: none;
  }
}
</style>
