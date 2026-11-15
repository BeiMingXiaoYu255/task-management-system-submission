/**
 * 候选成员弹窗：列出团队内可作为任务执行人的成员（级别、角色、技能）。
 *
 * 接口 GET /teams/{teamId}/members/candidates 与发布任务共用，
 * 仅团队管理员/子管理员可调用，因此入口按钮只对这些角色展示。
 */

import { useMemo, useState } from 'react'

import { useMemberCandidates } from '../../hooks/useMemberCandidates'
import type { MemberCandidateItem, TeamDetail } from '../../types/team'
import { TEAM_ROLE_LABELS } from '../../utils/displayUtils'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'
import Table from '../ui/Table'
import styles from './MemberCandidateDialog.module.css'

/** MemberCandidateDialog 组件属性。 */
export interface MemberCandidateDialogProps {
  /** 弹窗是否打开。 */
  open: boolean
  /** 团队详情。 */
  team: TeamDetail
  /** 关闭回调。 */
  onClose: () => void
}

/** 候选成员弹窗。 */
export default function MemberCandidateDialog({ open, team, onClose }: MemberCandidateDialogProps) {
  const [keyword, setKeyword] = useState<string>('')
  const candidatesState = useMemberCandidates(team.id, open)
  const candidates = candidatesState.data ?? []

  /** 按昵称/用户名/技能关键词过滤候选成员。 */
  const filteredCandidates = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase()
    if (normalizedKeyword === '') {
      return candidates
    }
    return candidates.filter(
      (candidate) =>
        candidate.nickname.toLowerCase().includes(normalizedKeyword) ||
        candidate.username.toLowerCase().includes(normalizedKeyword) ||
        candidate.skills.some((skill) => skill.name.toLowerCase().includes(normalizedKeyword)),
    )
  }, [candidates, keyword])

  /** 表头列定义。 */
  const columns = [
    {
      key: 'member',
      title: 'Member',
      render: (candidate: MemberCandidateItem) => (
        <div className={styles.memberCell}>
          <span className={styles.memberName}>{candidate.nickname}</span>
          <span className={styles.memberUsername}>@{candidate.username}</span>
        </div>
      ),
    },
    {
      key: 'level',
      title: 'Level',
      width: '140px',
      render: (candidate: MemberCandidateItem) =>
        candidate.levelName + ' (Level ' + candidate.levelOrder + ')',
    },
    {
      key: 'role',
      title: 'Role',
      width: '110px',
      render: (candidate: MemberCandidateItem) => (
        <Badge variant={candidate.role === 'member' ? 'outline' : 'default'} size="small">
          {TEAM_ROLE_LABELS[candidate.role]}
        </Badge>
      ),
    },
    {
      key: 'skills',
      title: 'Skills',
      render: (candidate: MemberCandidateItem) =>
        candidate.skills.length > 0 ? (
          <span className={styles.skillsText}>
            {candidate.skills.map((skill) => skill.name).join(', ')}
          </span>
        ) : (
          <span className={styles.mutedText}>—</span>
        ),
    },
  ]

  return (
    <Modal
      open={open}
      title="Candidate Members"
      size="large"
      onClose={onClose}
      footer={
        <div className={styles.footer}>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      }
    >
      <div className={styles.dialogBody}>
        <p className={styles.hintText}>
          When publishing a task, choose assignees from these members. Members can only select members with a lower level.
        </p>
        <Input
          label="Search Members"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="Search by nickname, username, or skill"
        />
        {candidatesState.error ? (
          <div className={styles.errorBox}>
            <span>{candidatesState.error}</span>
            <Button variant="secondary" size="small" onClick={candidatesState.reload}>
              Retry
            </Button>
          </div>
        ) : candidatesState.loading ? (
          <div className={styles.loadingBox}>
            <Spinner size="small" />
            <span>Loading candidates...</span>
          </div>
        ) : (
          <Table<MemberCandidateItem>
            columns={columns}
            rows={filteredCandidates}
            rowKey={(candidate) => candidate.userId}
            emptyText="No matching candidates"
          />
        )}
      </div>
    </Modal>
  )
}
