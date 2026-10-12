<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <button class="new-chat-btn" @click="$emit('new-conversation')">
        <span class="plus-icon">+</span>
        <span>新建对话</span>
      </button>
    </div>
    
    <div class="conversations-list">
      <div v-for="conversation in conversations" 
           :key="conversation.id"
           class="conversation-item"
           :class="{ active: conversation.id === activeConversation, unread: conversation.unread }"
           @click="$emit('select-conversation', conversation.id)">
        <div class="conversation-icon">
          <span v-if="conversation.id === activeConversation">💬</span>
          <span v-else>📝</span>
        </div>
        <div class="conversation-info">
          <div class="conversation-title">
            {{ conversation.title }}
            <span v-if="conversation.unread" class="unread-badge"></span>
          </div>
          <div class="conversation-preview">
            {{ conversation.preview }}
          </div>
          <div class="conversation-meta">
            <span class="timestamp">{{ conversation.timestamp }}</span>
          </div>
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
          <span class="usage-label">状态</span>
          <span class="usage-value status-value">演示</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  conversations: {
    type: Array,
    required: true
  },
  activeConversation: {
    type: String,
    required: true
  }
})

defineEmits(['select-conversation', 'new-conversation'])
</script>

<style scoped>
.chat-sidebar {
  width: 280px;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.new-chat-btn {
  width: 100%;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.new-chat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.plus-icon {
  font-size: 1.25rem;
  line-height: 1;
}

.conversations-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.conversation-item {
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  gap: 0.75rem;
  position: relative;
}

.conversation-item:hover {
  background: #f1f5f9;
}

.conversation-item.active {
  background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
  border: 1px solid #667eea;
}

.conversation-item.unread {
  background: linear-gradient(135deg, #10b98110 0%, #3b82f610 100%);
  border: 1px solid #10b98120;
}

.conversation-icon {
  font-size: 1.25rem;
  margin-top: 0.25rem;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-title {
  font-weight: 600;
  color: #1e293b;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.unread-badge {
  width: 8px;
  height: 8px;
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
  font-size: 0.75rem;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  margin-bottom: 0.25rem;
}

.conversation-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timestamp {
  color: #94a3b8;
  font-size: 0.7rem;
  font-weight: 500;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #e2e8f0;
  background: #ffffff;
}

.usage-info {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.usage-item {
  flex: 1;
  text-align: center;
  padding: 0.5rem;
  background: #f1f5f9;
  border-radius: 0.5rem;
}

.usage-label {
  display: block;
  color: #64748b;
  font-size: 0.7rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.usage-value {
  display: block;
  color: #1e293b;
  font-weight: 700;
  font-size: 1rem;
}

.status-value {
  color: #667eea;
}

@media (max-width: 768px) {
  .chat-sidebar {
    width: 100%;
  }
}
</style>