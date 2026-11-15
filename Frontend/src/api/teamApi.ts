/** 团队管理接口调用。 */

import type {
  CollaborationUnitCandidate,
  SaveSubTeamPayload,
  SubTeamDetail,
  SubTeamItem,
  UpdateSubTeamPayload,
} from '../types/collaboration'
import type { MessageResponse, PageResult } from '../types/common'
import type { TaskItem, TaskQuery } from '../types/task'
import type {
  CreateTeamPayload,
  GenerateInviteCodePayload,
  JoinRequestItem,
  JoinTeamPayload,
  JoinTeamResult,
  MemberCandidateItem,
  SaveLevelPayload,
  TeamBrief,
  TeamDetail,
  TeamLevel,
  TeamMemberItem,
  UpdateTeamPayload,
} from '../types/team'
import { request } from './httpClient'

/** 我加入的团队列表。 */
export function listMyTeams(): Promise<TeamBrief[]> {
  return request<TeamBrief[]>('/teams')
}

/** 创建团队（创建者自动成为团队管理员）。 */
export function createTeam(payload: CreateTeamPayload): Promise<TeamDetail> {
  return request<TeamDetail>('/teams', { method: 'POST', body: payload })
}

/** 获取团队详情。 */
export function getTeam(teamId: number): Promise<TeamDetail> {
  return request<TeamDetail>('/teams/' + teamId)
}

/** 修改团队信息（团队管理员）。 */
export function updateTeam(teamId: number, payload: UpdateTeamPayload): Promise<TeamDetail> {
  return request<TeamDetail>('/teams/' + teamId, { method: 'PUT', body: payload })
}

/** 解散团队（需传入团队名二次确认）。 */
export function deleteTeam(teamId: number, confirmName: string): Promise<MessageResponse> {
  return request<MessageResponse>('/teams/' + teamId, {
    method: 'DELETE',
    body: { confirmName },
  })
}

/** 转让团队管理员。 */
export function transferTeam(teamId: number, newAdminUserId: number): Promise<TeamDetail> {
  return request<TeamDetail>('/teams/' + teamId + '/transfer', {
    method: 'POST',
    body: { newAdminUserId },
  })
}

/** 加入团队（自由加入/申请/邀请码）。 */
export function joinTeam(payload: JoinTeamPayload): Promise<JoinTeamResult> {
  return request<JoinTeamResult>('/teams/join', { method: 'POST', body: payload })
}

/** 退出团队。 */
export function leaveTeam(teamId: number): Promise<MessageResponse> {
  return request<MessageResponse>('/teams/' + teamId + '/leave', { method: 'POST' })
}

/** 团队成员列表。 */
export function listTeamMembers(teamId: number): Promise<TeamMemberItem[]> {
  return request<TeamMemberItem[]>('/teams/' + teamId + '/members')
}

/** 踢出成员。 */
export function kickMember(teamId: number, userId: number): Promise<MessageResponse> {
  return request<MessageResponse>('/teams/' + teamId + '/members/' + userId, { method: 'DELETE' })
}

/** 设置/撤销子管理员（仅团队管理员）。 */
export function setMemberRole(
  teamId: number,
  userId: number,
  role: 'subAdmin' | 'member',
): Promise<MessageResponse> {
  return request<MessageResponse>('/teams/' + teamId + '/members/' + userId + '/role', {
    method: 'PUT',
    body: { role },
  })
}

/** 调整成员级别。 */
export function setMemberLevel(teamId: number, userId: number, levelId: number): Promise<MessageResponse> {
  return request<MessageResponse>('/teams/' + teamId + '/members/' + userId + '/level', {
    method: 'PUT',
    body: { levelId },
  })
}

/** 团队级别列表。 */
export function listLevels(teamId: number): Promise<TeamLevel[]> {
  return request<TeamLevel[]>('/teams/' + teamId + '/levels')
}

/** 新建级别（仅团队管理员）。 */
export function createLevel(teamId: number, payload: SaveLevelPayload): Promise<TeamLevel> {
  return request<TeamLevel>('/teams/' + teamId + '/levels', { method: 'POST', body: payload })
}

