/**
 * 协作目录面板：展示可申请协作的已认证团队及其子团队，并提供发起协作入口。
 *
 * 目录数据来自 GET /collaboration/directory；加载、错误、空态由父级传入。
 */

import type { CollaborationDirectoryItem } from '../../types/collaboration'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Spinner from '../ui/Spinner'
import styles from './CollaborationDirectoryPanel.module.css'

/** 协作目录面板属性。 */
export interface CollaborationDirectoryPanelProps {
  /** 目录数据。 */
  directory: CollaborationDirectoryItem[]
  /** 是否加载中。 */
  loading: boolean
  /** 错误提示。 */
  error: string | null
  /** 重新加载回调。 */
  onReload: () => void
  /** 发起协作回调（subTeamId 为空表示团队本级）。 */
  onApply: (teamId: number, subTeamId: number | null) => void
}

/** 协作目录面板组件。 */
export default function CollaborationDirectoryPanel({
  directory,
  loading,
  error,
  onReload,
  onApply,
}: CollaborationDirectoryPanelProps) {
  if (error !== null) {
    return (
      <section className={styles.errorBox}>
        <span>{error}</span>
        <Button variant="secondary" size="small" onClick={onReload}>
          Reload
        </Button>
      </section>
    )
  }

  if (loading && directory.length === 0) {
    return (
      <div className={styles.loadingBox}>
        <Spinner size="medium" />
        <span>Loading collaboration directory...</span>
      </div>
    )
  }

  if (directory.length === 0) {
    return (
      <EmptyState
        title="No teams available for collaboration"
        description="Only certified teams appear in the collaboration directory. Contact a global admin to complete team certification."
      />
    )
  }

  return (
    <ul className={styles.directoryList}>
      {directory.map((directoryItem) => (
        <li key={directoryItem.teamId} className={styles.teamCard}>
          <header className={styles.teamHeader}>
            <div>
              <h2 className={styles.teamName}>{directoryItem.teamName}</h2>
              <p className={styles.teamMeta}>
                {directoryItem.memberCount} members · {directoryItem.subTeams.length} sub-teams
              </p>
            </div>
            <Button size="small" onClick={() => onApply(directoryItem.teamId, null)}>
              Start Collaboration
            </Button>
          </header>

          <p className={styles.description}>
            {directoryItem.description ? directoryItem.description : 'No team description'}
          </p>

          {directoryItem.subTeams.length > 0 ? (
            <ul className={styles.subTeamList}>
              {directoryItem.subTeams.map((subTeam) => (
                <li key={subTeam.subTeamId} className={styles.subTeamItem}>
                  <div className={styles.subTeamInfo}>
                    <span className={styles.subTeamName}>{subTeam.name}</span>
                    <span className={styles.subTeamMeta}>
                      {subTeam.memberCount} members · Sub-team Lead:
                      {subTeam.leaderNickname ?? 'Not assigned'}
                    </span>
                  </div>
                  <Button
                    variant="secondary"
                    size="small"
                    onClick={() => onApply(directoryItem.teamId, subTeam.subTeamId)}
                  >
                    Start Collaboration with Sub-team
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.emptyHint}>This team has no sub-teams yet</p>
          )}
        </li>
      ))}
    </ul>
  )
}
