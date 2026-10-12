import { reactive, computed } from 'vue'

// 模拟用户存储
const KEY_USER = 'noschat.user'
const KEY_TOKEN = 'noschat.token'

// 用户状态管理
const state = reactive({
  user: null,
  token: null,
  isLoading: false
})

// 从本地存储初始化
try {
  const savedUser = localStorage.getItem(KEY_USER)
  const savedToken = localStorage.getItem(KEY_TOKEN)
  
  if (savedUser && savedToken) {
    state.user = JSON.parse(savedUser)
    state.token = savedToken
  }
} catch (e) {
  console.warn('Failed to load user from localStorage', e)
}

export function useAuth() {
  // 计算属性
  const isAuthenticated = computed(() => !!state.user && !!state.token)
  const currentUser = computed(() => state.user)
  const authToken = computed(() => state.token)
  const authLoading = computed(() => state.isLoading)

  // 注册函数
  async function register({ username, nickname, password }) {
    if (state.isLoading) return null
    
    state.isLoading = true
    try {
      // 模拟API调用延迟
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // 简单验证
      if (!username || !nickname || !password) {
        throw new Error('请填写所有必填字段')
      }
      
      if (username.length < 3) {
        throw new Error('用户名至少需要3个字符')
      }
      
      if (password.length < 6) {
        throw new Error('密码至少需要6个字符')
      }
      
      // 模拟检查用户名是否已存在
      const existingUsersStr = localStorage.getItem('noschat.users') || '[]'
      const existingUsers = JSON.parse(existingUsersStr)
      const userExists = existingUsers.some(u => u.username === username)
      
      if (userExists) {
        throw new Error('用户名已被使用')
      }
      
      // 创建新用户
      const newUser = {
        id: Date.now().toString(),
        username,
        nickname,
        createdAt: new Date().toISOString()
      }
      
      // 保存到用户列表
      existingUsers.push(newUser)
      localStorage.setItem('noschat.users', JSON.stringify(existingUsers))
      
      // 自动登录
      const token = `token_${Date.now()}_${Math.random().toString(36).substr(2)}`
      
      state.user = newUser
      state.token = token
      
      // 保存到本地存储
      localStorage.setItem(KEY_USER, JSON.stringify(newUser))
      localStorage.setItem(KEY_TOKEN, token)
      
      return { user: newUser, token }
    } catch (error) {
      throw error
    } finally {
      state.isLoading = false
    }
  }

  // 登录函数
  async function login({ username, password }) {
    if (state.isLoading) return null
    
    state.isLoading = true
    try {
      // 模拟API调用延迟
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // 简单验证
      if (!username || !password) {
        throw new Error('请填写用户名和密码')
      }
      
      // 模拟验证逻辑
      const usersStr = localStorage.getItem('noschat.users') || '[]'
      const users = JSON.parse(usersStr)
      const user = users.find(u => u.username === username)
      
      if (!user) {
        throw new Error('用户名或密码错误')
      }
      
      // 模拟密码验证 (在实际应用中应该使用bcrypt等)
      const isValid = password === '123456' // 简单演示，统一使用默认密码
      if (!isValid) {
        throw new Error('用户名或密码错误')
      }
      
      const token = `token_${Date.now()}_${Math.random().toString(36).substr(2)}`
      
      state.user = user
      state.token = token
      
      // 保存到本地存储
      localStorage.setItem(KEY_USER, JSON.stringify(user))
      localStorage.setItem(KEY_TOKEN, token)
      
      return { user, token }
    } catch (error) {
      throw error
    } finally {
      state.isLoading = false
    }
  }

  // 退出登录
  function logout() {
    state.user = null
    state.token = null
    localStorage.removeItem(KEY_USER)
    localStorage.removeItem(KEY_TOKEN)
  }

  // 更新用户信息
  function updateUser(updates) {
    if (!state.user) return
    
    const updatedUser = { ...state.user, ...updates }
    const usersStr = localStorage.getItem('noschat.users') || '[]'
    const users = JSON.parse(usersStr)
    const userIndex = users.findIndex(u => u.id === state.user.id)
    
    if (userIndex !== -1) {
      users[userIndex] = updatedUser
      localStorage.setItem('noschat.users', JSON.stringify(users))
    }
    
    state.user = updatedUser
    localStorage.setItem(KEY_USER, JSON.stringify(updatedUser))
    
    return updatedUser
  }

  return {
    // 状态
    isAuthenticated,
    currentUser,
    authToken,
    authLoading,
    
    // 方法
    register,
    login,
    logout,
    updateUser
  }
}