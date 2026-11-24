/**
 * 分页组件：显示总数与页码，页码过多时折叠为省略号。
 */

import styles from './Pagination.module.css'

/** 分页属性。 */
export interface PaginationProps {
  /** 当前页（从 1 开始）。 */
  page: number
  /** 每页条数。 */
  pageSize: number
  /** 数据总数。 */
  total: number
  /** 页码变化回调。 */
  onChange: (page: number) => void
}

/** 页码标记：数字页码或省略号。 */
type PageToken = number | 'leftEllipsis' | 'rightEllipsis'

/** 根据当前页与总页数计算需要展示的页码标记。 */
function buildPageTokens(currentPage: number, totalPages: number): PageToken[] {
  if (totalPages <= 7) {
    const tokens: PageToken[] = []
    for (let pageNumber = 1; pageNumber <= totalPages; pageNumber += 1) {
      tokens.push(pageNumber)
    }
    return tokens
  }
  const showLeftEllipsis = currentPage > 4
  const showRightEllipsis = currentPage < totalPages - 3
  const startPage = showLeftEllipsis ? currentPage - 1 : 2
  const endPage = showRightEllipsis ? currentPage + 1 : totalPages - 1
  const tokens: PageToken[] = [1]
  if (showLeftEllipsis) {
    tokens.push('leftEllipsis')
  }
  for (let pageNumber = startPage; pageNumber <= endPage; pageNumber += 1) {
    tokens.push(pageNumber)
  }
  if (showRightEllipsis) {
    tokens.push('rightEllipsis')
  }
  tokens.push(totalPages)
  return tokens
}

/** 分页组件。 */
export function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  if (total <= 0) {
    return null
  }
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)
  const tokens = buildPageTokens(safePage, totalPages)

  return (
    <div className={styles.pagination}>
      <span className={styles.totalText}>Total: {total}</span>
      <div className={styles.pageButtons}>
        <button
          type="button"
          className={styles.pageButton}
          disabled={safePage <= 1}
          onClick={() => onChange(safePage - 1)}
        >
          Previous
        </button>
        {tokens.map((token, index) => {
          if (token === 'leftEllipsis' || token === 'rightEllipsis') {
            return (
              <span key={token + '-' + index} className={styles.ellipsis}>
                ...
              </span>
            )
          }
          const isActive = token === safePage
          const classNames = [styles.pageButton]
          if (isActive) {
            classNames.push(styles.activePageButton)
          }
          return (
            <button
              key={token}
              type="button"
              className={classNames.join(' ')}
              aria-current={isActive ? 'page' : undefined}
              onClick={() => onChange(token)}
            >
              {token}
            </button>
          )
        })}
        <button
          type="button"
          className={styles.pageButton}
          disabled={safePage >= totalPages}
          onClick={() => onChange(safePage + 1)}
        >
          Next
        </button>
      </div>
    </div>
  )
}

export default Pagination
