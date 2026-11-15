"""仪表盘业务服务：聚合当前用户待办、任务分布、近七日趋势与团队统计。

统计口径说明：
    1. 待办类指标只统计当前用户作为执行人的任务分配（不含已取消任务的待办）；
    2. 趋势指标的 created 为当前用户当日创建的任务数，completed 为当日审核通过的待办数；
    3. teamStats 汇总当前用户所在团队的成员数与任务数，可按 teamId 过滤单个团队。
"""

from datetime import timedelta

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import forbidden
from TaskManagementBackend.core.permissions import getMembershipOrNone
from TaskManagementBackend.models import User
from TaskManagementBackend.repositories.dashboardRepository import DashboardRepository
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.utils.timeUtils import getCurrentTime

# 近七日趋势统计天数
TREND_DAYS = 7

# 未完成待办状态对应的 DashboardSummary 字段
PENDING_STATUS_FIELDS = (
    ("pendingAcceptance", "pendingAcceptanceCount"),
    ("inProgress", "inProgressCount"),
    ("pendingReview", "pendingReviewCount"),
)


class DashboardService(BaseService):
    """仪表盘业务服务：编排统计查询并组装 DashboardSummary。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化仪表盘仓储。"""
        super().__init__(db)
        self.dashboardRepository = DashboardRepository(db)

    def _validateTeamScope(self, currentUser: User, teamId: int | None) -> None:
        """校验团队筛选参数：只能查看自己已加入团队的统计。"""
        if teamId is None:
            return
        if getMembershipOrNone(self.db, teamId, currentUser.id) is None:
            raise forbidden("You are not a member of this team and cannot view its statistics")

    def _buildWeeklyTrend(self, currentUser: User, teamId: int | None) -> list[dict]:
        """构建近七日创建/完成趋势：缺失日期补 0，保证前端折线连续。"""
        today = getCurrentTime().replace(hour=0, minute=0, second=0, microsecond=0)
        startDay = today - timedelta(days=TREND_DAYS - 1)
        createdCounts = self.dashboardRepository.getCreatedTaskTrend(
            currentUser.id, teamId, startDay
        )
        completedCounts = self.dashboardRepository.getCompletedAssignmentTrend(
            currentUser.id, teamId, startDay
        )
        trendItems: list[dict] = []
        for offset in range(TREND_DAYS):
            dayKey = (startDay + timedelta(days=offset)).strftime("%Y-%m-%d")
            trendItems.append(
                {
                    "date": dayKey,
                    "created": createdCounts.get(dayKey, 0),
                    "completed": completedCounts.get(dayKey, 0),
                }
            )
        return trendItems

    def _buildTeamStats(self, currentUser: User, teamId: int | None) -> list[dict]:
        """构建团队统计列表：成员数、开放任务数、已归档任务数。"""
        teams = self.dashboardRepository.listUserTeams(currentUser.id, teamId)
        teamIds = [team.id for team in teams]
        memberCounts = self.dashboardRepository.countMembersByTeams(teamIds)
        taskCounts = self.dashboardRepository.countTasksByTeams(teamIds)
        teamStatistics: list[dict] = []
        for team in teams:
            openTaskCount, archivedTaskCount = taskCounts.get(team.id, (0, 0))
            teamStatistics.append(
                {
                    "teamId": team.id,
                    "teamName": team.name,
                    "memberCount": memberCounts.get(team.id, 0),
                    "openTaskCount": openTaskCount,
                    "archivedTaskCount": archivedTaskCount,
                }
            )
        return teamStatistics

    def getSummary(self, currentUser: User, teamId: int | None = None) -> dict:
        """获取仪表盘汇总数据；teamId 为空时聚合当前用户的全部团队。"""
        self._validateTeamScope(currentUser, teamId)
        statusCounts = self.dashboardRepository.getAssignmentStatusCounts(
            currentUser.id, teamId
        )
        weekStartTime = getCurrentTime() - timedelta(days=TREND_DAYS)
        summary = {
            "todoCount": sum(statusCounts.get(statusName, 0) for statusName, _ in PENDING_STATUS_FIELDS),
            "archivedThisWeek": self.dashboardRepository.countArchivedAssignments(
                currentUser.id, teamId, since=weekStartTime
            ),
            "overdueCount": self.dashboardRepository.countOverdueAssignments(
                currentUser.id, teamId
            ),
            "archivedTotal": self.dashboardRepository.countArchivedAssignments(
                currentUser.id, teamId
            ),
            "byPriority": [
                {"priority": priority, "count": count}
                for priority, count in self.dashboardRepository.getPriorityDistribution(
                    currentUser.id, teamId
                )
            ],
            "byStatus": [
                {"status": status, "count": count}
                for status, count in self.dashboardRepository.getStatusDistribution(
                    currentUser.id, teamId
                )
            ],
            "weeklyTrend": self._buildWeeklyTrend(currentUser, teamId),
            "teamStats": self._buildTeamStats(currentUser, teamId),
        }
        for statusName, fieldName in PENDING_STATUS_FIELDS:
            summary[fieldName] = statusCounts.get(statusName, 0)
        return summary
