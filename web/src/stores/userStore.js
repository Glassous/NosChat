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
  initialized: false,
  // 最近一次鉴权是否为「验证码登录自动注册」
  lastAuthIsNew: false,
  // 是否需要提示设置昵称（自动注册且当前昵称仍为邮箱）
  needsNicknamePrompt: false
})

/** 令牌失效（后端返回 401）时同步清理本地状态 */
window.addEventListener(UNAUTHORIZED_EVENT, () => {
  state.user = null
  state.token = null
  state.initialized = false
})

function applySession({ token, user, isNewUser = false }, { nicknamePrompt = false } = {}) {
  state.token = token
  state.user = user
  state.initialized = true
  state.lastAuthIsNew = Boolean(isNewUser)
  state.needsNicknamePrompt = Boolean(nicknamePrompt)
  saveToken(token)
  saveUser(user)
  return user
}

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(state.user && state.token))
  const currentUser = computed(() => state.user)
  const authToken = computed(() => state.token)
  const authLoading = computed(() => state.isLoading)
  const lastAuthIsNew = computed(() => state.lastAuthIsNew)
  const needsNicknamePrompt = computed(() => state.needsNicknamePrompt)

  /** 发送邮箱验证码（register 注册 / login 验证码登录 / reset 找回密码） */
  async function sendCode({ email, purpose = 'register' }) {
    return authApi.sendCode(email, purpose)
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

  /** 邮箱验证码登录（邮箱未注册时自动注册，并提示补全昵称） */
  async function loginWithCode({ email, code, nickname }) {
    if (state.isLoading) return null
    state.isLoading = true
    try {
      const data = await authApi.loginWithCode({ email, code, nickname })
      const autoRegistered = Boolean(data.isNewUser)
      // 昵称仍等于邮箱（即未设置过昵称）时，登录后弹出昵称设置
      const nicknameIsEmail = data.user?.nickname === data.user?.email
      applySession(data, { nicknamePrompt: autoRegistered && nicknameIsEmail })
      return data
    } finally {
      state.isLoading = false
    }
  }

  /** 找回密码（重置成功后自动登录） */
  async function resetPassword({ email, code, password }) {
    if (state.isLoading) return null
    state.isLoading = true
    try {
      const data = await authApi.resetPassword({ email, code, password })
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

  /** 保存昵称（留空时由后端回退为邮箱） */
  async function saveNickname(nickname) {
    const user = await authApi.updateProfile({ nickname: (nickname || '').trim() })
    state.user = user
    state.initialized = true
    saveUser(user)
    return user
  }

  /** 关闭昵称设置提示 */
  function clearNicknamePrompt() {
    state.needsNicknamePrompt = false
  }

  /** 本地更新用户信息 */
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
    lastAuthIsNew,
    needsNicknamePrompt,

    // 方法
    sendCode,
    register,
    login,
    loginWithCode,
    resetPassword,
    fetchMe,
    saveNickname,
    clearNicknamePrompt,
    logout,
    updateUser
  }
}

// 已有令牌但本地缺少用户信息时，后台补拉一次
if (state.token && !state.user) {
  void useAuth().fetchMe()
}
