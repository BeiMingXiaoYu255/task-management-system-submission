/**
 * 团队级别管理：级别列表与新建/编辑/删除。
 *
 * 权限：仅团队管理员可增删改；其他角色看到只读列表与“权限不足”提示，操作按钮隐藏。
 * 删除限制：级别下仍有成员时禁止删除（后端同样会拒绝，前端提前禁用并给出原因）。
 */

import { useEffect, useState } from 'react'

import { createLevel, deleteLevel, updateLevel } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { TeamDetail, TeamLevel } from '../../types/team'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Checkbox from '../ui/Checkbox'
import ConfirmDialog from '../ui/ConfirmDialog'
import Input from '../ui/Input'
import Modal from '../ui/Modal'
import Table from '../ui/Table'
import styles from './LevelManager.module.css'

/** 级别表单数据。 */
interface LevelFormState {
  name: string
  levelOrder: string
  canCreateTask: boolean
}

/** 空表单初始值。 */
const EMPTY_LEVEL_FORM: LevelFormState = { name: '', levelOrder: '', canCreateTask: true }

/** LevelManager 组件属性。 */
export interface LevelManagerProps {
  /** 团队详情。 */
  team: TeamDetail
  /** 数据变化后的刷新回调。 */
  onChanged: () => void
}

