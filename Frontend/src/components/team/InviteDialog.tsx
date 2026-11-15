/**
 * 邀请码弹窗：团队管理员/子管理员生成并复制邀请码。
 *
 * 生成参数：有效期（小时）与最大使用次数（0 表示不限制）。
 * 接口返回最新团队详情，成功后通知父级重新拉取，使弹窗内展示同步更新。
 * 待认证团队（pending）不能邀请成员，因此禁用生成按钮并给出提示。
 */

import { useEffect, useState } from 'react'

import { generateInviteCode } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { TeamDetail } from '../../types/team'
import { formatDateTime } from '../../utils/formatUtils'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Modal from '../ui/Modal'
import Select from '../ui/Select'
import styles from './InviteDialog.module.css'

/** 有效期下拉选项（小时）。 */
const EXPIRES_OPTIONS = [
  { value: 1, label: '1 hour' },
  { value: 24, label: '1 day' },
  { value: 72, label: '3 days' },
  { value: 168, label: '7 days' },
  { value: 720, label: '30 days' },
]

/** InviteDialog 组件属性。 */
export interface InviteDialogProps {
  /** 弹窗是否打开。 */
  open: boolean
  /** 当前团队详情。 */
  team: TeamDetail
  /** 关闭回调。 */
  onClose: () => void
  /** 生成成功后刷新团队详情回调。 */
  onUpdated: () => void
}

/** 邀请码弹窗。 */
export default function InviteDialog({ open, team, onClose, onUpdated }: InviteDialogProps) {
  const { showToast } = useToast()
  const [expiresInHours, setExpiresInHours] = useState<string>('24')
  const [maxUses, setMaxUses] = useState<string>('0')
  const [generating, setGenerating] = useState<boolean>(false)

  /** 每次打开时重置参数。 */
  useEffect(() => {
    if (!open) {
      return
    }
    setExpiresInHours('24')
    setMaxUses('0')
  }, [open])

  /** 生成新的邀请码。 */
  const handleGenerate = async (): Promise<void> => {
    const parsedMaxUses = Number(maxUses)
    if (!Number.isInteger(parsedMaxUses) || parsedMaxUses < 0) {
      showToast('Max uses must be an integer of 0 or greater.', 'error')
      return
    }
    setGenerating(true)
    try {
      await generateInviteCode(team.id, {
        expiresInHours: Number(expiresInHours),
        maxUses: parsedMaxUses,
      })
      showToast('Invite code generated.', 'success')
      onUpdated()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to generate invite code.'), 'error')
    } finally {
      setGenerating(false)
    }
  }

  /** 复制邀请码到剪贴板。 */
  const handleCopyInviteCode = async (): Promise<void> => {
    if (!team.inviteCode) {
      return
    }
    try {
      await navigator.clipboard.writeText(team.inviteCode)
      showToast('Invite code copied to clipboard.', 'success')
    } catch {
      showToast('Copy failed. Select and copy the invite code manually.', 'error')
    }
  }

  const canInvite = team.status === 'active'

  return (
    <Modal
      open={open}
      title="Team Invite Code"
      size="medium"
      onClose={() => {
        if (!generating) {
          onClose()
        }
      }}
      footer={
        <div className={styles.footer}>
          <Button variant="secondary" onClick={onClose} disabled={generating}>
            Close
          </Button>
          <Button onClick={handleGenerate} loading={generating} disabled={!canInvite}>
            Generate New Invite Code
          </Button>
        </div>
      }
    >
      <div className={styles.dialogBody}>
        {!canInvite ? (
          <p className={styles.warningHint}>The team is not certified yet. Invite codes are available after certification.</p>
        ) : null}

        <section className={styles.currentSection}>
          <span className={styles.sectionLabel}>Current Invite Code</span>
          {team.inviteCode ? (
            <>
              <div className={styles.codeRow}>
                <code className={styles.inviteCode}>{team.inviteCode}</code>
                <Button variant="secondary" size="small" onClick={() => void handleCopyInviteCode()}>
                  Copy
                </Button>
              </div>
              <span className={styles.hintText}>
                Expires: {formatDateTime(team.inviteExpiresAt)}
              </span>
            </>
          ) : (
            <span className={styles.hintText}>No active invite code. Generate one.</span>
          )}
        </section>

        <section className={styles.formSection}>
          <Select
            label="Valid For"
            value={expiresInHours}
            onChange={(nextValue) => setExpiresInHours(String(nextValue))}
            options={EXPIRES_OPTIONS}
            disabled={generating || !canInvite}
          />
          <Input
            label="Max Uses"
            type="number"
            value={maxUses}
            onChange={(event) => setMaxUses(event.target.value)}
            hint="0 means unlimited uses."
            disabled={generating || !canInvite}
          />
        </section>
        <p className={styles.hintText}>
          Regenerating invalidates the old code immediately. Send the new code to members who need to join.
        </p>
      </div>
    </Modal>
  )
}
