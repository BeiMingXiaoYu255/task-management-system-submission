//! 桌面外壳的全局运行时状态。
//!
//! 状态由 Tauri 的 `manage` 注入，所有窗口命令与后台线程通过互斥锁读写：
//! 1. 后端 HTTP 基地址与端口（getApiBaseUrl 命令返回）；
//! 2. 后端子进程句柄与标准输入管道（退出时用于优雅停机）；
//! 3. 启动就绪/失败状态与日志路径（便于错误页与诊断）。

use std::path::PathBuf;
use std::process::{Child, ChildStdin};
use std::sync::{Mutex, MutexGuard};

/// 后端 HTTP 服务默认端口，与后端配置 settings.port 默认值保持一致。
pub const DEFAULT_HTTP_PORT: u16 = 8765;

/// 后端 HTTP 服务端口上限：端口被占用时在 8765..=8775 范围内递增选择。
pub const MAX_HTTP_PORT: u16 = 8775;

/// 应用本地数据目录名：Windows 下为 %APPDATA%\\TaskManagementSystem。
pub const APPLICATION_DATA_DIRECTORY_NAME: &str = "TaskManagementSystem";

/// 后端运行期信息。
pub struct BackendRuntime {
    /// 前端调用的 API 基地址，例如 http://127.0.0.1:8765。
    pub apiBaseUrl: String,
    /// 后端实际监听的 HTTP 端口。
    pub httpPort: u16,
    /// 后端子进程句柄（发布模式下由桌面外壳托管）。
    pub childProcess: Option<Child>,
    /// 后端标准输入写端：保持打开表示父进程存活，关闭即触发后端 EOF 优雅停机。
    pub childStdin: Option<ChildStdin>,
    /// 是否由桌面外壳托管后端进程（开发模式为 false）。
    pub isManagedByDesktop: bool,
    /// 后端健康检查是否已通过。
    pub isReady: bool,
    /// 是否已进入退出流程，避免重复停机。
    pub isShuttingDown: bool,
    /// 启动失败时的中文错误信息。
    pub errorMessage: Option<String>,
    /// 桌面外壳日志文件路径。
    pub logFilePath: PathBuf,
}

/// 由 Tauri manage 注入的全局状态容器。
pub struct ManagedRuntimeState {
    /// 互斥锁保护的运行期信息。
    pub inner: Mutex<BackendRuntime>,
}

impl ManagedRuntimeState {
    /// 创建初始状态：发布模式下由后端编排模块填充真实地址与进程句柄。
    pub fn createInitialState() -> Self {
        ManagedRuntimeState {
            inner: Mutex::new(BackendRuntime {
                apiBaseUrl: format!("http://127.0.0.1:{}", DEFAULT_HTTP_PORT),
                httpPort: DEFAULT_HTTP_PORT,
                childProcess: None,
                childStdin: None,
                isManagedByDesktop: false,
                isReady: false,
                isShuttingDown: false,
                errorMessage: None,
                logFilePath: PathBuf::new(),
            }),
        }
    }

    /// 获取状态锁；若锁被中毒（持有线程 panic）则复用内部数据，避免桌面端直接崩溃。
    pub fn lock(&self) -> MutexGuard<'_, BackendRuntime> {
        self.inner
            .lock()
            .unwrap_or_else(|poisonError| poisonError.into_inner())
    }
}
