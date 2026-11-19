/**
 * 协作详情页：协作信息、双方对接人、协作任务列表与新建协作任务。
 *
 * 数据流：加载 GET /collaborations/{id} 与任务分页；确认/结束操作返回最新协作，
 * 直接回写详情，再刷新任务列表，避免整页重新加载。
 */

import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  getCollaboration,
  listCollaborationTasks,
} from '../../api/collaborationApi'
import { useToast } from '../../context/ToastContext'
import { useAsync } from '../../hooks/useAsync'
import { usePagination } from '../../hooks/usePagination'
import type { CollaborationItem } from '../../types/collaboration'
import Button from '../../components/ui/Button'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import CollaborationInfoPanel from '../../components/collaboration/CollaborationInfoPanel'
import CollaborationTaskList from '../../components/collaboration/CollaborationTaskList'
import ConfirmCollaborationDialog from '../../components/collaboration/ConfirmCollaborationDialog'
import CreateCollaborationTaskDialog from '../../components/collaboration/CreateCollaborationTaskDialog'
import EndCollaborationDialog from '../../components/collaboration/EndCollaborationDialog'
import CollaborationStatusBadge from '../../components/collaboration/CollaborationStatusBadge'
import { formatCollaborationUnit } from '../../components/collaboration/collaborationUtils'
import styles from './CollaborationDetailPage.module.css'

/** 协作详情页。 */
export default function CollaborationDetailPage() {
  const { collaborationId } = useParams<{ collaborationId: string }>()
  const parsedCollaborationId = Number(collaborationId)
  const isValidId = Number.isInteger(parsedCollaborationId) && parsedCollaborationId > 0
  const { showToast } = useToast()
  const [createTaskOpen, setCreateTaskOpen] = useState<boolean>(false)
  const [confirmOpen, setConfirmOpen] = useState<boolean>(false)
  const [endOpen, setEndOpen] = useState<boolean>(false)
  const pagination = usePagination()
  const { page, pageSize, setPage, setTotal } = pagination

  /** 加载协作详情。 */
  const loadCollaboration = useCallback(
    () =>
      isValidId
        ? getCollaboration(parsedCollaborationId)
        : Promise.reject(new Error('Invalid collaboration ID')),
    [isValidId, parsedCollaborationId],
  )

  /** 加载协作任务分页。 */
  const loadTasks = useCallback(
    () =>
      isValidId
        ? listCollaborationTasks(parsedCollaborationId, { page, pageSize })
        : Promise.resolve({ items: [], total: 0, page: 1, pageSize }),
    [isValidId, parsedCollaborationId, page, pageSize],
  )

  const collaborationState = useAsync(loadCollaboration, [loadCollaboration])
  const tasksState = useAsync(loadTasks, [loadTasks])
  const collaboration = collaborationState.data

  /** 任务列表加载完成后同步总数。 */
  useEffect(() => {
    setTotal(tasksState.data?.total ?? 0)
  }, [tasksState.data, setTotal])

  /** 处理成功：回写协作详情。 */
  const handleConfirmed = (updated: CollaborationItem): void => {
    setConfirmOpen(false)
    collaborationState.setData(updated)
    showToast(updated.status === 'active' ? 'Collaboration is now active' : 'Collaboration request rejected', 'success')
  }

  /** 结束协作成功。 */
  const handleEnded = (updated: CollaborationItem): void => {
    setEndOpen(false)
    collaborationState.setData(updated)
    showToast('Collaboration ended', 'success')
  }

  /** 新建协作任务成功。 */
  const handleTaskCreated = (): void => {
    setCreateTaskOpen(false)
    showToast('Collaboration task created. Awaiting receiver acceptance.', 'success')
    tasksState.reload()
  }

  if (collaborationState.loading) {
    return (
      <div className="page-container">
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading collaboration details...</span>
        </div>
      </div>
    )
  }

  if (collaborationState.error !== null || collaboration === null) {
    return (
      <div className="page-container">
        <EmptyState
          title="Unable to access this collaboration"
          description={collaborationState.error ?? 'The collaboration does not exist or you do not have permission to view it.'}
          action={
            <Link to="/collaborations">
              <Button variant="secondary">Back to Collaboration Center</Button>
            </Link>
          }
        />
      </div>
    )
  }

  const isActive = collaboration.status === 'active'

  return (
    <div className="page-container">
      <nav className={styles.breadcrumb} aria-label="Breadcrumb">
        <Link to="/collaborations" className={styles.breadcrumbLink}>
          ← Back to Collaboration Center
        </Link>
      </nav>

      <PageHeader
        title={
          formatCollaborationUnit(collaboration.initiatorUnit) +
          ' → ' +
          formatCollaborationUnit(collaboration.targetUnit)
        }
        description={'Applicant: ' + collaboration.createdByName + ' · Collaboration tasks are tracked by both parties'}
        actions={
          <div className={styles.headerActions}>
            <CollaborationStatusBadge status={collaboration.status} />
            {collaboration.canConfirm ? (
              <Button onClick={() => setConfirmOpen(true)}>Process Request</Button>
            ) : null}
            {collaboration.canEnd ? (
              <Button variant="danger" onClick={() => setEndOpen(true)}>
                End Collaboration
              </Button>
            ) : null}
          </div>
        }
      />

      {collaboration.status === 'pending' ? (
        <p className={styles.statusHint}>The collaboration request is awaiting receiver admin confirmation. Once confirmed, collaboration tasks can be dispatched.</p>
      ) : null}
      {collaboration.status === 'rejected' ? (
        <p className={styles.dangerHint}>The collaboration request was rejected. You can initiate a new request if needed.</p>
      ) : null}
      {collaboration.status === 'ended' ? (
        <p className={styles.statusHint}>The collaboration has ended. New collaboration tasks cannot be dispatched, but past tasks remain available.</p>
      ) : null}

      <div className={styles.detailLayout}>
        <CollaborationInfoPanel collaboration={collaboration} />
        <CollaborationTaskList
          tasks={tasksState.data?.items ?? []}
          loading={tasksState.loading}
          error={tasksState.error}
          canCreateTask={collaboration.canCreateTask && isActive}
          onCreate={() => setCreateTaskOpen(true)}
          onReload={tasksState.reload}
          page={page}
          pageSize={pageSize}
          total={pagination.total}
          onPageChange={setPage}
        />
      </div>

      <CreateCollaborationTaskDialog
        open={createTaskOpen}
        collaboration={collaboration}
        onClose={() => setCreateTaskOpen(false)}
        onCreated={handleTaskCreated}
      />

      <ConfirmCollaborationDialog
        open={confirmOpen}
        collaboration={collaboration}
        onClose={() => setConfirmOpen(false)}
        onConfirmed={handleConfirmed}
      />

      <EndCollaborationDialog
        open={endOpen}
        collaboration={collaboration}
        onClose={() => setEndOpen(false)}
        onEnded={handleEnded}
      />
    </div>
  )
}
