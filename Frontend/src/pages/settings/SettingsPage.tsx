/**
 * 系统设置页面：外观设置、账号安全、AI 配置与系统信息四大区块。
 *
 * 页面职责：
 * 1. 加载服务端界面设置并应用到 ThemeContext（只加载一次）；
 * 2. 组合外观 / 安全 / AI 配置 / 系统信息四个功能区块；
 * 3. 各区块自行处理保存与错误提示，页面只负责布局。
 */

import { useEffect } from 'react'

import AiConfigSection from '../../components/settings/AiConfigSection'
import AppearanceSection from '../../components/settings/AppearanceSection'
import SecuritySection from '../../components/settings/SecuritySection'
import SystemSection from '../../components/settings/SystemSection'
import Card from '../../components/ui/Card'
import PageHeader from '../../components/ui/PageHeader'
import { useTheme } from '../../context/ThemeContext'
import { useToast } from '../../context/ToastContext'
import { getSettings } from '../../api/settingApi'
import styles from './SettingsPage.module.css'

/** 系统设置页面。 */
export default function SettingsPage() {
  const { applyUserSettings } = useTheme()
  const { showToast } = useToast()

  /** 页面加载时同步服务端保存的界面设置。 */
  useEffect(() => {
    let cancelled = false
    const loadUserSettings = async (): Promise<void> => {
      try {
        const userSettings = await getSettings()
        if (!cancelled) {
          applyUserSettings(userSettings)
        }
      } catch (error) {
        if (!cancelled) {
          showToast(error instanceof Error ? error.message : 'Failed to load interface settings', 'error')
        }
      }
    }
    void loadUserSettings()
    return () => {
      cancelled = true
    }
  }, [applyUserSettings, showToast])

  return (
    <div className={styles.pageRoot}>
      <PageHeader
        title="System Settings"
        description="Adjust the interface appearance, manage account security, configure AI dispatch, and view system runtime information."
      />
      <div className={styles.settingsStack}>
        <Card title="Appearance Settings">
          <AppearanceSection />
        </Card>
        <Card title="Account Security">
          <SecuritySection />
        </Card>
        <Card title="AI Configuration">
          <AiConfigSection />
        </Card>
        <Card title="System Information">
          <SystemSection />
        </Card>
      </div>
    </div>
  )
}
