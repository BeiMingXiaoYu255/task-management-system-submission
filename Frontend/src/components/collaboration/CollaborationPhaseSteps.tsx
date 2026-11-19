/**
 * 协作任务阶段条：按“待接单 → 执行中 → 接收方审核 → 发起方审核 → 已归档”展示进度。
 *
 * 已拒绝状态不进入流转条，单独展示提示；归档后全部步骤标记为已完成。
 */

import type { CollaborationPhase } from '../../types/task'
import { COLLABORATION_PHASE_STEPS } from './collaborationUtils'
import styles from './CollaborationPhaseSteps.module.css'

/** 协作任务阶段条属性。 */
export interface CollaborationPhaseStepsProps {
  /** 当前协作阶段。 */
  phase: CollaborationPhase | null
  /** 任务是否已归档。 */
  archived: boolean
}

/** 阶段顺序（含归档）。 */
const PHASE_SEQUENCE: { key: string; label: string }[] = [
  ...COLLABORATION_PHASE_STEPS.map((step) => ({ key: step.phase, label: step.label })),
  { key: 'archived', label: 'Archived' },
]

/** 协作任务阶段条组件。 */
export default function CollaborationPhaseSteps({ phase, archived }: CollaborationPhaseStepsProps) {
  const currentIndex = archived
    ? PHASE_SEQUENCE.length - 1
    : phase === null || phase === 'rejected'
      ? -1
      : PHASE_SEQUENCE.findIndex((step) => step.key === phase)

  return (
    <section className={styles.phaseSection}>
      {phase === 'rejected' ? (
        <p className={styles.rejectedHint}>The receiver rejected this collaboration task, so it has been cancelled.</p>
      ) : null}
      <ol className={styles.stepList}>
        {PHASE_SEQUENCE.map((step, index) => {
          const isCompleted = currentIndex >= 0 && index < currentIndex
          const isCurrent = index === currentIndex
          const classNames = [styles.stepItem]
          if (isCompleted) {
            classNames.push(styles.completedStep)
          }
          if (isCurrent) {
            classNames.push(styles.currentStep)
          }
          return (
            <li key={step.key} className={classNames.join(' ')}>
              <span className={styles.stepIndex}>{index + 1}</span>
              <span className={styles.stepLabel}>{step.label}</span>
            </li>
          )
        })}
      </ol>
    </section>
  )
}