/** 时间格式化工具：统一列表中时间的显示格式。 */

/** 把 ISO 时间字符串格式化为 YYYY-MM-DD HH:mm。 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '—'
  }
  const pad = (part: number): string => String(part).padStart(2, '0')
  return (
    date.getFullYear() +
    '-' +
    pad(date.getMonth() + 1) +
    '-' +
    pad(date.getDate()) +
    ' ' +
    pad(date.getHours()) +
    ':' +
    pad(date.getMinutes())
  )
}

/** 把 ISO 时间字符串格式化为 YYYY-MM-DD。 */
export function formatDate(value: string | null | undefined): string {
  const dateTimeText = formatDateTime(value)
  return dateTimeText === '—' ? dateTimeText : dateTimeText.slice(0, 10)
}

/** 把 ISO 时间显示为相对时间（刚刚 / N 分钟前 / N 小时前 / N 天前）。 */
export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) {
    return '—'
  }
  const seconds = Math.floor((Date.now() - timestamp) / 1000)
  if (seconds < 60) {
    return 'Just now'
  }
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    return minutes + (minutes === 1 ? ' minute ago' : ' minutes ago')
  }
  if (seconds < 86400) {
    const hours = Math.floor(seconds / 3600)
    return hours + (hours === 1 ? ' hour ago' : ' hours ago')
  }
  if (seconds < 86400 * 30) {
    const days = Math.floor(seconds / 86400)
    return days + (days === 1 ? ' day ago' : ' days ago')
  }
  return formatDate(value)
}

/** 判断截止时间是否已超过。 */
export function checkOverdue(dueAt: string | null | undefined): boolean {
  if (!dueAt) {
    return false
  }
  const timestamp = new Date(dueAt).getTime()
  return !Number.isNaN(timestamp) && timestamp < Date.now()
}

/** 生成日期差描述，例如“还剩 2 天”“已逾期 1 天”。 */
export function formatDueDescription(dueAt: string | null | undefined): string {
  if (!dueAt) {
    return 'No due date'
  }
  const timestamp = new Date(dueAt).getTime()
  if (Number.isNaN(timestamp)) {
    return 'No due date'
  }
  const differenceDays = Math.ceil((timestamp - Date.now()) / 86400000)
  if (differenceDays < 0) {
    const overdueDays = Math.abs(differenceDays)
    return 'Overdue by ' + overdueDays + (overdueDays === 1 ? ' day' : ' days')
  }
  if (differenceDays === 0) {
    return 'Due today'
  }
  return 'Due in ' + differenceDays + (differenceDays === 1 ? ' day' : ' days')
}
