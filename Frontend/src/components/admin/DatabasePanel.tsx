/**
 * 管理后台数据库面板：左侧展示数据库表清单与行数，
 * 右侧分页浏览选中表的数据（敏感列已由后端脱敏），下方嵌入 SQL 执行器。
 */

import { useCallback, useEffect, useState } from 'react'

import { getDatabaseRows, listDatabaseTables } from '../../api/adminApi'
import type { DatabaseRowsResult, DatabaseTableInfo } from '../../types/admin'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Pagination from '../ui/Pagination'
import Spinner from '../ui/Spinner'
import Table from '../ui/Table'
import { useToast } from '../../context/ToastContext'
import SqlExecutor from './SqlExecutor'
import styles from './DatabasePanel.module.css'

/** 表数据浏览每页条数。 */
const ROWS_PAGE_SIZE = 20

/** 把单元格原始值转换为展示文本。 */
function formatCellValue(cellValue: unknown): string {
  if (cellValue === null || cellValue === undefined) {
    return '—'
  }
  if (typeof cellValue === 'object') {
    try {
      return JSON.stringify(cellValue)
    } catch {
      return String(cellValue)
    }
  }
  return String(cellValue)
}

/** 管理后台数据库面板。 */
export default function DatabasePanel() {
  const { showToast } = useToast()
  const [tables, setTables] = useState<DatabaseTableInfo[]>([])
  const [tablesLoading, setTablesLoading] = useState<boolean>(true)
  const [selectedTableName, setSelectedTableName] = useState<string | null>(null)
  const [rowsResult, setRowsResult] = useState<DatabaseRowsResult | null>(null)
  const [rowsLoading, setRowsLoading] = useState<boolean>(false)
  const [page, setPage] = useState<number>(1)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  /** 加载数据库表清单。 */
  const loadTables = useCallback(async (): Promise<void> => {
    setTablesLoading(true)
    try {
      const tableList = await listDatabaseTables()
      setTables(tableList)
      // 首次加载后默认选中第一张表，避免用户面对空白的右侧区域
      setSelectedTableName((previousTableName) => {
        if (previousTableName !== null) {
          return previousTableName
        }
        return tableList.length > 0 ? tableList[0].tableName : null
      })
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to load database tables', 'error')
    } finally {
      setTablesLoading(false)
    }
  }, [showToast])

  /** 加载选中表的分页数据。 */
  const loadTableRows = useCallback(async (): Promise<void> => {
    if (selectedTableName === null) {
      return
    }
    setRowsLoading(true)
    setErrorMessage(null)
    try {
      const tableRows = await getDatabaseRows(selectedTableName, page, ROWS_PAGE_SIZE)
      setRowsResult(tableRows)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load table data')
    } finally {
      setRowsLoading(false)
    }
  }, [selectedTableName, page])

  useEffect(() => {
    void loadTables()
  }, [loadTables])

  useEffect(() => {
    void loadTableRows()
  }, [loadTableRows])

  /** 切换选中表：重置分页并重新加载。 */
  const handleSelectTable = (tableName: string): void => {
    setSelectedTableName(tableName)
    setPage(1)
    setRowsResult(null)
  }

  /** 根据返回列动态构造表格列定义。 */
  const dynamicColumns =
    rowsResult === null
      ? []
      : rowsResult.columns.map((columnName) => ({
          key: columnName,
          title: columnName,
          render: (row: Record<string, unknown>) => (
            <span className={styles.cellText}>{formatCellValue(row[columnName])}</span>
          ),
        }))

  return (
    <div className={styles.databaseLayout}>
      <div className={styles.browseLayout}>
        <aside className={styles.tableListPanel}>
          <div className={styles.panelHeader}>
            <h3 className={styles.panelTitle}>Tables</h3>
            <Button variant="ghost" size="small" onClick={() => void loadTables()}>
              Refresh
            </Button>
          </div>
          {tablesLoading ? (
            <div className={styles.listState}><Spinner size="small" /><span>Loading ...</span></div>
          ) : tables.length === 0 ? (
            <p className={styles.emptyText}>No tables available.</p>
          ) : (
            <ul className={styles.tableList}>
              {tables.map((tableItem) => (
                <li key={tableItem.tableName}>
                  <button
                    type="button"
                    className={
                      tableItem.tableName === selectedTableName
                        ? styles.tableListItemActive
                        : styles.tableListItem
                    }
                    onClick={() => handleSelectTable(tableItem.tableName)}
                  >
                    <span className={styles.tableName}>{tableItem.tableName}</span>
                    <span className={styles.rowCount}>{tableItem.rowCount} rows</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className={styles.tableDataPanel}>
          {selectedTableName === null ? (
            <EmptyState title="Select a table" description="Choose a table from the list on the left to view its data." />
          ) : errorMessage !== null ? (
            <EmptyState
              title="Failed to load table data"
              description={errorMessage}
              action={<Button variant="secondary" onClick={() => void loadTableRows()}>Reload</Button>}
            />
          ) : rowsResult === null && rowsLoading ? (
            <div className={styles.listState}><Spinner /><span>Loading table data ...</span></div>
          ) : rowsResult === null ? (
            <EmptyState title="No table data yet" description="This table has no data to display." />
          ) : (
            <>
              <div className={styles.dataHeader}>
                <span className={styles.panelTitle}>{rowsResult.tableName}</span>
                <span className={styles.rowCount}>Total: {rowsResult.total} rows · Sensitive columns are masked by the backend</span>
              </div>
              <Table
                columns={dynamicColumns}
                rows={rowsResult.rows}
                rowKey={(row: Record<string, unknown>) => rowsResult.rows.indexOf(row)}
                loading={rowsLoading}
                emptyText="No data in this table"
              />
              <Pagination
                page={rowsResult.page}
                pageSize={rowsResult.pageSize}
                total={rowsResult.total}
                onChange={setPage}
              />
            </>
          )}
        </section>
      </div>

      <SqlExecutor />
    </div>
  )
}
