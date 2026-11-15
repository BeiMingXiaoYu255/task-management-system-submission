/**
 * 主题上下文：管理主题、字号、字体族，并同步到 html 根元素与 localStorage。
 * 登录后由 AppShell 调用 applyUserSettings 应用服务端保存的界面设置。
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import type { FontFamilyMode, FontSizeMode, ThemeMode, UserSettings } from '../types/setting'

/** 本地保存设置的键名。 */
const SETTINGS_STORAGE_KEY = 'tms.settings'

/** 默认界面设置。 */
export const DEFAULT_USER_SETTINGS: UserSettings = {
  theme: 'light',
  fontSize: 'medium',
  fontFamily: 'system',
}

/** 主题上下文暴露的接口。 */
interface ThemeContextValue extends UserSettings {
  /** 切换主题。 */
  setTheme: (theme: ThemeMode) => void
  /** 切换字号。 */
  setFontSize: (fontSize: FontSizeMode) => void
  /** 切换字体。 */
  setFontFamily: (fontFamily: FontFamilyMode) => void
  /** 应用服务端返回的完整设置。 */
  applyUserSettings: (settings: UserSettings) => void
}

/** 主题上下文对象。 */
const ThemeContext = createContext<ThemeContextValue | null>(null)

/** 读取本地缓存的界面设置。 */
function readLocalSettings(): UserSettings {
  try {
    const rawValue = localStorage.getItem(SETTINGS_STORAGE_KEY)
    if (!rawValue) {
      return DEFAULT_USER_SETTINGS
    }
    const parsedValue = JSON.parse(rawValue) as Partial<UserSettings>
    return {
      theme: parsedValue.theme === 'dark' ? 'dark' : 'light',
      fontSize: parsedValue.fontSize ?? 'medium',
      fontFamily: parsedValue.fontFamily ?? 'system',
    }
  } catch {
    return DEFAULT_USER_SETTINGS
  }
}

/** 主题提供者。 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<UserSettings>(readLocalSettings)

  /** 应用设置到 html 根元素并写入本地缓存。 */
  useEffect(() => {
    const rootElement = document.documentElement
    rootElement.dataset.theme = settings.theme
    rootElement.dataset.fontSize = settings.fontSize
    rootElement.dataset.fontFamily = settings.fontFamily
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
    } catch {
      // 本地存储不可用时忽略
    }
  }, [settings])

  /** 合并并应用新的设置。 */
  const applyUserSettings = useCallback((nextSettings: UserSettings): void => {
    setSettings(nextSettings)
  }, [])

  const contextValue = useMemo<ThemeContextValue>(
    () => ({
      ...settings,
      setTheme: (theme: ThemeMode) => setSettings((previous) => ({ ...previous, theme })),
      setFontSize: (fontSize: FontSizeMode) => setSettings((previous) => ({ ...previous, fontSize })),
      setFontFamily: (fontFamily: FontFamilyMode) =>
        setSettings((previous) => ({ ...previous, fontFamily })),
      applyUserSettings,
    }),
    [settings, applyUserSettings],
  )

  return <ThemeContext.Provider value={contextValue}>{children}</ThemeContext.Provider>
}

/** 读取主题上下文；必须在 ThemeProvider 内使用。 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (context === null) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
