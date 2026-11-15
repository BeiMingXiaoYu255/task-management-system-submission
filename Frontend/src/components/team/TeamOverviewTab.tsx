/**
 * 团队详情-概览 Tab：展示团队基本信息、我的身份与权限、级别概览。
 *
 * 数据完全来自父级已加载的 TeamDetail，本组件为纯展示组件，不发请求。
 */

import type { TeamDetail } from '../../types/team'
import { JOIN_METHOD_LABELS, TEAM_ROLE_LABELS, TEAM_STATUS_LABELS } from '../../utils/displayUtils'
import { formatDateTime } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import styles from './TeamOverviewTab.module.css'

/** TeamOverviewTab 组件属性。 */
export interface TeamOverviewTabProps {
  /** 团队详情。 */
  team: TeamDetail
}

/** 团队详情-概览 Tab。 */
export default function TeamOverviewTab({ team }: TeamOverviewTabProps) {
  const sortedLevels = [...team.levels].sort(
    (firstLevel, secondLevel) => secondLevel.levelOrder - firstLevel.levelOrder,
  )
  const isManager = team.currentUserRole === 'admin' || team.currentUserRole === 'subAdmin'
  const currentLevel = sortedLevels.find(
    (teamLevel) => teamLevel.levelOrder === team.currentUserLevelOrder,
  )
  const canCreateTask = isManager || (currentLevel?.canCreateTask === true)

  return (
    <div className={styles.overview}>
      {team.status === 'pending' ? (
        <p className={styles.pendingHint}>
          This team is pending certification: members cannot be invited until certification, but existing members can collaborate normally.
        </p>
      ) : null}
      {team.status === 'rejected' ? (
        <p className={styles.rejectedHint}>Team certification was rejected. Contact a Global Admin to resubmit for review.</p>
      ) : null}

      <section className={styles.infoSection}>
        <h2 className={styles.sectionTitle}>Team Information</h2>
        <dl className={styles.infoGrid}>
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Team Name</dt>
            <dd className={styles.infoValue}>{team.name}</dd>
          </div>
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Certification Status</dt>
            <dd className={styles.infoValue}>
              <Badge variant={team.status === 'active' ? 'solid' : 'outline'} size="small">
                {TEAM_STATUS_LABELS[team.status]}
              </Badge>
            </dd>
          </div>
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Join Method</dt>
            <dd className={styles.infoValue}>{JOIN_METHOD_LABELS[team.joinMethod]}</dd>
          </div>
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Members</dt>
            <dd className={styles.infoValue}>{team.memberCount} members</dd>
          </div>
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Created</dt>
            <dd className={styles.infoValue}>{formatDateTime(team.createdAt)}</dd>
          </div>
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>My Role</dt>
            <dd className={styles.infoValue}>{TEAM_ROLE_LABELS[team.currentUserRole]}</dd>
          </div>
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>My Level</dt>
            <dd className={styles.infoValue}>
              {currentLevel ? currentLevel.name + ' (Level ' + currentLevel.levelOrder + ')' : '—'}
            </dd>
          </div>
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Task Publishing</dt>
            <dd className={styles.infoValue}>{canCreateTask ? 'Allowed' : 'Not allowed'}</dd>
          </div>
          {isManager ? (
            <div className={styles.infoItem}>
              <dt className={styles.infoLabel}>Invite Code</dt>
              <dd className={styles.infoValue}>{team.inviteCode ?? 'Not generated'}</dd>
            </div>
          ) : null}
        </dl>
        <div className={styles.descriptionBlock}>
          <h3 className={styles.descriptionTitle}>Team Description</h3>
          <p className={styles.descriptionText}>
            {team.description ? team.description : 'No description yet.'}
          </p>
        </div>
      </section>

      <section className={styles.infoSection}>
        <h2 className={styles.sectionTitle}>My Permissions</h2>
        <ul className={styles.permissionList}>
          <li className={styles.permissionItem}>
            <span className={styles.permissionName}>Team Role</span>
            <span className={styles.permissionValue}>{TEAM_ROLE_LABELS[team.currentUserRole]}</span>
          </li>
          <li className={styles.permissionItem}>
            <span className={styles.permissionName}>Publish Tasks</span>
            <span className={styles.permissionValue}>{canCreateTask ? 'Allowed' : 'Not allowed'}</span>
          </li>
          <li className={styles.permissionItem}>
            <span className={styles.permissionName}>Review Join Requests</span>
            <span className={styles.permissionValue}>{isManager ? 'Allowed' : 'Not allowed'}</span>
          </li>
          <li className={styles.permissionItem}>
            <span className={styles.permissionName}>Manage Team Levels</span>
            <span className={styles.permissionValue}>
              {team.currentUserRole === 'admin' ? 'Allowed' : 'Not allowed'}
            </span>
          </li>
          <li className={styles.permissionItem}>
            <span className={styles.permissionName}>Adjust Member Levels</span>
            <span className={styles.permissionValue}>{isManager ? 'Allowed' : 'Not allowed'}</span>
          </li>
        </ul>
      </section>

      <section className={styles.infoSection}>
        <h2 className={styles.sectionTitle}>Level Overview</h2>
        <ul className={styles.levelList}>
          {sortedLevels.map((teamLevel) => (
            <li key={teamLevel.id} className={styles.levelItem}>
              <span className={styles.levelName}>{teamLevel.name}</span>
              <span className={styles.levelMeta}>
                Level {teamLevel.levelOrder} · {teamLevel.memberCount} members ·{' '}
                {teamLevel.canCreateTask ? 'Allowed' : 'Not allowed'}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
