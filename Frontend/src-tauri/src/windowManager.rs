//! 窗口管理：主窗口显隐、便签小窗与启动错误页。
//!
//! 设计说明：
//! 1. 主窗口在 tauri.conf.json 中配置为 visible=false，发布模式由后端编排模块在
//!    健康检查通过后调用 showMainWindow 显示，避免用户看到加载中的白屏；
//! 2. 开发模式（debug）窗口直接显示并加载 devUrl（http://localhost:5173）；
//! 3. 后端启动失败时创建独立错误窗口，通过初始化脚本在页面里渲染中文错误页；
//! 4. 主窗口关闭即退出整个应用（同时触发后端优雅停机），便签小窗单独关闭。

use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

use crate::runtimeState::DEFAULT_HTTP_PORT;
use crate::runtimeState::ManagedRuntimeState;

/// 便签小窗标签（与 capabilities/default.json 的 windows 列表保持一致）。
pub const STICKY_WINDOW_LABEL: &str = "sticky";

/// 启动错误窗口标签。
pub const STARTUP_ERROR_WINDOW_LABEL: &str = "startupError";

/// 应用启动时初始化窗口：开发模式立即显示主窗口并标注开发模式 API 地址。
pub fn initializeWindows(appHandle: &AppHandle) {
    // 仅开发模式需要立即显示主窗口；发布模式等待后端就绪后再显示。
    if cfg!(debug_assertions) {
        if let Some(state) = appHandle.try_state::<ManagedRuntimeState>() {
            let mut runtime = state.lock();
            runtime.apiBaseUrl = format!("http://127.0.0.1:{}", DEFAULT_HTTP_PORT);
            runtime.httpPort = DEFAULT_HTTP_PORT;
            runtime.isReady = true;
            runtime.isManagedByDesktop = false;
        }
        showMainWindow(appHandle);
    }
    closeApplicationWhenMainWindowCloses(appHandle);
}

/// 显示并聚焦主窗口。
pub fn showMainWindow(appHandle: &AppHandle) {
    if let Some(mainWindow) = appHandle.get_webview_window("main") {
        let _ = mainWindow.show();
        let _ = mainWindow.set_focus();
    }
}

/// 主窗口关闭时退出整个应用，避免遗留学生窗口与后台进程。
///
/// 注意：不能在窗口事件回调里同步调用 AppHandle::exit（Tauri 事件循环会等待回调返回，
/// 同步 exit 会导致应用无法退出）；这里投递到异步运行时后再退出，
/// 退出流程由 RunEvent::ExitRequested 中的后端优雅停机逻辑接管。
fn closeApplicationWhenMainWindowCloses(appHandle: &AppHandle) {
    if let Some(mainWindow) = appHandle.get_webview_window("main") {
        let appHandleClone = appHandle.clone();
        mainWindow.on_window_event(move |windowEvent| {
            if let tauri::WindowEvent::CloseRequested { .. } = windowEvent {
                let appHandleForExit = appHandleClone.clone();
                tauri::async_runtime::spawn(async move {
                    appHandleForExit.exit(0);
                });
            }
        });
    }
}

/// 打开便签小窗：已存在则聚焦，不存在则创建 380x620 置顶窗口并切换到 /sticky 路由。
pub fn openStickyWindow(appHandle: &AppHandle) -> Result<(), String> {
    if let Some(existingWindow) = appHandle.get_webview_window(STICKY_WINDOW_LABEL) {
        let _ = existingWindow.show();
        let _ = existingWindow.set_focus();
        return Ok(());
    }
    // initialization_script 在页面脚本执行前运行：先把地址栏切到 /sticky，
    // BrowserRouter 挂载时直接读取该路径，避免 eval 时机竞争导致小窗显示错误页面。
    let stickyWindow = WebviewWindowBuilder::new(
        appHandle,
        STICKY_WINDOW_LABEL,
        WebviewUrl::App("index.html".into()),
    )
    .title("Sticky To-dos")
    .inner_size(380.0, 620.0)
    .min_inner_size(320.0, 460.0)
    .resizable(true)
    .always_on_top(true)
    .center()
    .initialization_script(STICKY_ROUTE_SCRIPT)
    .build()
    .map_err(|error| format!("Failed to open the sticky window: {error}"))?;
    let _ = stickyWindow.set_focus();
    Ok(())
}

/// 关闭指定窗口（便签小窗的关闭按钮使用）。
pub fn closeWindow(window: &WebviewWindow) -> Result<(), String> {
    window.close().map_err(|error| format!("关闭窗口失败：{error}"))
}

/// 在前端单页应用里切换到 /sticky 路由的初始化脚本（每次页面加载前执行）。
///
/// 实现原理：初始化脚本先于页面内 React 执行，直接改写地址栏并派发 popstate；
/// 同时在 DOMContentLoaded/load 与多个时间点重试，覆盖脚本执行与 React 挂载的时序差异。
const STICKY_ROUTE_SCRIPT: &str = r#"
(function () {
  function navigateToStickyRoute() {
    try {
      if (window.location.pathname !== '/sticky') {
        window.history.replaceState(window.history.state, '', '/sticky');
        window.dispatchEvent(new PopStateEvent('popstate'));
      }
    } catch (error) {
      console.error('Failed to switch to the sticky route', error);
    }
  }
  navigateToStickyRoute();
  window.addEventListener('DOMContentLoaded', navigateToStickyRoute);
  window.addEventListener('load', navigateToStickyRoute);
  window.setTimeout(navigateToStickyRoute, 60);
  window.setTimeout(navigateToStickyRoute, 600);
})();
"#;