/** 级别管理组件。 */
export default function LevelManager({ team, onChanged }: LevelManagerProps) {
  const { showToast } = useToast()
  const [formOpen, setFormOpen] = useState<boolean>(false)
  const [editingLevel, setEditingLevel] = useState<TeamLevel | null>(null)
  const [formState, setFormState] = useState<LevelFormState>(EMPTY_LEVEL_FORM)
  const [formErrors, setFormErrors] = useState<{ name?: string; levelOrder?: string }>({})
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [deleteTarget, setDeleteTarget] = useState<TeamLevel | null>(null)
  const [deleting, setDeleting] = useState<boolean>(false)

  const isAdmin = team.currentUserRole === 'admin'

  /** 打开新建/编辑弹窗时初始化表单。 */
  useEffect(() => {
    if (!formOpen) {
      return
    }
    if (editingLevel) {
      setFormState({
        name: editingLevel.name,
        levelOrder: String(editingLevel.levelOrder),
        canCreateTask: editingLevel.canCreateTask,
      })
    } else {
      setFormState(EMPTY_LEVEL_FORM)
    }
    setFormErrors({})
  }, [formOpen, editingLevel])

  /** 打开新建弹窗。 */
  const openCreateForm = (): void => {
    setEditingLevel(null)
    setFormOpen(true)
  }

  /** 打开编辑弹窗。 */
  const openEditForm = (teamLevel: TeamLevel): void => {
    setEditingLevel(teamLevel)
    setFormOpen(true)
  }

  /** 校验并提交级别表单。 */
  const handleSubmit = async (): Promise<void> => {
    const trimmedName = formState.name.trim()
    const nextErrors: { name?: string; levelOrder?: string } = {}
    if (trimmedName.length < 1 || trimmedName.length > 50) {
      nextErrors.name = 'Level name must be 1-50 characters.'
    }
    const levelOrderValue = Number(formState.levelOrder)
    if (!Number.isInteger(levelOrderValue) || levelOrderValue <= 0) {
      nextErrors.levelOrder = 'Level value must be a positive integer.'
    } else {
      const duplicatedLevel = team.levels.find(
        (teamLevel) =>
          teamLevel.levelOrder === levelOrderValue && teamLevel.id !== editingLevel?.id,
      )
      if (duplicatedLevel) {
        nextErrors.levelOrder = 'Level value must be unique in the team; already used by ' + duplicatedLevel.name + '.'
      }
    }
    setFormErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      return
    }
    setSubmitting(true)
    try {
      const payload = {
        name: trimmedName,
        levelOrder: levelOrderValue,
        canCreateTask: formState.canCreateTask,
      }
      if (editingLevel) {
        await updateLevel(team.id, editingLevel.id, payload)
        showToast('Level updated.', 'success')
      } else {
        await createLevel(team.id, payload)
        showToast('Level created.', 'success')
      }
      setFormOpen(false)
      setEditingLevel(null)
      onChanged()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to save level.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  /** 删除级别。 */
  const handleDelete = async (): Promise<void> => {
    if (deleteTarget === null) {
      return
    }
    setDeleting(true)
    try {
      await deleteLevel(team.id, deleteTarget.id)
      showToast('Level deleted.', 'success')
      setDeleteTarget(null)
      onChanged()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to delete level.'), 'error')
    } finally {
      setDeleting(false)
    }
  }

  /** 表头列定义。 */
  const columns = [
    { key: 'name', title: 'Level Name', render: (teamLevel: TeamLevel) => teamLevel.name },
    {
      key: 'levelOrder',
      title: 'Level Value',
      width: '100px',
      render: (teamLevel: TeamLevel) => String(teamLevel.levelOrder),
    },
    {
      key: 'canCreateTask',
      title: 'Can Publish Tasks',
      width: '120px',
      render: (teamLevel: TeamLevel) => (
        <Badge variant={teamLevel.canCreateTask ? 'default' : 'outline'} size="small">
          {teamLevel.canCreateTask ? 'Allowed' : 'Not allowed'}
        </Badge>
      ),
    },
    {
      key: 'memberCount',
      title: 'Members',
      width: '100px',
      render: (teamLevel: TeamLevel) => String(teamLevel.memberCount),
    },
    {
      key: 'actions',
      title: 'Actions',
      width: '160px',
      render: (teamLevel: TeamLevel) =>
        isAdmin ? (
          <div className={styles.actionRow}>
            <Button variant="secondary" size="small" onClick={() => openEditForm(teamLevel)}>
              Edit
            </Button>
            <Button
              variant="ghost"
              size="small"
              disabled={teamLevel.memberCount > 0}
              title={teamLevel.memberCount > 0 ? 'This level still has members and cannot be deleted.' : undefined}
              onClick={() => setDeleteTarget(teamLevel)}
            >
              Delete
            </Button>
          </div>
        ) : (
          <span className={styles.mutedText}>—</span>
        ),
    },
  ]

  const sortedLevels = [...team.levels].sort(
    (firstLevel, secondLevel) => secondLevel.levelOrder - firstLevel.levelOrder,
  )

  return (
    <section className={styles.levelSection}>
      <header className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>Team Levels</h2>
          <p className={styles.sectionDescription}>
            Higher values mean higher levels. Members at a level that allows publishing can create tasks and assign them only to lower levels.
          </p>
        </div>
        {isAdmin ? (
          <Button onClick={openCreateForm}>Create Level</Button>
        ) : (
          <span className={styles.permissionHint}>Only Team Admins can manage levels</span>
        )}
      </header>

      <Table<TeamLevel>
        columns={columns}
        rows={sortedLevels}
        rowKey={(teamLevel) => teamLevel.id}
        emptyText="No levels yet"
      />

      <Modal
        open={formOpen}
        title={editingLevel ? 'Edit Level' : 'Create Level'}
        size="small"
        onClose={() => {
          if (!submitting) {
            setFormOpen(false)
          }
        }}
        footer={
          <div className={styles.footer}>
            <Button variant="secondary" onClick={() => setFormOpen(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} loading={submitting}>
              Save
            </Button>
          </div>
        }
      >
        <div className={styles.formBody}>
          <Input
            label="Level Name *"
            value={formState.name}
            onChange={(event) =>
              setFormState((previousState) => ({ ...previousState, name: event.target.value }))
            }
            placeholder="e.g. Senior Member"
            error={formErrors.name}
            maxLength={50}
            disabled={submitting}
          />
          <Input
            label="Level Value *"
            type="number"
            value={formState.levelOrder}
            onChange={(event) =>
              setFormState((previousState) => ({ ...previousState, levelOrder: event.target.value }))
            }
            hint="Higher values mean higher levels; must be unique in the team"
            error={formErrors.levelOrder}
            disabled={submitting}
          />
          <Checkbox
            checked={formState.canCreateTask}
            onChange={(event) =>
              setFormState((previousState) => ({
                ...previousState,
                canCreateTask: event.target.checked,
              }))
            }
            label="Members at this level can publish tasks"
            disabled={submitting}
          />
        </div>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete Level"
        description={
          deleteTarget
            ? 'Delete level "' + deleteTarget.name + '"? This cannot be undone.'
            : ''
        }
        confirmText="Delete"
        danger
        loading={deleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => {
          if (!deleting) {
            setDeleteTarget(null)
          }
        }}
      />
    </section>
  )
}
