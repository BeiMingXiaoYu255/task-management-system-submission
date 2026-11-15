/**
 * 团队成员表：展示成员角色、级别、技能，并提供调整级别/设置子管理员/踢人/转让管理员操作。
 *
 * 权限规则（与后端 core/permissions.py 保持一致，前端先做可达性过滤避免无效请求）：
 * - 团队管理员：可调整任何成员级别、设置/撤销子管理员、踢出除自己与管理员外的成员、转让管理员；
 * - 子管理员：仅可调整/踢出级别低于自己的普通成员；不能转让管理员；
 * - 普通成员：只读。
 */

import { useState } from 'react'

import { kickMember, setMemberRole, transferTeam } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { TeamDetail, TeamMemberItem } from '../../types/team'
import { TEAM_ROLE_LABELS } from '../../utils/displayUtils'
import { formatDate } from '../../utils/formatUtils'
import Avatar from '../ui/Avatar'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import ConfirmDialog from '../ui/ConfirmDialog'
import Dropdown from '../ui/Dropdown'
import Table from '../ui/Table'
import MemberLevelDialog from './MemberLevelDialog'
import styles from './MemberTable.module.css'

/** 需要二次确认的操作。 */
type ConfirmAction = 'kick' | 'transfer' | 'grantSubAdmin' | 'revokeSubAdmin'

/** 待确认操作数据。 */
interface PendingConfirm {
  action: ConfirmAction
  member: TeamMemberItem
}

/** MemberTable 组件属性。 */
export interface MemberTableProps {
  /** 团队详情（含成员与当前用户角色）。 */
  team: TeamDetail
  /** 当前登录用户 ID。 */
  currentUserId: number
  /** 成员数据变化后的刷新回调。 */
  onChanged: () => void
}

