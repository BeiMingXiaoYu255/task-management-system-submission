/**
 * 外观设置区块：主题、字号、字体族。
 *
 * 交互约定：
 * 1. 点击选项立即调用 ThemeContext 对应 setter，界面即时生效；
 * 2. 立即调用 settingApi.updateSettings 持久化到服务端；
 * 3. 保存失败时通过 toast 提示（本地已生效的设置不回滚，避免闪烁）。
 */

import { useState } from 'react'

import { updateSettings } from '../../api/settingApi'
import { useTheme } from '../../context/ThemeContext'
import { useToast } from '../../context/ToastContext'
import type { FontFamilyMode, FontSizeMode, ThemeMode } from '../../types/setting'
import Button from '../ui/Button'
import styles from './AppearanceSection.module.css'

/** 外观选项配置。 */
interface AppearanceOption<TValue extends string> {
  value: TValue
  label: string
  description: string
}

/** 主题选项。 */
const THEME_OPTIONS: AppearanceOption<ThemeMode>[] = [
  { value: 'light', label: 'Light', description: 'Black text on white, ideal for daytime work' },
  { value: 'dark', label: 'Dark', description: 'Low-saturation grayscale, gentler at night' },
]

/** 字号选项。 */
const FONT_SIZE_OPTIONS: AppearanceOption<FontSizeMode>[] = [
  { value: 'small', label: 'Small', description: 'Compact, ideal for information-dense pages' },
  { value: 'medium', label: 'Medium', description: 'Default size with balanced readability' },
  { value: 'large', label: 'Large', description: 'Larger text for comfortable viewing from a distance' },
]

/** 字体族选项。 */
const FONT_FAMILY_OPTIONS: AppearanceOption<FontFamilyMode>[] = [
  { value: 'system', label: 'System Default', description: 'Follow the operating system font' },
  { value: 'sans', label: 'Sans-serif', description: 'Modern, clean sans-serif font' },
  { value: 'serif', label: 'Serif', description: 'Serif font suited to long-form reading' },
  { value: 'monospace', label: 'Monospace', description: 'Monospace font for code and data' },
]

/** 外观设置区块。 */
export default function AppearanceSection() {
  const { theme, fontSize, fontFamily, setTheme, setFontSize, setFontFamily } = useTheme()
  const { showToast } = useToast()
  const [saving, setSaving] = useState<boolean>(false)

  /** 持久化完整外观设置；失败时提示用户。 */
  const persistSettings = async (
    nextTheme: ThemeMode,
    nextFontSize: FontSizeMode,
    nextFontFamily: FontFamilyMode,
  ): Promise<void> => {
    setSaving(true)
    try {
      await updateSettings({
        theme: nextTheme,
        fontSize: nextFontSize,
        fontFamily: nextFontFamily,
      })
      showToast('Appearance settings saved', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to save appearance settings', 'error')
    } finally {
      setSaving(false)
    }
  }

  /** 切换主题：立即生效并保存。 */
  const handleThemeChange = (nextTheme: ThemeMode): void => {
    setTheme(nextTheme)
    void persistSettings(nextTheme, fontSize, fontFamily)
  }

  /** 切换字号：立即生效并保存。 */
  const handleFontSizeChange = (nextFontSize: FontSizeMode): void => {
    setFontSize(nextFontSize)
    void persistSettings(theme, nextFontSize, fontFamily)
  }

  /** 切换字体族：立即生效并保存。 */
  const handleFontFamilyChange = (nextFontFamily: FontFamilyMode): void => {
    setFontFamily(nextFontFamily)
    void persistSettings(theme, fontSize, nextFontFamily)
  }

  /** 渲染一组外观选项按钮。 */
  const renderOptionGroup = <TValue extends string>(
    options: AppearanceOption<TValue>[],
    currentValue: TValue,
    onSelect: (nextValue: TValue) => void,
  ) => (
    <div className={styles.optionList}>
      {options.map((option) => (
        <Button
          key={option.value}
          variant={option.value === currentValue ? 'primary' : 'secondary'}
          size="small"
          onClick={() => onSelect(option.value)}
          title={option.description}
        >
          {option.label}
        </Button>
      ))}
    </div>
  )

  return (
    <div className={styles.appearanceLayout}>
      <div className={styles.settingRow}>
        <div className={styles.settingLabelArea}>
          <span className={styles.settingLabel}>Theme</span>
          <span className={styles.settingHint}>Takes effect immediately</span>
        </div>
        {renderOptionGroup(THEME_OPTIONS, theme, handleThemeChange)}
      </div>
      <div className={styles.settingRow}>
        <div className={styles.settingLabelArea}>
          <span className={styles.settingLabel}>Font Size</span>
          <span className={styles.settingHint}>Adjust the global base font size</span>
        </div>
        {renderOptionGroup(FONT_SIZE_OPTIONS, fontSize, handleFontSizeChange)}
      </div>
      <div className={styles.settingRow}>
        <div className={styles.settingLabelArea}>
          <span className={styles.settingLabel}>Font</span>
          <span className={styles.settingHint}>Choose the global font family</span>
        </div>
        {renderOptionGroup(FONT_FAMILY_OPTIONS, fontFamily, handleFontFamilyChange)}
      </div>
      {saving && <span className={styles.savingText}>Saving appearance settings ...</span>}
    </div>
  )
}
