/**
 * AI 执行人推荐面板（v1.1）：展示调度路由、原因、得分、命中率、活跃负载与匹配技能。
 *
 * 交互：
 * - 手动选择模式下支持“选择首选”“全选推荐”与逐人勾选，勾选结果写入任务表单；
 * - AI 自动分配模式下仅作预览（selectionEnabled=false），发布后由调度器自动选择执行人。
 */

import { useCallback, useState } from 'react'

import { recommendAssignees } from '../../api/aiApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { RecommendResponse } from '../../types/ai'
import type { TaskPriority } from '../../types/common'
import AiStatusPanel from '../notification/AiStatusPanel'
import Button from '../ui/Button'
import Spinner from '../ui/Spinner'
import styles from './AiRecommendPanel.module.css'

/** 调度路由中文名。 */
const ROUTE_LABELS: Record<'local' | 'llm', string> = {
  local: 'Local Rule Engine',
  llm: 'LLM Recommendation',
}

/** 默认候选人数上限。 */
const DEFAULT_MAX_CANDIDATES = 10

/** AiRecommendPanel 组件属性。 */
export interface AiRecommendPanelProps {
  /** 团队 ID。 */
  teamId: number
  /** 任务标题（用于生成推荐）。 */
  title: string
  /** 任务描述（用于生成推荐）。 */
  description: string
  /** 优先级。 */
  priority: string
  /** 目标级别下限（级别范围模式时传入）。 */
  targetLevelMin?: number
  /** 目标级别上限（级别范围模式时传入）。 */
  targetLevelMax?: number
  /** 所需技能标签（与表单选择一致，可为空）。 */
  requiredSkillNames?: string[]
  /** 候选人数上限。 */
  maxCandidates?: number
  /** 当前已选中的成员 ID 列表。 */
  selectedUserIds: number[]
  /** 选中成员变化回调。 */
  onSelectUserIds: (userIds: number[]) => void
  /** 是否允许选择候选；自动分配预览模式传 false。 */
  selectionEnabled?: boolean
}

