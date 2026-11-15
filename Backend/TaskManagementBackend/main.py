"""FastAPI 应用装配入口。

职责：
    1. 创建 FastAPI 实例、注册 CORS 与全局异常处理；
    2. 注册全部模块控制器（统一前缀 /api/v1）；
    3. 启动时初始化数据库表结构与内置数据；
    4. 存在前端构建产物时直接托管静态文件（桌面端与局域网访问共用）。
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHttpException
from starlette.responses import Response
from starlette.types import Scope

from TaskManagementBackend import APP_NAME, APP_VERSION
from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.controllers import (
    adminController,
    aiConfigController,
    aiController,
    authController,
    collaborationController,
    subTeamController,
    dashboardController,
    notificationController,
    settingController,
    systemController,
    taskController,
    teamController,
    todoController,
    userController,
)
from TaskManagementBackend.core.database import SessionLocal, engine, initDatabase
from TaskManagementBackend.core.exceptions import registerExceptionHandlers
from TaskManagementBackend.core.redisClient import cacheClient
from TaskManagementBackend.services.initializationService import initializeSystemData

# 应用日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("taskManagement")


class SinglePageStaticFiles(StaticFiles):
    """单页应用静态资源：未命中的路径回退到 index.html，支持前端路由刷新。"""

    async def get_response(self, path: str, scope: Scope) -> Response:
        """优先返回真实静态文件；404 时回退前端入口页。"""
        try:
            return await super().get_response(path, scope)
        except StarletteHttpException as exception:
            if exception.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


@asynccontextmanager
async def applicationLifespan(application: FastAPI):
    """应用生命周期：启动时建表并初始化内置数据，关闭时释放连接。"""
    logger.info("Initializing database and built-in data ...")
    initDatabase()
    databaseSession = SessionLocal()
    try:
        initializeSystemData(databaseSession)
    finally:
        databaseSession.close()
    logger.info("Database initialized. Cache mode: %s", cacheClient.mode)
    yield
    cacheClient.close()
    engine.dispose()
    logger.info("Application shut down")


def registerRouters(application: FastAPI) -> None:
    """注册全部模块控制器，统一使用 /api/v1 前缀。"""
    apiPrefix = "/api/v1"
    moduleRouters = [
        systemController.router,
        authController.router,
        userController.router,
        teamController.router,
        taskController.router,
        todoController.router,
        dashboardController.router,
        settingController.router,
        adminController.router,
        aiController.router,
        aiConfigController.router,
        notificationController.router,
        subTeamController.router,
        collaborationController.router,
    ]
    for moduleRouter in moduleRouters:
        application.include_router(moduleRouter, prefix=apiPrefix)


def mountFrontendStaticFiles(application: FastAPI) -> None:
    """若存在前端构建产物，则托管为单页应用静态资源。"""
    frontendDirectory = settings.resolvedFrontendDistPath
    if frontendDirectory and Path(frontendDirectory).is_dir():
        application.mount(
            "/",
            SinglePageStaticFiles(directory=frontendDirectory, html=True),
            name="frontend",
        )
        logger.info("Serving frontend static assets from: %s", frontendDirectory)
    else:
        logger.info("No frontend build found; serving API only")


def createApp() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    application = FastAPI(
        title=f"{APP_NAME} API",
        description="Backend API for the lightweight team task management system",
        version=APP_VERSION,
        lifespan=applicationLifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.corsOriginList,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    registerExceptionHandlers(application)
    registerRouters(application)
    mountFrontendStaticFiles(application)
    return application


# 供 uvicorn 直接引用的应用实例
app = createApp()