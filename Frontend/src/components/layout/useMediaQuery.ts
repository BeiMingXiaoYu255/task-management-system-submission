/**
 * 媒体查询 Hook：监听视口宽度变化，用于响应式布局（≤900px 侧边栏抽屉化）。
 */

import { useEffect, useState } from 'react'

/** 判断当前是否支持 matchMedia（jsdom 等环境可能缺失）。 */
function supportsMediaQuery(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
}

/** 订阅媒体查询结果。 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (!supportsMediaQuery()) {
      return false
    }
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    if (!supportsMediaQuery()) {
      return
    }
    const mediaQueryList = window.matchMedia(query)
    /** 媒体查询结果变化时同步状态。 */
    const handleChange = (event: MediaQueryListEvent): void => {
      setMatches(event.matches)
    }
    setMatches(mediaQueryList.matches)
    mediaQueryList.addEventListener('change', handleChange)
    return () => {
      mediaQueryList.removeEventListener('change', handleChange)
    }
  }, [query])

  return matches
}
