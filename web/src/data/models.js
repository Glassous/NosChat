/**
 * 模型清单运行时注册表。
 *
 * 模型数据不再内置：应用启动后调用后端 GET /api/models 拉取（后端由
 * server/config/models.json 声明），通过 setModels() 写入本注册表。
 * 组件继续使用 getModel(id) / relRelease() / sortModels() 等方法（签名保持不变）。
 */

import { reactive } from 'vue'

/** 可用模型列表（由后端清单填充，保持响应式以便界面自动更新） */
export const MODEL_LIST = reactive([])

/** 清单未就绪或 id 缺失时的兜底模型，避免组件读取字段时报错 */
export const FALLBACK_MODEL = Object.freeze({
  id: '',
  model: '',
  name: '未知模型',
  provider: '—',
  icon: '🤖',
  badge: '',
  color: '#667eea',
  desc: '正在获取模型信息…',
  tags: [],
  context: '—',
  released: '',
  speed: 3,
  intelligence: 3,
  temp: 0.7,
  reasoning: false,
  latency: [600, 1400]
})

function toTags(value) {
  if (Array.isArray(value)) return value.filter(item => String(item ?? '').trim())
  if (typeof value === 'string' && value.trim()) {
    return value.split(',').map(item => item.trim()).filter(Boolean)
  }
  return []
}

function toLatency(value) {
  if (Array.isArray(value) && value.length >= 2) {
    const low = Number(value[0])
    const high = Number(value[1])
    if (Number.isFinite(low) && Number.isFinite(high)) {
      return [Math.max(0, low), Math.max(low, high)]
    }
  }
  return [...FALLBACK_MODEL.latency]
}

/** 规范化后端返回的模型对象（字段缺失时使用兜底值） */
export function normalizeModel(raw) {
  const source = raw && typeof raw === 'object' ? raw : {}
  const id = String(source.id ?? source.model ?? '')
  return {
    id,
    model: String(source.model ?? id),
    name: String(source.name || id || FALLBACK_MODEL.name),
    provider: String(source.provider ?? ''),
    icon: String(source.icon || FALLBACK_MODEL.icon),
    badge: String(source.badge ?? ''),
    color: String(source.color || FALLBACK_MODEL.color),
    desc: String(source.desc ?? ''),
    tags: toTags(source.tags),
    context: String(source.context || FALLBACK_MODEL.context),
    released: String(source.released ?? ''),
    speed: Number(source.speed) || FALLBACK_MODEL.speed,
    intelligence: Number(source.intelligence) || FALLBACK_MODEL.intelligence,
    temp: Number.isFinite(Number(source.temp)) ? Number(source.temp) : FALLBACK_MODEL.temp,
    reasoning: Boolean(source.reasoning),
    latency: toLatency(source.latency)
  }
}

/** 写入模型清单（保留原数组引用，保证模板绑定无需改动） */
export function setModels(list) {
  const normalized = (Array.isArray(list) ? list : []).map(normalizeModel).filter(item => item.id)
  MODEL_LIST.splice(0, MODEL_LIST.length, ...normalized)
  return MODEL_LIST
}

/** 按 id 取模型，找不到则回退到首个模型或兜底对象 */
export function getModel(id) {
  return MODEL_LIST.find(item => item.id === id) || MODEL_LIST[0] || FALLBACK_MODEL
}

/** 发布日期 → 相对时间（用于列表右侧的轻量提示） */
export function relRelease(iso) {
  const then = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(then.getTime())) return ''
  const days = Math.max(0, Math.round((Date.now() - then.getTime()) / 86400000))
  if (days < 7) return days <= 0 ? '本周发布' : `${days} 天前发布`
  if (days < 31) return `${Math.floor(days / 7)} 周前发布`
  if (days < 365) return `${Math.floor(days / 30)} 个月前发布`
  const years = (days / 365).toFixed(1)
  return `${years} 年前发布`
}

/** 发布日期 → 可比较时间戳；缺失或非法排到最后 */
export function releaseTs(model) {
  const ts = Date.parse(`${(model && model.released) || ''}T00:00:00`)
  return Number.isNaN(ts) ? -Infinity : ts
}

/** 模型列表排序：default 保持原顺序，newest/oldest 按发布日期 */
export function sortModels(list, mode = 'default') {
  if (mode !== 'newest' && mode !== 'oldest') return list
  return [...list].sort((a, b) =>
    mode === 'newest' ? releaseTs(b) - releaseTs(a) : releaseTs(a) - releaseTs(b)
  )
}
