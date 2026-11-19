/**
 * 协作关系卡片：协作中心/团队协作 Tab 共用的展示单元。
 *
 * 展示发起方与接收方单位、状态、双方对接人、申请说明与拒绝原因；
 * 按钮显隐完全由后端返回的 canConfirm / canEnd 权限标记决定。
 */

import { Link } from 'react-router-dom'

import type { CollaborationItem } from '../../types/collaboration'
import { formatDateTime } from '../../utils/formatUtils'
import Button from '../ui/Button'
import CollaborationStatusBadge from './CollaborationStatusBadge'
import { formatCollaborationUnit } from './collaborationUtils'
import styles from './CollaborationCard.module.css'

/** 协作关系卡片属性。 */
export interface CollaborationCardProps {
  /** 协作关系数据。 */
  collaboration: CollaborationItem
  /** 接收方确认/拒绝入口；不传则不展示按钮。 */
  onConfirm?: (collaboration: CollaborationItem) => void
  /** 结束协作入口；不传则不展示按钮。 */
  onEnd?: (collaboration: CollaborationItem) => void
}

/** 协作关系卡片组件。 */
export default function CollaborationCard({
  collaboration,
  onConfirm,
  onEnd,
}: CollaborationCardProps) {
  return (
    <article className={styles.collaborationCard}>
      <header className={styles.cardHeader}>
        <h3 className={styles.unitTitle}>
          <span className={styles.unitName}>{formatCollaborationUnit(collaboration.initiatorUnit)}</span>
          <span className={styles.arrow} aria-hidden="true">
            →
          </span>
          <span className={styles.unitName}>{formatCollaborationUnit(collaboration.targetUnit)}</span>
        </h3>
        <CollaborationStatusBadge status={collaboration.status} />
      </header>

      <div className={styles.metaRow}>
        <span className={styles.metaItem}>Applicant: {collaboration.createdByName}</span>
        <span className={styles.metaItem}>Created: {formatDateTime(collaboration.createdAt)}</span>
        <span className={styles.metaItem}>
          Initiator liaison: {collaboration.initiatorLiaisonNickname ?? '—'}
        </span>
        <span className={styles.metaItem}>
          Receiver liaison: {collaboration.targetLiaisonNickname ?? '—'}
        </span>
      </div>

      {collaboration.message ? (
        <p className={styles.messageText}>Request note: {collaboration.message}</p>
      ) : null}
      {collaboration.rejectComment ? (
        <p className={collaboration.status === 'rejected' ? styles.rejectText : styles.commentText}>
          {collaboration.status === 'rejected' ? 'Rejection reason: ' : 'End reason: '}
          {collaboration.rejectComment}
        </p>
      ) : null}

      <footer className={styles.cardFooter}>
        {collaboration.canConfirm && onConfirm ? (
          <Button size="small" onClick={() => onConfirm(collaboration)}>
            Confirm Request
          </Button>
        ) : null}
        {collaboration.canEnd && onEnd ? (
          <Button variant="danger" size="small" onClick={() => onEnd(collaboration)}>
            End Collaboration
          </Button>
        ) : null}
        <Link to={'/collaborations/' + String(collaboration.id)} className={styles.detailLink}>
          View collaboration details →
        </Link>
      </footer>
    </article>
  )
}
