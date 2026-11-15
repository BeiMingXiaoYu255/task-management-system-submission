/// <reference types="vite/client" />

/** Tauri 注入的全局对象声明（仅桌面模式下存在）。 */
interface Window {
  __TAURI_INTERNALS__?: unknown
}
