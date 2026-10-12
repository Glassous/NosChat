/** 模型清单、会话与消息、流式对话接口。 */

import { API_BASE, ApiError, clearAuthStorage, getToken, request, UNAUTHORIZED_EVENT } from './client.js'

/** 模型清单（含介绍、发布日期等展示字段） */
export function fetchModels() {
  return request('/api/models', { auth: false })
}

/** 会话列表 */
export function fetchConversations() {
  return request('/api/conversations')
}

/** 新建会话（后端会附带一条欢迎消息） */
export function createConversation({ model, title } = {}) {
  return request('/api/conversations', { method: 'POST', body: { model, title } })
}

/** 会话历史消息 */
export function fetchMessages(conversationId) {
  return request(`/api/conversations/${encodeURIComponent(conversationId)}/messages`)
}

/** 更新会话（标题 / 模型 / 置顶 / 未读） */
export function updateConversation(conversationId, patch) {
  return request(`/api/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'PATCH',
    body: patch
  })
}

/** 删除会话 */
export function deleteConversation(conversationId) {
  return request(`/api/conversations/${encodeURIComponent(conversationId)}`, { method: 'DELETE' })
}

/**
 * 流式对话：POST + ReadableStream 解析 SSE。
 * 事件类型：start / thinking / content / done / error。
 * @param {{conversationId: string, model: string, content: string, signal?: AbortSignal, onEvent: (event: object) => void}} options
 */
export async function streamChat({ conversationId, model, content, signal, onEvent }) {
  const headers = { 'Content-Type': 'application/json', Accept: 'text/event-stream' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ conversationId, model, content }),
      signal
    })
  } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError('无法连接后端服务，请确认后端已启动', 0)
  }

  if (!response.ok) {
    let detail = ''
    try {
      const data = await response.json()
      detail = typeof data?.detail === 'string' ? data.detail : ''
    } catch {
      detail = ''
    }
    if (response.status === 401) {
      clearAuthStorage()
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
    }
    throw new ApiError(detail || `对话请求失败（${response.status}）`, response.status)
  }

  if (!response.body) {
    throw new ApiError('当前浏览器不支持流式响应', 0)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let errorMessage = ''

  const handleBlock = block => {
    for (const line of block.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const payload = trimmed.slice(5).trim()
      if (!payload) continue
      let event
      try {
        event = JSON.parse(payload)
      } catch {
        continue
      }
      if (event.type === 'error') errorMessage = event.message || '生成失败'
      onEvent(event)
    }
  }

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let index = buffer.indexOf('\n\n')
      while (index !== -1) {
        handleBlock(buffer.slice(0, index))
        buffer = buffer.slice(index + 2)
        index = buffer.indexOf('\n\n')
      }
    }
    if (buffer.trim()) handleBlock(buffer)
  } finally {
    reader.releaseLock?.()
  }

  return { error: errorMessage }
}
