//! 后端进程启动与探测工具：路径规范化、端口选择、子进程启动、健康检查、日志泵。
//!
//! 独立成模块的原因：进程编排（backendOrchestrator）只关心启动/退出流程，
//! 具体的 Windows 路径前缀处理、日志重定向与 HTTP 探活细节集中在这里，便于维护与单文件行数控制。

use std::fs::{create_dir_all, OpenOptions};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use tauri::{AppHandle, Manager};

use crate::runtimeState::{APPLICATION_DATA_DIRECTORY_NAME, DEFAULT_HTTP_PORT, MAX_HTTP_PORT};

/// 后端启动就绪的最长等待时间（秒）：首次运行需要初始化便携 MariaDB 数据目录，留足余量。
pub const BACKEND_STARTUP_TIMEOUT_SECONDS: u64 = 180;
/// 健康检查轮询间隔（毫秒）。
const HEALTH_POLL_INTERVAL_MILLISECONDS: u64 = 500;
/// Windows CREATE_NO_WINDOW 进程创建标志：后端是控制台程序，隐藏其控制台窗口。
const WINDOWS_CREATE_NO_WINDOW: u32 = 0x0800_0000;

/// 去掉 Windows 扩展长度路径前缀（\\?\\），避免传给 Python/MariaDB 子进程后无法识别。
///
/// Tauri 在 Windows 上部分路径 API（resource_dir 等）返回 \\?\C:\... 形式，
/// 子进程参数中出现该前缀会导致 mariadb-install-db.exe 报“系统找不到指定的路径”，必须规范化。
pub fn normalizePathForChildProcess(filePath: PathBuf) -> PathBuf {
    let pathText = filePath.to_string_lossy().to_string();
    if let Some(strippedText) = pathText.strip_prefix(r"\\?\UNC\") {
        return PathBuf::from(format!(r"\\{}", strippedText));
    }
    if let Some(strippedText) = pathText.strip_prefix(r"\\?\") {
        return PathBuf::from(strippedText);
    }
    filePath
}

/// 解析应用数据目录：优先环境变量覆盖，Windows 使用 %APPDATA%\\TaskManagementSystem。
pub fn resolveApplicationDataDirectory(appHandle: &AppHandle) -> PathBuf {
    if let Ok(directory) = std::env::var("TASK_MANAGEMENT_DATA_DIR") {
        if !directory.trim().is_empty() {
            return normalizePathForChildProcess(PathBuf::from(directory));
        }
    }
    if let Ok(appDataDirectory) = std::env::var("APPDATA") {
        if !appDataDirectory.trim().is_empty() {
            return normalizePathForChildProcess(
                Path::new(&appDataDirectory).join(APPLICATION_DATA_DIRECTORY_NAME),
            );
        }
    }
    let fallbackDirectory = appHandle.path().data_dir().unwrap_or_else(|_| std::env::temp_dir());
    normalizePathForChildProcess(fallbackDirectory.join(APPLICATION_DATA_DIRECTORY_NAME))
}

/// 解析安装资源根目录：Tauri 资源目录下的 resources/（安装包内由 staging 脚本写入）。
pub fn resolveResourceRootDirectory(appHandle: &AppHandle) -> Result<PathBuf, String> {
    let resourceDirectory = appHandle
        .path()
        .resource_dir()
        .map_err(|error| format!("无法定位安装资源目录：{error}"))?;
    let resourceRootDirectory = normalizePathForChildProcess(resourceDirectory.join("resources"));
    if !resourceRootDirectory.is_dir() {
        return Err(format!(
            "安装资源目录不存在：{}（请使用打包脚本重新构建安装包）",
            resourceRootDirectory.display()
        ));
    }
    Ok(resourceRootDirectory)
}

/// 解析后端可执行文件路径（Windows 为 runServer.exe，其他平台为 runServer）。
pub fn resolveBackendExecutablePath(resourceRootDirectory: &Path) -> Result<PathBuf, String> {
    let executableName = if cfg!(windows) { "runServer.exe" } else { "runServer" };
    let executablePath = resourceRootDirectory.join("backend").join(executableName);
    if !executablePath.is_file() {
        return Err(format!(
            "未找到后端可执行文件：{}（安装包资源缺失，请重新运行打包脚本）",
            executablePath.display()
        ));
    }
    Ok(executablePath)
}

/// 在 8765..=8775 范围内选择第一个可绑定的本机 HTTP 端口。
pub fn findAvailableHttpPort() -> Result<u16, String> {
    for candidatePort in DEFAULT_HTTP_PORT..=MAX_HTTP_PORT {
        if TcpListener::bind(("127.0.0.1", candidatePort)).is_ok() {
            return Ok(candidatePort);
        }
    }
    Err(format!(
        "端口 {DEFAULT_HTTP_PORT}-{MAX_HTTP_PORT} 均被占用，请关闭占用程序后重试"
    ))
}

