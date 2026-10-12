/**
 * 用户状态管理：对接后端 /api/auth（邮箱验证码注册 + 邮箱密码登录）。
 * 对外暴露的字段与函数签名保持与原实现一致，便于界面层零改动复用。
 */

import { computed, reactive } from 'vue'

import * as authApi from '../api/auth.js'
import {
  clearAuthStorage,
  getToken,
  loadUser,
  saveToken,
  saveUser,
  UNAUTHORIZED_EVENT
} from '../api/client.js'

const state = reactive({
  user: loadUser(),
  token: getToken() || null,
  isLoading: false,
  initialized: false
})

/** 令牌失效（后端返回 401）时同步清理本地状态 */
window.addEventListener(UNAUTHORIZED_EVENT, () => {
  state.user = null
  state.token = null
  state.initialized = false
})

function applySession({ token, user }) {
  state.token = token
  state.user = user
  state.initialized = true
  saveToken(token)
  saveUser(user)
  return user
}

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(state.user && state.token))
  const currentUser = computed(() => state.user)
  const authToken = computed(() => state.token)
  const authLoading = computed(() => state.isLoading)

  /** 发送注册验证码 */
  async function sendCode({ email }) {
    return authApi.sendCode(email)
  }

  /** 注册（成功后自动登录） */
  async function register({ email, code, nickname, password }) {
    if (state.isLoading) return null
    state.isLoading = true
    try {
      const data = await authApi.register({ email, code, nickname, password })
      applySession(data)
      return data
    } finally {
      state.isLoading = false
    }
  }

  /** 登录 */
  async function login({ email, password }) {
    if (state.isLoading) return null
    state.isLoading = true
    try {
      const data = await authApi.login({ email, password })
      applySession(data)
      return data
    } finally {
      state.isLoading = false
    }
  }

  /** 拉取当前用户（令牌存在时可校验登录态） */
  async function fetchMe() {
    if (!state.token) return null
    try {
      const user = await authApi.fetchMe()
      state.user = user
      state.initialized = true
      saveUser(user)
      return user
    } catch (error) {
      // 401 已由客户端统一清理；其它错误保留现状
      if (error?.status === 401) logout()
      return null
    }
  }

  /** 退出登录 */
  function logout() {
    state.user = null
    state.token = null
    state.initialized = false
    clearAuthStorage()
  }

  /** 本地更新用户信息（后端暂无资料修改接口） */
  function updateUser(updates) {
    if (!state.user) return null
    const updatedUser = { ...state.user, ...updates }
    state.user = updatedUser
    saveUser(updatedUser)
    return updatedUser
  }

  return {
    // 状态
    isAuthenticated,
    currentUser,
    authToken,
    authLoading,

    // 方法
    sendCode,
    register,
    login,
    fetchMe,
    logout,
    updateUser
  }
}

// 已有令牌但本地缺少用户信息时，后台补拉一次
if (state.token && !state.user) {
  void useAuth().fetchMe()
}
