/**
 * 管理后台团队管理面板：支持关键词搜索、认证状态筛选与分页。
 *
 * 管理员可对待认证团队执行认证通过或驳回操作；
 * 已认证团队可被驳回，已驳回团队可重新认证通过。
 */

import { useCallback, useEffect, useState } from 'react'

import { certifyTeam, listAdminTeams } from '../../api/adminApi'
import type { AdminTeamItem } from '../../types/admin'
import type { TeamStatus } from '../../types/common'
import { JOIN_METHOD_LABELS, TEAM_STATUS_LABELS } from '../../utils/displayUtils'
import { formatDate } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Input from '../ui/Input'
import Pagination from '../ui/Pagination'
import Select from '../ui/Select'
import Spinner from '../ui/Spinner'
import Table from '../ui/Table'
import { useToast } from '../../context/ToastContext'
import styles from './TeamsPanel.module.css'

/** 团队列表每页条数。 */
const PAGE_SIZE = 20

/** 认证状态筛选选项。 */
const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending Certification' },
  { value: 'active', label: 'Certified' },
  { value: 'rejected', label: 'Rejected' },
]

/** 认证状态对应的徽标风格。 */
function resolveStatusVariant(status: TeamStatus): 'default' | 'outline' | 'solid' {
  if (status === 'active') {
    return 'solid'
  }
  if (status === 'rejected') {
    return 'outline'
  }
  return 'default'
}

/** 管理后台团队管理面板。 */
export default function TeamsPanel() {
  const { showToast } = useToast()
  const [teams, setTeams] = useState<AdminTeamItem[]>([])
  const [total, setTotal] = useState<number>(0)
  const [page, setPage] = useState<number>(1)
  const [keywordDraft, setKeywordDraft] = useState<string>('')
  const [keyword, setKeyword] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [certifyingTeamId, setCertifyingTeamId] = useState<number | null>(null)

  /** 按当前筛选条件加载团队分页列表。 */
  const loadTeams = useCallback(async (): Promise<void> => {
    setLoading(true)
    setErrorMessage(null)
    try {
      const pageResult = await listAdminTeams({
        keyword: keyword === '' ? undefined : keyword,
        status: statusFilter === '' ? undefined : statusFilter,
        page,
        pageSize: PAGE_SIZE,
      })
      setTeams(pageResult.items)
      setTotal(pageResult.total)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load teams')
    } finally {
      setLoading(false)
    }
  }, [keyword, statusFilter, page])

  useEffect(() => {
    void loadTeams()
  }, [loadTeams])

  /** 搜索团队。 */
  const handleSearch = (): void => {
    setPage(1)
    setKeyword(keywordDraft.trim())
  }

  /** 重置筛选条件。 */
  const handleResetFilters = (): void => {
    setKeywordDraft('')
    setKeyword('')
    setStatusFilter('')
    setPage(1)
  }

  /** 认证状态筛选变化。 */
  const handleStatusFilterChange = (value: string | number): void => {
    setPage(1)
    setStatusFilter(String(value))
  }

  /** 认证通过 / 驳回团队。 */
  const handleCertify = async (teamItem: AdminTeamItem, approved: boolean): Promise<void> => {
    setCertifyingTeamId(teamItem.id)
    try {
      await certifyTeam(teamItem.id, approved)
      showToast('Team "' + teamItem.name + '" ' + (approved ? 'has been certified' : 'has been rejected'), 'success')
      await loadTeams()
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to update team certification', 'error')
    } finally {
      setCertifyingTeamId(null)
    }
  }

  return (
    <div className={styles.panelLayout}>
      <div className={styles.filterRow}>
        <div className={styles.keywordArea}>
          <Input
            value={keywordDraft}
            onChange={(event) => setKeywordDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                handleSearch()
              }
            }}
            placeholder="Search team name"
          />
        </div>
        <Select value={statusFilter} onChange={handleStatusFilterChange} options={STATUS_FILTER_OPTIONS} />
        <Button variant="secondary" onClick={handleSearch}>Search</Button>
        <Button variant="ghost" onClick={handleResetFilters}>Reset</Button>
      </div>

      {errorMessage !== null ? (
        <EmptyState
          title="Failed to load teams"
          description={errorMessage}
          action={<Button variant="secondary" onClick={() => void loadTeams()}>Reload</Button>}
        />
      ) : loading ? (
        <div className={styles.stateArea}><Spinner /><span>Loading teams ...</span></div>
      ) : teams.length === 0 ? (
        <EmptyState title="No matching teams" description="Adjust your keywords or filters and try again." />
      ) : (
        <>
          <Table
            columns={[
              {
                key: 'name',
                title: 'Team Name',
                render: (row: AdminTeamItem) => <span className={styles.teamName}>{row.name}</span>,
              },
              {
                key: 'creatorName',
                title: 'Creator',
                width: 120,
                render: (row: AdminTeamItem) => row.creatorName,
              },
              {
                key: 'joinMethod',
                title: 'Join Method',
                width: 110,
                render: (row: AdminTeamItem) =>
                  JOIN_METHOD_LABELS[row.joinMethod as keyof typeof JOIN_METHOD_LABELS] ?? row.joinMethod,
              },
              { key: 'memberCount', title: 'Members', width: 80, align: 'right', render: (row: AdminTeamItem) => row.memberCount },
              { key: 'taskCount', title: 'Tasks', width: 80, align: 'right', render: (row: AdminTeamItem) => row.taskCount },
              {
                key: 'status',
                title: 'Certification',
                width: 100,
                render: (row: AdminTeamItem) => (
                  <Badge variant={resolveStatusVariant(row.status)}>{TEAM_STATUS_LABELS[row.status]}</Badge>
                ),
              },
              {
                key: 'createdAt',
                title: 'Created At',
                width: 120,
                render: (row: AdminTeamItem) => formatDate(row.createdAt),
              },
              {
                key: 'actions',
                title: 'Actions',
                width: 170,
                render: (row: AdminTeamItem) => (
                  <div className={styles.actionRow}>
                    <Button
                      size="small"
                      variant="secondary"
                      loading={certifyingTeamId === row.id}
                      disabled={row.status === 'active'}
                      onClick={() => void handleCertify(row, true)}
                    >
                      Approve
                    </Button>
                    <Button
                      size="small"
                      variant="danger"
                      loading={certifyingTeamId === row.id}
                      disabled={row.status === 'rejected'}
                      onClick={() => void handleCertify(row, false)}
                    >
                      Reject
                    </Button>
                  </div>
                ),
              },
            ]}
            rows={teams}
            rowKey={(row: AdminTeamItem) => row.id}
            emptyText="No team data yet"
          />
          <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </>
      )}
    </div>
  )
}
