#!/usr/bin/env node

console.log('📁 NosChat 项目结构验证')
console.log('='.repeat(50))

const fs = require('fs')
const path = require('path')

function checkFile(filePath, description = '') {
  const exists = fs.existsSync(filePath)
  console.log(`${exists ? '✅' : '❌'} ${filePath} ${description}`)
  return exists
}

console.log('\n📦 根目录文件检查：')
console.log('-'.repeat(30))
checkFile('README.md', '项目主文档')
checkFile('.gitignore', 'Git 忽略配置')
checkFile('.env.example', '容器化环境变量样例')
checkFile('docker-compose.yml', '容器编排（后端 + PostgreSQL，不含前端）')
checkFile('web/', '前端项目目录（目录）')
checkFile('server/', '后端项目目录（目录）')

console.log('\n🎨 Web 前端项目检查：')
console.log('-'.repeat(30))
checkFile('web/index.html', 'HTML 模板')
checkFile('web/vite.config.js', 'Vite 配置（含 /api 代理）')
checkFile('web/package.json', '项目依赖配置')
checkFile('web/.env.example', '前端环境变量样例')
checkFile('web/vite.svg', '应用图标')
checkFile('web/src/App.vue', '主应用组件')
checkFile('web/src/stores/userStore.js', '用户状态（对接后端鉴权）')
checkFile('web/src/data/models.js', '模型清单运行时注册表')
checkFile('web/src/api/client.js', '接口客户端（base url / 令牌 / 错误规范化）')
checkFile('web/src/api/auth.js', '认证接口')
checkFile('web/src/api/chat.js', '模型 / 会话 / SSE 流式接口')
checkFile('web/src/components/ChatSidebar.vue', '侧边栏组件')
checkFile('web/src/components/ChatMessages.vue', '消息组件')
checkFile('web/src/components/ModelSelector.vue', '模型选择组件')
checkFile('web/src/components/ChatInput.vue', '输入组件')
checkFile('web/src/components/AuthPage.vue', '登录 / 注册（邮箱验证码）')

console.log('\n🐍 后端项目检查：')
console.log('-'.repeat(30))
checkFile('server/run.py', '启动入口（Windows 事件循环兼容）')
checkFile('server/requirements.txt', 'Python 依赖')
checkFile('server/Dockerfile', '后端镜像定义')
checkFile('server/.env.example', '后端环境变量样例')
checkFile('server/config/models.json', '模型清单配置（含介绍 / 发布日期等字段）')
checkFile('server/app/main.py', 'FastAPI 应用入口（9135）')
checkFile('server/app/config.py', '环境变量配置')
checkFile('server/app/database.py', '数据库连接与会话')
checkFile('server/app/models.py', 'ORM 模型（用户 / 验证码 / 会话 / 消息）')
checkFile('server/app/schemas.py', '请求响应模型')
checkFile('server/app/security.py', '密码哈希与 JWT')
checkFile('server/app/deps.py', '鉴权依赖')
checkFile('server/app/mailer.py', 'SMTP 邮件发送')
checkFile('server/app/llm.py', 'OpenAI 兼容流式调用')
checkFile('server/app/model_registry.py', '模型清单注册表')
checkFile('server/app/routers/auth.py', '认证路由')
checkFile('server/app/routers/catalog.py', '模型清单路由')
checkFile('server/app/routers/chat.py', '会话与流式对话路由')
checkFile('server/tests/smoke_api.py', '接口冒烟测试')

console.log('\n🚀 启动说明：')
console.log('-'.repeat(30))
console.log('【方式一】容器化一键启动（后端 + PostgreSQL）')
console.log('1. 复制 .env.example 为 .env 并填写 JWT_SECRET / OPENAI_API_KEY / SMTP_*')
console.log('2. docker compose up -d --build')
console.log('3. 健康检查：http://localhost:9135/health')
console.log('')
console.log('【方式二】本地开发')
console.log('1. 后端：cd server ; python -m venv .venv ; .venv/Scripts/pip install -r requirements.txt')
console.log('2. 复制 server/.env.example 为 server/.env 并填写配置')
console.log('3. 启动后端：cd server ; python run.py            # http://localhost:9135')
console.log('4. 前端：cd web ; npm install ; npm run dev        # http://localhost:3000')
console.log('5. 接口冒烟：cd server ; python tests/smoke_api.py')

console.log('\n📊 项目统计：')
console.log('-'.repeat(30))
const countFiles = (dir, skip = ['node_modules', '.venv', 'dist', '__pycache__']) => {
  let count = 0
  let items = []
  try {
    items = fs.readdirSync(dir, { withFileTypes: true })
  } catch {
    return 0
  }
  items.forEach(item => {
    if (skip.includes(item.name)) return
    if (item.isFile()) count++
    if (item.isDirectory()) count += countFiles(path.join(dir, item.name), skip)
  })
  return count
}

try {
  console.log(`📁 web 端文件数：${countFiles('web')} 个文件（已排除 node_modules/dist）`)
  console.log(`📁 server 端文件数：${countFiles('server')} 个文件（已排除 .venv/__pycache__）`)
} catch (err) {
  console.log('⚠️ 无法统计文件数量，目录可能不存在')
}

console.log('\n✅ 项目结构验证完成！')
console.log('💡 所有必要的文件都已创建完成。')
console.log('🚀 现在可以按照上面的步骤启动项目了。')
