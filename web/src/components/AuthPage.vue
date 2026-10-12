<template>
  <div class="auth-container">
    <!-- 背景装饰 -->
    <div class="auth-background">
      <div class="bg-blob bg-blob-1"></div>
      <div class="bg-blob bg-blob-2"></div>
      <div class="bg-blob bg-blob-3"></div>
    </div>

    <!-- 认证卡片 -->
    <div class="auth-card">
      <!-- 左上角logo -->
      <div class="auth-logo">
        <div class="logo-icon">🤖</div>
        <h1>NosChat</h1>
        <span class="tagline">AI 智能聊天助手</span>
      </div>

      <!-- 主内容区 -->
      <div class="auth-content">
        <!-- 标签页切换 -->
        <div class="auth-tabs">
          <button
            :class="['auth-tab', { active: mode === 'login' || mode === 'reset' }]"
            @click="switchMode('login')"
          >
            登录
          </button>
          <button
            :class="['auth-tab', { active: mode === 'register' }]"
            @click="switchMode('register')"
          >
            注册
          </button>
        </div>

        <div class="auth-forms">
          <!-- 登录表单（密码登录 / 验证码登录） -->
          <form
            v-if="mode === 'login'"
            class="auth-form"
            @submit.prevent="handleLoginSubmit"
            novalidate
          >
            <div class="auth-subtabs" role="tablist" aria-label="登录方式">
              <button
                type="button"
                role="tab"
                :class="['subtab', { on: loginMode === 'password' }]"
                :aria-selected="loginMode === 'password'"
                @click="loginMode = 'password'"
              >
                密码登录
              </button>
              <button
                type="button"
                role="tab"
                :class="['subtab', { on: loginMode === 'code' }]"
                :aria-selected="loginMode === 'code'"
                @click="loginMode = 'code'"
              >
                验证码登录
              </button>
            </div>

            <div class="form-group">
              <label for="login-email">
                <span class="icon">📧</span>
                <span>邮箱</span>
              </label>
              <div class="input-wrapper">
                <input
                  id="login-email"
                  v-model="loginForm.email"
                  type="email"
                  placeholder="请输入邮箱"
                  :disabled="authLoading"
                  required
                  autocomplete="email"
                />
                <span class="input-icon">@</span>
              </div>
              <p v-if="loginMode === 'code'" class="form-hint">
                该邮箱未注册时将自动创建账号
              </p>
            </div>

            <!-- 账号密码 -->
            <template v-if="loginMode === 'password'">
              <div class="form-group">
                <label for="login-password">
                  <span class="icon">🔒</span>
                  <span>密码</span>
                </label>
                <div class="input-wrapper">
                  <input
                    id="login-password"
                    v-model="loginForm.password"
                    :type="showPassword ? 'text' : 'password'"
                    placeholder="请输入密码"
                    :disabled="authLoading"
                    required
                    autocomplete="current-password"
                  />
                  <button
                    type="button"
                    class="toggle-password"
                    @click="showPassword = !showPassword"
                    tabindex="-1"
                  >
                    {{ showPassword ? '👁️' : '🙈' }}
                  </button>
                </div>
                <p class="form-hint row">
                  <span>使用注册邮箱与密码登录</span>
                  <button type="button" class="text-btn" @click="switchMode('reset')">
                    忘记密码？
                  </button>
                </p>
              </div>
            </template>

            <!-- 邮箱验证码（未注册自动注册） -->
            <template v-else>
              <div class="form-group">
                <label for="login-code">
                  <span class="icon">🔑</span>
                  <span>邮箱验证码</span>
                </label>
                <div class="input-wrapper has-code">
                  <input
                    id="login-code"
                    v-model.trim="loginForm.code"
                    type="text"
                    inputmode="numeric"
                    placeholder="请输入邮件中的验证码"
                    :disabled="authLoading"
                    required
                    autocomplete="one-time-code"
                    maxlength="8"
                  />
                  <button
                    type="button"
                    class="code-btn"
                    :disabled="authLoading || code.login.sending || code.login.countdown > 0"
                    @click="handleSendCode('login')"
                  >
                    {{ code.login.countdown > 0 ? `${code.login.countdown}s 后重发` : (code.login.sending ? '发送中…' : '获取验证码') }}
                  </button>
                </div>
                <p v-if="code.login.devCode" class="form-hint">开发模式验证码：{{ code.login.devCode }}</p>
                <p v-else-if="code.login.sent" class="form-hint">验证码已发送，请查收邮箱</p>
              </div>
            </template>

            <div class="form-actions">
              <button 
                type="submit" 
                class="auth-btn primary"
                :disabled="authLoading || !canSubmitLogin"
                :aria-busy="authLoading"
              >
                <template v-if="loginMode === 'code'">
                  <span v-if="!authLoading">登录 / 注册</span>
                  <span v-else>处理中...</span>
                </template>
                <template v-else>
                  <span v-if="!authLoading">登录</span>
                  <span v-else>登录中...</span>
                </template>
              </button>
            </div>

            <p class="form-switch">
              还没有账号？
              <button type="button" @click="switchMode('register')" class="text-btn">
                去注册
              </button>
            </p>
          </form>

          <!-- 注册表单 -->
          <form
            v-if="mode === 'register'"
            class="auth-form"
            @submit.prevent="handleRegister"
            novalidate
          >
            <div class="form-group">
              <label for="register-email">
                <span class="icon">📧</span>
                <span>邮箱 *</span>
              </label>
              <div class="input-wrapper">
                <input
                  id="register-email"
                  v-model="registerForm.email"
                  type="email"
                  placeholder="请输入邮箱，用于接收验证码"
                  :disabled="authLoading"
                  required
                  autocomplete="email"
                />
                <span class="input-icon">@</span>
              </div>
              <p v-if="mode === 'register' && registerForm.email" class="form-hint">
                {{ isEmailValid(registerForm.email) ? '格式正确' : '邮箱格式不正确' }}
              </p>
            </div>

            <div class="form-group">
              <label for="register-code">
                <span class="icon">🔑</span>
                <span>邮箱验证码 *</span>
              </label>
              <div class="input-wrapper has-code">
                <input
                  id="register-code"
                  v-model.trim="registerForm.code"
                  type="text"
                  inputmode="numeric"
                  placeholder="请输入邮件中的验证码"
                  :disabled="authLoading"
                  required
                  autocomplete="one-time-code"
                  maxlength="8"
                />
                <button
                  type="button"
                  class="code-btn"
                  :disabled="authLoading || code.register.sending || code.register.countdown > 0"
                  @click="handleSendCode('register')"
                >
                  {{ code.register.countdown > 0 ? `${code.register.countdown}s 后重发` : (code.register.sending ? '发送中…' : '获取验证码') }}
                </button>
              </div>
              <p v-if="code.register.devCode" class="form-hint">开发模式验证码：{{ code.register.devCode }}</p>
              <p v-else-if="code.register.sent" class="form-hint">验证码已发送，请查收邮箱</p>
            </div>

            <div class="form-group">
              <label for="register-nickname">
                <span class="icon">😊</span>
                <span>昵称 *</span>
              </label>
              <div class="input-wrapper">
                <input
                  id="register-nickname"
                  v-model="registerForm.nickname"
                  type="text"
                  placeholder="请输入昵称"
                  :disabled="authLoading"
                  required
                  autocomplete="nickname"
                />
                <span class="input-icon">🌟</span>
              </div>
            </div>

            <div class="form-group">
              <label for="register-password">
                <span class="icon">🔒</span>
                <span>密码 *</span>
              </label>
              <div class="input-wrapper">
                <input
                  id="register-password"
                  v-model="registerForm.password"
                  :type="showRegisterPassword ? 'text' : 'password'"
                  placeholder="请输入密码（至少6位字符）"
                  :disabled="authLoading"
                  required
                  autocomplete="new-password"
                  minlength="6"
                />
                <button
                  type="button"
                  class="toggle-password"
                  @click="showRegisterPassword = !showRegisterPassword"
                  tabindex="-1"
                >
                  {{ showRegisterPassword ? '👁️' : '🙈' }}
                </button>
              </div>
              <p v-if="mode === 'register' && registerForm.password" class="form-hint">
                {{ registerForm.password.length < 6 ? '密码太短' : '密码强度足够' }}
              </p>
            </div>

            <div class="form-group">
              <label for="register-confirm">
                <span class="icon">✅</span>
                <span>确认密码 *</span>
              </label>
              <div class="input-wrapper">
                <input
                  id="register-confirm"
                  v-model="registerForm.confirmPassword"
                  :type="showRegisterPassword ? 'text' : 'password'"
                  placeholder="请再次输入密码"
                  :disabled="authLoading"
                  required
                  autocomplete="new-password"
                  minlength="6"
                />
                <span class="input-icon">🔄</span>
              </div>
              <p
                v-if="registerForm.password && registerForm.confirmPassword"
                class="form-hint"
                :class="{ error: registerForm.password !== registerForm.confirmPassword }"
              >
                {{ registerForm.password === registerForm.confirmPassword ? '密码匹配' : '两次输入密码不一致' }}
              </p>
            </div>

            <div class="form-actions">
              <button 
                type="submit" 
                class="auth-btn primary"
                :disabled="authLoading || !isRegisterFormValid"
                :aria-busy="authLoading"
              >
                <span v-if="!authLoading">注册并登录</span>
                <span v-else>注册中...</span>
              </button>
            </div>

            <p class="form-switch">
              已有账号？
              <button type="button" @click="switchMode('login')" class="text-btn">
                去登录
              </button>
            </p>
          </form>

          <!-- 找回密码 -->
          <form
            v-if="mode === 'reset'"
            class="auth-form"
            @submit.prevent="handleResetPassword"
            novalidate
          >
            <div class="form-group">
              <label for="reset-email">
                <span class="icon">📧</span>
                <span>注册邮箱 *</span>
              </label>
              <div class="input-wrapper">
                <input
                  id="reset-email"
                  v-model="resetForm.email"
                  type="email"
                  placeholder="请输入注册邮箱"
                  :disabled="authLoading"
                  required
                  autocomplete="email"
                />
                <span class="input-icon">@</span>
              </div>
              <p v-if="resetForm.email" class="form-hint">
                {{ isEmailValid(resetForm.email) ? '格式正确' : '邮箱格式不正确' }}
              </p>
            </div>

            <div class="form-group">
              <label for="reset-code">
                <span class="icon">🔑</span>
                <span>邮箱验证码 *</span>
              </label>
              <div class="input-wrapper has-code">
                <input
                  id="reset-code"
                  v-model.trim="resetForm.code"
                  type="text"
                  inputmode="numeric"
                  placeholder="请输入邮件中的验证码"
                  :disabled="authLoading"
                  required
                  autocomplete="one-time-code"
                  maxlength="8"
                />
                <button
                  type="button"
                  class="code-btn"
                  :disabled="authLoading || code.reset.sending || code.reset.countdown > 0"
                  @click="handleSendCode('reset')"
                >
                  {{ code.reset.countdown > 0 ? `${code.reset.countdown}s 后重发` : (code.reset.sending ? '发送中…' : '获取验证码') }}
                </button>
              </div>
              <p v-if="code.reset.devCode" class="form-hint">开发模式验证码：{{ code.reset.devCode }}</p>
              <p v-else-if="code.reset.sent" class="form-hint">验证码已发送，请查收邮箱</p>
            </div>

            <div class="form-group">
              <label for="reset-password">
                <span class="icon">🔒</span>
                <span>新密码 *</span>
              </label>
              <div class="input-wrapper">
                <input
                  id="reset-password"
                  v-model="resetForm.password"
                  :type="showResetPassword ? 'text' : 'password'"
                  placeholder="请输入新密码（至少6位字符）"
                  :disabled="authLoading"
                  required
                  autocomplete="new-password"
                  minlength="6"
                />
                <button
                  type="button"
                  class="toggle-password"
                  @click="showResetPassword = !showResetPassword"
                  tabindex="-1"
                >
                  {{ showResetPassword ? '👁️' : '🙈' }}
                </button>
              </div>
              <p v-if="resetForm.password" class="form-hint">
                {{ resetForm.password.length < 6 ? '密码太短' : '密码强度足够' }}
              </p>
            </div>

            <div class="form-group">
              <label for="reset-confirm">
                <span class="icon">✅</span>
                <span>确认新密码 *</span>
              </label>
              <div class="input-wrapper">
                <input
                  id="reset-confirm"
                  v-model="resetForm.confirmPassword"
                  :type="showResetPassword ? 'text' : 'password'"
                  placeholder="请再次输入新密码"
                  :disabled="authLoading"
                  required
                  autocomplete="new-password"
                  minlength="6"
                />
                <span class="input-icon">🔄</span>
              </div>
              <p
                v-if="resetForm.password && resetForm.confirmPassword"
                class="form-hint"
                :class="{ error: resetForm.password !== resetForm.confirmPassword }"
              >
                {{ resetForm.password === resetForm.confirmPassword ? '密码匹配' : '两次输入密码不一致' }}
              </p>
            </div>

            <div class="form-actions">
              <button 
                type="submit" 
                class="auth-btn primary"
                :disabled="authLoading || !isResetFormValid"
                :aria-busy="authLoading"
              >
                <span v-if="!authLoading">重置密码并登录</span>
                <span v-else>重置中...</span>
              </button>
            </div>

            <p class="form-switch">
              想起密码了？
              <button type="button" @click="switchMode('login')" class="text-btn">
                返回登录
              </button>
            </p>
          </form>
        </div>

        <!-- 错误提示 -->
        <Transition name="fade">
          <div v-if="error" class="error-message" role="alert">
            <span class="error-icon">❌</span>
            <span>{{ error }}</span>
          </div>
        </Transition>
      </div>

      <!-- 底部信息 -->
      <div class="auth-footer">
        <p>© 2024 NosChat - AI 智能聊天助手</p>
        <p class="disclaimer">提示：此为演示版本，数据仅保存在浏览器本地存储中</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onBeforeUnmount } from 'vue'
