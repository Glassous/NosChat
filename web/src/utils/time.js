/** 时间展示工具：把后端返回的 ISO 时间转成界面既有格式。 */

const MINUTE = 60 * 1000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

function pad(value) {
  return String(value).padStart(2, '0')
}

function toDate(input) {
  if (!input) return null
  const date = input instanceof Date ? input : new Date(input)
  return Number.isNaN(date.getTime()) ? null : date
}

/** 消息时间：HH:MM */
export function fmtClock(input) {
  const date = toDate(input)
  if (!date) return ''
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** 当前时间：HH:MM（乐观渲染用） */
export function nowClock() {
  return fmtClock(new Date())
}

/** 会话时间：刚刚 / N 分钟前 / HH:MM / 昨天 HH:MM / N 天前 / MM-DD */
export function fmtRelative(input) {
  const date = toDate(input)
  if (!date) return ''

  const diff = Date.now() - date.getTime()
  if (diff < MINUTE) return '刚刚'
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)} 分钟前`

  const clock = fmtClock(date)
  const startOfToday = new Date()
  startOfToday.setHours(0, 0, 0, 0)

  if (date.getTime() >= startOfToday.getTime()) return clock
  if (date.getTime() >= startOfToday.getTime() - DAY) return `昨天 ${clock}`
  if (diff < 7 * DAY) return `${Math.floor(diff / DAY)} 天前`
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
