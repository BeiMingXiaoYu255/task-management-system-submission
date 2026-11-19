/**
 * 发起协作申请弹窗。
 *
 * 选择己方团队/子团队、接收方团队/子团队与己方对接人，填写申请说明后提交；
 * 数据加载、单位联动与校验逻辑集中在 useCreateCollaborationForm 中。
 */

import type { CollaborationItem } from '../../types/collaboration'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import Select from '../ui/Select'
import Textarea from '../ui/Textarea'
import { useCreateCollaborationForm } from './useCreateCollaborationForm'
import styles from './CreateCollaborationDialog.module.css'

/** 发起协作弹窗属性。 */
export interface CreateCollaborationDialogProps {
  /** 是否打开。 */
  open: boolean
  /** 默认己方团队（入口为团队协作 Tab 时预填）。 */
  initialInitiatorTeamId?: number
  /** 默认接收方团队（从团队目录点击发起时预填）。 */
  initialTargetTeamId?: number
  /** 默认接收方子团队。 */
  initialTargetSubTeamId?: number | null
  /** 关闭回调。 */
  onClose: () => void
  /** 创建成功回调。 */
  onCreated: (collaboration: CollaborationItem) => void
}

/** 发起协作申请弹窗。 */
export default function CreateCollaborationDialog({
  open,
  initialInitiatorTeamId,
  initialTargetTeamId,
  initialTargetSubTeamId,
  onClose,
  onCreated,
}: CreateCollaborationDialogProps) {
  const form = useCreateCollaborationForm({
    open,
    initialInitiatorTeamId,
    initialTargetTeamId,
    initialTargetSubTeamId,
    onCreated,
  })

  const footer = (
    <div className={styles.footer}>
      <Button variant="secondary" onClick={onClose} disabled={form.submitting}>
        Cancel
      </Button>
      <Button onClick={() => void form.submit()} loading={form.submitting}>
        Submit Request
      </Button>
    </div>
  )

  return (
    <Modal
      open={open}
      title="Initiate Collaboration Request"
      size="large"
      footer={footer}
      onClose={() => {
        if (!form.submitting) {
          onClose()
        }
      }}
    >
      <div className={styles.formBody}>
        <p className={styles.tipText}>
          Both units' admins must confirm the collaboration. Once approved, collaboration tasks can be dispatched from the collaboration details.
        </p>

        <Select
          label="Your Team"
          value={form.initiatorTeamId}
          onChange={form.onInitiatorTeamChange}
          options={form.initiatorTeamOptions}
          disabled={form.submitting}
          hint={form.initiatorRoleHint}
        />
        <Select
          label="Your Unit"
          value={form.initiatorSubTeamId}
          onChange={form.onInitiatorUnitChange}
          options={form.initiatorUnitOptions}
          disabled={form.submitting || form.initiatorTeamId <= 0}
          error={form.errors.initiatorUnit}
          hint={form.initiatorUnitHint}
        />

        <Select
          label="Receiving Team"
          value={form.targetTeamId}
          onChange={form.onTargetTeamChange}
          options={form.targetTeamOptions}
          disabled={form.submitting || form.directoryLoading}
          error={form.errors.targetTeam ?? form.directoryError ?? undefined}
          hint={form.directoryLoading ? 'Loading collaboration directory...' : undefined}
        />
        <Select
          label="Receiving Unit"
          value={form.targetSubTeamId}
          onChange={form.onTargetSubTeamChange}
          options={form.targetUnitOptions}
          disabled={form.submitting || form.targetTeamId <= 0}
          error={form.errors.targetUnit}
        />

        <div className={styles.liaisonBlock}>
          <Select
            label="Your Liaison"
            value={form.liaisonUserId}
            onChange={form.onLiaisonChange}
            options={form.liaisonOptions}
            disabled={form.submitting || form.initiatorTeamId <= 0}
            error={form.errors.liaison}
            placeholder="Select a liaison"
            hint={
              form.unitMembersLoading
                ? 'Loading unit members...'
                : (form.unitMembersError ?? 'The liaison publishes, confirms, and reviews collaboration tasks')
            }
          />
          {form.unitMembersError !== null ? (
            <Button variant="ghost" size="small" onClick={form.reloadUnitMembers}>
              Reload Members
            </Button>
          ) : null}
        </div>

        <Textarea
          label="Request Note"
          value={form.message}
          onChange={(event) => form.onMessageChange(event.target.value)}
          rows={3}
          maxLength={500}
          placeholder="Briefly describe the purpose and expected scope (optional, max 500 characters)"
          disabled={form.submitting}
        />

        {form.errors.sameUnit ? (
          <p className={styles.errorText} role="alert">
            {form.errors.sameUnit}
          </p>
        ) : null}
      </div>
    </Modal>
  )
}
