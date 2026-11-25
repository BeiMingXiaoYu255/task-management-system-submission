"""后端启动入口。

两种运行方式：
    1. 开发模式：uvicorn runServer:app --reload；直接使用 Backend/.env 配置；
    2. 桌面安装模式：runServer.exe --manage-runtime，由运行时管理器启动便携 MariaDB 与 Redis，
       注入连接配置后再启动 Web 服务。
"""

import argparse
import sys


def parseCommandLineArguments() -> argparse.Namespace:
    """解析命令行参数。"""
    argumentParser = argparse.ArgumentParser(description="Task Management System backend service")
    argumentParser.add_argument("--manage-runtime", action="store_true", help="Manage bundled MariaDB and Redis")
    argumentParser.add_argument("--host", default=None, help="Listen address (defaults to config)")
    argumentParser.add_argument("--port", type=int, default=None, help="Listen port (defaults to config)")
    argumentParser.add_argument("--reload", action="store_true", help="Enable hot reload in development")
    return argumentParser.parse_args()


def runServer() -> None:
    """启动后端服务主流程。"""
    commandLineArguments = parseCommandLineArguments()
    if commandLineArguments.manage_runtime:
        # 延迟导入：运行时管理器会在启动数据库后注入连接配置
        from TaskManagementBackend.desktop.runtimeManager import startManagedRuntime

        startManagedRuntime()

    # 运行时环境变量就绪后再创建应用
    from TaskManagementBackend.config.settings import settings
    from TaskManagementBackend.main import createApp

    application = createApp()
    import uvicorn

    uvicorn.run(
        application,
        host=commandLineArguments.host or settings.host,
        port=commandLineArguments.port or settings.port,
        reload=commandLineArguments.reload,
        log_level="info",
    )


if __name__ == "__main__":
    try:
        runServer()
    except KeyboardInterrupt:
        sys.exit(0)
else:
    # 作为模块被 uvicorn 导入时（uvicorn runServer:app）创建应用实例
    from TaskManagementBackend.main import app  # noqa: F401
