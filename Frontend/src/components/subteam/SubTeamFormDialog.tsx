/**
 * 子团队表单弹窗：创建子团队（名称/简介/子负责人/初始成员）或编辑子团队信息。
 *
 * 权限约束：仅团队管理员可任命子负责人；子负责人可编辑名称与简介。
 */

import { useEffect, useState } from 'react'

import { createSubTeam, updateSubTeam } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { SubTeamDetail, SubTeamItem } from '../../types/collaboration'
import type { TeamDetail } from '../../types/team'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Modal from '../ui/Modal'
import Select from '../ui/Select'
import Textarea from '../ui/Textarea'
import UnitMemberPicker, { type PickableMember } from '../collaboration/UnitMemberPicker'
import styles from './SubTeamFormDialog.module.css'

/** 子团队表单弹窗属性。 */
export interface SubTeamFormDialogProps {
  /** 是否打开。 */
  open: boolean
  /** 父团队详情（提供成员与当前用户角色）。 */
  team: TeamDetail
  /** 编辑对象；为空表示创建。 */
  subTeam: SubTeamItem | null
  /** 关闭回调。 */
  onClose: () => void
  /** 保存成功回调。 */
  onSaved: (subTeam: SubTeamDetail) => void
}

/** 子团队表单弹窗。 */
export default function SubTeamFormDialog({
  open,
  team,
  subTeam,
  onClose,
  onSaved,
}: SubTeamFormDialogProps) {
  const { showToast } = useToast()
  const isEditMode = subTeam !== null
  const isTeamAdmin = team.currentUserRole === 'admin'

  const [name, setName] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [leaderUserId, setLeaderUserId] = useState<number>(0)
  const [memberUserIds, setMemberUserIds] = useState<number[]>([])
  const [nameError, setNameError] = useState<string | undefined>(undefined)
  const [leaderError, setLeaderError] = useState<string | undefined>(undefined)
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 打开弹窗时初始化表单。 */
  useEffect(() => {
    if (!open) {
      return
    }
    setName(subTeam?.name ?? '')
    setDescription(subTeam?.description ?? '')
    setLeaderUserId(subTeam?.leaderUserId ?? 0)
    setMemberUserIds([])
    setNameError(undefined)
    setLeaderError(undefined)
  }, [open, subTeam])

  if (!open) {
    return null
  }

  /** 成员候选（父团队全体成员）。 */
  const candidates: PickableMember[] = team.members.map((member) => ({
    userId: member.userId,
    username: member.username,
    nickname: member.nickname,
    avatar: member.avatar,
    levelName: member.levelName,
  }))

  /** 子负责人选项。 */
  const leaderOptions = [
    { value: 0, label: 'Not assigned' },
    ...team.members.map((member) => ({
      value: member.userId,
      label: member.nickname + ' (' + member.username + ')',
    })),
  ]

  /** 提交表单。 */
  const handleSubmit = async (): Promise<void> => {
    const trimmedName = name.trim()
    let hasError = false
    if (trimmedName.length < 2 || trimmedName.length > 100) {
      setNameError('Sub-team name must be 2-100 characters')
      hasError = true
    }
    if (!isEditMode && leaderUserId <= 0) {
      setLeaderError('Select a sub-team lead when creating a sub-team')
      hasError = true
    }
    if (hasError) {
      return
    }
    setSubmitting(true)
    try {
      const trimmedDescription = description.trim()
      let saved: SubTeamDetail
      if (isEditMode) {
        saved = await updateSubTeam(team.id, subTeam.id, {
          name: trimmedName,
          description: trimmedDescription === '' ? null : trimmedDescription,
          ...(isTeamAdmin ? { leaderUserId: leaderUserId > 0 ? leaderUserId : null } : {}),
        })
      } else {
        const initialMemberIds =
          leaderUserId > 0 && !memberUserIds.includes(leaderUserId)
            ? [...memberUserIds, leaderUserId]
            : memberUserIds
        saved = await createSubTeam(team.id, {
          name: trimmedName,
          description: trimmedDescription === '' ? null : trimmedDescription,
          leaderUserId: leaderUserId > 0 ? leaderUserId : null,
          memberUserIds: initialMemberIds,
        })
      }
      onSaved(saved)
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to save the sub-team. Please try again.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const footer = (
    <div className={styles.footer}>
      <Button variant="secondary" onClick={onClose} disabled={submitting}>
        Cancel
      </Button>
      <Button onClick={() => void handleSubmit()} loading={submitting}>
        {isEditMode ? 'Save Changes' : 'Create Sub-team'}
      </Button>
    </div>
  )

  return (
    <Modal
      open={open}
      title={isEditMode ? 'Edit Sub-team' : 'Create Sub-team'}
      size="large"
      footer={footer}
      onClose={() => {
        if (!submitting) {
          onClose()
        }
      }}
    >
      <div className={styles.body}>
        <p className={styles.teamHint}>Parent team: {team.name}</p>
        <Input
          label="Sub-team Name"
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            setNameError(undefined)
          }}
          placeholder="Enter a sub-team name (2-100 characters)"
          maxLength={100}
          error={nameError}
          disabled={submitting}
          autoFocus
        />
        <Textarea
          label="Description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
          maxLength={500}
          placeholder="Briefly describe the sub-team responsibilities and scope (optional)"
          disabled={submitting}
        />
        <Select
          label="Sub-team Lead"
          value={leaderUserId}
          onChange={(value) => {
            setLeaderUserId(Number(value))
            setLeaderError(undefined)
          }}
          options={leaderOptions}
          disabled={submitting || (isEditMode && !isTeamAdmin)}
          error={leaderError}
          hint={
            isEditMode && !isTeamAdmin
              ? 'Only team admins can change the sub-team lead'
              : 'The sub-team lead must be a member of the parent team'
          }
        />
        {!isEditMode ? (
          <UnitMemberPicker
            label="Initial Members (multi-select)"
            members={candidates}
            selectedUserIds={memberUserIds}
            onChange={setMemberUserIds}
            disabled={submitting}
            emptyText="No parent team members available"
            hint="Members can be adjusted later in member management"
          />
        ) : (
          <p className={styles.hintText}>Use the "Members" action in the list to manage members.</p>
        )}
      </div>
    </Modal>
  )
}
