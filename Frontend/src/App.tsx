/**
 * 应用路由表与全局 Provider 装配。
 *
 * 约定：路由路径已在开发契约中冻结，页面实现者只替换 pages 下的页面文件，
 * 不修改本文件中的路径与权限规则。
 */

import { type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import AppShell from './components/layout/AppShell'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { ToastProvider } from './context/ToastContext'
import AdminPage from './pages/admin/AdminPage'
import LoginPage from './pages/auth/LoginPage'
import CollaborationCenterPage from './pages/collaborations/CollaborationCenterPage'
import CollaborationDetailPage from './pages/collaborations/CollaborationDetailPage'
import CollaborationTaskDetailPage from './pages/collaborations/CollaborationTaskDetailPage'
import NotificationCenterPage from './pages/notifications/NotificationCenterPage'
import RegisterPage from './pages/auth/RegisterPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import NotFoundPage from './pages/NotFoundPage'
import ProfilePage from './pages/profile/ProfilePage'
import SettingsPage from './pages/settings/SettingsPage'
import StickyTodoPage from './pages/sticky/StickyTodoPage'
import TaskCenterPage from './pages/tasks/TaskCenterPage'
import TaskDetailPage from './pages/tasks/TaskDetailPage'
import TeamDetailPage from './pages/teams/TeamDetailPage'
import TeamListPage from './pages/teams/TeamListPage'
import TodoListPage from './pages/todos/TodoListPage'

/** 页面加载占位。 */
function PageLoading() {
  return <div className="page-container">Loading...</div>
}

/** 登录守卫：未登录跳转登录页。 */
function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <PageLoading />
  }
  if (user === null) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

/** 全局管理员守卫：普通用户跳转仪表盘。 */
function RequireGlobalAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (user === null) {
    return <Navigate to="/login" replace />
  }
  if (user.user.globalRole !== 'superAdmin' && user.user.globalRole !== 'globalAdmin') {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}

/** 路由与全局上下文装配。 */
export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <ThemeProvider>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/sticky"
                element={
                  <RequireAuth>
                    <StickyTodoPage />
                  </RequireAuth>
                }
              />
              <Route
                element={
                  <RequireAuth>
                    <AppShell />
                  </RequireAuth>
                }
              >
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/teams" element={<TeamListPage />} />
                <Route path="/teams/:teamId" element={<TeamDetailPage />} />
                <Route path="/teams/:teamId/tasks/:taskId" element={<TaskDetailPage />} />
                <Route path="/tasks" element={<TaskCenterPage />} />
                <Route path="/todos" element={<TodoListPage />} />
                <Route path="/collaborations" element={<CollaborationCenterPage />} />
                <Route path="/collaborations/:collaborationId" element={<CollaborationDetailPage />} />
                <Route path="/collaboration-tasks/:taskId" element={<CollaborationTaskDetailPage />} />
                <Route path="/notifications" element={<NotificationCenterPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route
                  path="/admin"
                  element={
                    <RequireGlobalAdmin>
                      <AdminPage />
                    </RequireGlobalAdmin>
                  }
                />
              </Route>
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AuthProvider>
        </ThemeProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}
