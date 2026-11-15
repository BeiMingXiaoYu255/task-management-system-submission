/** 用户与个人资料类型。 */

import type { DateTimeString, GlobalRole } from './common'

/** 用户简要信息。 */
export interface UserBrief {
  id: number
  username: string
  nickname: string
  avatar: string | null
  globalRole: GlobalRole
}

/** 技能标签项。 */
export interface SkillItem {
  id: number
  name: string
  category: string | null
  proficiency: number
}

/** 用户完整资料。 */
export interface UserDetail extends UserBrief {
  email: string | null
  phone: string | null
  bio: string | null
  createdAt: DateTimeString
  skills: SkillItem[]
}

/** 修改个人资料请求体。 */
export interface UpdateProfilePayload {
  nickname: string
  email?: string | null
  phone?: string | null
  bio?: string | null
}

/** 保存技能请求体。 */
export interface SaveSkillsPayload {
  skills: { skillTagId: number; proficiency: number }[]
}

/** 新建技能标签请求体。 */
export interface CreateSkillTagPayload {
  name: string
  category?: string | null
}

/** 技能标签字典项（用于选择器）。 */
export interface SkillTagItem {
  id: number
  name: string
  category: string | null
}