import { useAuth } from '../stores/userStore.js'

const {
  login: loginApi,
  loginWithCode: loginWithCodeApi,
  register: registerApi,
  resetPassword: resetPasswordApi,
  sendCode: sendCodeApi,
  authLoading
} = useAuth()

const emit = defineEmits(['success'])

// 主模式：login（含密码/验证码两种方式）| register | reset（找回密码）
const mode = ref('login')
// 登录方式：password 密码登录 | code 验证码登录
const loginMode = ref('password')

// 登录表单（验证码登录不填写昵称，未注册时由后端用邮箱作为昵称）
const loginForm = reactive({
  email: '',
  password: '',
  code: ''
})

// 注册表单
const registerForm = reactive({
  email: '',
  code: '',
  nickname: '',
  password: '',
  confirmPassword: ''
})

// 找回密码表单
const resetForm = reactive({
  email: '',
  code: '',
  password: '',
  confirmPassword: ''
})

// 显示密码
const showPassword = ref(false)
const showRegisterPassword = ref(false)
const showResetPassword = ref(false)

// 错误信息
const error = ref('')

/** 验证码状态按用途独立维护（各自的重发倒计时互不影响） */
function createCodeState() {
  return reactive({ sending: false, countdown: 0, devCode: '', sent: false, timer: null })
}

