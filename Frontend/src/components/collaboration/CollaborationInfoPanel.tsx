/**
 * 协作信息面板：展示协作双方单位、状态、对接人、申请说明与拒绝/结束原因。
 */

import type { CollaborationItem } from '../../types/collaboration'
import { formatDateTime } from '../../utils/formatUtils'
import CollaborationStatusBadge from './CollaborationStatusBadge'
import { formatCollaborationUnit } from './collaborationUtils'
import styles from './CollaborationInfoPanel.module.css'

/** 协作信息面板属性。 */
export interface CollaborationInfoPanelProps {
  /** 协作关系数据。 */
  collaboration: CollaborationItem
}

/** 协作信息面板组件。 */
export default function CollaborationInfoPanel({ collaboration }: CollaborationInfoPanelProps) {
  return (
    <section className={styles.infoPanel}>
      <header className={styles.header}>
        <h2 className={styles.title}>Collaboration Info</h2>
        <CollaborationStatusBadge status={collaboration.status} />
      </header>

      <dl className={styles.infoGrid}>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Initiating Unit</dt>
          <dd className={styles.infoValue}>{formatCollaborationUnit(collaboration.initiatorUnit)}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Receiving Unit</dt>
          <dd className={styles.infoValue}>{formatCollaborationUnit(collaboration.targetUnit)}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Initiator Liaison</dt>
          <dd className={styles.infoValue}>{collaboration.initiatorLiaisonNickname ?? '—'}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Receiver Liaison</dt>
          <dd className={styles.infoValue}>{collaboration.targetLiaisonNickname ?? '—'}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Applicant</dt>
          <dd className={styles.infoValue}>{collaboration.createdByName}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Created</dt>
          <dd className={styles.infoValue}>{formatDateTime(collaboration.createdAt)}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>Updated</dt>
          <dd className={styles.infoValue}>{formatDateTime(collaboration.updatedAt)}</dd>
        </div>
        <div className={styles.infoItem}>
          <dt className={styles.infoLabel}>My Role in Collaboration</dt>
          <dd className={styles.infoValue}>
            {collaboration.myUnitRole === 'initiator'
              ? 'Initiator Member'
              : collaboration.myUnitRole === 'target'
                ? 'Receiver Member'
                : collaboration.myUnitRole === 'both'
                  ? 'Both Parties'
                  : '—'}
          </dd>
        </div>
      </dl>

      <div className={styles.textBlock}>
        <h3 className={styles.blockTitle}>Request Note</h3>
        <p className={styles.blockText}>
          {collaboration.message ? collaboration.message : 'No request note'}
        </p>
      </div>

      {collaboration.rejectComment ? (
        <div className={styles.textBlock}>
          <h3 className={styles.blockTitle}>
            {collaboration.status === 'rejected' ? 'Rejection Reason' : 'End Reason'}
          </h3>
          <p className={styles.dangerText}>{collaboration.rejectComment}</p>
        </div>
      ) : null}
    </section>
  )
}
