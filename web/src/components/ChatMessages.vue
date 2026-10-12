<template>
  <div class="chat-messages" ref="scrollRef" @scroll="onScroll">
    <div v-if="messages.length === 0" class="empty-state">
      <div class="empty-icon">🤖</div>
      <h3>开始新的对话</h3>
      <p class="empty-sub">
        当前模型：<strong>{{ activeModel.name }}</strong>（{{ activeModel.provider }}）
      </p>
      <p class="empty-tip">{{ activeModel.desc }}</p>
      <div class="suggestions">
        <button
          v-for="(suggestion, index) in suggestions"
          :key="index"
          class="suggestion-btn"
          @click="$emit('suggestion-selected', suggestion)"
        >
          {{ suggestion }}
        </button>
      </div>
    </div>

    <div v-else class="messages-container">
      <div
        v-for="message in messages"
        :key="message.id"
        class="message-wrapper"
        :class="message.type"
      >
        <div class="message-bubble">
          <div class="message-header">
            <div class="sender-info">
              <span
                class="sender-icon"
                :class="{ model: message.type === 'ai' }"
                :style="message.type === 'ai' ? { background: modelOf(message).color } : null"
              >{{ message.type === 'ai' ? modelOf(message).icon : '👤' }}</span>
              <span class="sender-name">
                {{ message.type === 'ai' ? modelOf(message).name : '用户' }}
              </span>
              <span v-if="message.type === 'ai'" class="sender-provider">
                {{ modelOf(message).provider }}
              </span>
            </div>
            <span class="message-time">{{ message.timestamp }}</span>
          </div>

          <!-- 深度思考：可展开 / 折叠 -->
          <div v-if="showThinking(message)" class="think" :class="{ open: isThinkOpen(message) }">
            <button
              type="button"
              class="think-head"
              :aria-expanded="isThinkOpen(message)"
              :aria-controls="`think-${message.id}`"
              :title="isThinkOpen(message) ? '折叠思考过程' : '展开查看思考过程'"
              @click="toggleThink(message)"
            >
              <span class="think-ic" :class="{ live: isThinking(message) }">🧠</span>
              <span class="think-label">{{ isThinking(message) ? '深度思考中' : '深度思考' }}</span>
              <span v-if="isThinking(message)" class="think-dots"><i></i><i></i><i></i></span>
              <span class="think-time">{{ thinkTime(message) }}</span>
              <span class="think-chev" aria-hidden="true">⌄</span>
            </button>

            <div
              :id="`think-${message.id}`"
              class="think-anim"
              :aria-hidden="isThinkOpen(message) ? null : 'true'"
            >
              <div class="think-clip">
                <div class="think-text" :class="{ caret: isThinking(message) }">
                  {{ message.thinking }}
                </div>
              </div>
            </div>
          </div>

          <div v-if="waitingAnswer(message)" class="message-content">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
          <div
            v-else
            class="message-content"
            :class="{ caret: message.phase === 'answer' }"
          >{{ message.content }}</div>
        </div>
      </div>

      <div v-if="isLoading && !hasLiveMessage" class="message-wrapper ai">
        <div class="message-bubble">
          <div class="message-header">
            <div class="sender-info">
              <span class="sender-icon model" :style="{ background: activeModel.color }">
                {{ activeModel.icon }}
              </span>
              <span class="sender-name">{{ activeModel.name }}</span>
              <span class="sender-provider">正在生成回复…</span>
            </div>
          </div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <button v-if="showJumpBtn" class="jump-bottom" @click="scrollToBottom(true)">
      ↓ 最新消息
    </button>
  </div>
</template>

<script setup>
import { ref, computed, reactive, watch, nextTick } from 'vue'
import { getModel } from '../data/models.js'

