/**
 * 团队危险操作区：
 * - 团队管理员：解散团队，必须输入完整团队名称二次确认；
 * - 普通成员/子管理员：退出团队（团队管理员必须先转让管理员后才能退出）。
 */

import { useState } from 'react'

import { deleteTeam, leaveTeam } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { TeamDetail } from '../../types/team'
import Button from '../ui/Button'
import ConfirmDialog from '../ui/ConfirmDialog'
import Input from '../ui/Input'
import styles from './TeamDangerZone.module.css'

/** TeamDangerZone 组件属性。 */
export interface TeamDangerZoneProps {
  /** 团队详情。 */
  team: TeamDetail
  /** 解散/退出成功后的回调（通常跳转团队列表）。 */
  onDissolved: () => void
}

/** 团队危险操作区。 */
export default function TeamDangerZone({ team, onDissolved }: TeamDangerZoneProps) {
  const { showToast } = useToast()
  const [confirmName, setConfirmName] = useState<string>('')
  const [dissolveDialogOpen, setDissolveDialogOpen] = useState<boolean>(false)
  const [leaveDialogOpen, setLeaveDialogOpen] = useState<boolean>(false)
  const [submitting, setSubmitting] = useState<boolean>(false)

  const isAdmin = team.currentUserRole === 'admin'
  const isNameMatched = confirmName.trim() === team.name

  /** 执行解散团队。 */
  const handleDissolve = async (): Promise<void> => {
    setSubmitting(true)
    try {
      await deleteTeam(team.id, confirmName.trim())
      showToast('Team dissolved.', 'success')
      setDissolveDialogOpen(false)
      onDissolved()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to dissolve team.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  /** 执行退出团队。 */
  const handleLeave = async (): Promise<void> => {
    setSubmitting(true)
    try {
      await leaveTeam(team.id)
      showToast('You left the team.', 'success')
      setLeaveDialogOpen(false)
      onDissolved()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to leave team.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className={styles.dangerSection}>
      <header className={styles.sectionHeader}>
        <h2 className={styles.dangerTitle}>Danger Zone</h2>
        <p className={styles.dangerDescription}>The following actions cannot be undone. Proceed with caution.</p>
      </header>

      {isAdmin ? (
        <div className={styles.dangerItem}>
          <div className={styles.dangerItemHeader}>
            <span className={styles.dangerItemName}>Dissolve Team</span>
            <span className={styles.dangerItemDescription}>
              Dissolving deletes team members, levels, and task data permanently.
            </span>
          </div>
          <Input
            label={'Type the team name "' + team.name + '" to confirm'}
            value={confirmName}
            onChange={(event) => setConfirmName(event.target.value)}
            placeholder="Enter the full team name"
            disabled={submitting}
          />
          <div className={styles.actionRow}>
            <Button
              variant="danger"
              disabled={!isNameMatched || submitting}
              onClick={() => setDissolveDialogOpen(true)}
            >
              Dissolve Team
            </Button>
          </div>
        </div>
      ) : (
        <div className={styles.dangerItem}>
          <div className={styles.dangerItemHeader}>
            <span className={styles.dangerItemName}>Leave Team</span>
            <span className={styles.dangerItemDescription}>
              After leaving, you can no longer view this team's tasks. Team Admins must transfer ownership before leaving.
            </span>
          </div>
          <div className={styles.actionRow}>
            <Button variant="danger" onClick={() => setLeaveDialogOpen(true)}>
              Leave Team
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={dissolveDialogOpen}
        title="Dissolve Team"
        description={'Dissolve team "' + team.name + '"? This cannot be undone.'}
        confirmText="Confirm Dissolution"
        danger
        loading={submitting}
        onConfirm={() => void handleDissolve()}
        onCancel={() => {
          if (!submitting) {
            setDissolveDialogOpen(false)
          }
        }}
      />

      <ConfirmDialog
        open={leaveDialogOpen}
        title="Leave Team"
        description="Leave this team? You will need to apply again or use an invite code to rejoin."
        confirmText="Confirm Leave"
        danger
        loading={submitting}
        onConfirm={() => void handleLeave()}
        onCancel={() => {
          if (!submitting) {
            setLeaveDialogOpen(false)
          }
        }}
      />
    </section>
  )
}
