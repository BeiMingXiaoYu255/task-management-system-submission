"""AI 配置接口控制器（v1.1.1）：AI/LLM 配置读写与连通性测试。

路由统一前缀 /api/v1/settings/ai-config，配置为系统级全局配置；
GET 任意登录用户可读（非管理员只读），PUT 与连通性测试仅全局管理员/超级用户。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getClientIp, getCurrentUser, requireGlobalAdmin
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.aiConfigSchema import (
    AIConfigResponse,
    AIConfigTestResponse,
    TestAIConfigRequest,
    UpdateAIConfigRequest,
)
from TaskManagementBackend.services.aiConfigService import AIConfigService

router = APIRouter(prefix="/settings/ai-config", tags=["AI Config"])


@router.get("", response_model=AIConfigResponse, summary="Get AI configuration")
def getAiConfig(
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """读取有效 AI 配置（数据库优先、环境兜底）：Key 仅管理员可见掩码。"""
    return AIConfigService(db).getConfig(currentUser)


@router.put("", response_model=AIConfigResponse, summary="Save AI configuration")
def updateAiConfig(
    payload: UpdateAIConfigRequest,
    currentUser: User = Depends(requireGlobalAdmin),
    clientIp: str = Depends(getClientIp),
    db: Session = Depends(getDb),
) -> dict:
    """部分更新 AI 配置并持久化到 system_settings，写审计日志后返回最新配置。"""
    return AIConfigService(db).updateConfig(currentUser, payload, clientIp)


@router.post("/test", response_model=AIConfigTestResponse, summary="AI connectivity test")
def testAiConfig(
    payload: TestAIConfigRequest,
    currentUser: User = Depends(requireGlobalAdmin),
    db: Session = Depends(getDb),
) -> dict:
    """测试本地规则引擎与 LLM 实际连通性（可用表单草稿覆盖，不修改已保存配置）。"""
    return AIConfigService(db).testConnectivity(payload)
