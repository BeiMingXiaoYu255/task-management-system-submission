"""桌面安装版运行时：跨平台进程与端口工具。

设计说明：
    1. 所有子进程以无窗口方式启动（Windows 使用 CREATE_NO_WINDOW），并重定向输出到日志文件；
    2. 端口探测同时用于"选择可用端口"和"等待服务就绪"；
    3. 停止进程优先发送终止信号，超时后结束整个进程树（Windows 使用 taskkill /T /F）；
    4. 提供父进程存活探测，供后端在 Tauri 外壳异常退出时兜底清理数据库与缓存进程。
"""

import ctypes
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

_logger = logging.getLogger("taskManagement.desktop.processUtils")

# Windows CREATE_NO_WINDOW：不弹出控制台窗口
WINDOWS_CREATE_NO_WINDOW = 0x08000000
# Windows SYNCHRONIZE 进程句柄权限
WINDOWS_SYNCHRONIZE_ACCESS = 0x00100000
# Windows WaitForSingleObject 返回码：对象已触发（进程已退出）
WINDOWS_WAIT_OBJECT_ZERO = 0x00000000


def isPortListening(port: int, host: str = "127.0.0.1", timeoutSeconds: float = 0.6) -> bool:
    """判断指定主机端口是否已有服务在监听（TCP 连接探测）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probeSocket:
        probeSocket.settimeout(timeoutSeconds)
        return probeSocket.connect_ex((host, port)) == 0


def findAvailablePort(startPort: int, maxAttempts: int = 40, host: str = "127.0.0.1") -> int:
    """从起始端口向上查找第一个可绑定的空闲端口。"""
    for portOffset in range(maxAttempts):
        candidatePort = startPort + portOffset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as bindSocket:
            bindSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                bindSocket.bind((host, candidatePort))
            except OSError:
                continue
            return candidatePort
    raise RuntimeError(f"All {maxAttempts} consecutive ports starting from {startPort} are already in use")


def waitForPortListening(
    port: int,
    timeoutSeconds: float,
    process: subprocess.Popen | None = None,
    host: str = "127.0.0.1",
) -> bool:
    """等待端口进入监听状态；传入进程句柄时若进程提前退出立即返回 False。"""
    deadline = time.monotonic() + timeoutSeconds
    while time.monotonic() < deadline:
        if isPortListening(port, host=host):
            return True
        if process is not None and process.poll() is not None:
            return False
        time.sleep(0.25)
    return False


def startDetachedProcess(
    executablePath: Path,
    arguments: list[str],
    workingDirectory: Path,
    logFilePath: Path,
    environment: dict[str, str] | None = None,
) -> subprocess.Popen:
    """启动后台子进程：无窗口、输出追加写入日志文件、不占用标准输入。"""
    logFilePath.parent.mkdir(parents=True, exist_ok=True)
    logFileHandle = open(logFilePath, "ab")
    creationFlags = WINDOWS_CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        return subprocess.Popen(
            [str(executablePath), *arguments],
            cwd=str(workingDirectory),
            stdin=subprocess.DEVNULL,
            stdout=logFileHandle,
            stderr=subprocess.STDOUT,
            env={**os.environ, **(environment or {})},
            creationflags=creationFlags,
            close_fds=True,
        )
    finally:
        # 子进程持有文件句柄副本后父进程即可关闭，避免日志文件被长期锁定
        logFileHandle.close()


def stopProcessTree(process: subprocess.Popen | None, timeoutSeconds: float = 10.0) -> None:
    """优雅结束子进程树：先 terminate，超时后强制结束整个进程树。"""
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:
        return
    try:
        process.wait(timeout=timeoutSeconds)
        return
    except subprocess.TimeoutExpired:
        pass
    _logger.warning("Process %s did not exit within %.1f seconds; force-killing the entire process tree", process.pid, timeoutSeconds)
    forceKillProcessTree(process)


def forceKillProcessTree(process: subprocess.Popen | None) -> None:
    """强制结束进程树：Windows 使用 taskkill /T /F，其他平台使用 kill。"""
    if process is None or process.poll() is not None:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                timeout=30,
                creationflags=WINDOWS_CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as exception:
            _logger.warning("taskkill failed to terminate the process tree: %s", exception)
    try:
        process.kill()
        process.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


def runCommandCaptured(
    executablePath: Path,
    arguments: list[str],
    timeoutSeconds: float = 60.0,
    logFilePath: Path | None = None,
    workingDirectory: Path | None = None,
) -> subprocess.CompletedProcess:
    """同步执行命令并捕获输出（用于 MariaDB 客户端建库、关闭数据库等短命令）。"""
    completedProcess = subprocess.run(
        [str(executablePath), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeoutSeconds,
        cwd=str(workingDirectory) if workingDirectory is not None else None,
        creationflags=WINDOWS_CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if logFilePath is not None:
        appendLogText(
            logFilePath,
            f"Command: {executablePath.name} {' '.join(arguments)}\n"
            f"Exit code: {completedProcess.returncode}\n"
            f"Standard output: {completedProcess.stdout.strip()}\n"
            f"Standard error: {completedProcess.stderr.strip()}",
        )
    return completedProcess


def appendLogText(logFilePath: Path, logText: str) -> None:
    """把诊断文本追加写入日志文件（失败时静默，不阻断主流程）。"""
    try:
        logFilePath.parent.mkdir(parents=True, exist_ok=True)
        with open(logFilePath, "a", encoding="utf-8") as logFileHandle:
            logFileHandle.write(logText + "\n")
    except OSError:
        pass


def readLogTail(logFilePath: Path, maxLines: int = 30) -> str:
    """读取日志文件最后若干行，用于启动失败时输出诊断信息。"""
    if not logFilePath.is_file():
        return ""
    try:
        logLines = logFilePath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(logLines[-maxLines:])


def isParentProcessAlive(parentProcessId: int) -> bool:
    """判断父进程是否仍存活（Tauri 外壳异常退出时用于兜底停止数据库与缓存）。"""
    if parentProcessId <= 0:
        return True
    if sys.platform == "win32":
        return _isWindowsProcessAlive(parentProcessId)
    try:
        os.kill(parentProcessId, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _isWindowsProcessAlive(processId: int) -> bool:
    """Windows 下通过 OpenProcess + WaitForSingleObject 判断进程是否存活。"""
    kernel32 = ctypes.windll.kernel32
    processHandle = kernel32.OpenProcess(WINDOWS_SYNCHRONIZE_ACCESS, False, processId)
    if not processHandle:
        return False
    try:
        waitResult = kernel32.WaitForSingleObject(processHandle, 0)
        # WAIT_TIMEOUT（0x102）表示进程仍在运行；WAIT_OBJECT_0 表示已退出
        return waitResult != WINDOWS_WAIT_OBJECT_ZERO
    finally:
        kernel32.CloseHandle(processHandle)