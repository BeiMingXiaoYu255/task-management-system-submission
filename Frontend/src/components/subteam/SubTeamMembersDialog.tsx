/**
 * 子团队成员维护弹窗：以父团队成员为候选，覆盖式设置子团队成员。
 *
 * 约束：子负责人必须是子团队成员；成员必须是父团队成员。
 */

import { useEffect, useState } from 'react'

import { getSubTeam, setSubTeamMembers } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import { useAsync } from '../../hooks/useAsync'
import type { SubTeamDetail, SubTeamItem } from '../../types/collaboration'
import type { TeamDetail } from '../../types/team'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import UnitMemberPicker, { type PickableMember } from '../collaboration/UnitMemberPicker'
import styles from './SubTeamMembersDialog.module.css'

/** 子团队成员维护弹窗属性。 */
export interface SubTeamMembersDialogProps {
  /** 是否打开。 */
  open: boolean
  /** 父团队详情。 */
  team: TeamDetail
  /** 目标子团队。 */
  subTeam: SubTeamItem | null
  /** 关闭回调。 */
  onClose: () => void
  /** 保存成功回调。 */
  onSaved: (subTeam: SubTeamDetail) => void
}

/** 子团队成员维护弹窗。 */
export default function SubTeamMembersDialog({
  open,
  team,
  subTeam,
  onClose,
  onSaved,
}: SubTeamMembersDialogProps) {
  const { showToast } = useToast()
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([])
  const [selectionError, setSelectionError] = useState<string | undefined>(undefined)
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 拉取子团队详情以获取当前成员。 */
  const detailState = useAsync<SubTeamDetail | null>(
    () =>
      open && subTeam !== null
        ? getSubTeam(team.id, subTeam.id)
        : Promise.resolve(null),
    [open, team.id, subTeam?.id],
  )

  /** 详情加载完成后同步已选成员（仅同步当前子团队的数据，避免切换时串数据）。 */
  useEffect(() => {
    if (!open || detailState.loading) {
      return
    }
    if (detailState.data !== null && detailState.data.id === subTeam?.id) {
      setSelectedUserIds(detailState.data.members.map((member) => member.userId))
      setSelectionError(undefined)
    }
  }, [open, detailState.data, detailState.loading, subTeam?.id])

  if (!open || subTeam === null) {
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

  /** 提交成员设置。 */
  const handleSubmit = async (): Promise<void> => {
    if (subTeam.leaderUserId !== null && !selectedUserIds.includes(subTeam.leaderUserId)) {
      setSelectionError('The sub-team lead must remain a member of the sub-team. Keep the lead selected.')
      return
    }
    setSubmitting(true)
    try {
      const saved = await setSubTeamMembers(team.id, subTeam.id, selectedUserIds)
      onSaved(saved)
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to save sub-team members. Please try again.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const footer = (
    <div className={styles.footer}>
      <Button variant="secondary" onClick={onClose} disabled={submitting}>
        Cancel
      </Button>
      <Button
        onClick={() => void handleSubmit()}
        loading={submitting}
        disabled={detailState.loading || detailState.error !== null}
      >
        Save Members
      </Button>
    </div>
  )

  return (
    <Modal
      open={open}
      title={'Member Management · ' + subTeam.name}
      size="large"
      footer={footer}
      onClose={() => {
        if (!submitting) {
          onClose()
        }
      }}
    >
      <div className={styles.body}>
        <p className={styles.hintText}>
          Members must belong to the parent team. Current sub-team lead:
          {subTeam.leaderNickname ?? 'Not assigned'}.
        </p>
        {detailState.error !== null ? (
          <div className={styles.errorBox}>
            <span>{detailState.error}</span>
            <Button variant="secondary" size="small" onClick={detailState.reload}>
              Reload
            </Button>
          </div>
        ) : null}
        <UnitMemberPicker
          label="Sub-team Members"
          members={candidates}
          selectedUserIds={selectedUserIds}
          onChange={(userIds) => {
            setSelectedUserIds(userIds)
            setSelectionError(undefined)
          }}
          loading={detailState.loading}
          disabled={submitting}
          error={selectionError}
          emptyText="No parent team members available"
          maxHeight={280}
        />
      </div>
    </Modal>
  )
}