const code = {
  register: createCodeState(),
  login: createCodeState(),
  reset: createCodeState()
}

const purposeForm = {
  register: () => registerForm,
  login: () => loginForm,
  reset: () => resetForm
}

function isEmailValid(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((value || '').trim())
}

function startCountdown(purpose, seconds) {
  const state = code[purpose]
  if (state.timer) clearInterval(state.timer)
  state.countdown = Math.max(1, Number(seconds) || 60)
  state.timer = setInterval(() => {
    state.countdown -= 1
    if (state.countdown <= 0) {
      clearInterval(state.timer)
      state.timer = null
      state.countdown = 0
    }
  }, 1000)
}

/** 切换主模式（登录 / 注册 / 找回密码） */
function switchMode(next, options = {}) {
  mode.value = next
  error.value = ''
  if (next === 'reset' && options.email) resetForm.email = options.email
}

// ---------------- 表单校验 ----------------

// 登录（密码 / 验证码）
const canSubmitLogin = computed(() => {
  const form = loginForm
  if (!isEmailValid(form.email)) return false
  if (loginMode.value === 'password') return Boolean(form.password)
  return Boolean(form.code) && form.code.length >= 4
})

// 注册表单验证
const isRegisterFormValid = computed(() => {
  const form = registerForm
  return (
    isEmailValid(form.email) &&
    form.code &&
    form.code.length >= 4 &&
    form.nickname &&
    form.password &&
    form.password.length >= 6 &&
    form.confirmPassword &&
    form.password === form.confirmPassword
  )
})

