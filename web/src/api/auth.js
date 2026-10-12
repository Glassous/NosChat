/** 认证相关接口（邮箱验证码注册 / 登录 / 当前用户）。 */

import { request } from './client.js'

/** 发送注册验证码，返回 { expiresIn, resendAfter, devCode? } */
export function sendCode(email) {
  return request('/api/auth/send-code', {
    method: 'POST',
    body: { email, purpose: 'register' },
    auth: false
  })
}

/** 注册（成功即返回登录令牌），返回 { token, expiresIn, user } */
export function register({ email, code, nickname, password }) {
  return request('/api/auth/register', {
    method: 'POST',
    body: { email, code, nickname, password },
    auth: false
  })
}

/** 登录，返回 { token, expiresIn, user } */
export function login({ email, password }) {
  return request('/api/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false
  })
}

/** 当前登录用户 */
export function fetchMe() {
  return request('/api/auth/me')
}
