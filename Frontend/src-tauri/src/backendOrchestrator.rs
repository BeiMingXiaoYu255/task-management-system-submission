//! 后端进程编排：发布模式下拉起随安装包分发的后端可执行文件并等待健康检查就绪。
//!
//! 设计说明：
//! 1. 开发模式（debug build）不启动后端，主窗口加载 Vite 开发服务器，后端由开发者手动运行；
//! 2. 发布模式下由 backendProcessLauncher 选择空闲 HTTP 端口、启动后端并轮询健康检查，
//!    就绪后显示主窗口，超时/提前退出显示中文错误页；
//! 3. 应用退出时关闭后端标准输入（触发其 EOF 优雅停机），超时后强制结束整个进程树
//!    （后端自己会先停止其托管的 MariaDB 与 Redis 子进程）。

use std::process::{Child, Command};
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager};

use crate::backendProcessLauncher::{
    appendLogLine, findAvailableHttpPort, resolveApplicationDataDirectory,
    resolveBackendExecutablePath, resolveResourceRootDirectory, spawnBackendProcess,
    waitForBackendReady,
};
use crate::runtimeState::ManagedRuntimeState;
use crate::windowManager;

/// 退出时等待后端优雅停机的时间（秒）。
const BACKEND_SHUTDOWN_TIMEOUT_SECONDS: u64 = 20;
/// Windows CREATE_NO_WINDOW 进程创建标志：强制结束进程树时隐藏控制台窗口。
const WINDOWS_CREATE_NO_WINDOW: u32 = 0x0800_0000;

/// 启动入口：开发模式直接返回（由 windowManager 显示窗口），发布模式后台线程拉起后端。
pub fn startBackendOnStartup(appHandle: &AppHandle) {
    if cfg!(debug_assertions) {
        // 开发模式：后端由开发者手动运行（127.0.0.1:8765），桌面外壳不托管任何进程
        return;
    }
    let appHandleClone = appHandle.clone();
    thread::spawn(move || {
        runManagedBackendStartup(&appHandleClone);
    });
}

/// 后台线程主流程：启动后端 → 成功显示主窗口 / 失败显示错误窗口。
fn runManagedBackendStartup(appHandle: &AppHandle) {
    match startManagedBackend(appHandle) {
        Ok(()) => {
            appendLogLine(&currentLogFilePath(appHandle), "后端健康检查通过，显示主窗口");
            windowManager::showMainWindow(appHandle);
        }
        Err(errorMessage) => {
            appendLogLine(
                &currentLogFilePath(appHandle),
                &format!("后端启动失败：{errorMessage}"),
            );
            {
                let state = appHandle.state::<ManagedRuntimeState>();
                state.lock().errorMessage = Some(errorMessage.clone());
            }
            windowManager::showStartupErrorWindow(appHandle, &errorMessage);
        }
    }
}

/// 读取当前日志文件路径（状态中尚未设置时返回空路径，appendLogLine 会忽略）。
fn currentLogFilePath(appHandle: &AppHandle) -> std::path::PathBuf {
    appHandle.state::<ManagedRuntimeState>().lock().logFilePath.clone()
}

/// 启动托管后端：解析路径 → 选择端口 → 启动进程 → 等待健康检查。
fn startManagedBackend(appHandle: &AppHandle) -> Result<(), String> {
    let applicationDataDirectory = resolveApplicationDataDirectory(appHandle);
    let logDirectory = applicationDataDirectory.join("logs");
    std::fs::create_dir_all(&logDirectory)
        .map_err(|error| format!("创建日志目录失败（{}）：{error}", logDirectory.display()))?;
    let logFilePath = logDirectory.join("desktop.log");
    {
        let state = appHandle.state::<ManagedRuntimeState>();
        state.lock().logFilePath = logFilePath.clone();
    }
    appendLogLine(&logFilePath, "开始启动随安装包分发的后端服务");
    let resourceRootDirectory = resolveResourceRootDirectory(appHandle)?;
    let executablePath = resolveBackendExecutablePath(&resourceRootDirectory)?;
    let httpPort = findAvailableHttpPort()?;
    appendLogLine(
        &logFilePath,
        &format!(
            "后端可执行文件：{}；HTTP 端口：{}；运行时目录：{}",
            executablePath.display(),
            httpPort,
            resourceRootDirectory.join("runtime").display()
        ),
    );
    let (childProcess, childStdin) = spawnBackendProcess(
        &executablePath,
        &resourceRootDirectory,
        &applicationDataDirectory,
        httpPort,
    )?;
    {
        let state = appHandle.state::<ManagedRuntimeState>();
        let mut runtime = state.lock();
        runtime.apiBaseUrl = format!("http://127.0.0.1:{httpPort}");
        runtime.httpPort = httpPort;
        runtime.childProcess = Some(childProcess);
        runtime.childStdin = childStdin;
        runtime.isManagedByDesktop = true;
        runtime.isShuttingDown = false;
    }
    waitForBackendReady(appHandle, httpPort)?;
    {
        let state = appHandle.state::<ManagedRuntimeState>();
        state.lock().isReady = true;
    }
    Ok(())
}

/// 应用退出：关闭后端标准输入触发优雅停机，超时后强制结束进程树。
pub fn shutdownBackend(appHandle: &AppHandle) {
    let state = appHandle.state::<ManagedRuntimeState>();
    {
        let mut runtime = state.lock();
        if runtime.isShuttingDown {
            return;
        }
        runtime.isShuttingDown = true;
    }
    let logFilePath = currentLogFilePath(appHandle);
    let childStdin = {
        let mut runtime = state.lock();
        runtime.childStdin.take()
    };
    if childStdin.is_none() && state.lock().childProcess.is_none() {
        return;
    }
    appendLogLine(&logFilePath, "应用退出：关闭后端标准输入，等待后端优雅停机");
    // 释放标准输入写端 → 后端 EOF 监控线程收到 EOF → 依次停止 uvicorn、Redis、MariaDB
    drop(childStdin);
    let mut childProcess = {
        let mut runtime = state.lock();
        runtime.childProcess.take()
    };
    if let Some(childProcessReference) = childProcess.as_mut() {
        let shutdownDeadline = Instant::now() + Duration::from_secs(BACKEND_SHUTDOWN_TIMEOUT_SECONDS);
        loop {
            match childProcessReference.try_wait() {
                Ok(Some(exitStatus)) => {
                    appendLogLine(
                        &logFilePath,
                        &format!("后端已优雅退出（退出码：{exitStatus}）"),
                    );
                    break;
                }
                Ok(None) => {
                    if Instant::now() >= shutdownDeadline {
                        appendLogLine(&logFilePath, "后端未在超时时间内退出，强制结束进程树");
                        forceKillProcessTree(childProcessReference);
                        break;
                    }
                    thread::sleep(Duration::from_millis(200));
                }
                Err(error) => {
                    appendLogLine(&logFilePath, &format!("等待后端退出失败：{error}"));
                    break;
                }
            }
        }
    }
}

/// 强制结束子进程及其派生的 MariaDB/Redis 子进程（Windows 使用 taskkill /T）。
fn forceKillProcessTree(childProcess: &mut Child) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let _ = Command::new("taskkill")
            .arg("/PID")
            .arg(childProcess.id().to_string())
            .arg("/T")
            .arg("/F")
            .creation_flags(WINDOWS_CREATE_NO_WINDOW)
            .status();
    }
    let _ = childProcess.kill();
}