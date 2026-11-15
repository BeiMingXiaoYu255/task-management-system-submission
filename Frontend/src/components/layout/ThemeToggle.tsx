/**
 * 主题切换按钮：在浅色/深色之间切换，并异步保存到服务端设置。
 * 保存失败不打断交互，本地主题已由 ThemeContext 立即生效。
 */

import { updateSettings } from '../../api/settingApi'
import { useTheme } from '../../context/ThemeContext'
import { IconMoon, IconSun } from './LayoutIcons'
import styles from './ThemeToggle.module.css'

/** 主题切换按钮。 */
export function ThemeToggle() {
  const { theme, fontSize, fontFamily, setTheme } = useTheme()
  const nextTheme = theme === 'dark' ? 'light' : 'dark'
  const buttonLabel = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'

  /** 切换主题并持久化到服务端。 */
  const handleToggleTheme = (): void => {
    setTheme(nextTheme)
    void updateSettings({ theme: nextTheme, fontSize, fontFamily }).catch(() => {
      // 服务端设置保存失败不影响本地主题切换，下次操作会重试
    })
  }

  return (
    <button
      type="button"
      className={styles.themeToggle}
      onClick={handleToggleTheme}
      aria-label={buttonLabel}
      title={buttonLabel}
    >
      {theme === 'dark' ? <IconSun size={16} /> : <IconMoon size={16} />}
    </button>
  )
}

export default ThemeToggle