/// 启动后端可执行文件，并为其标准输出/错误接日志泵；返回子进程与标准输入写端。
pub fn spawnBackendProcess(
    executablePath: &Path,
    resourceRootDirectory: &Path,
    applicationDataDirectory: &Path,
    httpPort: u16,
) -> Result<(Child, Option<ChildStdin>), String> {
    let logFilePath = applicationDataDirectory.join("logs").join("backend.log");
    let backendWorkingDirectory = executablePath
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| resourceRootDirectory.join("backend"));
    let mut command = Command::new(executablePath);
    command
        .current_dir(&backendWorkingDirectory)
        .arg("--manage-runtime")
        .arg("--port")
        .arg(httpPort.to_string())
        .env("TASK_MANAGEMENT_RUNTIME_DIR", resourceRootDirectory.join("runtime"))
        .env("TASK_MANAGEMENT_FRONTEND_DIR", resourceRootDirectory.join("frontend"))
        .env("TASK_MANAGEMENT_DATA_DIR", applicationDataDirectory)
        .env("TASK_MANAGEMENT_HTTP_PORT", httpPort.to_string())
        .env("TASK_MANAGEMENT_PARENT_PID", std::process::id().to_string())
        .env("PYTHONIOENCODING", "utf-8")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(WINDOWS_CREATE_NO_WINDOW);
    }
    let mut childProcess = command
        .spawn()
        .map_err(|error| format!("启动后端进程失败（{}）：{error}", executablePath.display()))?;
    let childStdin = childProcess.stdin.take();
    if let Some(stdoutPipe) = childProcess.stdout.take() {
        spawnLogPump(stdoutPipe, logFilePath.clone(), "stdout");
    }
    if let Some(stderrPipe) = childProcess.stderr.take() {
        spawnLogPump(stderrPipe, logFilePath, "stderr");
    }
    Ok((childProcess, childStdin))
}

/// 为子进程输出流启动日志泵线程：逐行写入 backend.log 并带上流标签。
fn spawnLogPump<R: Read + Send + 'static>(mut reader: R, logFilePath: PathBuf, streamLabel: &'static str) {
    thread::spawn(move || {
        let mut buffer = [0u8; 4096];
        let mut pendingText = String::new();
        loop {
            match reader.read(&mut buffer) {
                Ok(0) => break,
                Ok(readCount) => {
                    pendingText.push_str(&String::from_utf8_lossy(&buffer[..readCount]));
                    while let Some(lineBreakIndex) = pendingText.find('\n') {
                        let lineText = pendingText[..lineBreakIndex].trim_end().to_string();
                        pendingText.drain(..=lineBreakIndex);
                        appendLogLine(&logFilePath, &format!("[backend:{streamLabel}] {lineText}"));
                    }
                }
                Err(_) => break,
            }
        }
        if !pendingText.trim().is_empty() {
            appendLogLine(&logFilePath, &format!("[backend:{streamLabel}] {pendingText}"));
        }
    });
}

/// 轮询后端健康检查接口，直到就绪、进程提前退出或超时。
pub fn waitForBackendReady(appHandle: &AppHandle, httpPort: u16) -> Result<(), String> {
    let startupDeadline = Instant::now() + Duration::from_secs(BACKEND_STARTUP_TIMEOUT_SECONDS);
    loop {
        if probeBackendHealth(httpPort) {
            return Ok(());
        }
        {
            let state = appHandle.state::<crate::runtimeState::ManagedRuntimeState>();
            let mut runtime = state.lock();
            if let Some(childProcess) = runtime.childProcess.as_mut() {
                match childProcess.try_wait() {
                    Ok(Some(exitStatus)) => {
                        return Err(format!(
                            "后端进程提前退出（退出码：{exitStatus}），请查看日志目录中的 backend.log"
                        ));
                    }
                    Ok(None) => {}
                    Err(error) => return Err(format!("检查后端进程状态失败：{error}")),
                }
            } else {
                return Err(String::from("后端进程句柄丢失，无法继续等待启动"));
            }
        }
        if Instant::now() >= startupDeadline {
            return Err(format!(
                "后端启动超时（{BACKEND_STARTUP_TIMEOUT_SECONDS} 秒内未通过健康检查），请查看日志目录中的 backend.log 与 mariadb.log"
            ));
        }
        thread::sleep(Duration::from_millis(HEALTH_POLL_INTERVAL_MILLISECONDS));
    }
}

/// 探测后端健康检查接口是否返回 200 且 status=ok。
fn probeBackendHealth(httpPort: u16) -> bool {
    let socketAddress = SocketAddr::from(([127, 0, 0, 1], httpPort));
    let mut tcpStream = match TcpStream::connect_timeout(&socketAddress, Duration::from_millis(800)) {
        Ok(stream) => stream,
        Err(_) => return false,
    };
    let _ = tcpStream.set_read_timeout(Some(Duration::from_millis(1500)));
    let _ = tcpStream.set_write_timeout(Some(Duration::from_millis(1500)));
    let requestText =
        "GET /api/v1/health HTTP/1.1\r\nHost: 127.0.0.1\r\nAccept: application/json\r\nConnection: close\r\n\r\n";
    if tcpStream.write_all(requestText.as_bytes()).is_err() {
        return false;
    }
    let mut responseText = String::new();
    if tcpStream.read_to_string(&mut responseText).is_err() {
        return false;
    }
    let isSuccessStatus =
        responseText.starts_with("HTTP/1.1 200") || responseText.starts_with("HTTP/1.0 200");
    let isHealthyStatus = responseText.contains("\"status\":\"ok\"")
        || responseText.contains("\"status\": \"ok\"");
    isSuccessStatus && isHealthyStatus
}

/// 追加一行桌面外壳日志（失败静默，日志不可写不应影响应用运行）。
pub fn appendLogLine(logFilePath: &Path, message: &str) {
    if logFilePath.as_os_str().is_empty() {
        return;
    }
    if let Some(parentDirectory) = logFilePath.parent() {
        let _ = create_dir_all(parentDirectory);
    }
    let unixTimestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0);
    if let Ok(mut logFile) = OpenOptions::new().create(true).append(true).open(logFilePath) {
        let _ = writeln!(logFile, "[{unixTimestamp}] {message}");
    }
}
