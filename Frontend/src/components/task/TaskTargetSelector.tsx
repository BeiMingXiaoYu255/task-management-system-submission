/**
 * 任务接收者选择器：区分“指定成员”与“按级别范围”两种分配方式。
 *
 * - 指定成员：按级别分组勾选候选成员，并提供 AI 推荐面板一键填充；
 * - 级别范围：选择级别上下限，由后端按范围匹配成员；
 * - 权限提示：普通成员只能给级别低于自己的成员布置任务。
 */

import type { MemberCandidateItem, TeamLevel } from '../../types/team'
import type { AssignmentMode, TeamRole } from '../../types/common'
import Button from '../ui/Button'
import Checkbox from '../ui/Checkbox'
import RadioGroup from '../ui/RadioGroup'
import Select from '../ui/Select'
import AiRecommendPanel from './AiRecommendPanel'
import styles from './TaskTargetSelector.module.css'

/** 分配方式选项。 */
const ASSIGNMENT_MODE_OPTIONS = [
  { value: 'specific', label: 'Specific Members', description: 'Pick assignees one by one' },
  { value: 'levelRange', label: 'Level Range', description: 'Auto-assign by member level range' },
]

/** TaskTargetSelector 组件属性。 */
export interface TaskTargetSelectorProps {
  /** 团队 ID。 */
  teamId: number
  /** 分配方式。 */
  assignmentMode: AssignmentMode
  /** 已选成员 ID 列表。 */
  targetUserIds: number[]
  /** 级别范围下限（字符串形式，空串表示未选）。 */
  targetLevelMin: string
  /** 级别范围上限（字符串形式，空串表示未选）。 */
  targetLevelMax: string
  /** 团队级别列表。 */
  levels: TeamLevel[]
  /** 候选成员列表。 */
  candidates: MemberCandidateItem[]
  /** 候选成员是否加载中。 */
  candidatesLoading: boolean
  /** 候选成员加载错误。 */
  candidatesError: string | null
  /** 当前用户团队角色。 */
  currentUserRole: TeamRole
  /** 当前用户级别数值。 */
  currentUserLevelOrder: number
  /** 任务标题（供 AI 推荐）。 */
  taskTitle: string
  /** 任务描述（供 AI 推荐）。 */
  taskDescription: string
  /** 任务优先级（供 AI 推荐）。 */
  taskPriority: string
  /** 是否开启 AI 自动分配（开启后隐藏手动选择，仅展示 AI 预览）。 */
  autoAssign: boolean
  /** 所需技能标签（供 AI 推荐使用）。 */
  requiredSkillNames?: string[]
  /** 目标提示错误。 */
  error?: string
  onModeChange: (assignmentMode: AssignmentMode) => void
  onTargetUserIdsChange: (userIds: number[]) => void
  onLevelRangeChange: (levelMin: string, levelMax: string) => void
}

