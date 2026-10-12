<template>
  <!-- 用户未登录时显示认证页面 -->
  <AuthPage v-if="!isAuthenticated" @success="handleAuthSuccess" />

  <!-- 用户已登录时显示主聊天界面 -->
  <div v-else class="app-container">
    <header class="app-header">
      <div class="header-left">
        <button
          class="menu-toggle"
          @click="sidebarOpen = !sidebarOpen"
          :aria-label="sidebarOpen ? '关闭历史列表' : '打开历史列表'"
          :aria-expanded="sidebarOpen"
        >
          <span class="menu-bars" :class="{ open: sidebarOpen }"></span>
        </button>
        <div class="logo">
          <div class="logo-icon">🤖</div>
          <div class="logo-text">
            <h1>NosChat</h1>
            <span class="tagline">欢迎回来，{{ currentUser?.nickname || currentUser?.username }}</span>
          </div>
        </div>
      </div>

      <div class="header-right">
        <div class="user-info">
          <div class="user-avatar">
            {{ getAvatarInitial(currentUser?.nickname || currentUser?.username) }}
          </div>
          <div class="user-details">
            <span class="user-nickname">{{ currentUser?.nickname || currentUser?.username }}</span>
            <button @click="handleLogout" class="logout-btn" title="退出登录">
              退出
            </button>
          </div>
        </div>
        <div class="status-indicator">
          <span class="status-dot connected"></span>
          <span class="status-text">已登录 · 离线模式</span>
        </div>
      </div>
    </header>

    <main class="main-content">
      <div class="chat-container">
        <div
          v-if="!isDesktop && sidebarOpen"
          class="drawer-backdrop"
          @click="sidebarOpen = false"
        ></div>

        <Transition name="drawer">
          <ChatSidebar
            v-if="isDesktop || sidebarOpen"
            class="sidebar-slot"
            :conversations="conversations"
            :active-conversation="activeConversationId"
            :models="MODEL_LIST"
            @select-conversation="selectConversation"
            @new-conversation="createNewConversation"
            @edit-conversation="editConversation"
            @delete-conversation="askDeleteConversation"
            @close="sidebarOpen = false"
          />
        </Transition>

        <div class="chat-main">
          <div class="chat-toolbar">
            <div class="toolbar-model">
              <span class="toolbar-avatar" :style="{ background: currentModel.color }">
                {{ currentModel.icon }}
              </span>
              <div class="toolbar-text">
                <span class="toolbar-title">{{ currentConversation?.title || '新对话' }}</span>
                <span class="toolbar-sub">
                  {{ currentModel.name }} · {{ currentModel.provider }} · 上下文 {{ currentModel.context }} · {{ currentModel.released }} 发布
                </span>
              </div>
            </div>
            <div class="toolbar-right">
              <div class="toolbar-stats">
                <span class="stat">
                  <em>{{ currentMessages.length }}</em> 条消息
                </span>
                <span class="stat" :class="{ busy: isLoading }">
                  <em>{{ isLoading ? '回复中' : '就绪' }}</em>
                </span>
              </div>
              <button
                type="button"
                class="think-switch"
                :class="{ on: thinkDefaultOpen }"
                role="switch"
                :aria-checked="thinkDefaultOpen"
                :title="thinkDefaultOpen ? '深度思考默认展开，点击改为默认折叠' : '深度思考默认折叠，点击改为默认展开'"
                @click="thinkDefaultOpen = !thinkDefaultOpen"
              >
                <span class="switch-ic">🧠</span>
                <span class="switch-txt">深度思考</span>
                <span class="switch-track"><span class="switch-knob"></span></span>
              </button>
              <ModelSelector
                v-model="selectedModelId"
                :models="MODEL_LIST"
                @change="onModelChange"
              />
            </div>
          </div>

          <ChatMessages
            :messages="currentMessages"
            :is-loading="loadingInActive"
            :models="MODEL_LIST"
            :active-model-id="selectedModelId"
            :thinking-open="thinkDefaultOpen"
            @suggestion-selected="useSuggestion"
          />

          <ChatInput
            v-model="inputMessage"
            @send="sendMessage"
            :disabled="isLoading"
            :loading="isLoading"
            :model="currentModel"
          />
        </div>
      </div>
    </main>

    <footer class="app-footer">
      <p>© 2024 NosChat - AI 智能聊天助手</p>
      <p class="disclaimer">用户：{{ currentUser?.username }} | 昵称：{{ currentUser?.nickname }}</p>
    </footer>

    <!-- 删除确认弹窗 -->
    <Transition name="modal">
      <div v-if="pendingDelete" class="modal-backdrop" @click.self="pendingDelete = null">
        <div class="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="del-title">
          <div class="confirm-icon">🗑️</div>
          <h2 id="del-title">删除这个对话？</h2>
          <p class="confirm-text">
            「{{ pendingDelete.title }}」及其 {{ (messages[pendingDelete.id] || []).length }} 条消息将被移除，此操作无法撤销。
          </p>
          <div class="confirm-actions">
            <button class="btn ghost" @click="pendingDelete = null">取消</button>
            <button class="btn danger" @click="confirmDelete">删除</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 轻提示 -->
    <Transition name="toast">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import ChatSidebar from './components/ChatSidebar.vue'