// 找回密码表单验证
const isResetFormValid = computed(() => {
  const form = resetForm
  return (
    isEmailValid(form.email) &&
    form.code &&
    form.code.length >= 4 &&
    form.password &&
    form.password.length >= 6 &&
    form.confirmPassword &&
    form.password === form.confirmPassword
  )
})

// ---------------- 交互 ----------------

/** 发送邮箱验证码：register 注册 / login 验证码登录 / reset 找回密码 */
async function handleSendCode(purpose) {
  error.value = ''
  const form = purposeForm[purpose]()
  const state = code[purpose]

  if (!isEmailValid(form.email)) {
    error.value = '请输入正确的邮箱地址'
    return
  }

  state.sending = true
  try {
    const result = await sendCodeApi({ email: form.email.trim(), purpose })
    state.devCode = result?.devCode || ''
    state.sent = !result?.devCode
    // 开发模式（未配置 SMTP）下直接回填，便于自测
    if (result?.devCode) form.code = result.devCode
    startCountdown(purpose, result?.resendAfter || 60)
  } catch (err) {
    console.error('Send code failed:', err)
    state.sent = false
    error.value = err.message || '验证码发送失败，请稍后重试'
  } finally {
    state.sending = false
  }
}

// 密码登录
async function handleLogin() {
  error.value = ''
  try {
    await loginApi({
      email: loginForm.email.trim(),
      password: loginForm.password
    })
    emit('success')
  } catch (err) {
    console.error('Login failed:', err)
    error.value = err.message || '登录失败，请稍后重试'
  }
}

