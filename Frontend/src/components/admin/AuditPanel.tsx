/**
 * 管理后台审计日志面板：分页展示管理操作记录（操作人/动作/明细/IP/时间）。
 * 只读展示，不提供编辑能力。
 */

import { useCallback, useEffect, useState } from 'react'

import { listAuditLogs } from '../../api/adminApi'
import type { AuditLogItem } from '../../types/admin'
import { formatDateTime } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Pagination from '../ui/Pagination'
import Spinner from '../ui/Spinner'
import Table from '../ui/Table'
import styles from './AuditPanel.module.css'

/** 审计日志每页条数。 */
const PAGE_SIZE = 20

/** 审计动作对应的中文说明（未知动作直接展示原始值）。 */
const AUDIT_ACTION_LABELS: Record<string, string> = {
  databaseExecute: 'Execute SQL',
  updateGlobalRole: 'Change Global Role',
  updateUserStatus: 'Change User Status',
  certifyTeam: 'Team Certification',
  login: 'Sign In',
  logout: 'Sign Out',
  deleteAccount: 'Delete Account',
}

/** 管理后台审计日志面板。 */
export default function AuditPanel() {
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState<number>(0)
  const [page, setPage] = useState<number>(1)
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  /** 加载审计日志分页数据。 */
  const loadAuditLogs = useCallback(async (): Promise<void> => {
    setLoading(true)
    setErrorMessage(null)
    try {
      const pageResult = await listAuditLogs({ page, pageSize: PAGE_SIZE })
      setAuditLogs(pageResult.items)
      setTotal(pageResult.total)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    void loadAuditLogs()
  }, [loadAuditLogs])

  return (
    <div className={styles.panelLayout}>
      {errorMessage !== null ? (
        <EmptyState
          title="Failed to load audit logs"
          description={errorMessage}
          action={<Button variant="secondary" onClick={() => void loadAuditLogs()}>Reload</Button>}
        />
      ) : loading ? (
        <div className={styles.stateArea}><Spinner /><span>Loading audit logs ...</span></div>
      ) : auditLogs.length === 0 ? (
        <EmptyState title="No audit logs yet" description="Records appear here after administrators perform key actions." />
      ) : (
        <>
          <Table
            columns={[
              {
                key: 'operatorName',
                title: 'Operator',
                width: 130,
                render: (row: AuditLogItem) => (
                  <span className={styles.operatorName}>{row.operatorName}</span>
                ),
              },
              {
                key: 'action',
                title: 'Action',
                width: 140,
                render: (row: AuditLogItem) => (
                  <Badge variant="outline">{AUDIT_ACTION_LABELS[row.action] ?? row.action}</Badge>
                ),
              },
              {
                key: 'detail',
                title: 'Details',
                render: (row: AuditLogItem) => (
                  <span className={styles.detailText} title={row.detail ?? ''}>
                    {row.detail ?? '—'}
                  </span>
                ),
              },
              {
                key: 'ip',
                title: 'IP',
                width: 140,
                render: (row: AuditLogItem) => row.ip ?? '—',
              },
              {
                key: 'createdAt',
                title: 'Time',
                width: 150,
                render: (row: AuditLogItem) => formatDateTime(row.createdAt),
              },
            ]}
            rows={auditLogs}
            rowKey={(row: AuditLogItem) => row.id}
            emptyText="No audit logs yet"
          />
          <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </>
      )}
    </div>
  )
}