const props = defineProps({
  messages: {
    type: Array,
    required: true,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  models: {
    type: Array,
    default: () => []
  },
  activeModelId: {
    type: String,
    default: ''
  },
  // 深度思考区块的默认展开状态（用户仍可逐条点击覆盖）
  thinkingOpen: {
    type: Boolean,
    default: false
  }
})

defineEmits(['suggestion-selected'])

const scrollRef = ref(null)
const atBottom = ref(true)

const activeModel = computed(() => getModel(props.activeModelId))

// message.id -> 手动展开/折叠；无记录时跟随 thinkingOpen 默认值
const thinkMap = reactive({})

const suggestions = [
  '你好！你能做什么？',
  '解释一下人工智能的基本概念',
  '帮我写一段 JavaScript 代码示例',
  '如何学习编程？',
  '推荐一些技术书籍'
]

const showJumpBtn = computed(() => !atBottom.value && props.messages.length > 0)

// 正在流式生成的消息自带打字效果，无需额外的「正在生成」气泡
const hasLiveMessage = computed(() =>
  props.messages.some(m => m.phase === 'think' || m.phase === 'answer')
)

function modelOf(message) {
  return getModel(message.model || props.activeModelId)
}

function isThinking(m) {
  return m.phase === 'think'
}

function waitingAnswer(m) {
  return m.phase === 'answer' && !m.content
}

function showThinking(m) {
  return isThinking(m) || !!(m.thinking && m.thinking.length)
}

function isThinkOpen(m) {
  // 思考进行中强制展开，结束后回到默认/手动状态
  if (isThinking(m)) return true
  const manual = thinkMap[m.id]
  return manual === undefined ? props.thinkingOpen : manual
}

function toggleThink(m) {
  thinkMap[m.id] = !isThinkOpen(m)
}

function thinkTime(m) {
  const sec = m.thinkingSec || 0
  if (isThinking(m)) return `${sec} 秒`
  return sec ? `已思考 ${sec} 秒` : '已完成思考'
}

function onScroll() {
  const el = scrollRef.value
  if (!el) return
  atBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80
}

function scrollToBottom(smooth = false) {
  nextTick(() => {
    const el = scrollRef.value
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
    atBottom.value = true
  })
}

// 新消息 / 加载态变化时，若原本贴在底部则继续跟随
watch(
  () => [props.messages.length, props.isLoading],
  () => {
    if (atBottom.value) scrollToBottom()
  }
)

// 流式打字时文本不断变长，贴在底部的话跟着滚
watch(
  () => {
    const last = props.messages[props.messages.length - 1]
    if (!last) return ''
    return `${(last.thinking || '').length}/${(last.content || '').length}/${last.phase || ''}`
  },
  () => {
    if (atBottom.value) scrollToBottom()
  }
)

// 切换对话时直接定位到底部
watch(
  () => props.messages,
  () => scrollToBottom()
)

// 全局默认切换时清掉逐条手动状态，避免「点了没反应」
watch(
  () => props.thinkingOpen,
  () => {
    Object.keys(thinkMap).forEach(key => { delete thinkMap[key] })
  }
)
</script>

<style scoped>
.chat-messages {
  flex: 1;
  padding: clamp(0.85rem, 2.5vw, 1.5rem);
  overflow-y: auto;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  position: relative;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  text-align: center;
  color: #64748b;
  padding: 1rem 0;
}

.empty-icon {
  font-size: clamp(2.5rem, 8vw, 4rem);
  margin-bottom: 1rem;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

.empty-state h3 {
  font-size: clamp(1.1rem, 3.5vw, 1.5rem);
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.empty-sub {
  font-size: 0.85rem;
  margin-bottom: 0.35rem;
}

.empty-sub strong {
  color: #667eea;
}

.empty-tip {
  font-size: 0.78rem;
  opacity: 0.8;
  margin-bottom: 1.75rem;
  max-width: 320px;
  line-height: 1.5;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  justify-content: center;
  max-width: 600px;
}

.suggestion-btn {
  padding: 0.65rem 1.1rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  font-size: 0.82rem;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  min-height: 44px;
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
  max-width: min(80%, 720px);
  background: white;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  min-width: 0;
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
  border: 1px solid #eef2f7;
}

.message-header {
  padding: 0.6rem 0.9rem 0.45rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.message-wrapper.user .message-header {
  border-bottom-color: rgba(255, 255, 255, 0.1);
}

.sender-info {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
}

.sender-icon {
  font-size: 0.95rem;
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  border-radius: 0.35rem;
  display: grid;
  place-items: center;
}

.sender-icon.model {
  font-size: 0.8rem;
}

.sender-name {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.message-wrapper.user .sender-name {
  color: rgba(255, 255, 255, 0.85);
}

.message-wrapper.ai .sender-name {
  color: #334155;
}

.sender-provider {
  font-size: 0.65rem;
  color: #94a3b8;
  white-space: nowrap;
}

.message-wrapper.user .sender-provider {
  display: none;
}

.message-time {
  font-size: 0.66rem;
  opacity: 0.7;
  white-space: nowrap;
  flex: 0 0 auto;
}

.message-wrapper.user .message-time {
  color: rgba(255, 255, 255, 0.8);
}

.message-wrapper.ai .message-time {
  color: #94a3b8;
}

.message-content {
  padding: 0.9rem;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  font-size: 0.875rem;
}

.message-wrapper.user .message-content {
  color: white;
}

/* ---------- 深度思考（展开 / 折叠） ---------- */
.think {
  margin: 0.55rem 0.9rem 0;
  border: 1px solid #e8ecf5;
  border-radius: 0.7rem;
  background: linear-gradient(135deg, #f7f8ff 0%, #faf7ff 100%);
  overflow: hidden;
}

.think-head {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  padding: 0.5rem 0.6rem;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  color: #4c5687;
  transition: background 0.18s ease;
}

.think-head:hover {
  background: rgba(102, 126, 234, 0.07);
}

.think-head:focus-visible {
  outline: 2px solid #667eea;
  outline-offset: -2px;
}

.think-ic {
  font-size: 0.82rem;
  line-height: 1;
}

.think-ic.live {
  animation: thinkPulse 1.6s ease-in-out infinite;
}

@keyframes thinkPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.16); opacity: 0.75; }
}

.think-label {
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

.think-dots {
  display: flex;
  align-items: center;
  gap: 0.18rem;
}

.think-dots i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #8b93d6;
  animation: thinkDot 1.2s ease-in-out infinite;
}

.think-dots i:nth-child(2) { animation-delay: 0.18s; }
.think-dots i:nth-child(3) { animation-delay: 0.36s; }

@keyframes thinkDot {
  0%, 100% { transform: translateY(0); opacity: 0.45; }
  50% { transform: translateY(-3px); opacity: 1; }
}

.think-time {
  font-size: 0.68rem;
  color: #8b93b8;
  white-space: nowrap;
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}

.think-chev {
  font-size: 0.78rem;
  color: #98a1c8;
  transition: transform 0.25s ease;
  flex: 0 0 auto;
}

.think.open .think-chev {
  transform: rotate(180deg);
}

/* 0fr → 1fr 的高度过渡：不支持浏览器会直接切换，不影响功能 */
.think-anim {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.3s ease;
}

.think.open .think-anim {
  grid-template-rows: 1fr;
}

.think-clip {
  overflow: hidden;
  min-height: 0;
}

.think-text {
  margin: 0 0.6rem 0.6rem;
  padding: 0.55rem 0.65rem;
  border-left: 2px solid #c3cbf0;
  background: rgba(255, 255, 255, 0.72);
  border-radius: 0 0.45rem 0.45rem 0;
  font-size: 0.76rem;
  line-height: 1.7;
  color: #5b6490;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  max-height: 340px;
  overflow-y: auto;
}

/* 打字光标 */
.caret::after {
  content: '▍';
  margin-left: 1px;
  color: #667eea;
  animation: caretBlink 1s steps(2, start) infinite;
}

.think-text.caret::after {
  color: #8b93d6;
}

@keyframes caretBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.35rem 0;
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
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-8px); }
}

