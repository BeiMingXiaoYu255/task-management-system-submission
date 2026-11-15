/**
 * 入团申请审批面板：展示待处理申请，支持通过/拒绝。
 *
 * 仅团队管理员/子管理员可见（由父级控制渲染），通过后申请人的成员关系由后端建立，
 * 因此审批成功后需要同时刷新团队成员列表与申请列表。
 */

import { useCallback, useState } from 'react'

import { handleJoinRequest, listJoinRequests } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import { useAsync } from '../../hooks/useAsync'
import type { TeamDetail } from '../../types/team'
import { formatDateTime } from '../../utils/formatUtils'
import Avatar from '../ui/Avatar'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Spinner from '../ui/Spinner'
import styles from './JoinRequestPanel.module.css'

/** JoinRequestPanel 组件属性。 */
export interface JoinRequestPanelProps {
  /** 团队详情。 */
  team: TeamDetail
  /** 成员数据变化后的刷新回调。 */
  onChanged: () => void
}

/** 入团申请审批面板。 */
export default function JoinRequestPanel({ team, onChanged }: JoinRequestPanelProps) {
  const { showToast } = useToast()
  const [pendingRequestId, setPendingRequestId] = useState<number | null>(null)

  /** 拉取待处理申请列表。 */
  const loadJoinRequests = useCallback(
    () => listJoinRequests(team.id),
    [team.id],
  )
  const { data, loading, error, reload } = useAsync(loadJoinRequests, [loadJoinRequests])
  const joinRequests = data ?? []

  /** 审批单个入团申请。 */
  const handleRequest = async (requestId: number, action: 'approve' | 'reject'): Promise<void> => {
    setPendingRequestId(requestId)
    try {
      await handleJoinRequest(team.id, requestId, action)
      showToast(action === 'approve' ? 'Join request approved.' : 'Join request rejected.', 'success')
      reload()
      onChanged()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to review join request.'), 'error')
    } finally {
      setPendingRequestId(null)
    }
  }

  return (
    <section className={styles.requestSection}>
      <header className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>Pending Join Requests</h3>
        <span className={styles.sectionHint}>{joinRequests.length}  requests</span>
      </header>

      {loading ? (
        <div className={styles.loadingBox}>
          <Spinner size="small" />
          <span>Loading requests...</span>
        </div>
      ) : error ? (
        <div className={styles.errorBox}>
          <span>{error}</span>
          <Button variant="secondary" size="small" onClick={reload}>
            Retry
          </Button>
        </div>
      ) : joinRequests.length === 0 ? (
        <EmptyState title="No pending requests" description="New join requests will appear here." />
      ) : (
        <ul className={styles.requestList}>
          {joinRequests.map((joinRequest) => (
            <li key={joinRequest.id} className={styles.requestItem}>
              <Avatar name={joinRequest.nickname} size="small" />
              <div className={styles.requestMain}>
                <span className={styles.requestName}>
                  {joinRequest.nickname}
                  <span className={styles.requestUsername}>@{joinRequest.username}</span>
                </span>
                <span className={styles.requestMessage}>
                  {joinRequest.message ? joinRequest.message : 'No message provided.'}
                </span>
                <span className={styles.requestTime}>
                  Requested: {formatDateTime(joinRequest.createdAt)}
                </span>
              </div>
              <div className={styles.requestActions}>
                <Button
                  size="small"
                  loading={pendingRequestId === joinRequest.id}
                  disabled={pendingRequestId !== null && pendingRequestId !== joinRequest.id}
                  onClick={() => void handleRequest(joinRequest.id, 'approve')}
                >
                  Approve
                </Button>
                <Button
                  variant="danger"
                  size="small"
                  disabled={pendingRequestId !== null}
                  onClick={() => void handleRequest(joinRequest.id, 'reject')}
                >
                  Reject
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
