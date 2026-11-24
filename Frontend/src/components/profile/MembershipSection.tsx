/**
 * 团队身份展示组件：展示全局角色与当前用户在各团队中的角色、级别与认证状态。
 * 纯展示组件，数据来自 AuthContext 的当前用户信息。
 */

import type { TeamMembership } from '../../types/auth'
import type { GlobalRole } from '../../types/common'
import {
  GLOBAL_ROLE_LABELS,
  TEAM_ROLE_LABELS,
  TEAM_STATUS_LABELS,
} from '../../utils/displayUtils'
import { formatDate } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import EmptyState from '../ui/EmptyState'
import Table from '../ui/Table'
import styles from './MembershipSection.module.css'

/** 团队身份展示属性。 */
interface MembershipSectionProps {
  teams: TeamMembership[]
  globalRole: GlobalRole
}

/** 团队认证状态对应的徽标样式（仅用灰度区分）。 */
function resolveStatusVariant(status: TeamMembership['teamStatus']): 'default' | 'outline' | 'solid' {
  if (status === 'active') {
    return 'solid'
  }
  if (status === 'rejected') {
    return 'outline'
  }
  return 'default'
}

/** 团队身份与全局角色展示。 */
export default function MembershipSection({ teams, globalRole }: MembershipSectionProps) {
  return (
    <div className={styles.sectionLayout}>
      <div className={styles.globalRoleRow}>
        <span className={styles.rowLabel}>Global Role</span>
        <Badge variant="solid">{GLOBAL_ROLE_LABELS[globalRole]}</Badge>
        <span className={styles.rowHint}>Global roles are assigned by a system administrator</span>
      </div>
      {teams.length === 0 ? (
        <EmptyState title="Not in a team yet" description="Join or create a team to view your team roles and levels here." />
      ) : (
        <Table
          columns={[
            {
              key: 'teamName',
              title: 'Team',
              render: (row: TeamMembership) => <span className={styles.teamName}>{row.teamName}</span>,
            },
            {
              key: 'role',
              title: 'Team Role',
              width: 120,
              render: (row: TeamMembership) => TEAM_ROLE_LABELS[row.role],
            },
            {
              key: 'levelName',
              title: 'Level',
              width: 120,
              render: (row: TeamMembership) => row.levelName,
            },
            {
              key: 'teamStatus',
              title: 'Team Status',
              width: 110,
              render: (row: TeamMembership) => (
                <Badge variant={resolveStatusVariant(row.teamStatus)}>
                  {TEAM_STATUS_LABELS[row.teamStatus]}
                </Badge>
              ),
            },
            {
              key: 'canCreateTask',
              title: 'Can Publish Tasks',
              width: 100,
              render: (row: TeamMembership) => (row.canCreateTask ? 'Yes' : 'No'),
            },
            {
              key: 'joinedAt',
              title: 'Joined At',
              width: 120,
              render: (row: TeamMembership) => formatDate(row.joinedAt),
            },
          ]}
          rows={teams}
          rowKey={(row: TeamMembership) => row.teamId}
          emptyText="Not in a team yet"
        />
      )}
    </div>
  )
}
