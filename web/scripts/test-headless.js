// 无头测试：验证关键功能点是否存在
import { relRelease, getModel, mockReply, MODEL_LIST, MOCK_MESSAGES } from '../src/data/models.js'

console.log('🧪 执行功能验证：')
console.log(`1. 模型数量 = ${MODEL_LIST.length}`)
console.log(`2. 所有模型都有 released 字段: ${MODEL_LIST.every(m => /^\d{4}-\d{2}-\d{2}$/.test(m.released))}`)
console.log(`3. 有推理能力的模型: ${MODEL_LIST.filter(m => m.reasoning).map(m => m.name).join(', ')}`)
console.log(`4. 日期相对 time: '2024-05-13' → '${relRelease('2024-05-13')}'`)
console.log(`5. 模拟消息条数: ${Object.keys(MOCK_MESSAGES).reduce((sum, k) => sum + MOCK_MESSAGES[k].length, 0)}`)

const r1 = mockReply('deepseek-r1', '用户问题')
console.log(`6. 推理模型回复包含 thinking: ${r1.thinking.length > 0 ? '✅' : '❌'} (${r1.thinking.length} 字符)`)

const v3 = mockReply('deepseek-v3', '随便聊聊')
console.log(`7. 非推理模型 thinking 为空: ${!v3.thinking ? '✅' : '❌'}`)

process.exit(0)