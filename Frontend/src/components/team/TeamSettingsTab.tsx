/**
 * 团队详情-设置 Tab：
 * - 团队管理员：编辑团队信息、生成邀请码、解散团队；
 * - 其他成员：只读展示团队信息与邀请码，可退出团队（需先转让管理员的情况由后端校验）。
 */

import { useState } from 'react'

import type { TeamDetail } from '../../types/team'
import { formatDateTime } from '../../utils/formatUtils'
import Button from '../ui/Button'
import InviteDialog from './InviteDialog'
import TeamDangerZone from './TeamDangerZone'
import TeamInfoForm from './TeamInfoForm'
import styles from './TeamSettingsTab.module.css'

/** TeamSettingsTab 组件属性。 */
export interface TeamSettingsTabProps {
  /** 团队详情。 */
  team: TeamDetail
  /** 设置变化后的刷新回调。 */
  onChanged: () => void
  /** 团队解散或退出后的回调（跳转团队列表）。 */
  onDissolved: () => void
}

/** 团队详情-设置 Tab。 */
export default function TeamSettingsTab({ team, onChanged, onDissolved }: TeamSettingsTabProps) {
  const [inviteDialogOpen, setInviteDialogOpen] = useState<boolean>(false)
  const isManager = team.currentUserRole === 'admin' || team.currentUserRole === 'subAdmin'
  const isAdmin = team.currentUserRole === 'admin'

  return (
    <div className={styles.settingsTab}>
      {isAdmin ? (
        <TeamInfoForm team={team} onUpdated={onChanged} />
      ) : (
        <section className={styles.readonlySection}>
          <h2 className={styles.sectionTitle}>Team Settings</h2>
          <p className={styles.permissionHint}>Only Team Admins can update team info, manage levels, and dissolve the team.</p>
        </section>
      )}

      {isManager ? (
        <section className={styles.inviteSection}>
          <header className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Invite Codes</h2>
              <p className={styles.sectionDescription}>
                Generate invite codes to invite new members. Set an expiration and a maximum number of uses.
              </p>
            </div>
            <Button
              variant="secondary"
              size="small"
              onClick={() => setInviteDialogOpen(true)}
              disabled={team.status !== 'active'}
              title={team.status !== 'active' ? 'Team pending certification; members cannot be invited yet.' : undefined}
            >
              Generate Invite Code
            </Button>
          </header>
          <dl className={styles.inviteInfo}>
            <div className={styles.inviteItem}>
              <dt className={styles.inviteLabel}>Current Invite Code</dt>
              <dd className={styles.inviteValue}>{team.inviteCode ?? 'Not generated'}</dd>
            </div>
            <div className={styles.inviteItem}>
              <dt className={styles.inviteLabel}>Expires</dt>
              <dd className={styles.inviteValue}>{formatDateTime(team.inviteExpiresAt)}</dd>
            </div>
          </dl>
          {team.status !== 'active' ? (
            <p className={styles.permissionHint}>Team pending certification: invite codes are available after certification.</p>
          ) : null}
          <InviteDialog
            open={inviteDialogOpen}
            team={team}
            onClose={() => setInviteDialogOpen(false)}
            onUpdated={onChanged}
          />
        </section>
      ) : null}

      <TeamDangerZone team={team} onDissolved={onDissolved} />
    </div>
  )
}
