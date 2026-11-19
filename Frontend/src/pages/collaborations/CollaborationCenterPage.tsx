/**
 * 协作中心：我的协作 / 待我确认 / 团队目录 三个 Tab。
 *
 * 功能：查看与我相关的协作关系、处理待确认申请、浏览可协作团队目录并发起申请。
 * 按钮显隐由后端 canConfirm / canEnd / canCreateTask 权限标记控制。
 */

import { useCallback, useEffect, useState } from 'react'

import { getCollaborationDirectory, listCollaborations } from '../../api/collaborationApi'
import { useToast } from '../../context/ToastContext'
import { useAsync } from '../../hooks/useAsync'
import { usePagination } from '../../hooks/usePagination'
import type {
  CollaborationDirectoryItem,
  CollaborationItem,
  CollaborationStatus,
} from '../../types/collaboration'
import Button from '../../components/ui/Button'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Pagination from '../../components/ui/Pagination'
import Select from '../../components/ui/Select'
import Spinner from '../../components/ui/Spinner'
import Tabs from '../../components/ui/Tabs'
import CollaborationCard from '../../components/collaboration/CollaborationCard'
import CollaborationDirectoryPanel from '../../components/collaboration/CollaborationDirectoryPanel'
import ConfirmCollaborationDialog from '../../components/collaboration/ConfirmCollaborationDialog'
import CreateCollaborationDialog from '../../components/collaboration/CreateCollaborationDialog'
import EndCollaborationDialog from '../../components/collaboration/EndCollaborationDialog'
import styles from './CollaborationCenterPage.module.css'

/** 协作中心 Tab 键。 */
type CenterTabKey = 'mine' | 'pending' | 'directory'

/** 状态筛选选项。 */
const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'active', label: 'Active' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'ended', label: 'Ended' },
]

/** 发起协作弹窗的预填目标。 */
interface TargetPrefill {
  teamId: number
  subTeamId: number | null
}

