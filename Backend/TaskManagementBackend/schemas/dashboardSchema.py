"""仪表盘模块 Pydantic 数据模型：汇总统计、分布、趋势与团队统计。"""

from pydantic import BaseModel


class PriorityCountItem(BaseModel):
    """按优先级统计项。"""

    priority: str
    count: int


class StatusCountItem(BaseModel):
    """按状态统计项。"""

    status: str
    count: int


class TrendItem(BaseModel):
    """每日趋势项：created 当日创建数，completed 当日完成数。"""

    date: str
    created: int
    completed: int


class TeamStatItem(BaseModel):
    """单个团队的统计项。"""

    teamId: int
    teamName: str
    memberCount: int
    openTaskCount: int
    archivedTaskCount: int


class DashboardSummaryResponse(BaseModel):
    """仪表盘汇总响应结构。"""

    todoCount: int
    pendingAcceptanceCount: int
    inProgressCount: int
    pendingReviewCount: int
    archivedThisWeek: int
    overdueCount: int
    archivedTotal: int
    byPriority: list[PriorityCountItem]
    byStatus: list[StatusCountItem]
    weeklyTrend: list[TrendItem]
    teamStats: list[TeamStatItem]