/** 成员表组件。 */
export default function MemberTable({ team, currentUserId, onChanged }: MemberTableProps) {
  const { showToast } = useToast()
  const [levelTargetMember, setLevelTargetMember] = useState<TeamMemberItem | null>(null)
  const [pendingConfirm, setPendingConfirm] = useState<PendingConfirm | null>(null)
  const [actionLoading, setActionLoading] = useState<boolean>(false)

  const isAdmin = team.currentUserRole === 'admin'
  const isSubAdmin = team.currentUserRole === 'subAdmin'

  /** 是否可调整该成员级别。 */
  const canChangeLevel = (member: TeamMemberItem): boolean => {
    if (member.userId === currentUserId) {
      return false
    }
    if (isAdmin) {
      return true
    }
    return isSubAdmin && member.role === 'member' && member.levelOrder < team.currentUserLevelOrder
  }

  /** 是否可踢出该成员。 */
  const canKick = (member: TeamMemberItem): boolean => {
    if (member.userId === currentUserId) {
      return false
    }
    if (isAdmin) {
      return member.role !== 'admin'
    }
    return isSubAdmin && member.role === 'member' && member.levelOrder < team.currentUserLevelOrder
  }

  /** 是否可设置/撤销子管理员。 */
  const canToggleSubAdmin = (member: TeamMemberItem): boolean =>
    isAdmin && member.userId !== currentUserId && member.role !== 'admin'

  /** 是否可转让管理员。 */
  const canTransfer = (member: TeamMemberItem): boolean =>
    isAdmin && member.userId !== currentUserId && member.role !== 'admin'

  /** 执行确认后的成员操作。 */
  const handleConfirm = async (): Promise<void> => {
    if (pendingConfirm === null) {
      return
    }
    const { action, member } = pendingConfirm
    setActionLoading(true)
    try {
      if (action === 'kick') {
        await kickMember(team.id, member.userId)
        showToast('Member removed: ' + member.nickname, 'success')
      } else if (action === 'transfer') {
        await transferTeam(team.id, member.userId)
        showToast('Ownership transferred to: ' + member.nickname, 'success')
      } else if (action === 'grantSubAdmin') {
        await setMemberRole(team.id, member.userId, 'subAdmin')
        showToast('Sub-admin role assigned.', 'success')
      } else {
        await setMemberRole(team.id, member.userId, 'member')
        showToast('Sub-admin role revoked.', 'success')
      }
      onChanged()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Member action failed.'), 'error')
    } finally {
      setActionLoading(false)
      setPendingConfirm(null)
    }
  }

  /** 根据操作类型生成确认弹窗文案。 */
  const resolveConfirmText = (): { title: string; description: string; confirmText: string } => {
    if (pendingConfirm === null) {
      return { title: '', description: '', confirmText: 'Confirm' }
    }
    const memberName = pendingConfirm.member.nickname
    switch (pendingConfirm.action) {
      case 'kick':
        return {
          title: 'Remove Member',
          description: 'Remove ' + memberName + ' from the team? Their to-dos will be removed.',
          confirmText: 'Remove Member',
        }
      case 'transfer':
        return {
          title: 'Transfer Ownership',
          description: 'Transfer team admin to ' + memberName + '? You will become a Member, and this cannot be undone.',
          confirmText: 'Confirm Transfer',
        }
      case 'grantSubAdmin':
        return {
          title: 'Set as Sub-admin',
          description: 'Set ' + memberName + ' as a Sub-admin? Sub-admins can review join requests, generate invite codes, and manage lower-level members.',
          confirmText: 'Confirm',
        }
      default:
        return {
          title: 'Revoke Sub-admin',
          description: 'Remove ' + memberName + ' from the Sub-admin role?',
          confirmText: 'Confirm',
        }
    }
  }

  /** 渲染行内操作下拉菜单。 */
  const renderActions = (member: TeamMemberItem) => {
    const dropdownItems: { key: string; label: string; danger?: boolean; onClick: () => void }[] = []
    if (canChangeLevel(member)) {
      dropdownItems.push({
        key: 'changeLevel',
        label: 'Adjust Level',
        onClick: () => setLevelTargetMember(member),
      })
    }
    if (canToggleSubAdmin(member)) {
      dropdownItems.push(
        member.role === 'subAdmin'
          ? {
              key: 'revokeSubAdmin',
              label: 'Revoke Sub-admin',
              onClick: () => setPendingConfirm({ action: 'revokeSubAdmin', member }),
            }
          : {
              key: 'grantSubAdmin',
              label: 'Set as Sub-admin',
              onClick: () => setPendingConfirm({ action: 'grantSubAdmin', member }),
            },
      )
    }
    if (canTransfer(member)) {
      dropdownItems.push({
        key: 'transfer',
        label: 'Transfer Ownership',
        danger: true,
        onClick: () => setPendingConfirm({ action: 'transfer', member }),
      })
    }
    if (canKick(member)) {
      dropdownItems.push({
        key: 'kick',
        label: 'Remove Member',
        danger: true,
        onClick: () => setPendingConfirm({ action: 'kick', member }),
      })
    }
    if (dropdownItems.length === 0) {
      return <span className={styles.mutedText}>—</span>
    }
    return (
      <Dropdown
        trigger={
          <Button variant="secondary" size="small" disabled={actionLoading}>
            Actions
          </Button>
        }
        items={dropdownItems}
      />
    )
  }

  /** 表头列定义。 */
  const columns = [
    {
      key: 'member',
      title: 'Member',
      width: '22%',
      render: (member: TeamMemberItem) => (
        <div className={styles.memberCell}>
          <Avatar name={member.nickname} src={member.avatar ?? undefined} size="small" />
          <div className={styles.memberText}>
            <span className={styles.memberName}>{member.nickname}</span>
            <span className={styles.memberUsername}>@{member.username}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'role',
      title: 'Role',
      width: '110px',
      render: (member: TeamMemberItem) => (
        <Badge variant={member.role === 'member' ? 'outline' : 'default'} size="small">
          {TEAM_ROLE_LABELS[member.role]}
        </Badge>
      ),
    },
    {
      key: 'level',
      title: 'Level',
      width: '120px',
      render: (member: TeamMemberItem) => (
        <span>
          {member.levelName}
          <span className={styles.mutedText}> ({member.levelOrder})</span>
        </span>
      ),
    },
    {
      key: 'skills',
      title: 'Skills',
      render: (member: TeamMemberItem) =>
        member.skills.length > 0 ? (
          <span className={styles.skillsText}>
            {member.skills.map((skill) => skill.name).join(', ')}
          </span>
        ) : (
          <span className={styles.mutedText}>—</span>
        ),
    },
    {
      key: 'joinedAt',
      title: 'Joined',
      width: '120px',
      render: (member: TeamMemberItem) => formatDate(member.joinedAt),
    },
    {
      key: 'actions',
      title: 'Actions',
      width: '100px',
      render: (member: TeamMemberItem) => renderActions(member),
    },
  ]

  const sortedMembers = [...team.members].sort((firstMember, secondMember) => {
    const roleWeights: Record<string, number> = { admin: 3, subAdmin: 2, member: 1 }
    const roleDifference = roleWeights[secondMember.role] - roleWeights[firstMember.role]
    if (roleDifference !== 0) {
      return roleDifference
    }
    return secondMember.levelOrder - firstMember.levelOrder
  })

  const confirmTextConfig = resolveConfirmText()

  return (
    <>
      <Table<TeamMemberItem>
        columns={columns}
        rows={sortedMembers}
        rowKey={(member) => member.userId}
        emptyText="No team members yet"
      />
      <MemberLevelDialog
        open={levelTargetMember !== null}
        team={team}
        member={levelTargetMember}
        onClose={() => setLevelTargetMember(null)}
        onSaved={onChanged}
      />
      <ConfirmDialog
        open={pendingConfirm !== null}
        title={confirmTextConfig.title}
        description={confirmTextConfig.description}
        confirmText={confirmTextConfig.confirmText}
        danger
        loading={actionLoading}
        onConfirm={() => void handleConfirm()}
        onCancel={() => {
          if (!actionLoading) {
            setPendingConfirm(null)
          }
        }}
      />
    </>
  )
}
