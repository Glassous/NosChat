<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <button class="new-chat-btn" @click="$emit('new-conversation')">
        <span class="plus-icon">+</span>
        <span>新建对话</span>
      </button>
      <button class="drawer-close" @click="$emit('close')" aria-label="关闭">✕</button>
    </div>

    <div class="sidebar-search">
      <span class="search-icon">🔍</span>
      <input
        v-model.trim="keyword"
        type="search"
        class="search-input"
        placeholder="搜索历史对话…"
        aria-label="搜索历史对话"
      />
      <button v-if="keyword" class="search-clear" @click="keyword = ''" aria-label="清空搜索">✕</button>
    </div>

    <div class="conversations-list">
      <p v-if="filtered.length === 0" class="list-empty">
        {{ keyword ? '没有匹配的对话' : '还没有对话，点击「新建对话」开始吧' }}
      </p>

      <div
        v-for="conversation in filtered"
        :key="conversation.id"
        class="conversation-item"
        :class="{
          active: conversation.id === activeConversation,
          unread: conversation.unread,
          editing: conversation.id === editingId
        }"
        role="button"
        tabindex="0"
        @click="$emit('select-conversation', conversation.id)"
        @keydown.enter.prevent="$emit('select-conversation', conversation.id)"
      >
        <div class="conversation-icon" :style="{ background: modelOf(conversation).color }">
          {{ modelOf(conversation).icon }}
        </div>

        <div class="conversation-info">
          <div class="conversation-title">
            <template v-if="conversation.id === editingId">
              <input
                :ref="setTitleInputRef"
                v-model="editingTitle"
                class="title-edit-input"
                type="text"
                maxlength="30"
                aria-label="修改对话标题"
                @keydown.enter="saveEditTitle(conversation.id)"
                @keydown.esc="cancelEdit"
                @blur="saveEditTitle(conversation.id)"
                @click.stop
              />
            </template>
            <template v-else>
              <span class="title-text">
                <span v-if="conversation.pinned" class="pin">📌</span>{{ conversation.title }}
              </span>
              <span v-if="conversation.unread" class="unread-badge"></span>
            </template>
          </div>
          <div class="conversation-preview">{{ conversation.preview }}</div>
          <div class="conversation-meta">
            <span class="timestamp">{{ conversation.timestamp }}</span>
            <span class="model-chip">{{ modelOf(conversation).name }}</span>
          </div>
        </div>

        <div class="conversation-actions">
          <button
            class="action-btn edit-btn"
            :aria-label="`重命名：${conversation.title}`"
            title="修改标题"
            @click.stop="startEdit(conversation)"
          >✏️</button>
          <button
            class="action-btn delete-btn"
            :aria-label="`删除：${conversation.title}`"
            title="删除对话"
            @click.stop="$emit('delete-conversation', conversation.id)"
          >🗑️</button>
        </div>
      </div>
    </div>

    <div class="sidebar-footer">
      <div class="usage-info">
        <div class="usage-item">
          <span class="usage-label">对话</span>
          <span class="usage-value">{{ conversations.length }}</span>
        </div>
        <div class="usage-item">
          <span class="usage-label">未读</span>
          <span class="usage-value">{{ unreadCount }}</span>
        </div>
        <div class="usage-item">
          <span class="usage-label">状态</span>
          <span class="usage-value status-value">演示</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { getModel } from '../data/models.js'

