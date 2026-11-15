/**
 * 认证上下文：集中管理当前登录用户、登录/注册/登出与团队角色判断。
 * 页面只通过 useAuth 读取认证状态，不直接操作 localStorage。
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import * as authApi from '../api/authApi'
import { getStoredToken, setStoredToken } from '../api/httpClient'
import type { CurrentUser, LoginPayload, RegisterPayload } from '../types/auth'
import type { TeamRole } from '../types/common'

/** 认证上下文暴露的接口。 */
interface AuthContextValue {
  /** 当前用户；未登录为 null。 */
  user: CurrentUser | null
  /** 初始化认证状态中。 */
  loading: boolean
  /** 登录。 */
  login: (payload: LoginPayload) => Promise<CurrentUser>
  /** 注册并自动登录。 */
  register: (payload: RegisterPayload) => Promise<CurrentUser>
  /** 退出登录。 */
  logout: () => Promise<void>
  /** 重新拉取当前用户信息。 */
  refreshMe: () => Promise<void>
  /** 判断当前用户是否在指定团队拥有指定角色。 */
  hasTeamRole: (teamId: number, role: TeamRole | TeamRole[]) => boolean
}

/** 认证上下文对象。 */
const AuthContext = createContext<AuthContextValue | null>(null)

/** 认证状态提供者。 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  /** 刷新当前用户信息。 */
  const refreshMe = useCallback(async (): Promise<void> => {
    if (!getStoredToken()) {
      setUser(null)
      return
    }
    const currentUser = await authApi.getCurrentUser()
    setUser(currentUser)
  }, [])

  /** 初始化：存在 token 时拉取用户信息。 */
  useEffect(() => {
    let cancelled = false
    const initialize = async (): Promise<void> => {
      try {
        await refreshMe()
      } catch {
        if (!cancelled) {
          setStoredToken(null)
          setUser(null)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }
    void initialize()
    return () => {
      cancelled = true
    }
  }, [refreshMe])

  /** 监听请求层广播的 401 事件，自动清理登录态。 */
  useEffect(() => {
    const handleUnauthorized = (): void => {
      setStoredToken(null)
      setUser(null)
    }
    window.addEventListener('tms:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('tms:unauthorized', handleUnauthorized)
  }, [])

  /** 登录。 */
  const login = useCallback(async (payload: LoginPayload): Promise<CurrentUser> => {
    const authResponse = await authApi.login(payload)
    setStoredToken(authResponse.token)
    setUser(authResponse.user)
    return authResponse.user
  }, [])

  /** 注册并自动登录。 */
  const register = useCallback(async (payload: RegisterPayload): Promise<CurrentUser> => {
    const authResponse = await authApi.register(payload)
    setStoredToken(authResponse.token)
    setUser(authResponse.user)
    return authResponse.user
  }, [])

  /** 退出登录。 */
  const logout = useCallback(async (): Promise<void> => {
    try {
      await authApi.logout()
    } catch {
      // 网络异常时仍清理本地登录态
    } finally {
      setStoredToken(null)
      setUser(null)
    }
  }, [])

  /** 判断团队角色。 */
  const hasTeamRole = useCallback(
    (teamId: number, role: TeamRole | TeamRole[]): boolean => {
      const membership = user?.teams.find((team) => team.teamId === teamId)
      if (!membership) {
        return false
      }
      return Array.isArray(role) ? role.includes(membership.role) : membership.role === role
    },
    [user],
  )

  const contextValue = useMemo<AuthContextValue>(
    () => ({ user, loading, login, register, logout, refreshMe, hasTeamRole }),
    [user, loading, login, register, logout, refreshMe, hasTeamRole],
  )

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
}

/** 读取认证上下文；必须在 AuthProvider 内使用。 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
