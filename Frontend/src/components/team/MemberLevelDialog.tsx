/**
 * 调整成员级别弹窗。
 *
 * 权限：团队管理员可调整任意成员；子管理员只能调整比自己级别低的普通成员，
 * 因此下拉选项会按当前用户级别过滤，避免提交必然失败的请求。
 */

import { useEffect, useState } from 'react'

import { setMemberLevel } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { TeamDetail, TeamLevel, TeamMemberItem } from '../../types/team'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import Select from '../ui/Select'
import styles from './MemberLevelDialog.module.css'

/** MemberLevelDialog 组件属性。 */
export interface MemberLevelDialogProps {
  /** 弹窗是否打开。 */
  open: boolean
  /** 团队详情。 */
  team: TeamDetail
  /** 要调整级别的成员；为空表示未选择。 */
  member: TeamMemberItem | null
  /** 关闭回调。 */
  onClose: () => void
  /** 保存成功回调（刷新团队详情）。 */
  onSaved: () => void
}

/** 调整成员级别弹窗。 */
export default function MemberLevelDialog({
  open,
  team,
  member,
  onClose,
  onSaved,
}: MemberLevelDialogProps) {
  const { showToast } = useToast()
  const [levelId, setLevelId] = useState<string>('')
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 打开时用成员当前级别初始化。 */
  useEffect(() => {
    if (!open || member === null) {
      return
    }
    setLevelId(String(member.levelId))
  }, [open, member])

  /** 可选级别：子管理员只能选低于自己的级别。 */
  const selectableLevels: TeamLevel[] = [...team.levels]
    .filter((teamLevel) => {
      if (team.currentUserRole === 'admin') {
        return true
      }
      return teamLevel.levelOrder < team.currentUserLevelOrder
    })
    .sort((firstLevel, secondLevel) => secondLevel.levelOrder - firstLevel.levelOrder)

  const levelOptions = selectableLevels.map((teamLevel) => ({
    value: teamLevel.id,
    label: teamLevel.name + ' (Level ' + teamLevel.levelOrder + ')',
  }))

  /** 保存成员级别。 */
  const handleSave = async (): Promise<void> => {
    if (member === null || levelId === '') {
      return
    }
    setSubmitting(true)
    try {
      await setMemberLevel(team.id, member.userId, Number(levelId))
      showToast('Member level updated.', 'success')
      onSaved()
      onClose()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to update level.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      open={open}
      title="Adjust Member Level"
      size="small"
      onClose={() => {
        if (!submitting) {
          onClose()
        }
      }}
      footer={
        <div className={styles.footer}>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={handleSave} loading={submitting}>
            Save
          </Button>
        </div>
      }
    >
      <div className={styles.dialogBody}>
        {member ? (
          <p className={styles.memberInfo}>
            Member: {member.nickname} (@{member.username}) · Current level: {member.levelName}
          </p>
        ) : null}
        <Select
          label="New Level"
          value={levelId}
          onChange={(nextValue) => setLevelId(String(nextValue))}
          options={levelOptions}
          placeholder="Select a level"
          disabled={submitting}
          hint={
            team.currentUserRole === 'subAdmin'
              ? 'Sub-admins can only assign levels below their own.'
              : undefined
          }
        />
      </div>
    </Modal>
  )
}
