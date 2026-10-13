<template>
  <!-- 本地存在令牌但尚未由后端确认：显示校验态，避免闪现已登录界面 -->
  <div v-if="authToken && !sessionReady" class="app-boot">
    <div class="boot-card">
      <div class="boot-spinner"></div>
      <p>正在校验登录状态…</p>
    </div>
  </div>

  <!-- 用户未登录时显示认证页面 -->
  <AuthPage v-else-if="!isAuthenticated" @success="handleAuthSuccess" />

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
            <span
              class="user-nickname"
              title="点击修改昵称"
              @click="openNicknameDialog"
            >{{ currentUser?.nickname || currentUser?.username }}</span>
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
            :disabled="isLoading || quotaExceeded"
            :loading="isLoading"
            :model="currentModel"
            :quota-exceeded="quotaExceeded"
            :quota-limit="quota.limit"
            :quota-reset-label="quotaResetLabel"
          />
        </div>
      </div>
    </main>

    <footer class="app-footer">
      <p>© 2026 NosChat - AI 智能聊天助手</p>
      <p class="disclaimer">用户：{{ currentUser?.username }} | 昵称：{{ currentUser?.nickname }}</p>
    </footer>

    <!-- 昵称设置弹窗（验证码登录自动注册后弹出，也可点击顶部昵称打开） -->
    <Transition name="modal">
      <div v-if="nicknameDialog" class="modal-backdrop" @click.self="skipNickname">
        <div class="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="nick-title">
          <div class="confirm-icon">👋</div>
          <h2 id="nick-title">设置你的昵称</h2>
          <p class="confirm-text">
            账号已创建，填一个昵称方便识别；留空将使用邮箱作为昵称。
          </p>
          <input
            ref="nicknameInputRef"
            v-model.trim="nicknameInput"
            class="nickname-field"
            type="text"
            maxlength="32"
            placeholder="请输入昵称（可选）"
            aria-label="昵称"
            :disabled="nicknameSaving"
            @keydown.enter.prevent="saveNickname"
          />
          <div class="confirm-actions">
            <button class="btn ghost" @click="skipNickname" :disabled="nicknameSaving">
              用邮箱当昵称
            </button>
            <button class="btn primary" @click="saveNickname" :disabled="nicknameSaving">
              {{ nicknameSaving ? '保存中...' : '保存昵称' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

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
import { ref, computed, reactive, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import ChatSidebar from './components/ChatSidebar.vue'
import ChatMessages from './components/ChatMessages.vue'
import ChatInput from './components/ChatInput.vue'
import ModelSelector from './components/ModelSelector.vue'
import AuthPage from './components/AuthPage.vue'
import { MODEL_LIST, getModel, setModels } from './data/models.js'
import { useAuth } from './stores/userStore.js'
import { useQuota } from './stores/quotaStore.js'
import {
  createConversation,
  deleteConversation,
  fetchConversations,
  fetchMessages,
  fetchModels,
  streamChat,
  updateConversation
} from './api/chat.js'
import { fmtClock, fmtRelative, nowClock } from './utils/time.js'

// 用户认证状态
const {
  isAuthenticated,
  currentUser,
  authToken,
  sessionReady,
  logout: authLogout,
  lastAuthIsNew,
  needsNicknamePrompt,
  saveNickname: saveNicknameApi,
  clearNicknamePrompt
} = useAuth()

// 每日输出 token 额度（前端只展示与锁定；真正拦截在后端）
const {
  quota,
  exceeded: quotaExceeded,
  resetLabel: quotaResetLabel,
  loadUsage,
  refreshIfReset,
  applyUsage,
  resetUsage
} = useQuota()

// 聊天应用状态
const conversations = ref([])
const messages = reactive({})

const activeConversationId = ref('')
const inputMessage = ref('')
const isLoading = ref(false)
const sidebarOpen = ref(false)
const pendingDelete = ref(null)
const toast = ref('')
const selectedModelId = ref(localStorage.getItem('noschat.model') || '')

// 昵称设置弹窗（验证码登录自动注册后弹出，也支持手动打开）
const nicknameDialog = ref(false)
const nicknameInput = ref('')
const nicknameSaving = ref(false)
const nicknameInputRef = ref(null)

// 深度思考区块的默认展开状态
const thinkDefaultOpen = ref(localStorage.getItem('noschat.thinkOpen') === '1')
watch(thinkDefaultOpen, value => localStorage.setItem('noschat.thinkOpen', value ? '1' : '0'))

let seq = 0
const uid = () => `${Date.now()}-${++seq}`

// 当前流式回复的中断控制器
let streamController = null
const streamConversationId = ref('')

// 只有正在生成的那个对话才显示「生成中」占位气泡
const loadingInActive = computed(
  () => isLoading.value && streamConversationId.value === activeConversationId.value
)

function abortStream() {
  if (streamController) {
    streamController.abort()
    streamController = null
  }
}

function nowTime() {
  return nowClock()
}

/** 后端消息 → 界面消息 */
function toLocalMessage(row) {
  return {
    id: row.id,
    type: row.type,
    model: row.model,
    content: row.content || '',
    thinking: row.thinking || '',
    thinkingSec: row.thinkingSec || 0,
    phase: 'done',
    timestamp: fmtClock(row.createdAt)
  }
}

/** 后端会话 → 界面会话 */
function toLocalConversation(row) {
  return { ...row, timestamp: fmtRelative(row.updatedAt) }
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

async function loadModels() {
  const list = await fetchModels()
  setModels(list)
  if (!MODEL_LIST.some(model => model.id === selectedModelId.value)) {
    selectedModelId.value = MODEL_LIST[0]?.id || ''
  }
}

async function loadMessages(id, { force = false } = {}) {
  if (!id) return
  if (messages[id] && !force) return
  const rows = await fetchMessages(id)
  messages[id] = (rows || []).map(toLocalMessage)
}

async function loadConversations() {
  const rows = await fetchConversations()
  conversations.value = (rows || []).map(toLocalConversation)

  if (!conversations.value.some(item => item.id === activeConversationId.value)) {
    activeConversationId.value = conversations.value[0]?.id || ''
  }

  // 新账号没有任何会话时，自动开一个（保证输入框始终可用）
  if (!conversations.value.length) {
    await createNewConversation()
    return
  }

  if (activeConversationId.value) await loadMessages(activeConversationId.value)
}

// 登录后一次性拉取模型清单、会话列表与额度快照（幂等）
let bootstrapping = null
function bootstrap() {
  if (bootstrapping) return bootstrapping
  bootstrapping = (async () => {
    try {
      await loadModels()
      await loadConversations()
      await loadUsage()
    } catch (error) {
      showToast(error?.message || '加载数据失败')
    } finally {
      bootstrapping = null
    }
  })()
  return bootstrapping
}

async function selectConversation(id) {
  activeConversationId.value = id
  const conversation = conversations.value.find(c => c.id === id)
  if (conversation) {
    // 已读确认要落到后端（unread 属于后端状态，本地只做乐观展示）；
    // 仅在此前确实未读时才发请求，避免每次点击都产生一次写入
    const wasUnread = Boolean(conversation.unread)
    conversation.unread = false
    if (conversation.model) selectedModelId.value = conversation.model
    if (wasUnread) {
      updateConversation(id, { unread: false }).catch(error => {
        conversation.unread = true
        showToast(error?.message || '标记已读失败')
      })
    }
  }
  sidebarOpen.value = false
  try {
    await loadMessages(id)
  } catch (error) {
    showToast(error?.message || '加载消息失败')
  }
}

async function createNewConversation() {
  try {
    const data = await createConversation({ model: selectedModelId.value })
    const conversation = toLocalConversation(data.conversation)
    conversations.value.unshift(conversation)
    messages[conversation.id] = (data.messages || []).map(toLocalMessage)
    activeConversationId.value = conversation.id
    sidebarOpen.value = false
    showToast('已创建新对话')
  } catch (error) {
    showToast(error?.message || '新建对话失败')
  }
}

async function editConversation({ id, title }) {
  const conversation = conversations.value.find(c => c.id === id)
  if (!conversation || !title || conversation.title === title) return

  const previous = conversation.title
  conversation.title = title
  try {
    await updateConversation(id, { title })
    showToast('标题已更新')
  } catch (error) {
    conversation.title = previous
    showToast(error?.message || '标题更新失败')
  }
}

function askDeleteConversation(id) {
  const conversation = conversations.value.find(c => c.id === id)
  if (conversation) pendingDelete.value = conversation
}

async function confirmDelete() {
  const target = pendingDelete.value
  if (!target) return
  pendingDelete.value = null

  try {
    await deleteConversation(target.id)
  } catch (error) {
    showToast(error?.message || '删除对话失败')
    return
  }

  const index = conversations.value.findIndex(c => c.id === target.id)
  if (index !== -1) conversations.value.splice(index, 1)
  delete messages[target.id]

  if (target.id === activeConversationId.value) {
    if (conversations.value.length) {
      activeConversationId.value = conversations.value[0].id
      loadMessages(activeConversationId.value).catch(() => {})
    } else {
      await createNewConversation()
    }
  }
  showToast('对话已删除')
}

function useSuggestion(text) {
  inputMessage.value = text
  sendMessage()
}

async function sendMessage() {
  const content = inputMessage.value.trim()
  if (!content || isLoading.value) return

  const id = activeConversationId.value
  if (!id) {
    showToast('请先新建对话')
    return
  }
  if (!messages[id]) messages[id] = []

  // 乐观渲染用户消息
  messages[id].push({ id: uid(), type: 'user', content, timestamp: nowTime() })

  // 标题与预览由后端决定（start/done 事件带回权威值），前端只更新时间戳占位
  const conversation = currentConversation.value
  if (conversation) conversation.timestamp = '刚刚'

  inputMessage.value = ''
  isLoading.value = true

  const msgId = uid()
  messages[id].push({
    id: msgId,
    type: 'ai',
    model: selectedModelId.value,
    content: '',
    thinking: '',
    thinkingSec: 0,
    phase: 'answer',
    timestamp: nowTime()
  })

  const thinkStart = Date.now()
  streamConversationId.value = id
  abortStream()
  streamController = new AbortController()
  let streamError = ''

  try {
    const result = await streamChat({
      conversationId: id,
      model: selectedModelId.value,
      content,
      signal: streamController.signal,
      onEvent(event) {
        // 等待期间可能已切换或删除对话
        const list = messages[id]
        const message = list && list.find(item => item.id === msgId)

        if (event.type === 'start') {
          const target = conversations.value.find(c => c.id === id)
          if (target) {
            // 标题/预览以后端为准
            if (event.title) target.title = event.title
            if (event.preview) target.preview = event.preview
            target.timestamp = '刚刚'
          }
          return
        }
        if (!message) return

        if (event.type === 'thinking') {
          message.thinking += event.delta
          // 流式过程中的实时占位；结束后由 done/error 带回后端测量值覆盖
          message.thinkingSec = Math.max(1, Math.round((Date.now() - thinkStart) / 1000))
          message.phase = 'think'
        } else if (event.type === 'content') {
          message.content += event.delta
          message.phase = 'answer'
        } else if (event.type === 'done' || event.type === 'error') {
          message.phase = 'done'
          // 思考耗时以后端落库值为准，刷新前后保持一致
          if (typeof event.thinkingSec === 'number') message.thinkingSec = event.thinkingSec
          // 每轮结束同步最新额度，耗尽即锁定输入框（无需轮询）
          if (event.usage) applyUsage(event.usage)
          if (event.type === 'done') {
            const target = conversations.value.find(c => c.id === id)
            if (target) {
              if (event.title) target.title = event.title
              if (event.preview) target.preview = event.preview
              target.timestamp = '刚刚'
            }
          }
        }
      }
    })
    streamError = result?.error || ''
  } catch (error) {
    if (error?.name !== 'AbortError') {
      streamError = error?.message || '生成回复失败'
      // 额度用尽（402）：后端是硬闸门，这里同步状态并锁定输入框
      if (error?.code === 'quota_exceeded') {
        applyUsage(error.payload)
        streamError = error?.message || '今日输出 token 已达上限'
      }
    }
  } finally {
    streamController = null
    isLoading.value = false
    if (streamConversationId.value === id) streamConversationId.value = ''

    const list = messages[id]
    const message = list && list.find(item => item.id === msgId)
    if (message) {
      message.phase = 'done'
      // 完全没有产出的失败回复不予保留，避免留下空气泡
      if (!message.content && !message.thinking) {
        const index = list.indexOf(message)
        if (index !== -1) list.splice(index, 1)
      }
    }

    // 预览以 start/done 事件带回的后端值为准，这里不再本地重算
    const target = conversations.value.find(c => c.id === id)
    if (target && message?.content) target.timestamp = '刚刚'
    if (streamError) showToast(streamError)
  }
}

function onModelChange(model) {
  const conversation = currentConversation.value
  if (conversation) {
    conversation.model = model.id
    updateConversation(conversation.id, { model: model.id }).catch(error => {
      showToast(error?.message || '模型切换保存失败')
    })
  }
  localStorage.setItem('noschat.model', model.id)
  showToast(`已切换到 ${model.name}`)
}

function handleAuthSuccess() {
  showToast(lastAuthIsNew.value ? '账号已创建并登录！' : '登录成功！')
  bootstrap()
}

// ---------------- 昵称设置 ----------------

function openNicknameDialog() {
  const current = currentUser.value?.nickname || ''
  // 昵称仍是邮箱时视为未设置，清空以便直接输入
  nicknameInput.value = current === currentUser.value?.email ? '' : current
  nicknameDialog.value = true
  nextTick(() => nicknameInputRef.value?.focus())
}

function skipNickname() {
  nicknameDialog.value = false
  clearNicknamePrompt()
  showToast('已使用邮箱作为昵称')
}

async function saveNickname() {
  if (nicknameSaving.value) return
  nicknameSaving.value = true
  try {
    const user = await saveNicknameApi(nicknameInput.value)
    nicknameDialog.value = false
    clearNicknamePrompt()
    showToast(`昵称已更新为 ${user?.nickname || '邮箱'}`)
  } catch (error) {
    showToast(error?.message || '昵称保存失败')
  } finally {
    nicknameSaving.value = false
  }
}

function handleLogout() {
  abortStream()
  // 会先请求后端撤销该账号的全部令牌，再清空本地状态
  void authLogout()
  conversations.value = []
  Object.keys(messages).forEach(key => { delete messages[key] })
  activeConversationId.value = ''
  resetUsage()
  showToast('已退出登录')
}

function getAvatarInitial(name) {
  if (!name) return '?'
  return name.charAt(0).toUpperCase()
}

watch(activeConversationId, () => {
  sidebarOpen.value = false
})

// 登录成功后加载模型清单与历史会话
watch(isAuthenticated, value => {
  if (value) bootstrap()
})

// 验证码登录自动注册后，提示设置昵称
watch(needsNicknamePrompt, value => {
  if (value && !nicknameDialog.value) openNicknameDialog()
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

// 额度跨日自动解锁：额度用尽后每分钟检查一次重置时刻，到了就重新拉取
let quotaTimer = null

onMounted(() => {
  mql?.addEventListener('change', onViewportChange)
  if (isAuthenticated.value) bootstrap()
  quotaTimer = setInterval(() => { void refreshIfReset() }, 60 * 1000)
  console.log('NosChat AI 聊天应用已启动', { isAuthenticated: isAuthenticated.value })
})

onBeforeUnmount(() => {
  mql?.removeEventListener('change', onViewportChange)
  if (quotaTimer) {
    clearInterval(quotaTimer)
    quotaTimer = null
  }
  abortStream()
})
</script>

<style scoped>
/* 登录态校验占位（存在本地令牌但后端尚未确认时显示） */
.app-boot {
  display: grid;
  place-items: center;
  min-height: 100vh;
  min-height: 100dvh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.boot-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem 2.5rem;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 1.25rem;
  backdrop-filter: blur(10px);
  color: #fff;
  font-size: 0.9rem;
}

.boot-card p {
  margin: 0;
}

.boot-spinner {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  animation: boot-spin 0.9s linear infinite;
}

@keyframes boot-spin {
  to { transform: rotate(360deg); }
}

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
  cursor: pointer;
  border-bottom: 1px dashed transparent;
  transition: border-color 0.2s ease;
}

.user-nickname:hover {
  border-bottom-color: rgba(255, 255, 255, 0.6);
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

.btn.primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}

.btn.primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.4);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 昵称设置弹窗的输入框 */
.nickname-field {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.7rem;
  font-size: 0.9rem;
  color: #1e293b;
  background: #fff;
  margin-bottom: 1.25rem;
  transition: all 0.2s ease;
}

.nickname-field:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
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
  .boot-spinner { animation: none; }
  .menu-bars,
  .menu-bars::before,
  .menu-bars::after { transition: none; }
}
</style>