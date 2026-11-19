/**
 * 协作单位成员 Hook：按团队/子团队拉取可担任对接人或执行人的成员列表。
 *
 * 团队本级只传 teamId，子团队再传 subTeamId；未启用时返回空数组，避免多余请求。
 */

import { listUnitMembers } from '../../api/teamApi'
import { useAsync, type AsyncState } from '../../hooks/useAsync'
import type { CollaborationUnitCandidate } from '../../types/collaboration'

/**
 * 获取协作单位成员候选。
 *
 * @param teamId 单位所属团队 ID；为空表示尚未选择单位
 * @param subTeamId 子团队 ID；为空表示团队本级
 * @param enabled 是否启用请求（通常在弹窗打开且已选择单位时为 true）
 * @returns 成员候选异步状态
 */
export function useUnitMembers(
  teamId: number | null,
  subTeamId: number | null,
  enabled: boolean,
): AsyncState<CollaborationUnitCandidate[]> {
  return useAsync<CollaborationUnitCandidate[]>(
    () => (enabled && teamId !== null ? listUnitMembers(teamId, subTeamId) : Promise.resolve([])),
    [teamId, subTeamId, enabled],
  )
}

export default useUnitMembers
