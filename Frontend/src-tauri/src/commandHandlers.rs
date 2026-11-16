//! 前端可调用的 Tauri 命令。
//!
//! 前端约定（见 docs/development/frontendDesignContract.md 第 6 节）：
//! 1. 检测到 window.__TAURI_INTERNALS__ 时调用 getApiBaseUrl 获取后端地址；
//! 2. 桌面端打开粘贴待办小窗使用 openStickyWindow；
//! 3. 便签小窗关闭自身使用 closeCurrentWindow。

use tauri::{AppHandle, State, WebviewWindow};

use crate::runtimeState::ManagedRuntimeState;
use crate::windowManager;

/// 返回后端 API 基地址（例如 http://127.0.0.1:8765），供前端 httpClient 拼接请求。
#[tauri::command]
pub fn getApiBaseUrl(runtimeState: State<'_, ManagedRuntimeState>) -> String {
    runtimeState.lock().apiBaseUrl.clone()
}

/// 返回桌面运行期诊断信息，便于前端设置页/错误提示展示端口与日志路径。
#[tauri::command]
pub fn getDesktopRuntimeInfo(runtimeState: State<'_, ManagedRuntimeState>) -> serde_json::Value {
    let runtime = runtimeState.lock();
    serde_json::json!({
        "apiBaseUrl": runtime.apiBaseUrl,
        "httpPort": runtime.httpPort,
        "isReady": runtime.isReady,
        "isManagedByDesktop": runtime.isManagedByDesktop,
        "errorMessage": runtime.errorMessage,
        "logFilePath": runtime.logFilePath.to_string_lossy(),
    })
}

/// 打开（或聚焦已存在的）便签待办小窗：380x620、置顶、可关闭。
///
/// 必须使用 async 命令：同步 Tauri 命令运行在主线程，创建 WebView 窗口会等待事件循环，
/// 容易造成界面卡死（v1.2.1 修复）。async 命令在异步运行时执行，不会阻塞事件循环。
#[tauri::command]
pub async fn openStickyWindow(appHandle: AppHandle) -> Result<(), String> {
    windowManager::openStickyWindow(&appHandle)
}

/// 关闭当前窗口（便签小窗使用），不影响主窗口。
#[tauri::command]
pub async fn closeCurrentWindow(currentWindow: WebviewWindow) -> Result<(), String> {
    windowManager::closeWindow(&currentWindow)
}

/// 从便签小窗唤起并聚焦主窗口（便签窗点击标题时调用）。
#[tauri::command]
pub fn showMainWindow(appHandle: AppHandle) -> Result<(), String> {
    windowManager::showMainWindow(&appHandle);
    Ok(())
}