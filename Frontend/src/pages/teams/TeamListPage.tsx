/**
 * 团队列表页：展示我创建/加入的团队，支持创建团队、邀请码加入与申请加入。
 *
 * 数据流：
 * 1. GET /teams 拉取我可见的团队（含自己创建但待认证的团队）；
 * 2. 从 AuthContext 的团队身份列表中匹配角色/级别展示在卡片上；
 * 3. 创建或加入成功后同时刷新团队列表与当前用户身份，保证卡片角色信息即时更新。
 */

import { useCallback, useMemo, useState } from 'react'

import { listMyTeams } from '../../api/teamApi'
import { useAuth } from '../../context/AuthContext'
import { useAsync } from '../../hooks/useAsync'
import type { TeamMembership } from '../../types/auth'
import type { TeamDetail } from '../../types/team'
import Button from '../../components/ui/Button'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import CreateTeamDialog from '../../components/team/CreateTeamDialog'
import JoinTeamDialog from '../../components/team/JoinTeamDialog'
import TeamCard from '../../components/team/TeamCard'
import styles from './TeamListPage.module.css'

/** 团队列表页。 */
export default function TeamListPage() {
  const { user, refreshMe } = useAuth()
  const [createDialogOpen, setCreateDialogOpen] = useState<boolean>(false)
  const [joinDialogOpen, setJoinDialogOpen] = useState<boolean>(false)

  /** 拉取我加入的团队列表。 */
  const loadTeams = useCallback(() => listMyTeams(), [])
  const { data, loading, error, reload } = useAsync(loadTeams, [loadTeams])
  const teams = data ?? []

  /** 团队 ID → 当前用户身份映射，用于卡片展示角色与级别。 */
  const membershipMap = useMemo(() => {
    const nextMembershipMap = new Map<number, TeamMembership>()
    user?.teams.forEach((membership) => {
      nextMembershipMap.set(membership.teamId, membership)
    })
    return nextMembershipMap
  }, [user])

  const pendingTeamCount = teams.filter((team) => team.status === 'pending').length

  /** 创建/加入成功后刷新团队列表与当前用户身份。 */
  const handleDataChanged = (): void => {
    reload()
    void refreshMe().catch(() => undefined)
  }

  /** 创建成功回调（忽略新建团队参数，统一刷新）。 */
  const handleTeamCreated = (_createdTeam: TeamDetail): void => {
    handleDataChanged()
  }

  return (
    <div className="page-container">
      <PageHeader
        title="My Teams"
        description="Manage the teams you created or joined, then collaborate on tasks and members."
        actions={
          <div className={styles.headerActions}>
            <Button variant="secondary" onClick={reload} loading={loading}>
              Refresh
            </Button>
            <Button variant="secondary" onClick={() => setJoinDialogOpen(true)}>
              Join with Invite Code
            </Button>
            <Button onClick={() => setCreateDialogOpen(true)}>Create Team</Button>
          </div>
        }
      />

      {pendingTeamCount > 0 ? (
        <div className={styles.noticeBar} role="status">
          Pending teams: {pendingTeamCount}. Invite members after certification.
        </div>
      ) : null}

      {error ? (
        <section className={styles.errorBox}>
          <span>{error}</span>
          <Button variant="secondary" size="small" onClick={reload}>
            Reload
          </Button>
        </section>
      ) : loading && teams.length === 0 ? (
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading teams...</span>
        </div>
      ) : teams.length === 0 ? (
        <EmptyState
          title="No teams yet"
          description="Create a team to start collaborating, or join an existing team with an invite code."
          action={
            <div className={styles.emptyActions}>
              <Button onClick={() => setCreateDialogOpen(true)}>Create Team</Button>
              <Button variant="secondary" onClick={() => setJoinDialogOpen(true)}>
                Join with Invite Code
              </Button>
            </div>
          }
        />
      ) : (
        <ul className={styles.teamGrid}>
          {teams.map((team) => (
            <li key={team.id}>
              <TeamCard team={team} membership={membershipMap.get(team.id) ?? null} />
            </li>
          ))}
        </ul>
      )}

      <CreateTeamDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onCreated={handleTeamCreated}
      />
      <JoinTeamDialog
        open={joinDialogOpen}
        onClose={() => setJoinDialogOpen(false)}
        onJoined={handleDataChanged}
      />
    </div>
  )
}
