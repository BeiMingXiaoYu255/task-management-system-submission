/**
 * 子团队列表：团队详情「子团队」Tab 的主体表格。
 *
 * 仅负责展示与操作入口分发；权限判断由父级通过 canManage/canDelete 传入。
 */

import type { SubTeamItem } from '../../types/collaboration'
import { formatDateTime } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Table, { type TableColumn } from '../ui/Table'
import { getSubTeamRoleLabel } from '../collaboration/collaborationUtils'
import styles from './SubTeamList.module.css'

/** 子团队列表属性。 */
export interface SubTeamListProps {
  /** 子团队数据。 */
  subTeams: SubTeamItem[]
  /** 是否加载中。 */
  loading: boolean
  /** 错误提示。 */
  error: string | null
  /** 是否可创建子团队。 */
  canCreate: boolean
  /** 是否可删除子团队。 */
  canDelete: boolean
  /** 判断当前用户是否可管理某个子团队（编辑/成员维护）。 */
  canManage: (subTeam: SubTeamItem) => boolean
  /** 当前展开任务的子团队 ID。 */
  selectedSubTeamId: number | null
  /** 重新加载回调。 */
  onReload: () => void
  /** 创建回调。 */
  onCreate: () => void
  /** 编辑回调。 */
  onEdit: (subTeam: SubTeamItem) => void
  /** 成员维护回调。 */
  onManageMembers: (subTeam: SubTeamItem) => void
  /** 删除回调。 */
  onDelete: (subTeam: SubTeamItem) => void
  /** 查看子团队任务回调。 */
  onViewTasks: (subTeam: SubTeamItem) => void
}

/** 子团队列表组件。 */
export default function SubTeamList({
  subTeams,
  loading,
  error,
  canCreate,
  canDelete,
  canManage,
  selectedSubTeamId,
  onReload,
  onCreate,
  onEdit,
  onManageMembers,
  onDelete,
  onViewTasks,
}: SubTeamListProps) {
  /** 操作列：按权限渲染按钮。 */
  const renderActions = (subTeam: SubTeamItem) => (
    <div className={styles.actionGroup}>
      <Button variant="ghost" size="small" onClick={() => onViewTasks(subTeam)}>
        {selectedSubTeamId === subTeam.id ? 'Hide Tasks' : 'Sub-team Tasks'}
      </Button>
      {canManage(subTeam) ? (
        <>
          <Button variant="secondary" size="small" onClick={() => onEdit(subTeam)}>
            Edit
          </Button>
          <Button variant="secondary" size="small" onClick={() => onManageMembers(subTeam)}>
            Members
          </Button>
        </>
      ) : null}
      {canDelete ? (
        <Button variant="danger" size="small" onClick={() => onDelete(subTeam)}>
          Delete
        </Button>
      ) : null}
    </div>
  )

  const columns: TableColumn<SubTeamItem>[] = [
    {
      key: 'name',
      title: 'Sub-team',
      render: (subTeam) => (
        <div className={styles.nameCell}>
          <span className={styles.nameText}>{subTeam.name}</span>
          <span className={styles.descriptionText}>
            {subTeam.description ? subTeam.description : 'No description'}
          </span>
        </div>
      ),
    },
    {
      key: 'leader',
      title: 'Sub-team Lead',
      width: 140,
      render: (subTeam) => <span>{subTeam.leaderNickname ?? 'Not assigned'}</span>,
    },
    {
      key: 'memberCount',
      title: 'Members',
      width: 90,
      align: 'center',
      render: (subTeam) => <span>{subTeam.memberCount}</span>,
    },
    {
      key: 'myRole',
      title: 'My Role',
      width: 110,
      align: 'center',
      render: (subTeam) => <Badge variant="outline" size="small">{getSubTeamRoleLabel(subTeam.myRole)}</Badge>,
    },
    {
      key: 'createdAt',
      title: 'Created',
      width: 150,
      render: (subTeam) => <span className={styles.timeText}>{formatDateTime(subTeam.createdAt)}</span>,
    },
    {
      key: 'actions',
      title: 'Actions',
      width: 280,
      render: renderActions,
    },
  ]

  return (
    <section className={styles.listSection}>
      <header className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>Sub-teams ({subTeams.length})</h2>
          <p className={styles.sectionDescription}>
            Team admins can create sub-teams and appoint sub-team leads. Sub-team leads can maintain sub-team info and members.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Button variant="secondary" size="small" onClick={onReload} loading={loading}>
            Refresh
          </Button>
          {canCreate ? <Button onClick={onCreate}>Create Sub-team</Button> : null}
        </div>
      </header>

      {error !== null ? (
        <div className={styles.errorBox}>
          <span>{error}</span>
          <Button variant="secondary" size="small" onClick={onReload}>
            Reload
          </Button>
        </div>
      ) : null}

      <Table
        columns={columns}
        rows={subTeams}
        rowKey={(subTeam) => subTeam.id}
        loading={loading}
        emptyText="No sub-teams yet. Team admins can create sub-teams for internal group collaboration."
      />
    </section>
  )
}
