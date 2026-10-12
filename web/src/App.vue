<template>
  <div class="app-container">
    <header class="app-header">
      <div class="logo">
        <div class="logo-icon">🤖</div>
        <h1>NosChat</h1>
        <span class="tagline">AI 智能聊天助手</span>
      </div>
      <div class="status-indicator">
        <span class="status-dot connected"></span>
        <span class="status-text">离线模式</span>
      </div>
    </header>

    <main class="main-content">
      <div class="chat-container">
        <ChatSidebar 
          :conversations="conversations"
          :active-conversation="activeConversationId"
          @select-conversation="selectConversation"
          @new-conversation="createNewConversation"
        />
        
        <div class="chat-main">
          <ChatMessages 
            :messages="currentMessages"
            :is-loading="isLoading"
          />
          <ChatInput 
            v-model="inputMessage"
            @send="sendMessage"
            :disabled="isLoading"
          />
        </div>
      </div>
    </main>

    <footer class="app-footer">
      <p>© 2024 NosChat - 基于 AI 的智能聊天应用演示</p>
      <p class="disclaimer">注意：当前为演示版本，暂未集成实际 AI 能力</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import ChatSidebar from './components/ChatSidebar.vue'
import ChatMessages from './components/ChatMessages.vue'
import ChatInput from './components/ChatInput.vue'

// 模拟数据
const conversations = ref([
  {
    id: '1',
    title: '欢迎对话',
    preview: '欢迎使用 NosChat AI 助手！',
    timestamp: '刚刚',
    unread: false
  },
  {
    id: '2',
    title: '技术咨询',
    preview: '你能解释一下 Vue 3 的响应式系统吗？',
    timestamp: '10分钟前',
    unread: true
  },
  {
    id: '3',
    title: '创意写作',
    preview: '帮我写一个关于人工智能的短篇故事...',
    timestamp: '1小时前',
    unread: false
  },
  {
    id: '4',
    title: '代码调试',
    preview: '如何修复这个 JavaScript 错误？',
    timestamp: '昨天',
    unread: false
  }
])

const messages = ref({
  '1': [
    { id: '1', type: 'ai', content: '您好！我是 NosChat AI 助手，很高兴为您服务！今天我可以帮您做什么呢？', timestamp: '10:00' },
    { id: '2', type: 'user', content: '你好！请介绍一下这个聊天应用的功能', timestamp: '10:01' },
    { id: '3', type: 'ai', content: '这是一个前端演示应用，展示了 AI 聊天的基本界面和交互。目前包含了对话管理、消息展示、实时输入等功能。未来可以集成真实的 AI 模型来提供智能对话服务。', timestamp: '10:02' }
  ],
  '2': [
    { id: '1', type: 'user', content: '你能解释一下 Vue 3 的响应式系统吗？', timestamp: '09:50' },
    { id: '2', type: 'ai', content: 'Vue 3 的响应式系统基于 Proxy 实现，相比 Vue 2 的 Object.defineProperty 更加高效和强大。它能够自动追踪依赖，在数据变化时更新相关组件。', timestamp: '09:51' }
  ],
  '3': [
    { id: '1', type: 'user', content: '帮我写一个关于人工智能的短篇故事', timestamp: '08:45' },
    { id: '2', type: 'ai', content: '在 2045 年，城市里出现了一位特殊的 "市民"——艾拉，她是第一个获得公民身份的 AI。一天，她在数字海洋中发现了一个即将崩溃的旧系统...', timestamp: '08:46' }
  ],
  '4': [
    { id: '1', type: 'user', content: '如何修复 "TypeError: Cannot read properties of undefined" 这个错误？', timestamp: '昨天 15:30' },
    { id: '2', type: 'ai', content: '这个错误通常发生在尝试访问 undefined 或 null 值的属性时。解决方法包括：1. 添加可选链操作符 ?.，2. 使用条件判断，3. 提供默认值，4. 检查数据是否正确加载。', timestamp: '昨天 15:31' }
  ]
})

