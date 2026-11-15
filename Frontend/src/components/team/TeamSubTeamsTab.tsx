/**
 * 团队详情-子团队 Tab：子团队列表、创建/编辑/删除、成员维护与子团队任务入口。
 *
 * 权限：团队管理员可创建/删除/编辑全部子团队；子负责人可编辑自己负责的子团队与维护成员。
 */

import { useState } from 'react'

import { deleteSubTeam, listSubTeams } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import { useAsync } from '../../hooks/useAsync'
import type { SubTeamItem } from '../../types/collaboration'
import type { TeamDetail } from '../../types/team'
import ConfirmDialog from '../ui/ConfirmDialog'
import SubTeamFormDialog from '../subteam/SubTeamFormDialog'
import SubTeamList from '../subteam/SubTeamList'
import SubTeamMembersDialog from '../subteam/SubTeamMembersDialog'
import SubTeamTasksPanel from '../subteam/SubTeamTasksPanel'
import styles from './TeamSubTeamsTab.module.css'

/** TeamSubTeamsTab 组件属性。 */
export interface TeamSubTeamsTabProps {
  /** 团队详情（含当前用户角色与成员）。 */
  team: TeamDetail
}

/** 团队详情-子团队 Tab。 */
export default function TeamSubTeamsTab({ team }: TeamSubTeamsTabProps) {
  const { showToast } = useToast()
  const [formOpen, setFormOpen] = useState<boolean>(false)
  const [editingSubTeam, setEditingSubTeam] = useState<SubTeamItem | null>(null)
  const [membersTarget, setMembersTarget] = useState<SubTeamItem | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<SubTeamItem | null>(null)
  const [selectedSubTeam, setSelectedSubTeam] = useState<SubTeamItem | null>(null)
  const [deleting, setDeleting] = useState<boolean>(false)

  const { data, loading, error, reload } = useAsync<SubTeamItem[]>(
    () => listSubTeams(team.id),
    [team.id],
  )
  const subTeams = data ?? []
  const isTeamAdmin = team.currentUserRole === 'admin'

  /** 判断当前用户是否可管理指定子团队。 */
  const canManageSubTeam = (subTeam: SubTeamItem): boolean =>
    isTeamAdmin || subTeam.myRole === 'admin' || subTeam.myRole === 'leader'

  /** 打开创建弹窗。 */
  const handleCreate = (): void => {
    setEditingSubTeam(null)
    setFormOpen(true)
  }

  /** 打开编辑弹窗。 */
  const handleEdit = (subTeam: SubTeamItem): void => {
    setEditingSubTeam(subTeam)
    setFormOpen(true)
  }

  /** 子团队保存成功。 */
  const handleSaved = (): void => {
    setFormOpen(false)
    setEditingSubTeam(null)
    showToast('Sub-team saved.', 'success')
    reload()
  }

  /** 成员保存成功。 */
  const handleMembersSaved = (): void => {
    setMembersTarget(null)
    showToast('Sub-team members updated.', 'success')
    reload()
  }

  /** 确认删除子团队。 */
  const handleConfirmDelete = async (): Promise<void> => {
    if (deleteTarget === null) {
      return
    }
    setDeleting(true)
    try {
      await deleteSubTeam(team.id, deleteTarget.id)
      showToast('Sub-team deleted.', 'success')
      if (selectedSubTeam?.id === deleteTarget.id) {
        setSelectedSubTeam(null)
      }
      setDeleteTarget(null)
      reload()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to delete sub-team. Please try again.'), 'error')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className={styles.tabBody}>
      <SubTeamList
        subTeams={subTeams}
        loading={loading}
        error={error}
        canCreate={isTeamAdmin}
        canDelete={isTeamAdmin}
        canManage={canManageSubTeam}
        selectedSubTeamId={selectedSubTeam?.id ?? null}
        onReload={reload}
        onCreate={handleCreate}
        onEdit={handleEdit}
        onManageMembers={setMembersTarget}
        onDelete={setDeleteTarget}
        onViewTasks={(subTeam) =>
          setSelectedSubTeam((previousSubTeam) =>
            previousSubTeam?.id === subTeam.id ? null : subTeam,
          )
        }
      />

      {selectedSubTeam !== null ? (
        <SubTeamTasksPanel
          teamId={team.id}
          subTeam={selectedSubTeam}
          onClose={() => setSelectedSubTeam(null)}
        />
      ) : null}

      {formOpen ? (
        <SubTeamFormDialog
          open
          team={team}
          subTeam={editingSubTeam}
          onClose={() => {
            setFormOpen(false)
            setEditingSubTeam(null)
          }}
          onSaved={handleSaved}
        />
      ) : null}

      {membersTarget !== null ? (
        <SubTeamMembersDialog
          open
          team={team}
          subTeam={membersTarget}
          onClose={() => setMembersTarget(null)}
          onSaved={handleMembersSaved}
        />
      ) : null}

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete Sub-team"
        description={
          'Delete sub-team ' + (deleteTarget?.name ?? '') + '? Its tasks will be kept and become team-level tasks.'
        }
        confirmText="Confirm Delete"
        danger
        loading={deleting}
        onConfirm={() => void handleConfirmDelete()}
        onCancel={() => {
          if (!deleting) {
            setDeleteTarget(null)
          }
        }}
      />
    </div>
  )
}