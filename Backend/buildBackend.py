"""一键构建后端可执行文件（PyInstaller onedir）。

使用方式（必须使用后端虚拟环境）：
    Backend/.venv/Scripts/python.exe Backend/buildBackend.py
    Backend/.venv/Scripts/python.exe Backend/buildBackend.py --clean --skip-smoke-test

产物：
    Backend/dist/runServer/runServer.exe（含 _internal 依赖目录与 _internal/Frontend/dist 前端资源）

设计说明：
    1. 构建前校验前端构建产物是否存在（缺失时给出中文提示，避免安装包内没有前端页面）；
    2. 调用 PyInstaller 使用 backendServer.spec 配置，工作目录固定为 Backend/；
    3. 构建后校验可执行文件存在、输出体积与文件数，并执行 --help 冒烟测试确认可正常启动；
    4. 全部输出中文日志，便于构建流水线定位问题。
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

# 后端根目录（本文件所在目录）与仓库根目录
BACKEND_ROOT_DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT_DIRECTORY = BACKEND_ROOT_DIRECTORY.parent
# 前端构建产物目录
FRONTEND_DIST_DIRECTORY = PROJECT_ROOT_DIRECTORY / "Frontend" / "dist"
# PyInstaller 输出目录（Backend/dist/runServer）
BACKEND_DIST_DIRECTORY = BACKEND_ROOT_DIRECTORY / "dist"
BACKEND_BUILD_DIRECTORY = BACKEND_ROOT_DIRECTORY / "build"
BACKEND_SPEC_FILE_PATH = BACKEND_ROOT_DIRECTORY / "backendServer.spec"


def parseCommandLineArguments() -> argparse.Namespace:
    """解析命令行参数。"""
    argumentParser = argparse.ArgumentParser(description="构建后端可执行文件（PyInstaller onedir）")
    argumentParser.add_argument(
        "--clean",
        action="store_true",
        help="兼容旧参数：构建默认总是执行 --clean（前端 dist 文件名带 hash，缓存会导致静态资源遗漏）",
    )
    argumentParser.add_argument(
        "--skip-smoke-test", action="store_true", help="跳过构建后的 --help 冒烟测试"
    )
    return argumentParser.parse_args()


def checkFrontendBuildExists() -> None:
    """校验前端构建产物存在；缺失时抛出中文明细提示。"""
    indexFilePath = FRONTEND_DIST_DIRECTORY / "index.html"
    if not indexFilePath.is_file():
        raise RuntimeError(
            "未找到前端构建产物："
            f"{indexFilePath}。请先在 Frontend 目录执行 npm run build。"
        )
    fileCount = sum(1 for _ in FRONTEND_DIST_DIRECTORY.rglob("*") if _.is_file())
    print(f"[1/4] 前端构建产物已就绪：{FRONTEND_DIST_DIRECTORY}（{fileCount} 个文件）")


def runPyInstaller(cleanBuild: bool) -> None:
    """调用 PyInstaller 按 spec 配置打包后端。

    说明：始终附加 --clean。前端 dist 的 JS/CSS 文件名带内容 hash，
    PyInstaller 的 Analysis 缓存可能残留旧文件名导致新静态资源未被收集（实测踩坑），
    因此每次构建都清理缓存以保证产物完整可复现；cleanBuild 参数保留用于日志说明。
    """
    print("      Clean 模式：" + ("是（--clean 显式指定）" if cleanBuild else "是（默认强制执行）"))
    pyInstallerCommand = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(BACKEND_DIST_DIRECTORY),
        "--workpath",
        str(BACKEND_BUILD_DIRECTORY),
    ]
    pyInstallerCommand.append("--clean")
    pyInstallerCommand.append(str(BACKEND_SPEC_FILE_PATH))
    print("[2/4] 开始执行 PyInstaller 打包：")
    print("      " + " ".join(pyInstallerCommand))
    startedAt = time.monotonic()
    completedProcess = subprocess.run(pyInstallerCommand, cwd=str(BACKEND_ROOT_DIRECTORY))
    elapsedSeconds = time.monotonic() - startedAt
    if completedProcess.returncode != 0:
        raise RuntimeError(
            f"PyInstaller 打包失败（退出码：{completedProcess.returncode}），耗时 {elapsedSeconds:.1f} 秒"
        )
    print(f"      PyInstaller 打包完成，耗时 {elapsedSeconds:.1f} 秒")


def verifyBuildOutput() -> Path:
    """校验打包产物：可执行文件存在、目录文件数与总体积，返回可执行文件路径。"""
    executablePath = BACKEND_DIST_DIRECTORY / "runServer" / "runServer.exe"
    if not executablePath.is_file():
        executablePath = BACKEND_DIST_DIRECTORY / "runServer" / "runServer"
    if not executablePath.is_file():
        raise RuntimeError(f"打包产物缺少可执行文件：{BACKEND_DIST_DIRECTORY / 'runServer'}")
    bundleDirectory = executablePath.parent
    filePaths = [path for path in bundleDirectory.rglob("*") if path.is_file()]
    totalBytes = sum(path.stat().st_size for path in filePaths)
    frontendIndexPath = bundleDirectory / "_internal" / "Frontend" / "dist" / "index.html"
    if not frontendIndexPath.is_file():
        raise RuntimeError(f"打包产物缺少前端静态资源：{frontendIndexPath}")
    print(
        f"[3/4] 产物校验通过：{executablePath}（{len(filePaths)} 个文件，"
        f"共 {totalBytes / 1024 / 1024:.1f} MB）"
    )
    return executablePath


def runSmokeTest(executablePath: Path) -> None:
    """冒烟测试：执行 runServer --help，确认打包后可正常启动 Python 运行时。"""
    completedProcess = subprocess.run(
        [str(executablePath), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    if completedProcess.returncode != 0:
        raise RuntimeError(
            "可执行文件冒烟测试失败（--help 返回非零）："
            + (completedProcess.stderr or "")[-2000:]
        )
    print("[4/4] 冒烟测试通过：runServer.exe --help 正常返回")


def main() -> None:
    """构建主流程。"""
    commandLineArguments = parseCommandLineArguments()
    totalStartedAt = time.monotonic()
    print("=" * 60)
    print("后端可执行文件打包开始（PyInstaller onedir）")
    print("=" * 60)
    checkFrontendBuildExists()
    runPyInstaller(commandLineArguments.clean)
    executablePath = verifyBuildOutput()
    if not commandLineArguments.skip_smoke_test:
        runSmokeTest(executablePath)
    print("=" * 60)
    print(f"后端可执行文件打包完成，总耗时 {time.monotonic() - totalStartedAt:.1f} 秒")
    print(f"产物位置：{executablePath.parent}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exception:
        print(f"构建失败：{exception}", file=sys.stderr)
        sys.exit(1)