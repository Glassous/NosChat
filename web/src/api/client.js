/**
 * 后端接口客户端：统一 base url、Bearer 令牌、JSON 编解码与错误规范化。
 * 说明：仅数据层，不涉及任何 UI 结构与样式。
 */

const RAW_BASE = import.meta.env.VITE_API_BASE_URL
/** 未配置时默认直连本地后端（9135） */
export const API_BASE = String(RAW_BASE === undefined || RAW_BASE === null ? 'http://127.0.0.1:9135' : RAW_BASE)
  .replace(/\/+$/, '')

export const TOKEN_KEY = 'noschat.token'
export const USER_KEY = 'noschat.user'

/** 未授权事件：登录态失效时通知应用回到登录页 */
export const UNAUTHORIZED_EVENT = 'noschat:unauthorized'

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function saveToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function saveUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  else localStorage.removeItem(USER_KEY)
}

export function loadUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function clearAuthStorage() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

function extractMessage(data, status) {
  if (data && typeof data === 'object') {
    const detail = data.detail ?? data.message
    if (typeof detail === 'string' && detail.trim()) return detail
    if (Array.isArray(detail)) {
      const parts = detail
        .map(item => (typeof item === 'string' ? item : item?.msg))
        .filter(Boolean)
      if (parts.length) return parts.join('；')
    }
  }
  if (typeof data === 'string' && data.trim()) return data.trim().slice(0, 200)
  return `请求失败（${status}）`
}

function buildHeaders({ body, auth, extra }) {
  const headers = { Accept: 'application/json', ...(extra || {}) }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }
  return headers
}

/**
 * 发起请求并返回解析后的 JSON。
 * @param {string} path 以 /api 开头的路径
 * @param {{method?: string, body?: any, auth?: boolean, signal?: AbortSignal}} options
 */
export async function request(path, options = {}) {
  const { method = 'GET', body, auth = true, signal } = options
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: buildHeaders({ body, auth, extra: null }),
      body: body === undefined ? undefined : JSON.stringify(body),
      signal
    })
  } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError('无法连接后端服务，请确认后端已启动', 0)
  }

  if (response.status === 204) return null

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearAuthStorage()
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
    }
    throw new ApiError(extractMessage(data, response.status), response.status)
  }

  return data
}
