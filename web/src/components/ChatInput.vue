<template>
  <div class="chat-input">
    <div class="input-container">
      <div class="input-actions">
        <button class="action-btn" title="附加文件">
          📎
        </button>
        <button class="action-btn" title="表情符号">
          😊
        </button>
      </div>
      
      <div class="input-wrapper">
        <textarea
          ref="textareaRef"
          v-model="localValue"
          :placeholder="placeholder"
          :disabled="disabled"
          @keydown.enter.prevent="handleEnter"
          @input="adjustHeight"
          rows="1"
          class="message-textarea"
        />
        
        <div class="input-hints">
          <span class="hint-text">按 Enter 发送，Shift + Enter 换行</span>
          <span class="char-count">{{ localValue.length }}/1000</span>
        </div>
      </div>
      
      <div class="send-actions">
        <button 
          class="send-btn" 
          :disabled="!canSend || disabled"
          @click="handleSend"
          :class="{ loading: loading }"
          title="发送消息"
        >
          <span v-if="loading" class="send-loading">⏳</span>
          <span v-else>🚀</span>
        </button>
      </div>
    </div>
    
    <div v-if="showQuickActions" class="quick-actions">
      <button class="quick-action-btn" @click="insertSuggestion('你好！')">👋 打招呼</button>
      <button class="quick-action-btn" @click="insertSuggestion('谢谢！')">🙏 表示感谢</button>
      <button class="quick-action-btn" @click="insertSuggestion('请详细说明')">💡 请求解释</button>
      <button class="quick-action-btn" @click="insertSuggestion('举个例子')">🔍 请求示例</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '输入消息...'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'send'])

const textareaRef = ref(null)
const localValue = ref(props.modelValue)
const showQuickActions = ref(true)

const canSend = computed(() => {
  return localValue.value.trim().length > 0 && localValue.value.length <= 1000
})

function adjustHeight() {
  nextTick(() => {
    if (!textareaRef.value) return
    
    textareaRef.value.style.height = 'auto'
    const scrollHeight = textareaRef.value.scrollHeight
    const maxHeight = 150
    
    if (scrollHeight > maxHeight) {
      textareaRef.value.style.height = maxHeight + 'px'
      textareaRef.value.style.overflowY = 'auto'
    } else {
      textareaRef.value.style.height = scrollHeight + 'px'
      textareaRef.value.style.overflowY = 'hidden'
    }
    
    emit('update:modelValue', localValue.value)
    
    // 隐藏快捷操作当有内容时
    showQuickActions.value = localValue.value.trim().length === 0
  })
}

function handleEnter(event) {
  if (event.shiftKey) {
    // Shift + Enter: 插入换行
    const cursorPosition = textareaRef.value.selectionStart
    const text = localValue.value
    localValue.value = text.substring(0, cursorPosition) + '\n' + text.substring(cursorPosition)
    
    nextTick(() => {
      textareaRef.value.selectionStart = textareaRef.value.selectionEnd = cursorPosition + 1
      adjustHeight()
    })
  } else {
    // Enter: 发送消息
    if (canSend.value && !props.disabled) {
      handleSend()
    }
  }
}

function handleSend() {
  if (!canSend.value || props.disabled) return
  
  emit('send', localValue.value.trim())
}

function insertSuggestion(text) {
  localValue.value = text
  adjustHeight()
  nextTick(() => {
    textareaRef.value.focus()
    
    // 在插入建议后自动隐藏快捷操作
    showQuickActions.value = false
  })
}

onMounted(() => {
  adjustHeight()
})
</script>

<style scoped>
.chat-input {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  background: white;
}

.input-container {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
}

.input-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.action-btn {
  width: 40px;
  height: 40px;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 0.75rem;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.input-wrapper {
  flex: 1;
  position: relative;
}

.message-textarea {
  width: 100%;
  padding: 1rem 1rem 2.5rem;
  border: 2px solid #e2e8f0;
  border-radius: 1rem;
  font-family: inherit;
  font-size: 0.875rem;
  line-height: 1.5;
  resize: none;
  outline: none;
  transition: border-color 0.2s ease;
  background: white;
  color: #1e293b;
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
  padding: 0 1rem;
  pointer-events: none;
}

.hint-text {
  font-size: 0.7rem;
  color: #94a3b8;
}

.char-count {
  font-size: 0.7rem;
  color: #94a3b8;
  font-weight: 500;
}

.char-count:global(.warning) {
  color: #f59e0b;
}

.char-count:global(.error) {
  color: #ef4444;
}

.send-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
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
  gap: 0.5rem;
  margin-top: 1rem;
  flex-wrap: wrap;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.quick-action-btn {
  padding: 0.5rem 1rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 9999px;
  font-size: 0.75rem;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.quick-action-btn:hover {
  background: #e2e8f0;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

@media (max-width: 768px) {
  .chat-input {
    padding: 1rem;
  }
  
  .input-container {
    gap: 0.5rem;
  }
  
  .action-btn {
    width: 36px;
    height: 36px;
  }
  
  .send-btn {
    width: 44px;
    height: 44px;
  }
  
  .quick-actions {
    gap: 0.25rem;
  }
  
  .quick-action-btn {
    padding: 0.375rem 0.75rem;
    font-size: 0.7rem;
  }
}
</style>