import ChatMessages from './components/ChatMessages.vue'
import ChatInput from './components/ChatInput.vue'
import ModelSelector from './components/ModelSelector.vue'
import AuthPage from './components/AuthPage.vue'
import { MODEL_LIST, MOCK_CONVERSATIONS, MOCK_MESSAGES, getModel, mockReply } from './data/models.js'
import { useAuth } from './stores/userStore.js'

// 用户认证状态
const { isAuthenticated, currentUser, logout: authLogout } = useAuth()

// 聊天应用状态
const conversations = ref(
  MOCK_CONVERSATIONS.map(c => ({
    ...c,
    preview: lastPreview(c.id)
  }))
)

const messages = reactive({ ...MOCK_MESSAGES })

const activeConversationId = ref(conversations.value[0]?.id ?? '')
const inputMessage = ref('')
const isLoading = ref(false)
const sidebarOpen = ref(false)
const pendingDelete = ref(null)
const toast = ref('')
const selectedModelId = ref(localStorage.getItem('noschat.model') || MODEL_LIST[0].id)

// 深度思考区块的默认展开状态
const thinkDefaultOpen = ref(localStorage.getItem('noschat.thinkOpen') === '1')
watch(thinkDefaultOpen, value => localStorage.setItem('noschat.thinkOpen', value ? '1' : '0'))

let seq = 0
const uid = () => `${Date.now()}-${++seq}`

// 当前流式回复的定时器
let streamTimer = null
const streamConversationId = ref('')

// 只有正在生成的那个对话才显示「生成中」占位气泡
const loadingInActive = computed(
  () => isLoading.value && streamConversationId.value === activeConversationId.value
)

function clearStreamTimer() {
  if (streamTimer) {
    clearInterval(streamTimer)
    streamTimer = null
  }
}

function lastPreview(id) {
  const list = MOCK_MESSAGES[id]
  if (!list || !list.length) return '开始新的对话…'
  return previewOf(list[list.length - 1].content) || '开始新的对话…'
}

