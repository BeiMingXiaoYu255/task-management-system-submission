/**
 * 发起协作表单逻辑：集中处理候选数据加载、单位联动、校验与提交。
 *
 * 拆分为 Hook 的原因是表单联动与请求较多，组件只保留渲染以控制在 300 行以内。
 * 数据来源：GET /collaboration/directory、GET /teams/{id}/sub-teams、
 * GET /collaborations/units/members 与 POST /collaborations。
 */

import { useEffect, useMemo, useState } from 'react'

import { createCollaboration, getCollaborationDirectory } from '../../api/collaborationApi'
import { listSubTeams } from '../../api/teamApi'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import { useAsync } from '../../hooks/useAsync'
import type {
  CollaborationDirectoryItem,
  CollaborationItem,
  SubTeamItem,
} from '../../types/collaboration'
import type { SelectOption } from '../ui/Select'
import {
  buildInitiatorTeamOptions,
  buildInitiatorUnitOptions,
  buildLiaisonOptions,
  buildTargetTeamOptions,
  buildTargetUnitOptions,
  formatTeamRoleHint,
  TEAM_LEVEL_OPTION_VALUE,
} from './collaborationFormOptions'
import useUnitMembers from './useUnitMembers'

/** 发起协作表单错误集合。 */
export interface CreateCollaborationFormErrors {
  initiatorUnit?: string
  targetTeam?: string
  targetUnit?: string
  liaison?: string
  sameUnit?: string
}

/** useCreateCollaborationForm 入参。 */
export interface UseCreateCollaborationFormOptions {
  /** 弹窗是否打开。 */
  open: boolean
  /** 默认己方团队。 */
  initialInitiatorTeamId?: number
  /** 默认接收方团队。 */
  initialTargetTeamId?: number
  /** 默认接收方子团队。 */
  initialTargetSubTeamId?: number | null
  /** 创建成功回调。 */
  onCreated: (collaboration: CollaborationItem) => void
}

/** useCreateCollaborationForm 对外状态与操作。 */
export interface CreateCollaborationFormState {
  initiatorTeamId: number
  initiatorSubTeamId: number
  targetTeamId: number
  targetSubTeamId: number
  liaisonUserId: number
  message: string
  errors: CreateCollaborationFormErrors
  submitting: boolean
  initiatorTeamOptions: SelectOption[]
  initiatorUnitOptions: SelectOption[]
  targetTeamOptions: SelectOption[]
  targetUnitOptions: SelectOption[]
  liaisonOptions: SelectOption[]
  initiatorRoleHint: string | undefined
  initiatorUnitHint: string
  directoryLoading: boolean
  directoryError: string | null
  unitMembersLoading: boolean
  unitMembersError: string | null
  reloadUnitMembers: () => void
  onInitiatorTeamChange: (value: string | number) => void
  onInitiatorUnitChange: (value: string | number) => void
  onTargetTeamChange: (value: string | number) => void
  onTargetSubTeamChange: (value: string | number) => void
  onLiaisonChange: (value: string | number) => void
  onMessageChange: (message: string) => void
  submit: () => Promise<void>
}

