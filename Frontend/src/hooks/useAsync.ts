/**
 * 通用异步数据加载 Hook。
 *
 * 实现原理：
 * 1. 调用方传入 loader（返回 Promise 的函数）与依赖数组；
 * 2. 依赖数组任一元素变化或手动触发 reload 时执行 loader；
 * 3. 每次请求分配递增版本号并配合 cancelled 标记，丢弃过期结果，避免竞态覆盖；
 * 4. 对外暴露 data / loading / error / reload / setData，覆盖页面加载、刷新与局部更新三类场景。
 */

import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'

import { getErrorMessage } from './errorMessage'

/** useAsync 对外暴露的状态与操作接口。 */
export interface AsyncState<T> {
  /** 加载成功的数据；初始或失败时为 null。 */
  data: T | null
  /** 是否正在加载。 */
  loading: boolean
  /** 加载失败的中文提示；成功时为 null。 */
  error: string | null
  /** 手动重新加载（用于刷新按钮、操作成功后回拉）。 */
  reload: () => void
  /** 直接修改数据（用于操作成功后局部更新，避免重复请求）。 */
  setData: Dispatch<SetStateAction<T | null>>
}

/**
 * 创建异步加载状态。
 *
 * @param loader 返回 Promise 的加载函数（内部会保存最新引用，无需 useCallback 包裹）
 * @param dependencies 依赖数组，元素变化时自动重新加载；数组长度需保持稳定
 * @returns 异步状态与操作
 */
export function useAsync<T>(
  loader: () => Promise<T>,
  dependencies: readonly unknown[] = [],
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadVersion, setReloadVersion] = useState<number>(0)
  /** 始终指向最新 loader，避免把内联函数放入依赖导致死循环。 */
  const loaderRef = useRef<() => Promise<T>>(loader)
  loaderRef.current = loader

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    loaderRef
      .current()
      .then((result) => {
        if (cancelled) {
          return
        }
        setData(result)
        setLoading(false)
      })
      .catch((caughtError: unknown) => {
        if (cancelled) {
          return
        }
        setError(getErrorMessage(caughtError, 'Failed to load data. Please try again later.'))
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // 依赖数组由调用方显式给出，长度需保持稳定
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadVersion, ...dependencies])

  /** 重新执行加载。 */
  const reload = useCallback((): void => {
    setReloadVersion((previousVersion) => previousVersion + 1)
  }, [])

  return { data, loading, error, reload, setData }
}
