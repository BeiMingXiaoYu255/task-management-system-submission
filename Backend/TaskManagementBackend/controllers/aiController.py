"""AI 辅助接口控制器（v1.1）：模块状态与任务执行人推荐。

路由路径包含 /ai/status 与 /teams/{teamId}/ai/recommend-assignees，
因此路由器不设置统一前缀，由主应用追加 /api/v1；控制器只做参数转发，不写业务逻辑。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.aiSchema import (
    AiStatusResponse,
    RecommendAssigneesRequest,
    RecommendResponse,
)
from TaskManagementBackend.services.aiService import AIService

router = APIRouter(tags=["AI"])


@router.get("/ai/status", response_model=AiStatusResponse, summary="AI module status")
def getAiStatus(
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """返回 AI 模块调度模式、本地引擎与 LLM 配置状态。"""
    return AIService(db).getStatus()


@router.post(
    "/teams/{teamId}/ai/recommend-assignees",
    response_model=RecommendResponse,
    summary="Recommend task assignees",
)
def recommendAssignees(
    teamId: int,
    payload: RecommendAssigneesRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """按任务内容、级别范围与所需技能推荐执行人，返回调度链路与候选明细。"""
    return AIService(db).recommendAssignees(currentUser, teamId, payload)
