/**
 * 值防抖 Hook：输入框连续输入时延迟更新派生值，减少后端请求。
 *
 * 实现原理：每次 value 变化先清理上一个定时器，delay 毫秒内没有新变化才把
 * 最新值写入内部状态；组件卸载时清理定时器，避免卸载后 setState 告警。
 */

import { useEffect, useState } from 'react'

/**
 * 返回防抖后的值。
 *
 * @param value 原始值
 * @param delayMilliseconds 防抖延迟（毫秒）
 * @returns 防抖后的值
 */
export function useDebouncedValue<T>(value: T, delayMilliseconds: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timerIdentifier = window.setTimeout(() => {
      setDebouncedValue(value)
    }, delayMilliseconds)
    return () => {
      window.clearTimeout(timerIdentifier)
    }
  }, [value, delayMilliseconds])

  return debouncedValue
}
