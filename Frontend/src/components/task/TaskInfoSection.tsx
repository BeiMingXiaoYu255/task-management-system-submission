/**
 * 任务信息区：任务详情页顶部的基础信息网格与描述。
 *
 * 展示团队、发布者、创建/截止时间、分配方式、接受方式、优先级、状态与逾期标识；
 * 逾期使用危险色文字提示（不使用彩色背景，遵循黑白灰设计语言）。
 */

import type { TaskItem } from '../../types/task'
import { checkOverdue, formatDateTime } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import {
  getCollaborationPhaseLabel,
  resolveTaskSourceTags,
} from '../collaboration/collaborationUtils'
import PriorityBadge from './PriorityBadge'
import StatusBadge from './StatusBadge'
import styles from './TaskInfoSection.module.css'

/** TaskInfoSection 组件属性。 */
export interface TaskInfoSectionProps {
  /** 任务数据。 */
  task: TaskItem
}

/** 任务信息区组件。 */
export default function TaskInfoSection({ task }: TaskInfoSectionProps) {
  const isOverdue =
    checkOverdue(task.dueAt) && task.status !== 'archived' && task.status !== 'cancelled'
  const sourceTags = resolveTaskSourceTags(task)
  const sourceUnitName = task.sourceSubTeamName
    ? (task.sourceTeamName ?? '') + ' / ' + task.sourceSubTeamName
    : task.sourceTeamName
  const targetUnitName = task.targetSubTeamName
    ? (task.targetTeamName ?? '') + ' / ' + task.targetSubTeamName
    : task.targetTeamName
  // 兼容后端尚未返回 v1.1 字段的过渡期数据，避免列表渲染异常
  const requiredSkillNames = task.requiredSkillNames ?? []

  return (
    <section className={styles.infoSection}>
      <div className={styles.badgeRow}>
        <PriorityBadge priority={task.priority} />
        <StatusBadge status={task.status} kind="task" />
        {isOverdue ? <span className={styles.overdueTag}>Overdue</span> : null}
        {sourceTags.map((sourceTag) => (
          <Badge key={sourceTag.key} variant="outline" size="small">
            {sourceTag.label}
          </Badge>
        ))}
        {task.collaborationPhase !== null ? (
          <Badge variant="default" size="small">
            Collaboration stage: {getCollaborationPhaseLabel(task.collaborationPhase)}
          </Badge>
        ) : null}
      </div>

      <dl className={styles.infoGrid}>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Team</dt>
          <dd className={styles.infoValue}>{task.teamName}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Publisher</dt>
          <dd className={styles.infoValue}>{task.createdByName}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Created</dt>
          <dd className={styles.infoValue}>{formatDateTime(task.createdAt)}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Due Date</dt>
          <dd className={isOverdue ? styles.infoValueDanger : styles.infoValue}>
            {formatDateTime(task.dueAt)}
          </dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Assignment Method</dt>
          <dd className={styles.infoValue}>
            {task.assignmentMode === 'specific'
              ? 'Specific Members'
              : 'Level Range ' +
                String(task.targetLevelMin ?? '-') +
                ' ~ ' +
                String(task.targetLevelMax ?? '-')}
          </dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Acceptance Mode</dt>
          <dd className={styles.infoValue}>
            {task.acceptanceMode === 'mandatory' ? 'Mandatory' : 'Optional'}
          </dd>
        </div>
        {task.subTeamId !== null ? (
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Sub-team</dt>
            <dd className={styles.infoValue}>{task.subTeamName ?? '—'}</dd>
          </div>
        ) : null}
        {task.sourceTeamId !== null ? (
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Initiating Unit</dt>
            <dd className={styles.infoValue}>{sourceUnitName ?? '—'}</dd>
          </div>
        ) : null}
        {task.targetTeamId !== null ? (
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Receiving Unit</dt>
            <dd className={styles.infoValue}>{targetUnitName ?? '—'}</dd>
          </div>
        ) : null}
        {task.autoAssigned ? (
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Assignment Source</dt>
            <dd className={styles.infoValue}>AI Auto-assignment</dd>
          </div>
        ) : null}
        {requiredSkillNames.length > 0 ? (
          <div className={styles.infoItem}>
            <dt className={styles.infoLabel}>Required Skills</dt>
            <dd className={styles.infoValue}>{requiredSkillNames.join(', ')}</dd>
          </div>
        ) : null}
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Reviews</dt>
          <dd className={styles.infoValue}>{task.reviewCount} records</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Archived</dt>
          <dd className={styles.infoValue}>{formatDateTime(task.archivedAt)}</dd>
        </div>
      </dl>

      <div className={styles.descriptionBlock}>
        <h3 className={styles.descriptionTitle}>Task Description</h3>
        <p className={styles.descriptionText}>
          {task.description ? task.description : 'No task description.'}
        </p>
      </div>
    </section>
  )
}