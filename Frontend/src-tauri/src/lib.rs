//! 桌面客户端外壳入口：装配运行时状态、窗口管理、后端进程编排与前端命令。
//!
//! 设计说明：
//! 1. 开发模式（debug build）不启动后端，窗口加载 Vite 开发服务器地址，后端由开发者手动运行；
//! 2. 发布模式先隐藏主窗口，拉起随安装包分发的后端可执行文件并轮询健康检查，
//!    就绪后显示主窗口；超时或后端提前退出时展示启动错误窗口；
//! 3. 应用退出时关闭后端标准输入触发其优雅停机，超时后强制结束进程树。

#![allow(non_snake_case)]

mod backendOrchestrator;
mod backendProcessLauncher;
mod commandHandlers;
mod runtimeState;
mod windowManager;

use runtimeState::ManagedRuntimeState;
use tauri::RunEvent;

/// 创建并运行 Tauri 应用。
pub fn run() {
    let application = tauri::Builder::default()
        .manage(ManagedRuntimeState::createInitialState())
        .invoke_handler(tauri::generate_handler![
            commandHandlers::getApiBaseUrl,
            commandHandlers::getDesktopRuntimeInfo,
            commandHandlers::openStickyWindow,
            commandHandlers::closeCurrentWindow,
            commandHandlers::showMainWindow,
        ])
        .setup(|application| {
            // 窗口初始化必须在启动检查前执行：开发模式直接显示，发布模式等后端就绪后再显示
            windowManager::initializeWindows(application.handle());
            backendOrchestrator::startBackendOnStartup(application.handle());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("任务管理系统桌面外壳初始化失败");
    // 应用退出（含主窗口关闭、系统关机、任务管理器结束等）时统一优雅结束后端
    application.run(|appHandle, runEvent| {
        if matches!(runEvent, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            backendOrchestrator::shutdownBackend(appHandle);
        }
    });
}