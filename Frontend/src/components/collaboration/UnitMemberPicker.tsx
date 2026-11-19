/**
 * 单位成员选择器：以复选框列表维护多选结果，可按昵称/用户名搜索。
 *
 * 复用场景：发起协作选择对接人（单选场景由父级取第一个）、
 * 接收方确认接单指派执行人、子团队成员维护。
 */

import { useMemo, useState } from 'react'

import Checkbox from '../ui/Checkbox'
import Input from '../ui/Input'
import Spinner from '../ui/Spinner'
import styles from './UnitMemberPicker.module.css'

/** 可选择成员的最小结构：团队/子团队/协作单位成员均满足。 */
export interface PickableMember {
  userId: number
  username: string
  nickname: string
  avatar: string | null
  levelName: string
  isLeader?: boolean
}

/** 单位成员选择器属性。 */
export interface UnitMemberPickerProps {
  /** 可选成员列表。 */
  members: PickableMember[]
  /** 已选用户 ID 列表。 */
  selectedUserIds: number[]
  /** 选择结果变化回调。 */
  onChange: (userIds: number[]) => void
  /** 成员加载中。 */
  loading?: boolean
  /** 是否禁用全部交互。 */
  disabled?: boolean
  /** 无成员时的提示文案。 */
  emptyText?: string
  /** 是否展示搜索框，默认 true。 */
  searchable?: boolean
  /** 字段标题。 */
  label?: string
  /** 错误文案。 */
  error?: string
  /** 辅助提示。 */
  hint?: string
  /** 列表最大高度（像素），默认 220。 */
  maxHeight?: number
}

/** 单位成员选择器组件。 */
export default function UnitMemberPicker({
  members,
  selectedUserIds,
  onChange,
  loading = false,
  disabled = false,
  emptyText = 'No members available',
  searchable = true,
  label,
  error,
  hint,
  maxHeight = 220,
}: UnitMemberPickerProps) {
  const [keyword, setKeyword] = useState<string>('')

  /** 按昵称/用户名过滤后的成员列表。 */
  const visibleMembers = useMemo(() => {
    const trimmedKeyword = keyword.trim().toLowerCase()
    if (trimmedKeyword === '') {
      return members
    }
    return members.filter(
      (member) =>
        member.nickname.toLowerCase().includes(trimmedKeyword) ||
        member.username.toLowerCase().includes(trimmedKeyword),
    )
  }, [members, keyword])

  /** 勾选/取消某个成员。 */
  const toggleMember = (userId: number, checked: boolean): void => {
    if (checked) {
      onChange([...selectedUserIds, userId])
      return
    }
    onChange(selectedUserIds.filter((selectedUserId) => selectedUserId !== userId))
  }

  const listStyle = { maxHeight: maxHeight + 'px' }

  return (
    <div className={styles.picker}>
      {label ? <span className={styles.label}>{label}</span> : null}
      {searchable ? (
        <Input
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="Search by nickname or username"
          disabled={disabled}
        />
      ) : null}
      {loading ? (
        <div className={styles.stateBox}>
          <Spinner size="small" />
          <span>Loading members...</span>
        </div>
      ) : visibleMembers.length === 0 ? (
        <p className={styles.stateBox}>{emptyText}</p>
      ) : (
        <ul className={styles.memberList} style={listStyle}>
          {visibleMembers.map((member) => (
            <li key={member.userId} className={styles.memberItem}>
              <Checkbox
                checked={selectedUserIds.includes(member.userId)}
                onChange={(event) => toggleMember(member.userId, event.target.checked)}
                disabled={disabled}
                label={
                  <span className={styles.memberLabel}>
                    <span className={styles.memberName}>{member.nickname}</span>
                    <span className={styles.memberMeta}>
                      {member.username} · {member.levelName}
                      {member.isLeader ? ' · Sub-team Lead' : ''}
                    </span>
                  </span>
                }
              />
            </li>
          ))}
        </ul>
      )}
      {error ? (
        <span className={styles.error} role="alert">
          {error}
        </span>
      ) : hint ? (
        <span className={styles.hint}>{hint}</span>
      ) : null}
      <span className={styles.selectedHint}>{selectedUserIds.length} selected</span>
    </div>
  )
}