/// 创建启动错误窗口：加载前端入口页，用初始化脚本把页面替换为中文错误页。
pub fn showStartupErrorWindow(appHandle: &AppHandle, errorMessage: &str) {
    if appHandle.get_webview_window(STARTUP_ERROR_WINDOW_LABEL).is_some() {
        return;
    }
    let initializationScript = buildStartupErrorInitializationScript(errorMessage);
    let buildResult = WebviewWindowBuilder::new(
        appHandle,
        STARTUP_ERROR_WINDOW_LABEL,
        WebviewUrl::App("index.html".into()),
    )
    .title("Task Management System - Startup Failed")
    .inner_size(640.0, 480.0)
    .resizable(false)
    .center()
    .initialization_script(initializationScript)
    .build();
    match buildResult {
        Ok(errorWindow) => {
            let errorWindowClone = errorWindow.clone();
            errorWindow.on_window_event(move |windowEvent| {
                if let tauri::WindowEvent::CloseRequested { .. } = windowEvent {
                    errorWindowClone.app_handle().exit(0);
                }
            });
            let _ = errorWindow.set_focus();
        }
        Err(buildError) => {
            // 极端情况下窗口创建失败：至少把隐藏的主窗口显示出来，避免应用“无界面”卡住
            crate::backendProcessLauncher::appendLogLine(
                &appHandle
                    .state::<ManagedRuntimeState>()
                    .lock()
                    .logFilePath,
                &format!("Failed to create the startup error window: {buildError}; error: {errorMessage}"),
            );
            showMainWindow(appHandle);
        }
    }
}

/// 构造启动错误页注入脚本：中文提示 + 日志路径 + 退出方式说明。
fn buildStartupErrorInitializationScript(errorMessage: &str) -> String {
    let serializedMessage = serde_json::to_string(errorMessage)
        .unwrap_or_else(|_| String::from(r#""Backend service failed to start""#));
    let scriptTemplate = r#"
(function () {
  window.__TASK_MANAGEMENT_STARTUP_ERROR__ = __ERROR_MESSAGE__;
  function renderStartupErrorPage() {
    if (document.getElementById('taskManagementStartupError')) { return; }
    var styleElement = document.createElement('style');
    styleElement.textContent = [
      'html,body{margin:0;padding:0;height:100%;background:#141414;color:#e8e8e8;',
      'font-family:system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;}',
      'main{box-sizing:border-box;height:100%;display:flex;flex-direction:column;',
      'justify-content:center;gap:14px;padding:40px 44px;}',
      'h1{margin:0;font-size:22px;font-weight:650;letter-spacing:1px;}',
      '.hint{font-size:13px;line-height:1.8;color:#9a9a9a;margin:0;}',
      '.detail{font-size:12px;line-height:1.7;color:#c9c9c9;padding:14px 16px;',
      'border:1px solid #2e2e2e;border-radius:4px;word-break:break-all;background:#1c1c1c;}',
      '.path{font-family:Consolas,monospace;font-size:12px;color:#e8e8e8;}'
    ].join('');
    var titleElement = document.createElement('h1');
    titleElement.textContent = 'Backend service failed to start';
    var hintElement = document.createElement('p');
    hintElement.className = 'hint';
    hintElement.textContent = 'The app needs its bundled database, cache and backend service to start. Reopen the app to retry; if the problem persists, send the error details and log file below to your administrator.';
    var detailElement = document.createElement('div');
    detailElement.className = 'detail';
    detailElement.textContent = 'Error: ' + String(window.__TASK_MANAGEMENT_STARTUP_ERROR__ || 'Unknown error');
    var pathElement = document.createElement('p');
    pathElement.className = 'hint';
    pathElement.textContent = 'Log directory: %APPDATA%\\TaskManagementSystem\\logs (backend.log, desktop.log)';
    var retryHintElement = document.createElement('p');
    retryHintElement.className = 'hint';
    retryHintElement.textContent = 'Close this window to exit the app.';
    var container = document.createElement('main');
    container.id = 'taskManagementStartupError';
    container.appendChild(titleElement);
    container.appendChild(hintElement);
    container.appendChild(detailElement);
    container.appendChild(pathElement);
    container.appendChild(retryHintElement);
    if (!document.head.contains(styleElement)) { document.head.appendChild(styleElement); }
    if (document.body) { document.body.replaceChildren(container); }
  }
  document.addEventListener('DOMContentLoaded', renderStartupErrorPage);
  window.setTimeout(renderStartupErrorPage, 900);
  window.setTimeout(renderStartupErrorPage, 2400);
})();
"#;
    scriptTemplate.replace("__ERROR_MESSAGE__", &serializedMessage)
}