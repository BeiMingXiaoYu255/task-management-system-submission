"""仪表盘接口控制器：汇总统计数据。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.dashboardSchema import DashboardSummaryResponse
from TaskManagementBackend.services.dashboardService import DashboardService

# 仪表盘路由统一前缀 /dashboard
router = APIRouter(tags=["Dashboard"], prefix="/dashboard")


@router.get("/summary", response_model=DashboardSummaryResponse, summary="Dashboard Summary")
def getDashboardSummary(
    teamId: int | None = Query(default=None, description="Team filter. Aggregates all teams when omitted."),
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """仪表盘汇总：待办统计、优先级/状态分布、近七日趋势与团队统计。"""
    return DashboardService(db).getSummary(currentUser, teamId)
