/**
 * 便签待办页面：适配 380×620 独立小窗的极简待办清单。
 *
 * 设计要点：
 * 1. 不依赖 AppShell（已挂载独立路由），只保留标题栏与清单；
 * 2. 我的待办按优先级从高到低排序，支持勾选接受/完成与手动刷新；
 * 3. 点击标题打开主窗口（桌面模式优先唤起主窗口，浏览器模式新开 /todos）；
 * 4. 支持 Esc 关闭窗口：桌面模式调用 closeCurrentWindow 命令，浏览器调用 window.close()。
 */

import { useCallback, useEffect, useMemo, useState } from 'react'

import { acceptTask, submitTask } from '../../api/taskApi'
import { listTodos } from '../../api/todoApi'
import Button from '../../components/ui/Button'
import Checkbox from '../../components/ui/Checkbox'
import EmptyState from '../../components/ui/EmptyState'
import Spinner from '../../components/ui/Spinner'
import { useToast } from '../../context/ToastContext'
import type { TaskPriority } from '../../types/common'
import type { TodoItem } from '../../types/todo'
import {
  PRIORITY_WEIGHTS,
  getAssignmentStatusLabel,
  getPriorityLabel,
} from '../../utils/displayUtils'
import { formatDueDescription } from '../../utils/formatUtils'
import styles from './StickyTodoPage.module.css'

/** 便签页一次加载的待办数量。 */
const STICKY_PAGE_SIZE = 50

/** 调用桌面原生命令；命令不存在时返回 null，由调用方降级处理。 */
async function invokeDesktopCommand(commandName: string): Promise<string | null> {
  if (!window.__TAURI_INTERNALS__) {
    return null
  }
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    return await invoke<string>(commandName)
  } catch {
    return null
  }
}

/** 关闭便签小窗：桌面模式调用原生命令，浏览器模式退回 window.close()。 */
async function closeStickyWindow(): Promise<void> {
  if (window.__TAURI_INTERNALS__) {
    try {
      const { invoke } = await import('@tauri-apps/api/core')
      await invoke('closeCurrentWindow')
      return
    } catch {
      // 原生命令不可用时继续尝试浏览器关闭
    }
  }
  window.close()
}