// 验证码登录：邮箱未注册时自动注册（昵称使用邮箱）
async function handleCodeLogin() {
  error.value = ''
  try {
    await loginWithCodeApi({
      email: loginForm.email.trim(),
      code: loginForm.code.trim(),
      nickname: ''
    })
    emit('success')
  } catch (err) {
    console.error('Code login failed:', err)
    error.value = err.message || '验证码登录失败，请稍后重试'
  }
}

// 登录表单提交：按当前登录方式分发
function handleLoginSubmit() {
  return loginMode.value === 'code' ? handleCodeLogin() : handleLogin()
}

// 注册
async function handleRegister() {
  error.value = ''
  try {
    if (registerForm.password !== registerForm.confirmPassword) {
      throw new Error('两次输入的密码不一致')
    }
    await registerApi({
      email: registerForm.email.trim(),
      code: registerForm.code.trim(),
      nickname: registerForm.nickname.trim(),
      password: registerForm.password
    })
    emit('success')
  } catch (err) {
    console.error('Registration failed:', err)
    error.value = err.message || '注册失败，请稍后重试'
  }
}

// 找回密码：重置成功后自动登录
async function handleResetPassword() {
  error.value = ''
  try {
    if (resetForm.password !== resetForm.confirmPassword) {
      throw new Error('两次输入的密码不一致')
    }
    await resetPasswordApi({
      email: resetForm.email.trim(),
      code: resetForm.code.trim(),
      password: resetForm.password
    })
    emit('success')
  } catch (err) {
    console.error('Reset password failed:', err)
    error.value = err.message || '密码重置失败，请稍后重试'
  }
}

onBeforeUnmount(() => {
  Object.values(code).forEach(state => {
    if (state.timer) {
      clearInterval(state.timer)
      state.timer = null
    }
  })
})
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  min-height: 100dvh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: grid;
  place-items: center;
  padding: clamp(0.5rem, 2.5vw, 2rem);
  position: relative;
  overflow: hidden;
}

.auth-background {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}

.bg-blob {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
}

.bg-blob-1 {
  width: 40vmax;
  height: 40vmax;
  top: -20vmax;
  right: -15vmax;
}

.bg-blob-2 {
  width: 30vmax;
  height: 30vmax;
  bottom: -10vmax;
  left: -15vmax;
}

.bg-blob-3 {
  width: 20vmax;
  height: 20vmax;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 1.5rem;
  box-shadow: 0 30px 80px rgba(30, 41, 59, 0.35);
  padding: clamp(1.5rem, 4vw, 2.5rem);
  position: relative;
  z-index: 1;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.auth-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 2rem;
}