/** 任务接收者选择器。 */
export default function TaskTargetSelector({
  teamId,
  assignmentMode,
  targetUserIds,
  targetLevelMin,
  targetLevelMax,
  levels,
  candidates,
  candidatesLoading,
  candidatesError,
  currentUserRole,
  currentUserLevelOrder,
  taskTitle,
  taskDescription,
  taskPriority,
  autoAssign,
  requiredSkillNames = [],
  error,
  onModeChange,
  onTargetUserIdsChange,
  onLevelRangeChange,
}: TaskTargetSelectorProps) {
  /** AI 自动分配模式：隐藏手动选择，仅保留说明与推荐预览。 */
  if (autoAssign) {
    return (
      <div className={styles.selector}>
        <div className={styles.autoAssignSection}>
          <p className={styles.autoAssignTitle}>AI Auto-assignment enabled</p>
          <p className={styles.permissionHint}>
            The AI dispatcher selects assignees when the task is published, with no manual selection. If nothing matches, the publisher can assign from the task details page.
          </p>
        </div>
        <AiRecommendPanel
          teamId={teamId}
          title={taskTitle}
          description={taskDescription}
          priority={taskPriority}
          targetLevelMin={targetLevelMin === '' ? undefined : Number(targetLevelMin)}
          targetLevelMax={targetLevelMax === '' ? undefined : Number(targetLevelMax)}
          requiredSkillNames={requiredSkillNames}
          selectedUserIds={targetUserIds}
          onSelectUserIds={onTargetUserIdsChange}
          selectionEnabled={false}
        />
      </div>
    )
  }

  /** 级别下拉选项：按级别从高到低排列。 */
  const levelOptions = [...levels]
    .sort((firstLevel, secondLevel) => secondLevel.levelOrder - firstLevel.levelOrder)
    .map((teamLevel) => ({
      value: String(teamLevel.levelOrder),
      label: teamLevel.name + ' (Level ' + teamLevel.levelOrder + ')',
    }))

  /** 普通成员只能选择级别低于自己的候选成员（与后端权限规则一致）。 */
  const selectableCandidates =
    currentUserRole === 'member'
      ? candidates.filter((candidate) => candidate.levelOrder < currentUserLevelOrder)
      : candidates

  /** 按级别分组候选成员，级别高的分组在前。 */
  const groupedCandidates = [...levels]
    .sort((firstLevel, secondLevel) => secondLevel.levelOrder - firstLevel.levelOrder)
    .map((teamLevel) => ({
      teamLevel,
      members: selectableCandidates.filter(
        (candidate) => candidate.levelOrder === teamLevel.levelOrder,
      ),
    }))
    .filter((group) => group.members.length > 0)

  /** 切换单个候选成员。 */
  const toggleCandidate = (userId: number, checked: boolean): void => {
    if (checked) {
      onTargetUserIdsChange([...targetUserIds, userId])
    } else {
      onTargetUserIdsChange(targetUserIds.filter((selectedUserId) => selectedUserId !== userId))
    }
  }

  /** 检查某个级别分组的成员是否全部选中。 */
  const isLevelGroupSelected = (members: MemberCandidateItem[]): boolean =>
    members.length > 0 && members.every((member) => targetUserIds.includes(member.userId))

  /** 勾选/取消某个级别分组。 */
  const toggleLevelGroup = (members: MemberCandidateItem[], checked: boolean): void => {
    const memberUserIds = members.map((member) => member.userId)
    if (checked) {
      const mergedUserIds = new Set<number>(targetUserIds)
      memberUserIds.forEach((userId) => mergedUserIds.add(userId))
      onTargetUserIdsChange(Array.from(mergedUserIds))
    } else {
      onTargetUserIdsChange(
        targetUserIds.filter((selectedUserId) => !memberUserIds.includes(selectedUserId)),
      )
    }
  }

  return (
    <div className={styles.selector}>
      <div className={styles.section}>
        <span className={styles.sectionLabel}>Assignment Method</span>
        <RadioGroup<AssignmentMode>
          value={assignmentMode}
          onChange={onModeChange}
          options={ASSIGNMENT_MODE_OPTIONS}
        />
        {currentUserRole === 'member' ? (
          <p className={styles.permissionHint}>
            Your current level is {currentUserLevelOrder}. You can only assign tasks to members with a lower level.
          </p>
        ) : null}
      </div>

      {assignmentMode === 'specific' ? (
        <div className={styles.section}>
          <div className={styles.targetHeader}>
            <span className={styles.sectionLabel}>Select Assignees (selected {targetUserIds.length} members)</span>
            {candidatesLoading ? <span className={styles.loadingText}>Loading candidates...</span> : null}
          </div>
          {candidatesError ? <p className={styles.errorText}>{candidatesError}</p> : null}
          {!candidatesLoading && groupedCandidates.length === 0 ? (
            <p className={styles.emptyHint}>No selectable members (they may all be at your level or higher).</p>
          ) : null}
          <div className={styles.candidateGroups}>
            {groupedCandidates.map((group) => (
              <div key={group.teamLevel.id} className={styles.candidateGroup}>
                <div className={styles.groupHeader}>
                  <span className={styles.groupName}>
                    {group.teamLevel.name} ({group.members.length} members)
                  </span>
                  <Button
                    variant="ghost"
                    size="small"
                    onClick={() => toggleLevelGroup(group.members, !isLevelGroupSelected(group.members))}
                  >
                    {isLevelGroupSelected(group.members) ? 'Clear Selection' : 'Select Group'}
                  </Button>
                </div>
                <ul className={styles.candidateList}>
                  {group.members.map((member) => (
                    <li key={member.userId} className={styles.candidateItem}>
                      <Checkbox
                        checked={targetUserIds.includes(member.userId)}
                        onChange={(event) => toggleCandidate(member.userId, event.target.checked)}
                        label={
                          <span className={styles.candidateLabel}>
                            <span className={styles.candidateName}>{member.nickname}</span>
                            <span className={styles.candidateMeta}>
                              @{member.username} · {member.levelName}
                            </span>
                            {member.skills.length > 0 ? (
                              <span className={styles.candidateSkills}>
                                {member.skills.map((skill) => skill.name).join(', ')}
                              </span>
                            ) : null}
                          </span>
                        }
                      />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          {error ? <p className={styles.errorText}>{error}</p> : null}
          <AiRecommendPanel
            teamId={teamId}
            title={taskTitle}
            description={taskDescription}
            priority={taskPriority}
            targetLevelMin={
              targetLevelMin === '' ? undefined : Number(targetLevelMin)
            }
            targetLevelMax={
              targetLevelMax === '' ? undefined : Number(targetLevelMax)
            }
            requiredSkillNames={requiredSkillNames}
            selectedUserIds={targetUserIds}
            onSelectUserIds={onTargetUserIdsChange}
          />
        </div>
      ) : (
        <div className={styles.section}>
          <div className={styles.rangeRow}>
            <Select
              label="Minimum Level"
              value={targetLevelMin}
              onChange={(nextValue) => onLevelRangeChange(String(nextValue), targetLevelMax)}
              options={levelOptions}
              placeholder="Select the minimum level"
            />
            <Select
              label="Maximum Level"
              value={targetLevelMax}
              onChange={(nextValue) => onLevelRangeChange(targetLevelMin, String(nextValue))}
              options={levelOptions}
              placeholder="Select the maximum level"
            />
          </div>
          <p className={styles.permissionHint}>
            All members within the level range will be assigned. The range must cover lower levels; members cannot assign tasks to their own level or higher.
          </p>
          {error ? <p className={styles.errorText}>{error}</p> : null}
        </div>
      )}
    </div>
  )
}