.jump-bottom {
  position: sticky;
  bottom: 0.5rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 0.4rem 0.9rem;
  font-size: 0.75rem;
  color: #667eea;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
  min-height: 36px;
}

.jump-bottom:hover {
  background: #667eea;
  color: #fff;
}

@media (max-width: 768px) {
  .message-bubble {
    max-width: 90%;
  }

  .suggestions {
    flex-direction: column;
    width: 100%;
    max-width: 340px;
  }

  .suggestion-btn {
    width: 100%;
  }

  .sender-provider {
    display: none;
  }

  .empty-tip {
    margin-bottom: 1.25rem;
  }
}

@media (max-width: 420px) {
  .message-bubble {
    max-width: 95%;
  }

  .message-content {
    font-size: 0.85rem;
    padding: 0.75rem;
  }

  .message-header {
    padding: 0.5rem 0.7rem 0.4rem;
  }

  .think {
    margin: 0.45rem 0.7rem 0;
  }

  .think-text {
    font-size: 0.74rem;
    max-height: 240px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .empty-icon { animation: none; }
  .message-wrapper { animation: none; }
  .typing-indicator span { animation: none; }
  .think-anim { transition: none; }
  .think-chev { transition: none; }
  .think-ic.live,
  .think-dots i,
  .caret::after { animation: none; }
}
</style>
