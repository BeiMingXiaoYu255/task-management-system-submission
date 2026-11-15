/**
 * 团队信息编辑表单：修改团队名称、简介与加入方式（仅团队管理员可用）。
 */

import { useState } from 'react'

import { updateTeam } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { JoinMethod } from '../../types/common'
import type { TeamDetail } from '../../types/team'
import Button from '../ui/Button'
import Input from '../ui/Input'
import RadioGroup from '../ui/RadioGroup'
import Textarea from '../ui/Textarea'
import styles from './TeamInfoForm.module.css'

/** 加入方式选项。 */
const JOIN_METHOD_OPTIONS = [
  { value: 'inviteOnly', label: 'Invite Code Only', description: 'An invite code is required to join.' },
  { value: 'approval', label: 'Approval Required', description: 'Requests are reviewed by an admin.' },
  { value: 'free', label: 'Free Join', description: 'Anyone who knows the team can join.' },
]

/** TeamInfoForm 组件属性。 */
export interface TeamInfoFormProps {
  /** 团队详情。 */
  team: TeamDetail
  /** 保存成功后的刷新回调。 */
  onUpdated: () => void
}

/** 团队信息编辑表单。 */
export default function TeamInfoForm({ team, onUpdated }: TeamInfoFormProps) {
  const { showToast } = useToast()
  const [name, setName] = useState<string>(team.name)
  const [description, setDescription] = useState<string>(team.description ?? '')
  const [joinMethod, setJoinMethod] = useState<JoinMethod>(team.joinMethod)
  const [nameError, setNameError] = useState<string | undefined>(undefined)
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 保存团队信息。 */
  const handleSubmit = async (): Promise<void> => {
    const trimmedName = name.trim()
    if (trimmedName.length < 2 || trimmedName.length > 100) {
      setNameError('Team name must be 2-100 characters.')
      return
    }
    setSubmitting(true)
    try {
      await updateTeam(team.id, {
        name: trimmedName,
        description: description.trim() === '' ? null : description.trim(),
        joinMethod,
      })
      showToast('Team info updated.', 'success')
      onUpdated()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to save team info.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className={styles.infoFormSection}>
      <header className={styles.sectionHeader}>
        <h2 className={styles.sectionTitle}>Team Information</h2>
        <p className={styles.sectionDescription}>Update the team name, description, and join method.</p>
      </header>
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
          error={nameError}
          maxLength={100}
          disabled={submitting}
        />
        <Textarea
          label="Team Description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
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
        <div className={styles.footer}>
          <Button onClick={handleSubmit} loading={submitting}>
            Save Team Info
          </Button>
        </div>
      </div>
    </section>
  )
}
