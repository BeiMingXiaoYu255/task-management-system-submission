/**
 * 任务个人操作 Hook：封装接受/拒绝/提交完成/取消/审核五种操作。
 *
 * 统一处理：互斥的加载态（同一时间只允许一个操作进行）、成功提示、
 * 失败中文提示，以及操作成功后回传最新任务详情给页面刷新视图。
 */

import { useCallback, useRef, useState } from 'react'

import * as taskApi from '../api/taskApi'
import { useToast } from '../context/ToastContext'
import type { ReviewTaskPayload, TaskDetail } from '../types/task'
import { getErrorMessage } from './errorMessage'

/** 任务操作类型标识。 */
export type TaskActionKey = 'accept' | 'decline' | 'submit' | 'cancel' | 'review'

/** useTaskActions 对外接口。 */
export interface TaskActions {
  /** 当前正在执行的操作；无操作时为 null。 */
  pendingAction: TaskActionKey | null
  /** 接受可选任务，成功返回最新详情。 */
  accept: (taskId: number) => Promise<TaskDetail | null>
  /** 拒绝可选任务，成功返回最新详情。 */
  decline: (taskId: number) => Promise<TaskDetail | null>
  /** 提交完成，进入待审核，成功返回最新详情。 */
  submit: (taskId: number) => Promise<TaskDetail | null>
  /** 取消任务（发布者/团队管理员），成功返回最新详情。 */
  cancel: (taskId: number) => Promise<TaskDetail | null>
  /** 审核某个执行人的提交，成功返回最新详情。 */
  review: (taskId: number, payload: ReviewTaskPayload) => Promise<TaskDetail | null>
}

/**
 * 创建任务操作集合。
 *
 * @param onChanged 任意操作成功后的回调（页面据此刷新详情或列表）
 */
export function useTaskActions(onChanged?: (task: TaskDetail) => void): TaskActions {
  const { showToast } = useToast()
  const [pendingAction, setPendingAction] = useState<TaskActionKey | null>(null)
  /** 保存最新回调引用，避免因内联回调变化导致操作函数频繁重建。 */
  const onChangedRef = useRef<((task: TaskDetail) => void) | undefined>(onChanged)
  onChangedRef.current = onChanged

  /** 执行单个操作：互斥、错误提示、成功提示与回调集中处理。 */
  const runAction = useCallback(
    async (
      actionKey: TaskActionKey,
      operation: () => Promise<TaskDetail>,
      successMessage: string,
    ): Promise<TaskDetail | null> => {
      if (pendingAction !== null) {
        return null
      }
      setPendingAction(actionKey)
      try {
        const updatedTask = await operation()
        showToast(successMessage, 'success')
        onChangedRef.current?.(updatedTask)
        return updatedTask
      } catch (caughtError: unknown) {
        showToast(getErrorMessage(caughtError), 'error')
        return null
      } finally {
        setPendingAction(null)
      }
    },
    [pendingAction, showToast],
  )

  const accept = useCallback(
    (taskId: number): Promise<TaskDetail | null> =>
      runAction('accept', () => taskApi.acceptTask(taskId), 'Task accepted'),
    [runAction],
  )

  const decline = useCallback(
    (taskId: number): Promise<TaskDetail | null> =>
      runAction('decline', () => taskApi.declineTask(taskId), 'Task declined'),
    [runAction],
  )

  const submit = useCallback(
    (taskId: number): Promise<TaskDetail | null> =>
      runAction('submit', () => taskApi.submitTask(taskId), 'Submitted. Waiting for the publisher to review.'),
    [runAction],
  )

  const cancel = useCallback(
    (taskId: number): Promise<TaskDetail | null> =>
      runAction('cancel', () => taskApi.cancelTask(taskId), 'Task cancelled'),
    [runAction],
  )

  const review = useCallback(
    (taskId: number, payload: ReviewTaskPayload): Promise<TaskDetail | null> =>
      runAction(
        'review',
        () => taskApi.reviewTask(taskId, payload),
        payload.approved ? 'Approved. The task has been archived.' : 'Rejected. The task is back in progress.',
      ),
    [runAction],
  )

  return { pendingAction, accept, decline, submit, cancel, review }
}