/** 创建表单逻辑 Hook。 */
export function useCreateCollaborationForm({
  open,
  initialInitiatorTeamId,
  initialTargetTeamId,
  initialTargetSubTeamId,
  onCreated,
}: UseCreateCollaborationFormOptions): CreateCollaborationFormState {
  const { user } = useAuth()
  const { showToast } = useToast()
  const memberships = user?.teams ?? []

  const [initiatorTeamId, setInitiatorTeamId] = useState<number>(0)
  const [initiatorSubTeamId, setInitiatorSubTeamId] = useState<number>(TEAM_LEVEL_OPTION_VALUE)
  const [targetTeamId, setTargetTeamId] = useState<number>(0)
  const [targetSubTeamId, setTargetSubTeamId] = useState<number>(TEAM_LEVEL_OPTION_VALUE)
  const [liaisonUserId, setLiaisonUserId] = useState<number>(0)
  const [message, setMessage] = useState<string>('')
  const [errors, setErrors] = useState<CreateCollaborationFormErrors>({})
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 协作目录：仅在弹窗打开时请求。 */
  const directoryState = useAsync<CollaborationDirectoryItem[]>(
    () => (open ? getCollaborationDirectory() : Promise.resolve([])),
    [open],
  )

  /** 己方团队的子团队列表。 */
  const subTeamsState = useAsync<SubTeamItem[]>(
    () => (open && initiatorTeamId > 0 ? listSubTeams(initiatorTeamId) : Promise.resolve([])),
    [open, initiatorTeamId],
  )

  /** 己方单位成员（对接人候选）。 */
  const unitMembersState = useUnitMembers(
    initiatorTeamId > 0 ? initiatorTeamId : null,
    initiatorSubTeamId > 0 ? initiatorSubTeamId : null,
    open && initiatorTeamId > 0,
  )

  /** 打开弹窗或预填参数变化时重置表单。 */
  useEffect(() => {
    if (!open) {
      return
    }
    setInitiatorTeamId(initialInitiatorTeamId ?? memberships[0]?.teamId ?? 0)
    setInitiatorSubTeamId(TEAM_LEVEL_OPTION_VALUE)
    setTargetTeamId(initialTargetTeamId ?? 0)
    setTargetSubTeamId(initialTargetSubTeamId ?? TEAM_LEVEL_OPTION_VALUE)
    setLiaisonUserId(0)
    setMessage('')
    setErrors({})
    // 仅在弹窗打开时按当前用户团队取默认值，避免用户信息刷新导致表单被重置
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialInitiatorTeamId, initialTargetTeamId, initialTargetSubTeamId])

  const initiatorMembership = memberships.find(
    (membership) => membership.teamId === initiatorTeamId,
  )
  const isInitiatorTeamAdmin = initiatorMembership?.role === 'admin'

  /** 可发起协作的子团队：团队管理员可选全部，子负责人仅可选自己负责的子团队。 */
  const allowedSubTeams = useMemo(() => {
    const subTeams = subTeamsState.data ?? []
    if (isInitiatorTeamAdmin) {
      return subTeams
    }
    return subTeams.filter(
      (subTeam) => subTeam.myRole === 'leader' || subTeam.myRole === 'admin',
    )
  }, [subTeamsState.data, isInitiatorTeamAdmin])

  /** 己方团队选项。 */
  const initiatorTeamOptions = buildInitiatorTeamOptions(memberships)

  /** 己方单位选项：团队本级（仅管理员）+ 允许的子团队。 */
  const initiatorUnitOptions = useMemo<SelectOption[]>(
    () => buildInitiatorUnitOptions(isInitiatorTeamAdmin, allowedSubTeams),
    [isInitiatorTeamAdmin, allowedSubTeams],
  )

  /** 接收方目录项。 */
  const targetDirectoryItem = (directoryState.data ?? []).find(
    (directoryItem) => directoryItem.teamId === targetTeamId,
  )

  /** 接收方团队选项。 */
  const targetTeamOptions = buildTargetTeamOptions(directoryState.data ?? [])

  /** 接收方单位选项：团队本级 + 目录中的子团队。 */
  const targetUnitOptions = useMemo<SelectOption[]>(
    () => buildTargetUnitOptions(targetDirectoryItem),
    [targetDirectoryItem],
  )

  /** 对接人选项。 */
  const liaisonOptions = buildLiaisonOptions(unitMembersState.data ?? [])

  /** 切换己方团队：重置子团队与对接人。 */
  const handleInitiatorTeamChange = (value: string | number): void => {
    setInitiatorTeamId(Number(value))
    setInitiatorSubTeamId(TEAM_LEVEL_OPTION_VALUE)
    setLiaisonUserId(0)
    setErrors({})
  }

  /** 切换己方单位：重置对接人。 */
  const handleInitiatorUnitChange = (value: string | number): void => {
    setInitiatorSubTeamId(Number(value))
    setLiaisonUserId(0)
    setErrors((previousErrors) => ({ ...previousErrors, initiatorUnit: undefined }))
  }

  /** 切换接收方团队：重置接收方子团队。 */
  const handleTargetTeamChange = (value: string | number): void => {
    setTargetTeamId(Number(value))
    setTargetSubTeamId(TEAM_LEVEL_OPTION_VALUE)
    setErrors((previousErrors) => ({ ...previousErrors, targetTeam: undefined }))
  }

  /** 校验表单。 */
  const validateForm = (): boolean => {
    const nextErrors: CreateCollaborationFormErrors = {}
    if (initiatorTeamId <= 0) {
      nextErrors.initiatorUnit = 'Select your team'
    } else if (!isInitiatorTeamAdmin && initiatorSubTeamId <= 0) {
      nextErrors.initiatorUnit = 'Select a sub-team you lead as the initiating unit'
    }
    if (targetTeamId <= 0) {
      nextErrors.targetTeam = 'Select a receiving team'
    }
    if (
      targetTeamId > 0 &&
      targetTeamId === initiatorTeamId &&
      targetSubTeamId === initiatorSubTeamId
    ) {
      nextErrors.sameUnit = 'The initiating and receiving units cannot be the same'
    }
    if (liaisonUserId <= 0) {
      nextErrors.liaison = 'Select your liaison'
    }
    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  /** 提交协作申请。 */
  const submit = async (): Promise<void> => {
    if (!validateForm()) {
      return
    }
    setSubmitting(true)
    try {
      const created = await createCollaboration({
        initiatorTeamId,
        initiatorSubTeamId: initiatorSubTeamId > 0 ? initiatorSubTeamId : null,
        targetTeamId,
        targetSubTeamId: targetSubTeamId > 0 ? targetSubTeamId : null,
        initiatorLiaisonUserId: liaisonUserId,
        message: message.trim() === '' ? null : message.trim(),
      })
      onCreated(created)
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to submit the collaboration request. Please try again.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return {
    initiatorTeamId,
    initiatorSubTeamId,
    targetTeamId,
    targetSubTeamId,
    liaisonUserId,
    message,
    errors,
    submitting,
    initiatorTeamOptions,
    initiatorUnitOptions,
    targetTeamOptions,
    targetUnitOptions,
    liaisonOptions,
    initiatorRoleHint: initiatorMembership
      ? 'My role: ' + formatTeamRoleHint(initiatorMembership.role)
      : undefined,
    initiatorUnitHint:
      !isInitiatorTeamAdmin && allowedSubTeams.length === 0
        ? 'You are not an admin of this team and do not lead any sub-teams, so you cannot initiate collaborations'
        : 'Sub-team collaborations are created in the name of the sub-team',
    directoryLoading: directoryState.loading,
    directoryError: directoryState.error,
    unitMembersLoading: unitMembersState.loading,
    unitMembersError: unitMembersState.error,
    reloadUnitMembers: unitMembersState.reload,
    onInitiatorTeamChange: handleInitiatorTeamChange,
    onInitiatorUnitChange: handleInitiatorUnitChange,
    onTargetTeamChange: handleTargetTeamChange,
    onTargetSubTeamChange: (value) => setTargetSubTeamId(Number(value)),
    onLiaisonChange: (value) => {
      setLiaisonUserId(Number(value))
      setErrors((previousErrors) => ({ ...previousErrors, liaison: undefined }))
    },
    onMessageChange: setMessage,
    submit,
  }
}