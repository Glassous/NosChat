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
            :class="['auth-tab', { active: mode === 'login' }]"
            @click="mode = 'login'"
          >
            登录
          </button>
          <button
            :class="['auth-tab', { active: mode === 'register' }]"
            @click="mode = 'register'"
          >
            注册
          </button>
        </div>

        <div class="auth-forms">
          <!-- 登录表单 -->
          <form
            v-if="mode === 'login'"
            class="auth-form"
            @submit.prevent="handleLogin"
            novalidate
          >
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
                  placeholder="请输入注册邮箱"
                  :disabled="authLoading"
                  required
                  autocomplete="email"
                />
                <span class="input-icon">@</span>
              </div>
            </div>

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
              <p class="form-hint">
                使用注册邮箱与密码登录
              </p>
            </div>

            <div class="form-actions">
              <button 
                type="submit" 
                class="auth-btn primary"
                :disabled="authLoading || !loginForm.email || !loginForm.password"
                :aria-busy="authLoading"
              >
                <span v-if="!authLoading">登录</span>
                <span v-else>登录中...</span>
              </button>
            </div>

            <p class="form-switch">
              还没有账号？
              <button type="button" @click="mode = 'register'" class="text-btn">
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
                  :disabled="authLoading || codeSending || countdown > 0"
                  @click="handleSendCode"
                >
                  {{ countdown > 0 ? `${countdown}s 后重发` : (codeSending ? '发送中…' : '获取验证码') }}
                </button>
              </div>
              <p v-if="devCode" class="form-hint">开发模式验证码：{{ devCode }}</p>
              <p v-else-if="codeSent" class="form-hint">验证码已发送，请查收邮箱</p>
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
              <button type="button" @click="mode = 'login'" class="text-btn">
                去登录
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
  register: registerApi,
  sendCode: sendCodeApi,
  authLoading
} = useAuth()

const emit = defineEmits(['success'])

// 模式切换：login 或 register
const mode = ref('login')

// 登录表单
const loginForm = reactive({
  email: '',
  password: ''
})

// 注册表单
const registerForm = reactive({
  email: '',
  code: '',
  nickname: '',
  password: '',
  confirmPassword: ''
})

// 显示密码
const showPassword = ref(false)
const showRegisterPassword = ref(false)

// 错误信息
const error = ref('')

// 验证码发送状态
const codeSending = ref(false)
const countdown = ref(0)
const devCode = ref('')
const codeSent = ref(false)
let countdownTimer = null

function isEmailValid(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((value || '').trim())
}

function startCountdown(seconds) {
  if (countdownTimer) clearInterval(countdownTimer)
  countdown.value = Math.max(1, Number(seconds) || 60)
  countdownTimer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearInterval(countdownTimer)
      countdownTimer = null
      countdown.value = 0
    }
  }, 1000)
}

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

// 发送邮箱验证码
async function handleSendCode() {
  error.value = ''

  if (!isEmailValid(registerForm.email)) {
    error.value = '请输入正确的邮箱地址'
    return
  }

  codeSending.value = true
  try {
    const result = await sendCodeApi({ email: registerForm.email.trim() })
    devCode.value = result?.devCode || ''
    codeSent.value = !result?.devCode
    // 开发模式（未配置 SMTP）下直接回填，便于自测
    if (result?.devCode) registerForm.code = result.devCode
    startCountdown(result?.resendAfter || 60)
  } catch (err) {
    console.error('Send code failed:', err)
    error.value = err.message || '验证码发送失败，请稍后重试'
  } finally {
    codeSending.value = false
  }
}

// 处理登录
async function handleLogin() {
  error.value = ''
  
  try {
    await loginApi({
      email: loginForm.email.trim(),
      password: loginForm.password
    })
    
    // 登录成功后发出事件
    emit('success')
    
  } catch (err) {
    console.error('Login failed:', err)
    error.value = err.message || '登录失败，请稍后重试'
  }
}

// 处理注册
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
    
    // 注册成功并自动登录后发出事件
    emit('success')
    
  } catch (err) {
    console.error('Registration failed:', err)
    error.value = err.message || '注册失败，请稍后重试'
  }
}

onBeforeUnmount(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
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