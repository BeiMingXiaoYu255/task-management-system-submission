/** 用户资料与技能标签接口调用。 */

import type {
  CreateSkillTagPayload,
  SaveSkillsPayload,
  SkillTagItem,
  UpdateProfilePayload,
  UserDetail,
} from '../types/user'
import { request } from './httpClient'

/** 获取本人资料。 */
export function getMyProfile(): Promise<UserDetail> {
  return request<UserDetail>('/users/me')
}

/** 修改本人资料。 */
export function updateMyProfile(payload: UpdateProfilePayload): Promise<UserDetail> {
  return request<UserDetail>('/users/me', { method: 'PUT', body: payload })
}

/** 覆盖式保存本人技能。 */
export function saveMySkills(payload: SaveSkillsPayload): Promise<UserDetail> {
  return request<UserDetail>('/users/me/skills', { method: 'PUT', body: payload })
}

/** 新建技能标签。 */
export function createSkillTag(payload: CreateSkillTagPayload): Promise<SkillTagItem> {
  return request<SkillTagItem>('/users/me/skills/tags', { method: 'POST', body: payload })
}

/** 获取全部技能标签字典。 */
export function listSkillTags(keyword?: string): Promise<SkillTagItem[]> {
  return request<SkillTagItem[]>('/skill-tags', { query: { keyword } })
}

/** 查看他人资料（受权限限制，隐私字段可能为空）。 */
export function getUserProfile(userId: number): Promise<UserDetail> {
  return request<UserDetail>('/users/' + userId + '/profile')
}

/** 查看同团队公开资料。 */
export function getUserPublicProfile(userId: number): Promise<UserDetail> {
  return request<UserDetail>('/users/' + userId + '/public-profile')
}
