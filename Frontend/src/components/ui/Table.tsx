/**
 * 表格组件：列定义驱动渲染，支持加载态、空态与整行点击。
 * 泛型 RowType 由 rows 自动推断，列 render 拿到强类型行数据。
 */

import type { CSSProperties, ReactNode } from 'react'

import Spinner from './Spinner'
import styles from './Table.module.css'

/** 表格对齐方式。 */
export type TableAlign = 'left' | 'center' | 'right'

/** 列定义。 */
export interface TableColumn<RowType> {
  /** 列唯一键。 */
  key: string
  /** 列标题。 */
  title: ReactNode
  /** 列宽（数字按像素处理）。 */
  width?: number | string
  /** 对齐方式，默认 left。 */
  align?: TableAlign
  /** 单元格渲染函数。 */
  render: (row: RowType) => ReactNode
}

/** 表格属性。 */
export interface TableProps<RowType> {
  /** 列定义列表。 */
  columns: TableColumn<RowType>[]
  /** 行数据列表。 */
  rows: RowType[]
  /** 行唯一键生成函数。 */
  rowKey: (row: RowType) => string | number
  /** 空数据文案，默认“暂无数据”。 */
  emptyText?: string
  /** 是否处于加载态。 */
  loading?: boolean
  /** 整行点击回调。 */
  onRowClick?: (row: RowType) => void
}

/** 把列宽转换为行内样式。 */
function buildWidthStyle(width: number | string | undefined): CSSProperties | undefined {
  if (width === undefined) {
    return undefined
  }
  return { width: typeof width === 'number' ? width + 'px' : width }
}

/** 解析对齐样式类名。 */
function resolveAlignClass<RowType>(align: TableAlign | undefined): string {
  if (align === 'center') {
    return styles.alignCenter
  }
  if (align === 'right') {
    return styles.alignRight
  }
  return styles.alignLeft
}

/** 通用表格。 */
export function Table<RowType>({
  columns,
  rows,
  rowKey,
  emptyText = 'No data yet',
  loading = false,
  onRowClick,
}: TableProps<RowType>) {
  const columnCount = columns.length
  return (
    <div className={styles.tableWrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={[styles.th, resolveAlignClass(column.align)].join(' ')}
                style={buildWidthStyle(column.width)}
              >
                {column.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td className={styles.stateCell} colSpan={columnCount}>
                <span className={styles.loadingBlock}>
                  <Spinner size="small" />
                  <span>Loading...</span>
                </span>
              </td>
            </tr>
          ) : rows.length === 0 ? (
            <tr>
              <td className={styles.stateCell} colSpan={columnCount}>
                {emptyText}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                className={onRowClick ? styles.clickableRow : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={[styles.td, resolveAlignClass(column.align)].join(' ')}
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

export default Table
