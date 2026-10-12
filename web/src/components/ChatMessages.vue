<template>
  <div class="chat-messages">
    <div v-if="messages.length === 0" class="empty-state">
      <div class="empty-icon">🤖</div>
      <h3>开始新的对话</h3>
      <p>输入一条消息开始与 AI 助手聊天</p>
      <div class="suggestions">
        <button v-for="(suggestion, index) in suggestions" 
                :key="index"
                class="suggestion-btn"
                @click="$emit('suggestion-selected', suggestion)">
          {{ suggestion }}
        </button>
      </div>
    </div>
    
    <div v-else class="messages-container">
      <div v-for="message in messages" 
           :key="message.id"
           class="message-wrapper"
           :class="message.type">
        <div class="message-bubble">
          <div class="message-header">
            <div class="sender-info">
              <span class="sender-icon">{{ message.type === 'ai' ? '🤖' : '👤' }}</span>
              <span class="sender-name">{{ message.type === 'ai' ? 'AI 助手' : '用户' }}</span>
            </div>
            <span class="message-time">{{ message.timestamp }}</span>
          </div>
          <div class="message-content">
            {{ message.content }}
          </div>
        </div>
      </div>
      
      <div v-if="isLoading" class="message-wrapper ai">
        <div class="message-bubble">
          <div class="message-header">
            <div class="sender-info">
              <span class="sender-icon">🤖</span>
              <span class="sender-name">AI 助手</span>
            </div>
          </div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  messages: {
    type: Array,
    required: true,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['suggestion-selected'])

const suggestions = [
  '你好！你能做什么？',
  '解释一下人工智能的基本概念',
  '帮我写一段 JavaScript 代码示例',
  '如何学习编程？',
  '推荐一些技术书籍'
]
</script>

<style scoped>
.chat-messages {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #64748b;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1.5rem;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

.empty-state h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.empty-state p {
  font-size: 1rem;
  opacity: 0.8;
  margin-bottom: 2rem;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  justify-content: center;
  max-width: 600px;
}

.suggestion-btn {
  padding: 0.75rem 1.25rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
}

.suggestion-btn:hover {
  background: #f1f5f9;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.messages-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message-wrapper {
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-wrapper.user {
  align-items: flex-end;
}

.message-wrapper.ai {
  align-items: flex-start;
}

.message-bubble {
  max-width: 80%;
  background: white;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.message-wrapper.user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 0.25rem;
}

.message-wrapper.ai .message-bubble {
  background: white;
  color: #1e293b;
  border-bottom-left-radius: 0.25rem;
}

.message-header {
  padding: 0.75rem 1rem 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.message-wrapper.user .message-header {
  border-bottom-color: rgba(255, 255, 255, 0.1);
}

.sender-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sender-icon {
  font-size: 1rem;
}

.sender-name {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.message-wrapper.user .sender-name {
  color: rgba(255, 255, 255, 0.8);
}

.message-wrapper.ai .sender-name {
  color: #64748b;
}

.message-time {
  font-size: 0.7rem;
  opacity: 0.7;
}

.message-wrapper.user .message-time {
  color: rgba(255, 255, 255, 0.8);
}

.message-wrapper.ai .message-time {
  color: #94a3b8;
}

.message-content {
  padding: 1rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-wrapper.user .message-content {
  color: white;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 1rem 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  animation: typing 1.4s ease-in-out infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-8px);
  }
}

@media (max-width: 768px) {
  .chat-messages {
    padding: 1rem;
  }
  
  .message-bubble {
    max-width: 90%;
  }
  
  .suggestions {
    flex-direction: column;
  }
}
</style>