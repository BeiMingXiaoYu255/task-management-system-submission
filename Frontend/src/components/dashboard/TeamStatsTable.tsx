/**
 * 团队维度统计表格：展示每个团队的成员数、未完成任务数与已归档任务数。
 * 纯展示组件，表格列定义使用 components/ui/Table 契约 API。
 */

import type { TeamStatItem } from '../../types/dashboard'
import Card from '../ui/Card'
import EmptyState from '../ui/EmptyState'
import Table from '../ui/Table'
import styles from './TeamStatsTable.module.css'

/** 团队统计表格属性。 */
interface TeamStatsTableProps {
  teamStats: TeamStatItem[]
}

/** 团队维度统计卡片。 */
export default function TeamStatsTable({ teamStats }: TeamStatsTableProps) {
  return (
    <Card title="Team Statistics">
      {teamStats.length === 0 ? (
        <EmptyState
          title="No team statistics yet"
          description="Join a team and create tasks to see each team's output here."
        />
      ) : (
        <Table
          columns={[
            {
              key: 'teamName',
              title: 'Team',
              render: (row: TeamStatItem) => (
                <span className={styles.teamName}>{row.teamName}</span>
              ),
            },
            {
              key: 'memberCount',
              title: 'Members',
              width: 100,
              align: 'right',
              render: (row: TeamStatItem) => row.memberCount,
            },
            {
              key: 'openTaskCount',
              title: 'Open Tasks',
              width: 120,
              align: 'right',
              render: (row: TeamStatItem) => row.openTaskCount,
            },
            {
              key: 'archivedTaskCount',
              title: 'Archived Tasks',
              width: 120,
              align: 'right',
              render: (row: TeamStatItem) => row.archivedTaskCount,
            },
          ]}
          rows={teamStats}
          rowKey={(row: TeamStatItem) => row.teamId}
          emptyText="No team data yet"
        />
      )}
    </Card>
  )
}