const props = defineProps({
  conversations: {
    type: Array,
    required: true
  },
  activeConversation: {
    type: String,
    required: true
  },
  models: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits([
  'select-conversation',
  'new-conversation',
  'edit-conversation',
  'delete-conversation',
  'close'
])

const keyword = ref('')
const editingId = ref(null)
const editingTitle = ref('')

// v-for 内的字符串 ref 会被收集成数组，改用回调 ref 直接拿到当前唯一的编辑输入框并聚焦
let editingSaving = false

function setTitleInputRef(el) {
  if (el) {
    el.focus()
    el.select()
  }
}

const filtered = computed(() => {
  const kw = keyword.value.toLowerCase()
  if (!kw) return props.conversations
  return props.conversations.filter(c =>
    `${c.title} ${c.preview}`.toLowerCase().includes(kw)
  )
})

const unreadCount = computed(() => props.conversations.filter(c => c.unread).length)

function modelOf(conversation) {
  return getModel(conversation.model)
}

function startEdit(conversation) {
  editingId.value = conversation.id
  editingTitle.value = conversation.title
}

function saveEditTitle(conversationId) {
  // Enter 提交后输入框被卸载会再次触发 blur，用标志位避免重复提交
  if (editingSaving || editingId.value !== conversationId) return

  const title = editingTitle.value.trim()
  editingSaving = true
  if (title) {
    emit('edit-conversation', { id: conversationId, title })
  }
  editingId.value = null
  editingTitle.value = ''
  nextTick(() => { editingSaving = false })
}

function cancelEdit() {
  editingId.value = null
  editingTitle.value = ''
}
</script>

<style scoped>
.chat-sidebar {
  width: 280px;
  flex: 0 0 280px;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.new-chat-btn {
  flex: 1;
  padding: 0.7rem 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  min-height: 44px;
  white-space: nowrap;
}

.new-chat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.plus-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.drawer-close {
  display: none;
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 0.7rem;
  color: #64748b;
  font-size: 0.9rem;
  cursor: pointer;
}

.drawer-close:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.sidebar-search {
  padding: 0.65rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
}

.search-icon {
  font-size: 0.8rem;
  opacity: 0.6;
}

.search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.8rem;
  color: #1e293b;
  padding: 0.3rem 0;
}

.search-input::placeholder {
  color: #94a3b8;
}

.search-clear {
  border: none;
  background: #f1f5f9;
  color: #64748b;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  font-size: 0.6rem;
  cursor: pointer;
  line-height: 1;
}

.conversations-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
  -webkit-overflow-scrolling: touch;
}

.list-empty {
  padding: 2rem 1rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.78rem;
  line-height: 1.6;
}

.conversation-item {
  padding: 0.7rem;
  margin-bottom: 0.45rem;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
  display: flex;
  gap: 0.6rem;
  position: relative;
  /* 预留边框，避免选中时内容跳动 */
  border: 1px solid transparent;
  outline: none;
}

.conversation-item:hover {
  background: #f1f5f9;
}

.conversation-item:focus-visible {
  border-color: #667eea;
  background: #f1f5f9;
}

.conversation-item:hover .conversation-actions,
.conversation-item.editing .conversation-actions {
  opacity: 1;
}

.conversation-item.active {
  background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
  border-color: #667eea;
}

.conversation-item.unread:not(.active) {
  background: linear-gradient(135deg, #10b98110 0%, #3b82f610 100%);
  border-color: #10b98133;
}

.conversation-icon {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  border-radius: 0.55rem;
  display: grid;
  place-items: center;
  font-size: 0.95rem;
  margin-top: 0.1rem;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-title {
  font-weight: 600;
  color: #1e293b;
  font-size: 0.85rem;
  margin-bottom: 0.2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
}

.title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.pin {
  margin-right: 0.15rem;
  font-size: 0.75rem;
}

.unread-badge {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.conversation-preview {
  color: #64748b;
  font-size: 0.73rem;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  margin-bottom: 0.25rem;
}

.conversation-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.4rem;
}

.timestamp {
  color: #94a3b8;
  font-size: 0.68rem;
  font-weight: 500;
  white-space: nowrap;
}

.model-chip {
  font-size: 0.62rem;
  color: #667eea;
  background: #667eea14;
  padding: 0.05rem 0.35rem;
  border-radius: 999px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 55%;
}

.conversation-actions {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  opacity: 0;
  transition: opacity 0.2s ease;
  align-self: center;
}

.action-btn {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 0.4rem;
  font-size: 0.72rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  background: transparent;
  padding: 0;
}

.edit-btn:hover {
  background: rgba(102, 126, 234, 0.15);
  transform: scale(1.08);
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  transform: scale(1.08);
}

.title-edit-input {
  width: 100%;
  padding: 0.15rem 0.4rem;
  border: 1px solid #667eea;
  border-radius: 0.375rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: #1e293b;
  background: white;
  outline: none;
  font-family: inherit;
}

.title-edit-input:focus {
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.sidebar-footer {
  padding: 0.75rem;
  border-top: 1px solid #e2e8f0;
  background: #ffffff;
}

.usage-info {
  display: flex;
  gap: 0.4rem;
}

.usage-item {
  flex: 1;
  text-align: center;
  padding: 0.4rem 0.2rem;
  background: #f1f5f9;
  border-radius: 0.5rem;
  min-width: 0;
}

.usage-label {
  display: block;
  color: #64748b;
  font-size: 0.62rem;
  font-weight: 500;
  letter-spacing: 0.03em;
  margin-bottom: 0.15rem;
}

.usage-value {
  display: block;
  color: #1e293b;
  font-weight: 700;
  font-size: 0.95rem;
}

.status-value {
  color: #667eea;
  font-size: 0.8rem;
}

/* 窄屏（抽屉态）：侧栏宽度由外层容器控制 */
@media (max-width: 900px) {
  .chat-sidebar {
    width: 100%;
    flex: 0 0 auto;
    border-right: none;
  }

  .drawer-close {
    display: block;
  }

  /* 触屏无 hover，操作按钮需常显 */
  .conversation-actions {
    opacity: 1;
  }
}

@media (max-width: 400px) {
  .sidebar-header { padding: 0.85rem 0.7rem; }
  .sidebar-search { padding: 0.5rem 0.7rem; }
  .conversations-list { padding: 0.35rem; }
  .conversation-item { padding: 0.6rem 0.5rem; gap: 0.45rem; }
  .conversation-icon { width: 26px; height: 26px; flex-basis: 26px; font-size: 0.85rem; }
  .model-chip { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .unread-badge { animation: none; }
  .action-btn:hover { transform: none; }
  .new-chat-btn:hover { transform: none; }
}
</style>
