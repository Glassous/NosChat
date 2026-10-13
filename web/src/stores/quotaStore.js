/**
 * 额度状态：对接后端 /api/usage/today。
 *
 * 前端只做展示与"别让用户白打字"的锁定；真正的拦截在后端
 * POST /api/chat/stream（额度用尽固定返回 402 quota_exceeded），
 * 因此绕过输入框也无法超额度。
 *
 * 额度快照来源有两个：登录后 GET /api/usage/today，以及每轮对话结束时
 * SSE done/error 事件携带的 usage 字段（无需轮询）。
 */

import { computed, reactive } from 'vue'

import { fetchUsage } from '../api/usage.js'

const state = reactive({
  limit: 0,
  used: 0,
  remaining: 0,
  exceeded: false,
  resetAt: '',
  day: '',
  timezone: '',
  /** 是否已从后端拿到过一次快照 */
  loaded: false
})

function toNumber(value, fallback = 0) {
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

/** 写入一次后端下发的额度快照（字段缺失时保持原值，避免界面闪回） */
export function applyUsage(payload) {
  if (!payload || typeof payload !== 'object') return state
  if (payload.limit !== undefined) state.limit = toNumber(payload.limit)
  if (payload.used !== undefined) state.used = toNumber(payload.used)
  state.remaining = payload.remaining !== undefined
    ? toNumber(payload.remaining)
    : Math.max(0, state.limit - state.used)
  if (payload.exceeded !== undefined) state.exceeded = Boolean(payload.exceeded)
  else state.exceeded = state.limit > 0 && state.used >= state.limit
  if (typeof payload.resetAt === 'string') state.resetAt = payload.resetAt
  if (typeof payload.day === 'string') state.day = payload.day
  if (typeof payload.timezone === 'string') state.timezone = payload.timezone
  state.loaded = true
  return state
}

/** 退出登录时清空，避免下一个账号看到上一个账号的额度状态 */
export function resetUsage() {
  state.limit = 0
  state.used = 0
  state.remaining = 0
  state.exceeded = false
  state.resetAt = ''
  state.day = ''
  state.timezone = ''
  state.loaded = false
  return state
}

/** 重置时刻是否已过（用于跨日自动解锁；解析失败时保守返回 false） */
function resetPassed() {
  if (!state.resetAt) return false
  const ts = Date.parse(state.resetAt.replace(' ', 'T'))
  return Number.isFinite(ts) && Date.now() >= ts
}

export function useQuota() {
  const exceeded = computed(() => state.exceeded)
  /** 展示用的重置时间：后端已按 QUOTA_TIMEZONE 格式化，直接展示即可 */
  const resetLabel = computed(() => state.resetAt || '')

  /** 拉取一次额度快照（失败静默：不阻塞聊天，后端仍会拦截） */
  async function loadUsage() {
    try {
      applyUsage(await fetchUsage())
    } catch {
      /* 未登录/网络异常：保持现状 */
    }
    return state
  }

  /** 供 App 的定时器调用：跨日后重新拉取以解锁输入框 */
  async function refreshIfReset() {
    if (state.exceeded && resetPassed()) await loadUsage()
  }

  return {
    quota: state,
    exceeded,
    resetLabel,
    loadUsage,
    refreshIfReset,
    applyUsage,
    resetUsage
  }
}
