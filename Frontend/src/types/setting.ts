/** 用户界面设置类型。 */

/** 主题。 */
export type ThemeMode = 'light' | 'dark'

/** 字号档位。 */
export type FontSizeMode = 'small' | 'medium' | 'large'

/** 字体族档位。 */
export type FontFamilyMode = 'system' | 'serif' | 'sans' | 'monospace'

/** 用户界面设置。 */
export interface UserSettings {
  theme: ThemeMode
  fontSize: FontSizeMode
  fontFamily: FontFamilyMode
}

/** 修改设置的请求体。 */
export interface UpdateSettingsPayload {
  theme: ThemeMode
  fontSize: FontSizeMode
  fontFamily: FontFamilyMode
}