/** AI 执行人推荐面板。 */
export default function AiRecommendPanel({
  teamId,
  title,
  description,
  priority,
  targetLevelMin,
  targetLevelMax,
  requiredSkillNames = [],
  maxCandidates = DEFAULT_MAX_CANDIDATES,
  selectedUserIds,
  onSelectUserIds,
  selectionEnabled = true,
}: AiRecommendPanelProps) {
  const { showToast } = useToast()
  const [response, setResponse] = useState<RecommendResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [hasRequested, setHasRequested] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  /** 请求推荐结果并展示调度路由与原因。 */
  const requestRecommendations = useCallback(async (): Promise<void> => {
    if (title.trim().length < 2) {
      showToast('Enter a task title of at least 2 characters before requesting AI recommendations', 'info')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const recommendResponse = await recommendAssignees(teamId, {
        title: title.trim(),
        description: description.trim() === '' ? null : description.trim(),
        priority: priority as TaskPriority,
        targetLevelMin: targetLevelMin ?? null,
        targetLevelMax: targetLevelMax ?? null,
        requiredSkillNames: requiredSkillNames.length > 0 ? requiredSkillNames : undefined,
        maxCandidates,
      })
      setResponse(recommendResponse)
      setHasRequested(true)
      if (recommendResponse.candidates.length === 0) {
        showToast(recommendResponse.reason || 'No suitable candidates found. Adjust the required skills and try again.', 'info')
      }
    } catch (caughtError: unknown) {
      const message = getErrorMessage(caughtError, 'Failed to get AI recommendations. Please try again.')
      setError(message)
      showToast(message, 'error')
    } finally {
      setLoading(false)
    }
  }, [
    description,
    maxCandidates,
    priority,
    requiredSkillNames,
    showToast,
    targetLevelMax,
    targetLevelMin,
    teamId,
    title,
  ])

  const candidates = response?.candidates ?? []
  const isSelected = (userId: number): boolean => selectedUserIds.includes(userId)

  /** 切换单个推荐成员的选中状态。 */
  const toggleUser = (userId: number): void => {
    if (!selectionEnabled) {
      return
    }
    if (isSelected(userId)) {
      onSelectUserIds(selectedUserIds.filter((selectedUserId) => selectedUserId !== userId))
    } else {
      onSelectUserIds([...selectedUserIds, userId])
    }
  }

  /** 选择首选（排名第一的候选）。 */
  const selectPreferred = (): void => {
    if (!selectionEnabled || candidates.length === 0) {
      return
    }
    const preferredCandidate = candidates[0]
    onSelectUserIds([preferredCandidate.userId])
    showToast('Selected preferred assignee ' + preferredCandidate.nickname, 'success')
  }

  /** 全选推荐（与已选成员去重合并）。 */
  const selectAllRecommended = (): void => {
    if (!selectionEnabled || candidates.length === 0) {
      return
    }
    const mergedUserIds = new Set<number>(selectedUserIds)
    candidates.forEach((candidate) => mergedUserIds.add(candidate.userId))
    onSelectUserIds(Array.from(mergedUserIds))
  }

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <div className={styles.headerText}>
          <h4 className={styles.title}>{selectionEnabled ? 'AI Assignee Recommendation' : 'AI Assignment Preview'}</h4>
          <p className={styles.subtitle}>
            {selectionEnabled
              ? 'Candidates are ranked by skill match, active workload, and dispatch mode. Fill the selected members in one click.'
              : 'Preview only. AI auto-assigns assignees after the task is published.'}
          </p>
        </div>
        <Button
          variant="secondary"
          size="small"
          onClick={() => {
            void requestRecommendations()
          }}
          loading={loading}
        >
          {hasRequested ? 'Recommend Again' : 'Get Recommendations'}
        </Button>
      </header>

      <AiStatusPanel compact />

      <p className={styles.requirementLine}>
        {requiredSkillNames.length > 0
          ? 'Required skills: ' + requiredSkillNames.join(', ')
          : 'No required skills specified; inferred from the title and description'}
        {' · Max candidates: ' + String(maxCandidates)}
      </p>

      {error !== null ? (
        <div className={styles.errorBox}>
          <span className={styles.errorText}>{error}</span>
          <Button
            variant="ghost"
            size="small"
            onClick={() => {
              void requestRecommendations()
            }}
          >
            Retry
          </Button>
        </div>
      ) : null}

      {loading ? (
        <div className={styles.loadingBox}>
          <Spinner size="small" />
          <span className={styles.hint}>Calculating candidates...</span>
        </div>
      ) : null}

      {hasRequested && !loading ? (
        candidates.length === 0 ? (
          <p className={styles.emptyHint}>{response?.reason ?? 'No recommended members. Select candidates manually.'}</p>
        ) : (
          <>
            <div className={styles.summary}>
              <span className={styles.routeBadge}>
                {response?.route ? ROUTE_LABELS[response.route] : 'No route available'}
              </span>
              <span className={styles.reasonText}>{response?.reason}</span>
            </div>
            <div className={styles.toolbar}>
              <span className={styles.selectionSummary}>
                {selectionEnabled
                  ? 'Selected: ' + String(selectedUserIds.length) + ' · Candidates: ' + String(candidates.length)
                  : String(candidates.length) + ' candidates; assignees are chosen automatically after publishing'}
              </span>
              {selectionEnabled ? (
                <div className={styles.toolbarActions}>
                  <Button variant="ghost" size="small" onClick={selectPreferred}>
                    Select Preferred
                  </Button>
                  <Button variant="ghost" size="small" onClick={selectAllRecommended}>
                    Select All Recommended
                  </Button>
                </div>
              ) : (
                <span className={styles.hint}>AI selects assignees automatically after publishing</span>
              )}
            </div>
            <ul className={styles.recommendList}>
              {candidates.map((candidate, index) => {
                const selected = selectionEnabled && isSelected(candidate.userId)
                const itemClassName = selected
                  ? styles.recommendItem + ' ' + styles.recommendItemSelected
                  : styles.recommendItem
                return (
                  <li key={candidate.userId} className={itemClassName}>
                    <div className={styles.itemHeader}>
                      <span className={styles.rank}>{index + 1}</span>
                      <span className={styles.memberName}>{candidate.nickname}</span>
                      <span className={styles.memberLevel}>
                        @{candidate.username} · {candidate.levelName}
                      </span>
                      {index === 0 ? <span className={styles.preferredBadge}>Preferred</span> : null}
                      <span className={styles.score}>Score {candidate.score}</span>
                    </div>
                    <div className={styles.metrics}>
                      <span>Match rate {Math.round(candidate.matchRatio * 100)}%</span>
                      <span>Active to-dos: {candidate.activeTasks}</span>
                      <span>Route: {ROUTE_LABELS[candidate.route]}</span>
                    </div>
                    {candidate.matchedSkills.length > 0 ? (
                      <p className={styles.skills}>
                        Matched skills: {candidate.matchedSkills.join(', ')}
                      </p>
                    ) : (
                      <p className={styles.skills}>No skill tags matched; ranked by overall workload</p>
                    )}
                    <p className={styles.reasons}>{candidate.reasons.join('; ') || 'No recommendation reason'}</p>
                    {selectionEnabled ? (
                      <div className={styles.itemFooter}>
                        <Button
                          variant={selected ? 'secondary' : 'primary'}
                          size="small"
                          onClick={() => toggleUser(candidate.userId)}
                        >
                          {selected ? 'Deselect' : index === 0 ? 'Select Preferred' : 'Select'}
                        </Button>
                      </div>
                    ) : null}
                  </li>
                )
              })}
            </ul>
          </>
        )
      ) : null}
    </section>
  )
}
