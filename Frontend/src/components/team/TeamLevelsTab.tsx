/**
 * 团队详情-级别 Tab：包装级别管理组件，保留 Tab 层职责单一。
 */

import type { TeamDetail } from '../../types/team'
import LevelManager from './LevelManager'
import styles from './TeamLevelsTab.module.css'

/** TeamLevelsTab 组件属性。 */
export interface TeamLevelsTabProps {
  /** 团队详情。 */
  team: TeamDetail
  /** 数据变化后的刷新回调。 */
  onChanged: () => void
}

/** 团队详情-级别 Tab。 */
export default function TeamLevelsTab({ team, onChanged }: TeamLevelsTabProps) {
  return (
    <div className={styles.levelsTab}>
      <LevelManager team={team} onChanged={onChanged} />
    </div>
  )
}