.logo-icon {
  font-size: 3rem;
  animation: pulse 2s infinite;
  margin-bottom: 0.5rem;
}

.auth-logo h1 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 0.25rem 0;
}

.tagline {
  color: #64748b;
  font-size: 0.9rem;
}

.auth-content {
  margin-bottom: 2rem;
}

.auth-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  background: #f1f5f9;
  border-radius: 999px;
  padding: 0.25rem;
}

.auth-tab {
  flex: 1;
  padding: 0.75rem 1rem;
  border: none;
  background: none;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.auth-tab:hover {
  color: #475569;
}

.auth-tab.active {
  background: #fff;
  color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

/* 登录方式切换：密码登录 / 验证码登录 */
.auth-subtabs {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 1.25rem;
}

.subtab {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 0.6rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.subtab:hover {
  color: #475569;
  border-color: #cbd5e1;
}

.subtab.on {
  color: #4f46e5;
  border-color: #667eea80;
  background: linear-gradient(135deg, #667eea10, #764ba210);
}

.auth-forms {
  position: relative;
  min-height: 300px;
}

.auth-form {
  animation: fadeIn 0.3s ease;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.label .icon {
  font-size: 1rem;
}

.input-wrapper {
  position: relative;
}

.input-wrapper input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.7rem;
  font-size: 0.9rem;
  color: #1e293b;
  background: #fff;
  transition: all 0.2s ease;
}

.input-wrapper input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

.input-wrapper input:disabled {
  background: #f8fafc;
  cursor: not-allowed;
  opacity: 0.7;
}

.input-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 0.9rem;
}

.toggle-password {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0.25rem;
}

.toggle-password:hover {
  color: #64748b;
}

/* 邮箱验证码：输入框右侧按钮，沿用现有输入框配色与圆角风格 */
.input-wrapper.has-code input {
  padding-right: 6.75rem;
}

.code-btn {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #667eea;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.25rem;
  white-space: nowrap;
}

.code-btn:hover:not(:disabled) {
  color: #4f46e5;
}

.code-btn:disabled {
  color: #94a3b8;
  cursor: not-allowed;
}

.form-hint {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.25rem;
  margin-left: 0.25rem;
}

.form-hint.error {
  color: #ef4444;
}

/* 提示行内带操作（如「忘记密码？」） */
.form-hint.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.form-actions {
  margin: 2rem 0 1.5rem;
}

.auth-btn {
  width: 100%;
  padding: 0.875rem 1.5rem;
  border: none;
  border-radius: 0.7rem;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
}

.auth-btn.primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.auth-btn.primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.5);
}

.auth-btn.primary:active:not(:disabled) {
  transform: translateY(0);
}

.auth-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-btn[aria-busy="true"] {
  opacity: 0.8;
  cursor: wait;
}

.form-switch {
  text-align: center;
  font-size: 0.85rem;
  color: #64748b;
}

.text-btn {
  background: none;
  border: none;
  color: #667eea;
  font: inherit;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  text-underline-offset: 0.2em;
}

.text-btn:hover {
  color: #4f46e5;
}

.error-message {
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.7rem;
  padding: 0.75rem 1rem;
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #dc2626;
}

.error-icon {
  flex: 0 0 auto;
  font-size: 1rem;
}

.auth-footer {
  text-align: center;
  border-top: 1px solid #e2e8f0;
  padding-top: 1.5rem;
  margin-top: 2rem;
}

.auth-footer p {
  font-size: 0.75rem;
  color: #64748b;
  margin: 0.25rem 0;
}

.disclaimer {
  font-size: 0.7rem;
  color: #94a3b8;
}

/* 动画 */
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 响应式调整 */
@media (max-width: 480px) {
  .auth-card {
    padding: clamp(1.25rem, 3vw, 1.5rem);
  }
  
  .auth-tab {
    padding: 0.6rem 0.75rem;
    font-size: 0.85rem;
  }
  
  .logo-icon {
    font-size: 2.5rem;
  }
  
  .auth-logo h1 {
    font-size: 1.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .logo-icon { animation: none; }
  .auth-form { animation: none; }
  .fade-enter-active,
  .fade-leave-active { transition: none; }
}
</style>