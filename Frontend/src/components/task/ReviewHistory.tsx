/**
 * 审核历史：按时间倒序展示任务全部审核记录（通过/驳回、审核人、意见、时间）。
 */

import type { ReviewRecord } from '../../types/task'
import { formatDateTime } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import styles from './ReviewHistory.module.css'

/** ReviewHistory 组件属性。 */
export interface ReviewHistoryProps {
  /** 审核记录列表。 */
  reviews: ReviewRecord[]
}

/** 审核历史组件。 */
export default function ReviewHistory({ reviews }: ReviewHistoryProps) {
  const sortedReviews = [...reviews].sort((firstReview, secondReview) =>
    firstReview.createdAt < secondReview.createdAt ? 1 : -1,
  )

  return (
    <section className={styles.historySection}>
      <header className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>Review History</h3>
        <span className={styles.sectionHint}>{sortedReviews.length} records</span>
      </header>
      {sortedReviews.length === 0 ? (
        <p className={styles.emptyHint}>No review records yet.</p>
      ) : (
        <ul className={styles.historyList}>
          {sortedReviews.map((reviewRecord) => (
            <li key={reviewRecord.id} className={styles.historyItem}>
              <div className={styles.itemHeader}>
                <Badge variant={reviewRecord.result === 'approved' ? 'default' : 'outline'} size="small">
                  {reviewRecord.result === 'approved' ? 'Approved' : 'Rejected'}
                </Badge>
                <span className={styles.reviewerName}>{reviewRecord.reviewerName}</span>
                <span className={styles.reviewTime}>{formatDateTime(reviewRecord.createdAt)}</span>
              </div>
              {reviewRecord.comment ? (
                <p className={styles.reviewComment}>{reviewRecord.comment}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
