/**
 * 管理后台 SQL 执行器：执行单条 SQL 并展示结果。
 *
 * 安全约定：
 * 1. 仅允许单条语句（后端同样校验）；
 * 2. 识别出写入/结构变更类危险语句时，先弹出二次确认；
 * 3. SELECT 类语句展示结果表格，DML 展示影响行数。
 */

import { useState } from 'react'

import { executeSql } from '../../api/adminApi'
import type { ExecuteSqlResult } from '../../types/admin'
import Button from '../ui/Button'
import Card from '../ui/Card'
import EmptyState from '../ui/EmptyState'
import ConfirmDialog from '../ui/ConfirmDialog'
import Table from '../ui/Table'
import Textarea from '../ui/Textarea'
import { useToast } from '../../context/ToastContext'
import styles from './SqlExecutor.module.css'

/** 危险语句识别正则：写入或结构变更类需要二次确认。 */
const DANGEROUS_STATEMENT_PATTERN = /^\s*(insert|update|delete|replace|create|alter|drop|truncate)\b/i

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

/** SQL 执行结果表格属性。 */
interface SqlResultTableProps {
  result: ExecuteSqlResult
}

/** 执行结果表格：列名动态取自返回行。 */
function SqlResultTable({ result }: SqlResultTableProps) {
  if (result.rows.length === 0) {
    return null
  }
  const columnNames = Object.keys(result.rows[0])
  return (
    <Table
      columns={columnNames.map((columnName) => ({
        key: columnName,
        title: columnName,
        render: (row: Record<string, unknown>) => (
          <span className={styles.cellText}>{formatCellValue(row[columnName])}</span>
        ),
      }))}
      rows={result.rows}
      rowKey={(row: Record<string, unknown>) => result.rows.indexOf(row)}
      emptyText="No rows returned"
    />
  )
}

/** 管理后台 SQL 执行器。 */
export default function SqlExecutor() {
  const { showToast } = useToast()
  const [sqlText, setSqlText] = useState<string>('')
  const [executing, setExecuting] = useState<boolean>(false)
  const [confirmOpen, setConfirmOpen] = useState<boolean>(false)
  const [executeResult, setExecuteResult] = useState<ExecuteSqlResult | null>(null)
  const [pendingSql, setPendingSql] = useState<string>('')

  /** 真正执行 SQL 请求。 */
  const runSql = async (sql: string): Promise<void> => {
    setExecuting(true)
    try {
      const result = await executeSql(sql)
      setExecuteResult(result)
      showToast(
        result.affectedRows > 0
          ? 'SQL executed successfully. ' + result.affectedRows + ' rows affected'
          : 'SQL executed successfully',
        'success',
      )
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to execute SQL', 'error')
    } finally {
      setExecuting(false)
      setConfirmOpen(false)
    }
  }

  /** 点击执行：先做空值与危险语句判断。 */
  const handleExecute = (): void => {
    const trimmedSql = sqlText.trim()
    if (trimmedSql.length === 0) {
      showToast('Enter a SQL statement to execute', 'error')
      return
    }
    if (DANGEROUS_STATEMENT_PATTERN.test(trimmedSql)) {
      setPendingSql(trimmedSql)
      setConfirmOpen(true)
      return
    }
    void runSql(trimmedSql)
  }

  return (
    <Card title="Execute SQL">
      <div className={styles.executorLayout}>
        <p className={styles.warningText}>
          Only a single DML statement is allowed. Write operations are recorded in the audit log, so proceed with caution.
        </p>
        <Textarea
          value={sqlText}
          onChange={(event) => setSqlText(event.target.value)}
          rows={5}
          placeholder="e.g. SELECT * FROM t_user LIMIT 20"
        />
        <div className={styles.actionRow}>
          <Button variant="primary" loading={executing} onClick={handleExecute}>
            Execute SQL
          </Button>
          <Button variant="ghost" onClick={() => { setSqlText(''); setExecuteResult(null) }}>
            Clear
          </Button>
        </div>

        {executeResult === null ? (
          <EmptyState title="No results yet" description="Returned data will appear here after you run a SELECT statement." />
        ) : (
          <div className={styles.resultArea}>
            <div className={styles.resultSummary}>
              <span>Statement Type: {executeResult.statementType}</span>
              <span>Affected Rows: {executeResult.affectedRows}</span>
              <span>Returned Rows: {executeResult.rows.length}</span>
            </div>
            <SqlResultTable result={executeResult} />
          </div>
        )}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="Confirm Write Operation"
        description={'This statement may modify database data and cannot be undone. Execute it?\n' + pendingSql.slice(0, 120)}
        confirmText="Execute"
        danger
        loading={executing}
        onConfirm={() => void runSql(pendingSql)}
        onCancel={() => setConfirmOpen(false)}
      />
    </Card>
  )
}
