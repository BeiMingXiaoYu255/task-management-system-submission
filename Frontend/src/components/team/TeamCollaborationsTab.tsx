/**
 * 团队详情-协作 Tab：展示该团队（含其子团队）参与的协作关系，并提供发起协作入口。
 *
 * 数据说明：GET /collaborations 返回“与我相关”的协作，这里再按团队 ID 兜底过滤，
 * 保证在团队视角下只展示与该团队相关的记录。
 */

import { useState } from 'react'

import { listCollaborations } from '../../api/collaborationApi'
import { listSubTeams } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { useAsync } from '../../hooks/useAsync'
import type { CollaborationItem, SubTeamItem } from '../../types/collaboration'
import type { TeamDetail } from '../../types/team'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Spinner from '../ui/Spinner'
import CollaborationCard from '../collaboration/CollaborationCard'
import ConfirmCollaborationDialog from '../collaboration/ConfirmCollaborationDialog'
import CreateCollaborationDialog from '../collaboration/CreateCollaborationDialog'
import EndCollaborationDialog from '../collaboration/EndCollaborationDialog'
import styles from './TeamCollaborationsTab.module.css'

/** TeamCollaborationsTab 组件属性。 */
export interface TeamCollaborationsTabProps {
  /** 团队详情。 */
  team: TeamDetail
}

/** 团队详情-协作 Tab。 */
export default function TeamCollaborationsTab({ team }: TeamCollaborationsTabProps) {
  const { showToast } = useToast()
  const [createOpen, setCreateOpen] = useState<boolean>(false)
  const [confirmTarget, setConfirmTarget] = useState<CollaborationItem | null>(null)
  const [endTarget, setEndTarget] = useState<CollaborationItem | null>(null)

  /** 拉取与我相关的协作（团队视角下再按单位过滤）。 */
  const collaborationsState = useAsync(() => listCollaborations({ page: 1, pageSize: 100 }), [])
  const subTeamsState = useAsync<SubTeamItem[]>(() => listSubTeams(team.id), [team.id])

  const teamCollaborations = (collaborationsState.data?.items ?? []).filter(
    (collaboration) =>
      collaboration.initiatorUnit.teamId === team.id || collaboration.targetUnit.teamId === team.id,
  )

  /** 是否可发起协作：团队管理员或任一子团队负责人/管理员。 */
  const canInitiate =
    team.currentUserRole === 'admin' ||
    (subTeamsState.data ?? []).some(
      (subTeam) => subTeam.myRole === 'leader' || subTeam.myRole === 'admin',
    )

  /** 确认/拒绝成功。 */
  const handleConfirmed = (collaboration: CollaborationItem): void => {
    setConfirmTarget(null)
    showToast(
      collaboration.status === 'active' ? 'Collaboration active.' : 'Collaboration request rejected.',
      'success',
    )
    collaborationsState.reload()
  }

  /** 结束协作成功。 */
  const handleEnded = (): void => {
    setEndTarget(null)
    showToast('Collaboration ended.', 'success')
    collaborationsState.reload()
  }

  return (
    <div className={styles.tabBody}>
      <header className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>Team Collaborations ({teamCollaborations.length})</h2>
          <p className={styles.sectionDescription}>
            View collaborations involving this team and its sub-teams. Pending requests can be handled here.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Button
            variant="secondary"
            size="small"
            onClick={collaborationsState.reload}
            loading={collaborationsState.loading}
          >
            Refresh
          </Button>
          {canInitiate ? <Button onClick={() => setCreateOpen(true)}>Start Collaboration</Button> : null}
        </div>
      </header>

      {!canInitiate ? (
        <p className={styles.permissionHint}>Only Team Admins or Sub-team Leads can start collaborations on behalf of this team.</p>
      ) : null}

      {collaborationsState.error !== null ? (
        <div className={styles.errorBox}>
          <span>{collaborationsState.error}</span>
          <Button variant="secondary" size="small" onClick={collaborationsState.reload}>
            Reload
          </Button>
        </div>
      ) : collaborationsState.loading && teamCollaborations.length === 0 ? (
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading collaborations...</span>
        </div>
      ) : teamCollaborations.length === 0 ? (
        <EmptyState
          title="No collaborations yet"
          description="Shows collaborations relevant to you (units you manage or where you are the liaison). Start a collaboration with another certified team, or open the Collaboration Center to view all collaborations."
          action={canInitiate ? <Button onClick={() => setCreateOpen(true)}>Start Collaboration</Button> : undefined}
        />
      ) : (
        <ul className={styles.collaborationList}>
          {teamCollaborations.map((collaboration) => (
            <li key={collaboration.id}>
              <CollaborationCard
                collaboration={collaboration}
                onConfirm={setConfirmTarget}
                onEnd={setEndTarget}
              />
            </li>
          ))}
        </ul>
      )}

      <CreateCollaborationDialog
        open={createOpen}
        initialInitiatorTeamId={team.id}
        onClose={() => setCreateOpen(false)}
        onCreated={() => {
          setCreateOpen(false)
          showToast('Collaboration request submitted. Waiting for the receiver to confirm.', 'success')
          collaborationsState.reload()
        }}
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