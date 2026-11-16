# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：把 FastAPI 后端打包为 onedir 可执行文件（Backend/dist/runServer/runServer.exe）。

设计说明：
    1. onedir 模式（而非 onefile）：启动更快，且安装包内可直接更新单个文件；
    2. 把前端构建产物 Frontend/dist 一并打入包内（COLLECT 后的 _internal/Frontend/dist），
       桌面安装版还会由 Tauri 外壳通过环境变量指定独立的资源目录；
    3. Uvicorn 的动态导入（协议/事件循环/lifespan 实现）与 desktop 运行时模块显式声明为 hiddenimports，
       避免打包后运行时 ImportError；
    4. 构建入口为 runServer.py（--manage-runtime 时先启动便携数据库与缓存）。
"""

from pathlib import Path

# SPECPATH 为 spec 文件所在目录（Backend/）
backendRootDirectory = Path(SPECPATH).resolve()
projectRootDirectory = backendRootDirectory.parent
frontendDistDirectory = projectRootDirectory / "Frontend" / "dist"

# ===== 随包分发的静态资源 =====
dataFiles = []
if frontendDistDirectory.is_dir():
    dataFiles.append((str(frontendDistDirectory), "Frontend/dist"))

# ===== 隐式依赖：Uvicorn 动态导入的实现模块与桌面运行时管理模块 =====
hiddenImportModules = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "TaskManagementBackend.desktop.runtimeManager",
    "TaskManagementBackend.desktop.runtimePaths",
    "TaskManagementBackend.desktop.databaseRuntime",
    "TaskManagementBackend.desktop.redisRuntime",
    "TaskManagementBackend.desktop.processUtils",
    "pymysql.constants.CLIENT",
    "pymysql.constants.FIELD_TYPE",
]

analysis = Analysis(
    [str(backendRootDirectory / "runServer.py")],
    pathex=[str(backendRootDirectory)],
    binaries=[],
    datas=dataFiles,
    hiddenimports=hiddenImportModules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tests", "tkinter"],
    noarchive=False,
)

pythonArchive = PYZ(analysis.pure)

executable = EXE(
    pythonArchive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="runServer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collectionOutput = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="runServer",
)