function previewOf(text) {
  const oneLine = (text || '').replace(/\s+/g, ' ').trim()
  return oneLine.length > 34 ? oneLine.slice(0, 34) + '…' : oneLine
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const currentConversation = computed(() =>
  conversations.value.find(c => c.id === activeConversationId.value)
)

const currentModel = computed(() => getModel(selectedModelId.value))

const currentMessages = computed(() => messages[activeConversationId.value] || [])

function showToast(text) {
  toast.value = text
  setTimeout(() => { if (toast.value === text) toast.value = '' }, 2200)
}

function selectConversation(id) {
  activeConversationId.value = id
  const conversation = conversations.value.find(c => c.id === id)
  if (conversation) {
    conversation.unread = false
    if (conversation.model) selectedModelId.value = conversation.model
  }
  sidebarOpen.value = false
}

function createNewConversation() {
  const newId = uid()
  conversations.value.unshift({
    id: newId,
    title: '新对话',
    preview: '开始新的对话…',
    timestamp: '刚刚',
    pinned: false,
    unread: false,
    model: selectedModelId.value
  })
  messages[newId] = [
    {
      id: uid(),
      type: 'ai',
      model: selectedModelId.value,
      content: `你好，${currentUser.value?.nickname || '朋友'}！当前模型是 ${currentModel.value.name}。有什么可以帮你的吗？`,
      timestamp: nowTime()
    }
  ]
  activeConversationId.value = newId
  sidebarOpen.value = false
  showToast('已创建新对话')
}

function editConversation({ id, title }) {
  const conversation = conversations.value.find(c => c.id === id)
  if (conversation && title && conversation.title !== title) {
    conversation.title = title
    showToast('标题已更新')
  }
}

function askDeleteConversation(id) {
  const conversation = conversations.value.find(c => c.id === id)
  if (conversation) pendingDelete.value = conversation
}

function confirmDelete() {
  const target = pendingDelete.value
  if (!target) return
  pendingDelete.value = null

  const index = conversations.value.findIndex(c => c.id === target.id)
  if (index === -1) return
  conversations.value.splice(index, 1)
  delete messages[target.id]

  if (target.id === activeConversationId.value) {
    if (conversations.value.length) {
      activeConversationId.value = conversations.value[0].id
    } else {
      createNewConversation()
    }
  }
  showToast('对话已删除')
}

function useSuggestion(text) {
  inputMessage.value = text
  sendMessage()
}

function sendMessage() {
  const content = inputMessage.value.trim()
  if (!content || isLoading.value) return

  const id = activeConversationId.value
  if (!messages[id]) messages[id] = []

  messages[id].push({ id: uid(), type: 'user', content, timestamp: nowTime() })

  const conversation = currentConversation.value
  if (conversation) {
    conversation.preview = previewOf(content)
    conversation.timestamp = '刚刚'
    // 首次提问时用问题内容自动命名
    if (conversation.title === '新对话') {
      conversation.title = content.length > 16 ? content.slice(0, 16) + '…' : content
    }
  }

  inputMessage.value = ''
  isLoading.value = true

  const reply = mockReply(selectedModelId.value, content)
  const [min, max] = reply.latency
  const total = min + Math.random() * (max - min)

  // 有深度思考的模型：先逐字吐思考，再逐字吐结论
  const TICK = 50
  const thinkMs = reply.thinking ? total * 0.6 : 0
  const answerMs = Math.max(TICK, total - thinkMs)
  const thinkStep = Math.max(2, Math.ceil((reply.thinking || '').length / (thinkMs / TICK)))
  const answerStep = Math.max(2, Math.ceil(reply.content.length / (answerMs / TICK)))

  const msgId = uid()
  messages[id].push({
    id: msgId,
    type: 'ai',
    model: reply.model,
    content: '',
    thinking: '',
    thinkingSec: 0,
    phase: reply.thinking ? 'think' : 'answer',
    timestamp: nowTime()
  })

  const thinkStart = Date.now()
  streamConversationId.value = id
  clearStreamTimer()

  const finish = () => {
    clearStreamTimer()
    isLoading.value = false
    if (streamConversationId.value === id) streamConversationId.value = ''
    const target = conversations.value.find(c => c.id === id)
    if (target) {
      target.preview = previewOf(reply.content)
      target.timestamp = '刚刚'
    }
  }

  streamTimer = setInterval(() => {
    const list = messages[id]
    // 等待期间可能已切换或删除对话
    const msg = list && list.find(item => item.id === msgId)
    if (!msg) {
      finish()
      return
    }

    if (msg.phase === 'think') {
      msg.thinking = reply.thinking.slice(0, msg.thinking.length + thinkStep)
      msg.thinkingSec = Math.max(1, Math.round((Date.now() - thinkStart) / 1000))
      if (msg.thinking.length >= reply.thinking.length) {
        msg.thinking = reply.thinking
        msg.phase = 'answer'
      }
    } else if (msg.phase === 'answer') {
      msg.content = reply.content.slice(0, msg.content.length + answerStep)
      if (msg.content.length >= reply.content.length) {
        msg.content = reply.content
        msg.phase = 'done'
        finish()
      }
    } else {
      finish()
    }
  }, TICK)
}

function onModelChange(model) {
  const conversation = currentConversation.value
  if (conversation) conversation.model = model.id
  localStorage.setItem('noschat.model', model.id)
  showToast(`已切换到 ${model.name}`)
}

function handleAuthSuccess() {
  showToast('登录成功！')
  // 可以在这里添加其他登录成功后的逻辑
}

function handleLogout() {
  authLogout()
  showToast('已退出登录')
}

function getAvatarInitial(name) {
  if (!name) return '?'
  return name.charAt(0).toUpperCase()
}

watch(activeConversationId, () => {
  sidebarOpen.value = false
})

// 响应式：>900px 内联侧栏，<=900px 收进抽屉
const mql = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia('(min-width: 901px)')
  : null
const isDesktop = ref(mql ? mql.matches : true)

function onViewportChange(e) {
  isDesktop.value = e.matches
  if (e.matches) sidebarOpen.value = false
}

onMounted(() => {
  mql?.addEventListener('change', onViewportChange)
  console.log('NosChat AI 聊天应用已启动', { isAuthenticated: isAuthenticated.value })
})

onBeforeUnmount(() => {
  mql?.removeEventListener('change', onViewportChange)
  clearStreamTimer()
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;
}

.app-header {
  flex: 0 0 auto;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  padding: clamp(0.5rem, 1.6vw, 1rem) clamp(0.75rem, 2.5vw, 2rem);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.3rem 0.75rem 0.3rem 0.3rem;
  border-radius: 999px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  display: grid;
  place-items: center;
  font-weight: bold;
  font-size: 0.9rem;
}

.user-details {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.user-nickname {
  color: white;
  font-size: 0.85rem;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logout-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: rgba(255, 255, 255, 0.9);
  padding: 0.2rem 0.5rem;
  border-radius: 0.5rem;
  font-size: 0.7rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.35);
}

.menu-toggle {
  display: none;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.1);
  border-radius: 0.7rem;
  cursor: pointer;
  place-items: center;
}

.menu-bars,
.menu-bars::before,
.menu-bars::after {
  display: block;
  width: 18px;
  height: 2px;
  background: #fff;
  border-radius: 2px;
  transition: transform 0.25s ease, opacity 0.2s ease;
}

.menu-bars {
  position: relative;
}

.menu-bars::before,
.menu-bars::after {
  content: '';
  position: absolute;
  left: 0;
}

.menu-bars::before { top: -6px; }
.menu-bars::after { top: 6px; }

.menu-bars.open { background: transparent; }
.menu-bars.open::before { transform: translateY(6px) rotate(45deg); }
.menu-bars.open::after { transform: translateY(-6px) rotate(-45deg); }

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.logo-text {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.logo-icon {
  font-size: clamp(1.3rem, 3vw, 2rem);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.logo h1 {
  font-size: clamp(1.05rem, 2.4vw, 1.5rem);
  font-weight: 700;
  color: white;
  margin: 0;
  white-space: nowrap;
}

.tagline {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.8rem;
  white-space: nowrap;
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

.status-text {
  color: white;
  font-size: 0.85rem;
  white-space: nowrap;
}

.main-content {
  flex: 1;
  padding: clamp(0.5rem, 2.5vw, 2rem);
  overflow: hidden;
  min-height: 0;
}

.chat-container {
  display: flex;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
}

.drawer-backdrop {
  display: none;
}

.sidebar-slot {
  z-index: 20;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.chat-toolbar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem clamp(0.85rem, 2vw, 1.5rem);
  border-bottom: 1px solid #e2e8f0;
  background: rgba(248, 250, 252, 0.9);
}

.toolbar-model {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
}

.toolbar-avatar {
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border-radius: 0.6rem;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 1rem;
}

.toolbar-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.toolbar-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 42vw;
}

.toolbar-sub {
  font-size: 0.7rem;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 0 0 auto;
  min-width: 0;
}

.toolbar-stats {
  display: flex;
  gap: 0.4rem;
  flex: 0 0 auto;
}

.stat {
  font-size: 0.68rem;
  color: #64748b;
  background: #eef2f7;
  border-radius: 999px;
  padding: 0.25rem 0.6rem;
  white-space: nowrap;
}

.stat em {
  font-style: normal;
  font-weight: 700;
  color: #475569;
}

.stat.busy {
  background: #667eea18;
  color: #667eea;
}

.stat.busy em {
  color: #667eea;
}

/* 深度思考默认展开开关 */
.think-switch {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex: 0 0 auto;
  min-height: 36px;
  padding: 0.3rem 0.55rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  cursor: pointer;
  font-family: inherit;
  color: #64748b;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, color 0.2s ease;
}

.think-switch:hover {
  border-color: #667eea;
  color: #4f46e5;
}

.think-switch:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.18);
}

.think-switch.on {
  color: #4f46e5;
  border-color: #667eea80;
  background: linear-gradient(135deg, #667eea10, #764ba210);
}

.switch-ic {
  font-size: 0.85rem;
  line-height: 1;
}

.switch-txt {
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
}

.switch-track {
  position: relative;
  width: 26px;
  height: 14px;
  flex: 0 0 26px;
  border-radius: 999px;
  background: #e2e8f0;
  transition: background 0.2s ease;
}

.think-switch.on .switch-track {
  background: #667eea;
}

.switch-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.25);
  transition: transform 0.2s ease;
}

