/**
 * 创建团队弹窗：填写团队名称、简介与加入方式。
 *
 * 创建成功后创建者自动成为团队管理员，团队默认处于待认证（pending）状态，
 * 因此成功后提示用户等待全局管理员认证。
 */

import { useEffect, useState } from 'react'

import { createTeam } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { JoinMethod } from '../../types/common'
import type { TeamDetail } from '../../types/team'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Modal from '../ui/Modal'
import RadioGroup from '../ui/RadioGroup'
import Textarea from '../ui/Textarea'
import styles from './CreateTeamDialog.module.css'

/** 加入方式选项。 */
const JOIN_METHOD_OPTIONS = [
  { value: 'inviteOnly', label: 'Invite Code Only', description: 'An invite code is required to join. Most secure.' },
  { value: 'approval', label: 'Approval Required', description: 'Members submit a request and join after admin approval.' },
  { value: 'free', label: 'Free Join', description: 'Anyone who knows the team can join directly.' },
]

/** CreateTeamDialog 组件属性。 */
export interface CreateTeamDialogProps {
  /** 弹窗是否打开。 */
  open: boolean
  /** 关闭回调。 */
  onClose: () => void
  /** 创建成功回调（返回新建团队详情）。 */
  onCreated: (team: TeamDetail) => void
}

/** 创建团队弹窗。 */
export default function CreateTeamDialog({ open, onClose, onCreated }: CreateTeamDialogProps) {
  const { showToast } = useToast()
  const [name, setName] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [joinMethod, setJoinMethod] = useState<JoinMethod>('inviteOnly')
  const [nameError, setNameError] = useState<string | undefined>(undefined)
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 每次打开时重置表单。 */
  useEffect(() => {
    if (!open) {
      return
    }
    setName('')
    setDescription('')
    setJoinMethod('inviteOnly')
    setNameError(undefined)
  }, [open])

  /** 提交创建请求。 */
  const handleSubmit = async (): Promise<void> => {
    const trimmedName = name.trim()
    if (trimmedName.length < 2 || trimmedName.length > 100) {
      setNameError('Team name must be 2-100 characters.')
      return
    }
    setSubmitting(true)
    try {
      const createdTeam = await createTeam({
        name: trimmedName,
        description: description.trim() === '' ? null : description.trim(),
        joinMethod,
      })
      showToast('Team created. Waiting for Global Admin certification.', 'success')
      onCreated(createdTeam)
      onClose()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to create team. Please try again.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      open={open}
      title="Create Team"
      size="medium"
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
          <Button onClick={handleSubmit} loading={submitting}>
            Create Team
          </Button>
        </div>
      }
    >
      <div className={styles.formBody}>
        <Input
          label="Team Name *"
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            if (nameError) {
              setNameError(undefined)
            }
          }}
          placeholder="2-100 characters, e.g. Product R&D Center"
          error={nameError}
          maxLength={100}
          disabled={submitting}
        />
        <Textarea
          label="Team Description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Describe the team goals, scope, and how you collaborate."
          rows={3}
          maxLength={500}
          disabled={submitting}
        />
        <div className={styles.section}>
          <span className={styles.sectionLabel}>Join Method</span>
          <RadioGroup<JoinMethod>
            value={joinMethod}
            onChange={setJoinMethod}
            options={JOIN_METHOD_OPTIONS}
            disabled={submitting}
          />
        </div>
      </div>
    </Modal>
  )
}
