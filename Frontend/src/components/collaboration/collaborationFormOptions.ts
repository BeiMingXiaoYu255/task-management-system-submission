/**
 * 发起协作表单的选项构造工具：纯函数，便于复用与测试。
 *
 * 约定：单位选项值 0 表示团队本级；对接人/团队选项均由接口数据映射而来。
 */

import type { TeamMembership } from '../../types/auth'
import type {
  CollaborationDirectoryItem,
  CollaborationUnitCandidate,
  SubTeamItem,
} from '../../types/collaboration'
import type { SelectOption } from '../ui/Select'

/** 团队本级选项值。 */
export const TEAM_LEVEL_OPTION_VALUE = 0

/** 把团队角色转换为中文提示。 */
export function formatTeamRoleHint(
  role: 'admin' | 'subAdmin' | 'member' | null | undefined,
): string {
  if (role === 'admin') {
    return 'Team Admin'
  }
  if (role === 'subAdmin') {
    return 'Sub-admin'
  }
  if (role === 'member') {
    return 'Member'
  }
  return 'Not a team admin'
}

/** 构造己方团队选项。 */
export function buildInitiatorTeamOptions(memberships: TeamMembership[]): SelectOption[] {
  return memberships.map((membership) => ({
    value: membership.teamId,
    label: membership.teamName,
  }))
}

/**
 * 构造己方单位选项。
 *
 * 团队管理员可选团队本级与全部子团队；子负责人仅可选自己负责的子团队。
 */
export function buildInitiatorUnitOptions(
  isTeamAdmin: boolean,
  allowedSubTeams: SubTeamItem[],
): SelectOption[] {
  const options: SelectOption[] = [
    isTeamAdmin
      ? { value: TEAM_LEVEL_OPTION_VALUE, label: 'Team level' }
      : { value: TEAM_LEVEL_OPTION_VALUE, label: 'Select a sub-team you lead' },
  ]
  allowedSubTeams.forEach((subTeam) => {
    options.push({ value: subTeam.id, label: 'Sub-team: ' + subTeam.name })
  })
  return options
}

/** 构造接收方团队选项（含“请选择”占位项）。 */
export function buildTargetTeamOptions(directory: CollaborationDirectoryItem[]): SelectOption[] {
  return [
    { value: TEAM_LEVEL_OPTION_VALUE, label: 'Select a receiving team' },
    ...directory.map((directoryItem) => ({
      value: directoryItem.teamId,
      label: directoryItem.teamName,
    })),
  ]
}

/** 构造接收方单位选项：团队本级 + 该团队的子团队。 */
export function buildTargetUnitOptions(
  targetDirectoryItem: CollaborationDirectoryItem | undefined,
): SelectOption[] {
  const options: SelectOption[] = [
    { value: TEAM_LEVEL_OPTION_VALUE, label: 'Team level' },
  ]
  ;(targetDirectoryItem?.subTeams ?? []).forEach((subTeam) => {
    options.push({ value: subTeam.subTeamId, label: 'Sub-team: ' + subTeam.name })
  })
  return options
}

/** 构造对接人选项。 */
export function buildLiaisonOptions(members: CollaborationUnitCandidate[]): SelectOption[] {
  return members.map((member) => ({
    value: member.userId,
    label: member.nickname + ' (' + member.levelName + ')',
  }))
}