.think-switch.on .switch-knob {
  transform: translateX(12px);
}

.app-footer {
  flex: 0 0 auto;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  padding: 0.75rem clamp(0.75rem, 2.5vw, 2rem);
  text-align: center;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.app-footer p {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.8rem;
  margin: 0.2rem 0;
}

.disclaimer {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.7rem;
}

/* 弹窗 */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  padding: 1rem;
}

.confirm-dialog {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 1rem;
  padding: 1.5rem;
  text-align: center;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.35);
}

.confirm-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.confirm-dialog h2 {
  font-size: 1.05rem;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.confirm-text {
  font-size: 0.82rem;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 1.25rem;
}

.confirm-actions {
  display: flex;
  gap: 0.6rem;
}

.btn {
  flex: 1;
  min-height: 44px;
  border-radius: 0.7rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.btn.ghost {
  background: #f1f5f9;
  color: #475569;
  border-color: #e2e8f0;
}

.btn.ghost:hover { background: #e2e8f0; }

.btn.danger {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: #fff;
}

.btn.danger:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(239, 68, 68, 0.4);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .confirm-dialog,
.modal-leave-active .confirm-dialog {
  transition: transform 0.2s ease;
}

.modal-enter-from .confirm-dialog,
.modal-leave-to .confirm-dialog {
  transform: translateY(12px) scale(0.96);
}

.toast {
  position: fixed;
  z-index: 90;
  left: 50%;
  bottom: clamp(1rem, 6vh, 2.5rem);
  transform: translateX(-50%);
  background: rgba(30, 41, 59, 0.94);
  color: #fff;
  font-size: 0.8rem;
  padding: 0.6rem 1rem;
  border-radius: 999px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.3);
  white-space: nowrap;
  max-width: calc(100vw - 2rem);
  overflow: hidden;
  text-overflow: ellipsis;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
}

/* 平板 / 窄屏：侧栏收起为抽屉 */
@media (max-width: 900px) {
  .menu-toggle { display: grid; }

  .drawer-backdrop {
    display: block;
    position: absolute;
    inset: 0;
    z-index: 25;
    background: rgba(15, 23, 42, 0.4);
    backdrop-filter: blur(2px);
  }

  .sidebar-slot {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 30;
    width: min(82vw, 300px);
    box-shadow: 12px 0 40px rgba(15, 23, 42, 0.28);
  }

  .status-indicator {
    padding: 0.4rem 0.6rem;
  }
  
  .user-info {
    padding: 0.2rem 0.5rem 0.2rem 0.2rem;
  }
  
  .user-details {
    flex-direction: column;
    gap: 0.2rem;
    align-items: flex-start;
  }
}

.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.22s ease;
}

.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(-100%);
}

@media (max-width: 768px) {
  .tagline, .status-text { display: none; }
  .logo { gap: 0.5rem; }
  .header-left { gap: 0.5rem; }
  .app-footer .disclaimer { display: none; }
  
  .user-info {
    display: none;
  }
}

@media (max-width: 640px) {
  .toolbar-stats { display: none; }
  .chat-toolbar { padding: 0.55rem 0.7rem; gap: 0.4rem; }
  .toolbar-title { max-width: 30vw; }

  /* 窄屏只留图标 + 轨道，避免挤压模型选择器 */
  .switch-txt { display: none; }
  .think-switch { padding: 0.3rem 0.4rem; gap: 0.3rem; }
}

@media (max-width: 480px) {
  .confirm-dialog { padding: 1.15rem; }
  .toolbar-sub { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .logo-icon { animation: none; }
  .menu-bars,
  .menu-bars::before,
  .menu-bars::after { transition: none; }
}
</style>