/** 协作中心页面。 */
export default function CollaborationCenterPage() {
  const { showToast } = useToast()
  const [activeTab, setActiveTab] = useState<CenterTabKey>('mine')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [createOpen, setCreateOpen] = useState<boolean>(false)
  const [targetPrefill, setTargetPrefill] = useState<TargetPrefill | null>(null)
  const [confirmTarget, setConfirmTarget] = useState<CollaborationItem | null>(null)
  const [endTarget, setEndTarget] = useState<CollaborationItem | null>(null)
  const pagination = usePagination()
  const { page, pageSize, setPage, setTotal, resetPage } = pagination

  /** 拉取我的协作列表。 */
  const loadMine = useCallback(
    () =>
      listCollaborations({
        status: statusFilter === '' ? undefined : (statusFilter as CollaborationStatus),
        page,
        pageSize,
      }),
    [statusFilter, page, pageSize],
  )

  /** 拉取待确认申请（最多 100 条，前端按 canConfirm 过滤）。 */
  const loadPending = useCallback(
    () => listCollaborations({ status: 'pending', page: 1, pageSize: 100 }),
    [],
  )

  const mineState = useAsync(loadMine, [loadMine])
  const pendingState = useAsync(loadPending, [loadPending])
  const directoryState = useAsync<CollaborationDirectoryItem[]>(getCollaborationDirectory, [])

  const mineItems = mineState.data?.items ?? []
  const pendingItems = (pendingState.data?.items ?? []).filter((item) => item.canConfirm)

  /** 列表加载完成后同步总数。 */
  useEffect(() => {
    setTotal(mineState.data?.total ?? 0)
  }, [mineState.data, setTotal])

  /** 状态筛选变化时回到第一页。 */
  useEffect(() => {
    resetPage()
  }, [statusFilter, resetPage])

  /** 刷新所有列表。 */
  const reloadAll = (): void => {
    mineState.reload()
    pendingState.reload()
  }

  /** 打开发起协作弹窗。 */
  const openCreateDialog = (prefill: TargetPrefill | null): void => {
    setTargetPrefill(prefill)
    setCreateOpen(true)
  }

  /** 协作申请创建成功。 */
  const handleCreated = (): void => {
    setCreateOpen(false)
    setTargetPrefill(null)
    showToast('Collaboration request submitted. Awaiting receiver confirmation.', 'success')
    reloadAll()
  }

  /** 确认/拒绝成功。 */
  const handleConfirmed = (collaboration: CollaborationItem): void => {
    setConfirmTarget(null)
    showToast(
      collaboration.status === 'active' ? 'Collaboration is now active' : 'Collaboration request rejected',
      'success',
    )
    reloadAll()
  }

  /** 结束协作成功。 */
  const handleEnded = (): void => {
    setEndTarget(null)
    showToast('Collaboration ended', 'success')
    reloadAll()
  }

  /** 渲染我的协作 Tab 内容。 */
  const renderMineTab = () => {
    if (mineState.error !== null) {
      return (
        <div className={styles.errorBox}>
          <span>{mineState.error}</span>
          <Button variant="secondary" size="small" onClick={mineState.reload}>
            Reload
          </Button>
        </div>
      )
    }
    if (mineState.loading && mineItems.length === 0) {
      return (
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading collaborations...</span>
        </div>
      )
    }
    if (mineItems.length === 0) {
      return (
        <EmptyState
          title="No collaborations yet"
          description="You can initiate a collaboration request with another team or sub-team, or wait for another unit to initiate one with you."
          action={<Button onClick={() => openCreateDialog(null)}>Start Collaboration</Button>}
        />
      )
    }
    return (
      <>
        <ul className={styles.collaborationList}>
          {mineItems.map((collaboration) => (
            <li key={collaboration.id}>
              <CollaborationCard
                collaboration={collaboration}
                onConfirm={setConfirmTarget}
                onEnd={setEndTarget}
              />
            </li>
          ))}
        </ul>
        <Pagination page={page} pageSize={pageSize} total={pagination.total} onChange={setPage} />
      </>
    )
  }

  /** 渲染待我确认 Tab 内容。 */
  const renderPendingTab = () => {
    if (pendingState.error !== null) {
      return (
        <div className={styles.errorBox}>
          <span>{pendingState.error}</span>
          <Button variant="secondary" size="small" onClick={pendingState.reload}>
            Reload
          </Button>
        </div>
      )
    }
    if (pendingState.loading && pendingItems.length === 0) {
      return (
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading pending requests...</span>
        </div>
      )
    }
    if (pendingItems.length === 0) {
      return (
        <EmptyState
          title="No requests awaiting your confirmation"
          description="Requests appear here when another unit initiates a collaboration with a team or sub-team you manage."
        />
      )
    }
    return (
      <ul className={styles.collaborationList}>
        {pendingItems.map((collaboration) => (
          <li key={collaboration.id}>
            <CollaborationCard
              collaboration={collaboration}
              onConfirm={setConfirmTarget}
              onEnd={setEndTarget}
            />
          </li>
        ))}
      </ul>
    )
  }

  return (
    <div className="page-container">
      <PageHeader
        title="Collaboration Center"
        description="Manage collaborations between teams and sub-teams, dispatch collaboration tasks, and track both parties' review progress."
        actions={<Button onClick={() => openCreateDialog(null)}>Start Collaboration</Button>}
      />

      <Tabs
        items={[
          { key: 'mine', label: 'My Collaborations' },
          { key: 'pending', label: 'Pending Confirmation' + (pendingItems.length > 0 ? ' (' + pendingItems.length + ')' : '') },
          { key: 'directory', label: 'Team Directory' },
        ]}
        activeKey={activeTab}
        onChange={(nextKey) => setActiveTab(nextKey as CenterTabKey)}
      />

      <div className={styles.tabContent}>
        {activeTab === 'mine' ? (
          <>
            <div className={styles.filterRow}>
              <Select
                value={statusFilter}
                onChange={(value) => setStatusFilter(String(value))}
                options={STATUS_FILTER_OPTIONS}
                disabled={mineState.loading}
              />
            </div>
            {renderMineTab()}
          </>
        ) : null}

        {activeTab === 'pending' ? renderPendingTab() : null}

        {activeTab === 'directory' ? (
          <CollaborationDirectoryPanel
            directory={directoryState.data ?? []}
            loading={directoryState.loading}
            error={directoryState.error}
            onReload={directoryState.reload}
            onApply={(teamId, subTeamId) => openCreateDialog({ teamId, subTeamId })}
          />
        ) : null}
      </div>

      <CreateCollaborationDialog
        open={createOpen}
        initialTargetTeamId={targetPrefill?.teamId}
        initialTargetSubTeamId={targetPrefill?.subTeamId ?? null}
        onClose={() => {
          setCreateOpen(false)
          setTargetPrefill(null)
        }}
        onCreated={handleCreated}
      />

      <ConfirmCollaborationDialog
        open={confirmTarget !== null}
        collaboration={confirmTarget}
        onClose={() => setConfirmTarget(null)}
        onConfirmed={handleConfirmed}
      />

      <EndCollaborationDialog
        open={endTarget !== null}
        collaboration={endTarget}
        onClose={() => setEndTarget(null)}
        onEnded={handleEnded}
      />
    </div>
  )
}