/** 便签待办页面。 */
export default function StickyTodoPage() {
  const { showToast } = useToast()
  const [todoItems, setTodoItems] = useState<TodoItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [processingAssignmentId, setProcessingAssignmentId] = useState<number | null>(null)

  /** 拉取我的未归档待办（按优先级倒序）。 */
  const loadTodos = useCallback(async (): Promise<void> => {
    setLoading(true)
    setErrorMessage(null)
    try {
      const pageResult = await listTodos({
        sortBy: 'priority',
        sortOrder: 'desc',
        pageSize: STICKY_PAGE_SIZE,
        page: 1,
      })
      setTodoItems(pageResult.items)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load to-dos')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadTodos()
  }, [loadTodos])

  /** Esc 关闭窗口。 */
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key !== 'Escape') {
        return
      }
      void closeStickyWindow()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  /** 客户端再按优先级排序一次，避免后端排序口径缺失。 */
  const sortedTodoItems = useMemo(() => {
    const priorityWeight = (priority: string): number =>
      PRIORITY_WEIGHTS[priority as TaskPriority] ?? 0
    return [...todoItems].sort((leftItem, rightItem) => priorityWeight(rightItem.priority) - priorityWeight(leftItem.priority))
  }, [todoItems])

  /** 点击标题：桌面模式唤起主窗口，浏览器模式打开主窗口页面。 */
  const openMainWindow = async (): Promise<void> => {
    const invokeResult = await invokeDesktopCommand('showMainWindow')
    if (invokeResult === null) {
      window.open('/todos', '_blank')
    }
  }

  /** 勾选待办：待接受任务执行接受，进行中任务提交完成。 */
  const handleToggleTodo = async (todoItem: TodoItem): Promise<void> => {
    if (todoItem.assignmentStatus === 'pendingAcceptance') {
      setProcessingAssignmentId(todoItem.assignmentId)
      try {
        await acceptTask(todoItem.taskId)
        showToast('Task accepted: ' + todoItem.title, 'success')
        await loadTodos()
      } catch (error) {
        showToast(error instanceof Error ? error.message : 'Failed to accept task', 'error')
      } finally {
        setProcessingAssignmentId(null)
      }
      return
    }
    if (todoItem.assignmentStatus === 'inProgress') {
      setProcessingAssignmentId(todoItem.assignmentId)
      try {
        await submitTask(todoItem.taskId)
        showToast('Task submitted: ' + todoItem.title + '. Waiting for review.', 'success')
        await loadTodos()
      } catch (error) {
        showToast(error instanceof Error ? error.message : 'Failed to submit task', 'error')
      } finally {
        setProcessingAssignmentId(null)
      }
    }
  }

  /** 判断待办是否可勾选操作。 */
  const canToggleTodo = (todoItem: TodoItem): boolean =>
    todoItem.assignmentStatus === 'pendingAcceptance' || todoItem.assignmentStatus === 'inProgress'

  return (
    <div className={styles.stickyRoot}>
      <header className={styles.stickyHeader}>
        <div className={styles.headerTitleArea}>
          <h1 className={styles.headerTitle}>Sticky To-dos</h1>
          <span className={styles.headerCount}>{sortedTodoItems.length} items</span>
        </div>
        <div className={styles.headerActions}>
          <Button variant="ghost" size="small" onClick={() => void loadTodos()}>
            Refresh
          </Button>
          <Button variant="ghost" size="small" onClick={() => void openMainWindow()}>
            Main Window
          </Button>
          <Button variant="ghost" size="small" onClick={() => void closeStickyWindow()}>
            Close
          </Button>
        </div>
      </header>

      <main className={styles.stickyBody}>
        {loading ? (
          <div className={styles.stateArea}>
            <Spinner size="small" />
            <span>Loading to-dos...</span>
          </div>
        ) : errorMessage !== null ? (
          <div className={styles.stateAreaColumn}>
            <span className={styles.errorText}>{errorMessage}</span>
            <Button variant="secondary" size="small" onClick={() => void loadTodos()}>
              Reload
            </Button>
          </div>
        ) : sortedTodoItems.length === 0 ? (
          <EmptyState title="No to-dos yet" description="You have no to-dos to handle right now." />
        ) : (
          <ul className={styles.todoList}>
            {sortedTodoItems.map((todoItem) => (
              <li key={todoItem.assignmentId} className={styles.todoRow}>
                <Checkbox
                  checked={false}
                  disabled={!canToggleTodo(todoItem) || processingAssignmentId !== null}
                  onChange={() => void handleToggleTodo(todoItem)}
                  label={
                    <span className={styles.visuallyHidden}>
                      {todoItem.assignmentStatus === 'pendingAcceptance' ? 'Accept Task' : 'Submit Completion'}
                    </span>
                  }
                />
                <div className={styles.todoContent}>
                  <button
                    type="button"
                    className={styles.todoTitleButton}
                    onClick={() => void openMainWindow()}
                    title="Open the main window for details"
                  >
                    {todoItem.title}
                  </button>
                  <div className={styles.todoMetaRow}>
                    <span className={styles.todoMeta}>{todoItem.teamName}</span>
                    <span className={styles.todoMeta}>{getPriorityLabel(todoItem.priority)} priority</span>
                    <span className={todoItem.overdue ? styles.overdueText : styles.todoMeta}>
                      {formatDueDescription(todoItem.dueAt)}
                    </span>
                  </div>
                </div>
                <span className={styles.statusText}>
                  {getAssignmentStatusLabel(todoItem.assignmentStatus)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </main>

      <footer className={styles.stickyFooter}>
        <span className={styles.footerHint}>Check to accept or submit completion · Press Esc or click Close to close</span>
      </footer>
    </div>
  )
}