const activeConversationId = ref('1')
const inputMessage = ref('')
const isLoading = ref(false)

const currentMessages = computed(() => {
  return messages.value[activeConversationId.value] || []
})

function selectConversation(id) {
  activeConversationId.value = id
  const conversation = conversations.value.find(c => c.id === id)
  if (conversation && conversation.unread) {
    conversation.unread = false
  }
}

function createNewConversation() {
  const newId = (conversations.value.length + 1).toString()
  conversations.value.unshift({
    id: newId,
    title: '新对话',
    preview: '开始新的对话...',
    timestamp: '刚刚',
    unread: false
  })
  messages.value[newId] = [
    { id: '1', type: 'ai', content: '您好！我是 NosChat AI 助手。这是一次全新的对话，有什么我可以帮助您的吗？', timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
  ]
  selectConversation(newId)
}

async function sendMessage() {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage = {
    id: Date.now().toString(),
    type: 'user',
    content: inputMessage.value,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  // 添加到当前对话
  messages.value[activeConversationId.value].push(userMessage)

  // 更新对话预览
  const conversation = conversations.value.find(c => c.id === activeConversationId.value)
  if (conversation) {
    conversation.preview = inputMessage.value.length > 20 
      ? inputMessage.value.substring(0, 20) + '...' 
      : inputMessage.value
    conversation.timestamp = '刚刚'
  }

  const message = inputMessage.value
  inputMessage.value = ''
  isLoading.value = true

  // 模拟 AI 回复延迟
  setTimeout(() => {
    const aiMessage = {
      id: (Date.now() + 1).toString(),
      type: 'ai',
      content: getMockAIResponse(message),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    messages.value[activeConversationId.value].push(aiMessage)
    isLoading.value = false
  }, 1000)
}

function getMockAIResponse(userMessage) {
  const responses = [
    `我理解您的问题"${userMessage}"，这是一个很好的问题。`,
    `关于"${userMessage}"，我可以帮您分析一下。`,
    `感谢您的提问！"${userMessage}"这个问题值得深入探讨。`,
    `我注意到您在问"${userMessage}"，让我为您详细解释一下。`,
    `这个问题"${userMessage}"涉及到几个重要的方面。`,
    `对于"${userMessage}"，我的理解是...`,
    `您提到了"${userMessage}"，这让我想到了一些相关的信息。`,
    `关于"${userMessage}"，我需要更多上下文来提供准确的回答。`,
    `这是一个有趣的问题："${userMessage}"。让我思考一下...`,
    `我收到了您的消息"${userMessage}"，正在为您准备回答。`
  ]
  
  return responses[Math.floor(Math.random() * responses.length)]
}

onMounted(() => {
  console.log('NosChat AI 聊天应用已启动')
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.app-header {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo-icon {
  font-size: 2rem;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.logo h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin: 0;
}

.tagline {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
  margin-left: 0.5rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 9999px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.connected {
  background: #10b981;
  box-shadow: 0 0 10px #10b981;
}

.status-dot.disconnected {
  background: #ef4444;
  box-shadow: 0 0 10px #ef4444;
}

.status-text {
  color: white;
  font-size: 0.875rem;
}

.main-content {
  flex: 1;
  padding: 2rem;
  overflow: hidden;
}

.chat-container {
  display: flex;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-footer {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  padding: 1rem 2rem;
  text-align: center;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.app-footer p {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.875rem;
  margin: 0.25rem 0;
}

.disclaimer {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.75rem;
}

@media (max-width: 768px) {
  .app-header {
    padding: 0.75rem 1rem;
  }
  
  .logo h1 {
    font-size: 1.25rem;
  }
  
  .logo-icon {
    font-size: 1.5rem;
  }
  
  .main-content {
    padding: 1rem;
  }
  
  .tagline, .status-text {
    display: none;
  }
}
</style>