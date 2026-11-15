/**
 * 运行环境适配工具：桌面模式（Tauri）与浏览器模式的行为差异集中在此。
 */

/** 是否运行在 Tauri 桌面壳内。 */
export function isDesktopEnvironment(): boolean {
  return typeof window !== 'undefined' && Boolean(window.__TAURI_INTERNALS__)
}

/**
 * 打开便签待办小窗。
 * - 桌面模式：调用 Rust 命令 openStickyWindow 打开独立窗口；
 * - 浏览器模式：window.open 打开 /sticky 弹窗（380x620）。
 * 返回是否成功打开，供调用方提示用户。
 */
export async function openStickyWindow(): Promise<boolean> {
  if (isDesktopEnvironment()) {
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('openStickyWindow')
    return true
  }
  const openedWindow = window.open(
    '/sticky',
    'sticky',
    'width=380,height=620,resizable=yes,scrollbars=yes',
  )
  return openedWindow !== null
}

/** 复制文本到剪贴板：优先 Clipboard API，失败时回退到临时 textarea 方案。 */
export async function copyTextToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // 剪贴板权限被拒绝时改用回退方案
    }
  }
  const temporaryTextarea = document.createElement('textarea')
  temporaryTextarea.value = text
  temporaryTextarea.style.position = 'fixed'
  temporaryTextarea.style.opacity = '0'
  temporaryTextarea.setAttribute('readonly', 'readonly')
  document.body.appendChild(temporaryTextarea)
  temporaryTextarea.select()
  let copied = false
  try {
    copied = document.execCommand('copy')
  } catch {
    copied = false
  }
  document.body.removeChild(temporaryTextarea)
  return copied
}
