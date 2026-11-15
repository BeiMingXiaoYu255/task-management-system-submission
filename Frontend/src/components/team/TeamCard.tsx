/**
 * 团队卡片：团队列表页展示团队基础信息、认证状态、我的角色与级别。
 *
 * data 来源：GET /teams 返回 TeamBrief + AuthContext 中当前用户的团队身份（membership）。
 * 待认证团队（pending）仅创建者可见且不能邀请他人，因此卡片上给出醒目文字提示。
 */

import { Link } from 'react-router-dom'

import type { TeamBrief } from '../../types/team'
import type { TeamMembership } from '../../types/auth'
import { JOIN_METHOD_LABELS, TEAM_ROLE_LABELS, TEAM_STATUS_LABELS } from '../../utils/displayUtils'
import { formatDate } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import Card from '../ui/Card'
import styles from './TeamCard.module.css'

/** TeamCard 组件属性。 */
export interface TeamCardProps {
  /** 团队简要信息。 */
  team: TeamBrief
  /** 当前用户在该团队中的身份；缺省表示未加入。 */
  membership?: TeamMembership | null
}

/** 团队认证状态对应的徽标变体。 */
function resolveStatusBadgeVariant(status: TeamBrief['status']): 'default' | 'outline' | 'solid' {
  if (status === 'active') {
    return 'solid'
  }
  if (status === 'rejected') {
    return 'outline'
  }
  return 'default'
}

/** 团队卡片组件。 */
export default function TeamCard({ team, membership = null }: TeamCardProps) {
  return (
    <Card
      className={styles.teamCard}
      title={<span className={styles.teamName}>{team.name}</span>}
      actions={
        <Badge variant={resolveStatusBadgeVariant(team.status)} size="small">
          {TEAM_STATUS_LABELS[team.status]}
        </Badge>
      }
    >
      <div className={styles.cardBody}>
        <p className={team.description ? styles.description : styles.descriptionEmpty}>
          {team.description ? team.description : 'No description yet.'}
        </p>

        {team.status === 'pending' ? (
          <p className={styles.pendingHint}>
            Team pending certification: members can be invited after Global Admin approval.
          </p>
        ) : null}
        {team.status === 'rejected' ? (
          <p className={styles.rejectedHint}>Team certification was rejected. Contact a Global Admin.</p>
        ) : null}

        <div className={styles.metaRow}>
          <span className={styles.metaItem}>{team.memberCount}  members</span>
          <span className={styles.metaItem}>{JOIN_METHOD_LABELS[team.joinMethod]}</span>
          <span className={styles.metaItem}>Created {formatDate(team.createdAt)}</span>
        </div>

        <div className={styles.metaRow}>
          {membership ? (
            <>
              <span className={styles.roleTag}>{TEAM_ROLE_LABELS[membership.role]}</span>
              <span className={styles.metaItem}>Level: {membership.levelName}</span>
              <span className={styles.metaItem}>
                {membership.canCreateTask ? 'Can publish tasks' : 'Cannot publish tasks'}
              </span>
            </>
          ) : (
            <span className={styles.metaItemMuted}>You have not joined this team yet.</span>
          )}
        </div>

        <div className={styles.cardFooter}>
          <Link to={'/teams/' + team.id} className={styles.detailLink}>
            Enter Team →
          </Link>
        </div>
      </div>
    </Card>
  )
}