/** 修改级别。 */
export function updateLevel(teamId: number, levelId: number, payload: SaveLevelPayload): Promise<TeamLevel> {
  return request<TeamLevel>('/teams/' + teamId + '/levels/' + levelId, {
    method: 'PUT',
    body: payload,
  })
}

/** 删除级别。 */
export function deleteLevel(teamId: number, levelId: number): Promise<MessageResponse> {
  return request<MessageResponse>('/teams/' + teamId + '/levels/' + levelId, { method: 'DELETE' })
}

/** 生成邀请码。 */
export function generateInviteCode(
  teamId: number,
  payload: GenerateInviteCodePayload,
): Promise<TeamDetail> {
  return request<TeamDetail>('/teams/' + teamId + '/invite-code', { method: 'POST', body: payload })
}

/** 待处理入团申请列表。 */
export function listJoinRequests(teamId: number): Promise<JoinRequestItem[]> {
  return request<JoinRequestItem[]>('/teams/' + teamId + '/join-requests')
}

/** 审批入团申请。 */
export function handleJoinRequest(
  teamId: number,
  requestId: number,
  action: 'approve' | 'reject',
): Promise<MessageResponse> {
  return request<MessageResponse>('/teams/' + teamId + '/join-requests/' + requestId, {
    method: 'PUT',
    body: { action },
  })
}

/** 任务可选成员候选列表（含级别与技能）。 */
export function listMemberCandidates(teamId: number): Promise<MemberCandidateItem[]> {
  return request<MemberCandidateItem[]>('/teams/' + teamId + '/members/candidates')
}
// ===== v1.1 子团队与协作单位成员 =====

/** 团队子团队列表（含负责人与成员数）。 */
export function listSubTeams(teamId: number): Promise<SubTeamItem[]> {
  return request<SubTeamItem[]>('/teams/' + teamId + '/sub-teams')
}

/** 创建子团队（团队管理员）。 */
export function createSubTeam(teamId: number, payload: SaveSubTeamPayload): Promise<SubTeamDetail> {
  return request<SubTeamDetail>('/teams/' + teamId + '/sub-teams', {
    method: 'POST',
    body: payload,
  })
}

/** 子团队详情（含成员列表）。 */
export function getSubTeam(teamId: number, subTeamId: number): Promise<SubTeamDetail> {
  return request<SubTeamDetail>('/teams/' + teamId + '/sub-teams/' + subTeamId)
}

/** 修改子团队信息（团队管理员或子负责人）。 */
export function updateSubTeam(
  teamId: number,
  subTeamId: number,
  payload: UpdateSubTeamPayload,
): Promise<SubTeamDetail> {
  return request<SubTeamDetail>('/teams/' + teamId + '/sub-teams/' + subTeamId, {
    method: 'PUT',
    body: payload,
  })
}

/** 删除子团队（团队管理员），其下任务 subTeamId 置空。 */
export function deleteSubTeam(teamId: number, subTeamId: number): Promise<MessageResponse> {
  return request<MessageResponse>('/teams/' + teamId + '/sub-teams/' + subTeamId, {
    method: 'DELETE',
  })
}

/** 覆盖式设置子团队成员（团队管理员或子负责人）。 */
export function setSubTeamMembers(
  teamId: number,
  subTeamId: number,
  userIds: number[],
): Promise<SubTeamDetail> {
  return request<SubTeamDetail>('/teams/' + teamId + '/sub-teams/' + subTeamId + '/members', {
    method: 'PUT',
    body: { userIds },
  })
}

/** 子团队任务分页列表（子团队成员/团队管理员可见）。 */
export function listSubTeamTasks(
  teamId: number,
  subTeamId: number,
  query: TaskQuery,
): Promise<PageResult<TaskItem>> {
  return request<PageResult<TaskItem>>(
    '/teams/' + teamId + '/sub-teams/' + subTeamId + '/tasks',
    { query: { ...query } },
  )
}

/**
 * 协作单位成员候选（用于选择对接人/指派执行人）。
 *
 * 团队本级只传 teamId；子团队需同时传 subTeamId。
 */
export function listUnitMembers(
  teamId: number,
  subTeamId?: number | null,
): Promise<CollaborationUnitCandidate[]> {
  return request<CollaborationUnitCandidate[]>('/collaborations/units/members', {
    query: { teamId, subTeamId: subTeamId ?? undefined },
  })
}