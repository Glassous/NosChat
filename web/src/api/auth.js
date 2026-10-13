/** 认证相关接口（验证码注册 / 验证码登录 / 找回密码 / 密码登录）。 */

import { request } from './client.js'

/**
 * 发送邮箱验证码。
 * @param {string} email 邮箱
 * @param {'register'|'login'|'reset'} purpose 用途
 * @returns {Promise<{expiresIn:number,resendAfter:number,devCode?:string|null}>}
 */
export function sendCode(email, purpose = 'register') {
  return request('/api/auth/send-code', {
    method: 'POST',
    body: { email, purpose },
    auth: false
  })
}

/** 注册（成功即返回登录令牌），返回 { token, expiresIn, user, isNewUser } */
export function register({ email, code, nickname, password }) {
  return request('/api/auth/register', {
    method: 'POST',
    body: { email, code, nickname, password },
    auth: false
  })
}

/** 邮箱密码登录 */
export function login({ email, password }) {
  return request('/api/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false
  })
}

/** 邮箱验证码登录：邮箱未注册时自动注册（昵称留空则使用邮箱） */
export function loginWithCode({ email, code, nickname }) {
  return request('/api/auth/login-code', {
    method: 'POST',
    body: { email, code, nickname },
    auth: false
  })
}

/** 找回密码：验证码校验通过后重置密码并自动登录 */
export function resetPassword({ email, code, password }) {
  return request('/api/auth/reset-password', {
    method: 'POST',
    body: { email, code, password },
    auth: false
  })
}

/** 当前登录用户 */
export function fetchMe() {
  return request('/api/auth/me')
}

/**
 * 退出登录：后端会把令牌版本 +1，使该账号此前签发的所有令牌立即失效。
 * 前端必须在清空本地令牌之前发起该请求（请求头读取 localStorage 中的令牌）。
 */
export function logout() {
  return request('/api/auth/logout', { method: 'POST' })
}

/** 更新昵称（昵称留空时后端会回退为邮箱） */
export function updateProfile({ nickname }) {
  return request('/api/auth/me', {
    method: 'PATCH',
    body: { nickname }
  })
}
