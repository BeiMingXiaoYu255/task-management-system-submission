/**
 * 任务可选成员候选 Hook：发布任务弹窗打开时拉取候选成员。
 *
 * 候选接口仅团队管理员/子管理员可调用，因此通过 enabled 控制是否请求；
 * 未启用时直接返回空数组，避免普通成员打开页面产生 403 噪音。
 */

import { listMemberCandidates } from '../api/teamApi'
import type { MemberCandidateItem } from '../types/team'
import { useAsync, type AsyncState } from './useAsync'

/**
 * 获取任务接收者候选列表。
 *
 * @param teamId 团队 ID
 * @param enabled 是否允许请求（通常为弹窗打开且当前用户有发布权限）
 * @returns 候选成员异步状态
 */
export function useMemberCandidates(
  teamId: number,
  enabled: boolean,
): AsyncState<MemberCandidateItem[]> {
  return useAsync<MemberCandidateItem[]>(
    () => (enabled ? listMemberCandidates(teamId) : Promise.resolve([])),
    [teamId, enabled],
  )
}
