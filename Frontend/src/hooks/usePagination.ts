/**
 * 分页状态 Hook：统一管理页码、每页条数与总数。
 *
 * 页面把 page / pageSize 拼进列表查询参数，加载完成后调用 setTotal 写入总数；
 * 筛选条件变化时调用 resetPage 回到第一页。
 */

import { useCallback, useState } from 'react'

/** 默认每页条数（与接口契约一致）。 */
export const DEFAULT_PAGE_SIZE = 20

/** 分页状态与操作接口。 */
export interface PaginationState {
  /** 当前页码，从 1 开始。 */
  page: number
  /** 每页条数。 */
  pageSize: number
  /** 数据总条数。 */
  total: number
  /** 设置页码（非法值会被修正为 1）。 */
  setPage: (page: number) => void
  /** 设置每页条数，同时回到第一页。 */
  setPageSize: (pageSize: number) => void
  /** 写入总条数。 */
  setTotal: (total: number) => void
  /** 回到第一页。 */
  resetPage: () => void
}

/**
 * 创建分页状态。
 *
 * @param initialPageSize 初始每页条数
 */
export function usePagination(initialPageSize: number = DEFAULT_PAGE_SIZE): PaginationState {
  const [page, setPageValue] = useState<number>(1)
  const [pageSize, setPageSizeValue] = useState<number>(initialPageSize)
  const [total, setTotalValue] = useState<number>(0)

  const setPage = useCallback((nextPage: number): void => {
    setPageValue(Number.isFinite(nextPage) && nextPage >= 1 ? Math.floor(nextPage) : 1)
  }, [])

  const setPageSize = useCallback((nextPageSize: number): void => {
    setPageSizeValue(Number.isFinite(nextPageSize) && nextPageSize >= 1 ? Math.floor(nextPageSize) : DEFAULT_PAGE_SIZE)
    setPageValue(1)
  }, [])

  const setTotal = useCallback((nextTotal: number): void => {
    setTotalValue(Number.isFinite(nextTotal) && nextTotal > 0 ? Math.floor(nextTotal) : 0)
  }, [])

  const resetPage = useCallback((): void => {
    setPageValue(1)
  }, [])

  return { page, pageSize, total, setPage, setPageSize, setTotal, resetPage }
}
