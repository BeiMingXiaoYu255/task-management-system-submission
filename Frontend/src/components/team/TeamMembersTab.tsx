/**
 * 团队详情-成员 Tab：成员表 + 候选成员查看 +（管理员/子管理员可见的）入团申请审批面板。
 */

import { useState } from 'react'

import type { TeamDetail } from '../../types/team'
import Button from '../ui/Button'
import JoinRequestPanel from './JoinRequestPanel'
import MemberCandidateDialog from './MemberCandidateDialog'
import MemberTable from './MemberTable'
import styles from './TeamMembersTab.module.css'

/** TeamMembersTab 组件属性。 */
export interface TeamMembersTabProps {
  /** 团队详情。 */
  team: TeamDetail
  /** 当前登录用户 ID。 */
  currentUserId: number
  /** 数据变化后的刷新回调。 */
  onChanged: () => void
}

/** 团队详情-成员 Tab。 */
export default function TeamMembersTab({ team, currentUserId, onChanged }: TeamMembersTabProps) {
  const [candidateDialogOpen, setCandidateDialogOpen] = useState<boolean>(false)
  const isManager = team.currentUserRole === 'admin' || team.currentUserRole === 'subAdmin'

  return (
    <div className={styles.membersTab}>
      <section className={styles.memberSection}>
        <header className={styles.sectionHeader}>
          <div>
            <h2 className={styles.sectionTitle}>Team Members ({team.members.length})</h2>
            <p className={styles.sectionDescription}>
              Admins can adjust member levels, set sub-admins, remove members, or transfer ownership.
            </p>
          </div>
          <div className={styles.headerActions}>
            {isManager ? (
              <Button
                variant="secondary"
                size="small"
                onClick={() => setCandidateDialogOpen(true)}
              >
                View Candidate Members
              </Button>
            ) : null}
            <Button variant="secondary" size="small" onClick={onChanged}>
              Refresh
            </Button>
          </div>
        </header>
        <MemberTable team={team} currentUserId={currentUserId} onChanged={onChanged} />
      </section>

      {isManager ? <JoinRequestPanel team={team} onChanged={onChanged} /> : null}

      <MemberCandidateDialog
        open={candidateDialogOpen}
        team={team}
        onClose={() => setCandidateDialogOpen(false)}
      />
    </div>
  )
}
