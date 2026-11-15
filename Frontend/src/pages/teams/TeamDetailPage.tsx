/**
 * 团队详情页：内部七个 Tab（概览/任务/子团队/协作/成员/级别/设置）。
 *
 * 数据流：页面统一加载一次 TeamDetail，各 Tab 共享同一份数据；
 * 成员/级别/设置等操作成功后调用 reload 重新拉取团队详情，保证各 Tab 数据一致。
 * 权限不足时不做路由级拦截（普通成员可查看只读信息），由各 Tab 内部禁用操作。
 */

import { useCallback, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { getTeam } from '../../api/teamApi'
import { useAuth } from '../../context/AuthContext'
import { useAsync } from '../../hooks/useAsync'
import type { TeamDetail } from '../../types/team'
import { TEAM_STATUS_LABELS } from '../../utils/displayUtils'
import Button from '../../components/ui/Button'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import Tabs from '../../components/ui/Tabs'
import TeamCollaborationsTab from '../../components/team/TeamCollaborationsTab'
import TeamLevelsTab from '../../components/team/TeamLevelsTab'
import TeamMembersTab from '../../components/team/TeamMembersTab'
import TeamOverviewTab from '../../components/team/TeamOverviewTab'
import TeamSettingsTab from '../../components/team/TeamSettingsTab'
import TeamSubTeamsTab from '../../components/team/TeamSubTeamsTab'
import TeamTasksTab from '../../components/team/TeamTasksTab'
import styles from './TeamDetailPage.module.css'

/** 团队详情页 Tab 键。 */
type TeamTabKey =
  | 'overview'
  | 'tasks'
  | 'subteams'
  | 'collaborations'
  | 'members'
  | 'levels'
  | 'settings'

/** Tab 配置。 */
const TEAM_TAB_ITEMS: { key: TeamTabKey; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'tasks', label: 'Tasks' },
  { key: 'subteams', label: 'Sub-teams' },
  { key: 'collaborations', label: 'Collaborations' },
  { key: 'members', label: 'Members' },
  { key: 'levels', label: 'Levels' },
  { key: 'settings', label: 'Settings' },
]

/** 团队详情页。 */
export default function TeamDetailPage() {
  const { teamId } = useParams<{ teamId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<TeamTabKey>('overview')
  const parsedTeamId = Number(teamId)

  /** 加载团队详情：先校验路由参数，避免发出无效请求。 */
  const loadTeam = useCallback((): Promise<TeamDetail> => {
    if (!Number.isInteger(parsedTeamId) || parsedTeamId <= 0) {
      return Promise.reject(new Error('Invalid team ID'))
    }
    return getTeam(parsedTeamId)
  }, [parsedTeamId])

  const { data: team, loading, error, reload } = useAsync(loadTeam, [loadTeam])
  const currentUserId = user?.user.id ?? 0

  /** 返回团队列表。 */
  const handleBackToList = (): void => {
    navigate('/teams')
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading team info...</span>
        </div>
      </div>
    )
  }

  if (error !== null || team === null) {
    return (
      <div className="page-container">
        <EmptyState
          title="Unable to access this team"
          description={error ?? 'The team does not exist or you do not have access.'}
          action={<Button onClick={handleBackToList}>Back to Teams</Button>}
        />
      </div>
    )
  }

  return (
    <div className="page-container">
      <nav className={styles.breadcrumb} aria-label="Breadcrumb">
        <Link to="/teams" className={styles.breadcrumbLink}>
          ← Back to Teams
        </Link>
      </nav>

      <PageHeader
        title={team.name}
        description={
          TEAM_STATUS_LABELS[team.status] + ' · ' + team.memberCount + ' members · My role: ' +
          (team.currentUserRole === 'admin'
            ? 'Team Admin'
            : team.currentUserRole === 'subAdmin'
              ? 'Sub-admin'
              : 'Member')
        }
        actions={
          <Button variant="secondary" onClick={reload} loading={loading}>
            Refresh
          </Button>
        }
      />

      <Tabs
        items={TEAM_TAB_ITEMS}
        activeKey={activeTab}
        onChange={(nextKey) => setActiveTab(nextKey as TeamTabKey)}
      />

      <div className={styles.tabContent}>
        {activeTab === 'overview' ? <TeamOverviewTab team={team} /> : null}
        {activeTab === 'tasks' ? <TeamTasksTab team={team} /> : null}
        {activeTab === 'subteams' ? <TeamSubTeamsTab team={team} /> : null}
        {activeTab === 'collaborations' ? <TeamCollaborationsTab team={team} /> : null}
        {activeTab === 'members' ? (
          <TeamMembersTab team={team} currentUserId={currentUserId} onChanged={reload} />
        ) : null}
        {activeTab === 'levels' ? <TeamLevelsTab team={team} onChanged={reload} /> : null}
        {activeTab === 'settings' ? (
          <TeamSettingsTab team={team} onChanged={reload} onDissolved={handleBackToList} />
        ) : null}
      </div>
    </div>
  )
}