"""任务领域业务服务：发布、列表、详情、修改、取消与审核状态机。

任务聚合状态由本模块的 recomputeTaskStatus 在每次分配变化后统一重算，
保证列表筛选与详情展示的状态始终一致。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import forbidden, notFound, validationError
from TaskManagementBackend.core.permissions import (
    getMembershipOrNone,
    requireCanCreateTask,
    requireCanEditTask,
    requireTeamActiveForTasks,
    requireTeamMember,
    resolveTargetMembers,
)
from TaskManagementBackend.models import (
    SubTeam,
    SubTeamMember,
    Task,
    TaskAssignment,
    Team,
    TeamMember,
    User,
)
from TaskManagementBackend.models.enums import (
    AcceptanceMode,
    AssignmentMode,
    AssignmentSource,
    AssignmentStatus,
    CollaborationPhase,
    NotificationType,
    ReviewStage,
    TaskStatus,
    TeamRole,
)
from TaskManagementBackend.repositories.taskRepository import TaskRepository
from TaskManagementBackend.schemas.taskSchema import CreateTaskRequest, UpdateTaskRequest
from TaskManagementBackend.services.aiAssignmentService import autoAssignTask
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.notificationService import createNotifications
from TaskManagementBackend.utils.timeUtils import getCurrentTime


def buildAssignmentItem(assignment: TaskAssignment) -> dict:
    """把任务分配 ORM 对象序列化为 TaskAssignmentItem 字典。"""
    user = assignment.user
    return {
        "id": assignment.id,
        "userId": assignment.userId,
        "username": user.username if user is not None else "deleted",
        "nickname": user.nickname if user is not None else "Deleted User",
        "avatar": user.avatar if user is not None else None,
        "status": assignment.status,
        "acceptedAt": assignment.acceptedAt,
        "submittedAt": assignment.submittedAt,
        "reviewedAt": assignment.reviewedAt,
        "reviewedBy": assignment.reviewedBy,
        "reviewComment": assignment.reviewComment,
        "reviewStage": assignment.reviewStage,
        "targetReviewedAt": assignment.targetReviewedAt,
        "targetReviewerId": assignment.targetReviewerId,
        "targetReviewComment": assignment.targetReviewComment,
        "assignmentSource": assignment.assignmentSource or "manual",
    }


def splitRequiredSkillNames(requiredSkillNames: str | None) -> list[str]:
    """把数据库中的逗号分隔技能标签解析为列表。"""
    if not requiredSkillNames:
        return []
    return [skillName.strip() for skillName in requiredSkillNames.split(",") if skillName.strip()]


def buildTaskItem(task: Task, currentUser: User, membership: TeamMember | None) -> dict:
    """把任务 ORM 对象序列化为 TaskItem 字典，并附带当前用户视角的权限标记。"""
    assignments = list(task.assignments)
    myAssignment = next((item for item in assignments if item.userId == currentUser.id), None)
    isTeamAdmin = membership is not None and membership.role == TeamRole.ADMIN
    isCollaborationTask = task.collaborationId is not None
    if isCollaborationTask:
        # 协作任务由协作模块提供确认/双审核权限标记，普通审核标记关闭
        hasReviewPermission = False
        hasEditPermission = task.createdBy == currentUser.id
        canAssignMembers = False
    else:
        hasReviewPermission = (
            task.createdBy == currentUser.id if task.createdBy is not None else isTeamAdmin
        )
        hasEditPermission = task.createdBy == currentUser.id or isTeamAdmin
        canAssignMembers = (
            len(assignments) == 0
            and (task.createdBy == currentUser.id or isTeamAdmin)
            and task.status not in (TaskStatus.ARCHIVED, TaskStatus.CANCELLED)
        )
    return {
        "id": task.id,
        "teamId": task.teamId,
        "teamName": task.team.name if task.team is not None else "",
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "assignmentMode": task.assignmentMode,
        "acceptanceMode": task.acceptanceMode,
        "targetLevelMin": task.targetLevelMin,
        "targetLevelMax": task.targetLevelMax,
        "dueAt": task.dueAt,
        "createdBy": task.createdBy,
        "createdByName": task.creator.nickname if task.creator is not None else "Deleted User",
        "createdAt": task.createdAt,
        "updatedAt": task.updatedAt,
        "archivedAt": task.archivedAt,
        "assignments": [buildAssignmentItem(item) for item in assignments],
        "myAssignment": buildAssignmentItem(myAssignment) if myAssignment is not None else None,
        "canReview": hasReviewPermission,
        "canEdit": hasEditPermission and task.status not in (TaskStatus.ARCHIVED, TaskStatus.CANCELLED),
        "canAssign": canAssignMembers,
        "reviewCount": len(task.reviews),
        "subTeamId": task.subTeamId,
        "subTeamName": task.subTeam.name if task.subTeam is not None else None,
        "sourceTeamId": task.sourceTeamId,
        "sourceTeamName": task.sourceTeam.name if task.sourceTeam is not None else None,
        "sourceSubTeamId": task.sourceSubTeamId,
        "sourceSubTeamName": task.sourceSubTeam.name if task.sourceSubTeam is not None else None,
        "targetTeamId": task.targetTeamId,
        "targetTeamName": task.targetTeam.name if task.targetTeam is not None else None,
        "targetSubTeamId": task.targetSubTeamId,
        "targetSubTeamName": task.targetSubTeam.name if task.targetSubTeam is not None else None,
        "collaborationId": task.collaborationId,
        "collaborationPhase": task.collaborationPhase,
        "collaborationComment": task.collaborationComment,
        "autoAssigned": bool(task.autoAssigned),
        "requiredSkillNames": splitRequiredSkillNames(task.requiredSkillNames),
    }


def buildTaskDetail(task: Task, currentUser: User, membership: TeamMember | None) -> dict:
    """在任务列表项基础上追加审核记录，构建 TaskDetail 字典。"""
    detail = buildTaskItem(task, currentUser, membership)
    detail["reviews"] = [
        {
            "id": review.id,
            "taskId": review.taskId,
            "assignmentId": review.assignmentId,
            "reviewerId": review.reviewerId or 0,
            "reviewerName": review.reviewerName,
            "result": review.result,
            "comment": review.comment,
            "createdAt": review.createdAt,
        }
        for review in task.reviews
    ]
    return detail


def recomputeTaskStatus(task: Task, taskRepository: TaskRepository) -> None:
    """按全部分配记录重算任务聚合状态（每次分配变化后调用）。

    规则：已归档/已取消为终态；全部分配归档 → archived 并记录归档时间；
    存在待审核 → pendingReview；存在进行中 → inProgress；仅待接受 → published；
    没有任何分配（可选任务全部被拒绝）→ cancelled。
    """
    if task.status in (TaskStatus.ARCHIVED, TaskStatus.CANCELLED):
        return
    counts = taskRepository.countAssignmentStatuses(task.id)
    totalCount = sum(counts.values())
    if totalCount == 0:
        task.status = TaskStatus.CANCELLED
        return
    archivedCount = counts.get(AssignmentStatus.ARCHIVED.value, 0)
    if archivedCount == totalCount:
        task.status = TaskStatus.ARCHIVED
        task.archivedAt = task.archivedAt or getCurrentTime()
        return
    if counts.get(AssignmentStatus.PENDING_REVIEW.value, 0) > 0:
        task.status = TaskStatus.PENDING_REVIEW
    elif counts.get(AssignmentStatus.IN_PROGRESS.value, 0) > 0:
        task.status = TaskStatus.IN_PROGRESS
    else:
        task.status = TaskStatus.PUBLISHED


class TaskService(BaseService):
    """任务业务服务：编排权限校验、状态机推进与响应序列化。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化任务仓储。"""
        super().__init__(db)
        self.taskRepository = TaskRepository(db)

    def _isSubTeamMember(self, subTeamId: int | None, userId: int) -> bool:
        """判断用户是否属于指定子团队。"""
        if subTeamId is None:
            return False
        statement = select(SubTeamMember.id).where(
            SubTeamMember.subTeamId == subTeamId, SubTeamMember.userId == userId
        )
        return self.db.execute(statement).first() is not None

    def _getSubTeamOrRaise(self, teamId: int, subTeamId: int | None) -> SubTeam | None:
        """校验子团队属于指定团队并返回；未指定时返回 None。"""
        if subTeamId is None:
            return None
        subTeam = self.db.get(SubTeam, subTeamId)
        if subTeam is None or subTeam.parentTeamId != teamId:
            raise validationError("Sub-team not found or does not belong to this team")
        return subTeam

    def _listUserSubTeamIds(self, teamId: int, userId: int) -> list[int]:
        """查询用户在指定团队下所属的全部子团队主键。"""
        statement = (
            select(SubTeamMember.subTeamId)
            .join(SubTeam, SubTeam.id == SubTeamMember.subTeamId)
            .where(SubTeam.parentTeamId == teamId, SubTeamMember.userId == userId)
        )
        return [int(row) for row in self.db.execute(statement).scalars().all()]

    def _loadTaskForView(
        self, currentUser: User, taskId: int, teamId: int | None = None
    ) -> tuple[Task, TeamMember | None, Team]:
        """加载任务并校验查看权限（兼容普通任务、子团队任务与协作任务）。

        返回 (任务, 当前用户在该任务相关团队中的成员关系, 相关团队)。
        协作任务允许发起方或接收方团队成员查看；普通子团队任务仅子团队成员与团队管理者可见。
        """
        task = self.taskRepository.getTaskWithRelations(taskId)
        if task is None:
            raise notFound("Task not found")
        relatedTeamIds = {task.teamId}
        if task.sourceTeamId is not None:
            relatedTeamIds.add(task.sourceTeamId)
        if teamId is not None and teamId not in relatedTeamIds:
            raise notFound("Task not found")
        if task.collaborationId is not None:
            membership = getMembershipOrNone(self.db, task.teamId, currentUser.id)
            membershipTeamId = task.teamId
            if membership is None and task.sourceTeamId is not None:
                membership = getMembershipOrNone(self.db, task.sourceTeamId, currentUser.id)
                membershipTeamId = task.sourceTeamId
            if membership is None:
                raise forbidden("You are not a member of the teams participating in this collaboration task")
            team = self.db.get(Team, membershipTeamId)
            requireTeamActiveForTasks(team)
            return task, membership, team
        team, membership = requireTeamMember(self.db, task.teamId, currentUser)
        requireTeamActiveForTasks(team)
        if task.subTeamId is not None and membership.role not in (TeamRole.ADMIN, TeamRole.SUB_ADMIN):
            if not self._isSubTeamMember(task.subTeamId, currentUser.id):
                raise forbidden("This task is only visible to sub-team members")
        return task, membership, team

    def _getTaskForMember(
        self, currentUser: User, taskId: int, teamId: int | None = None
    ) -> tuple[Task, TeamMember]:
        """查询任务并校验当前用户是所属团队成员（普通任务操作入口）。"""
        task, membership, _team = self._loadTaskForView(currentUser, taskId, teamId)
        if membership is None:
            raise forbidden("You are not a member of this team")
        return task, membership

    def _reloadAndBuildDetail(self, taskId: int, currentUser: User, membership: TeamMember) -> dict:
        """提交事务后重新加载任务关系并序列化详情，避免关系集合残留旧状态。"""
        self.db.expire_all()
        reloadedTask = self.taskRepository.getTaskWithRelations(taskId)
        return buildTaskDetail(reloadedTask, currentUser, membership)

    def createTask(self, currentUser: User, teamId: int, request: CreateTaskRequest) -> dict:
        """发布任务：校验发布权限，支持指定成员/级别范围与 AI 自动选择执行人。"""
        team, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamActiveForTasks(team)
        title = (request.title or "").strip()
        if not 2 <= len(title) <= 200:
            raise validationError("Task title must be 2-200 characters")
        dueAt = request.dueAt
        if dueAt is not None:
            dueAt = dueAt.replace(tzinfo=None) if dueAt.tzinfo is not None else dueAt
            if dueAt <= getCurrentTime():
                raise validationError("Due date must be later than the current time")
        subTeam = self._getSubTeamOrRaise(teamId, request.subTeamId)
        if subTeam is not None:
            isTeamManager = membership.role in (TeamRole.ADMIN, TeamRole.SUB_ADMIN)
            if not isTeamManager and not self._isSubTeamMember(subTeam.id, currentUser.id):
                raise forbidden("Only sub-team members or team managers can publish tasks in a sub-team")
        requiredSkillNames = [
            skillName.strip()
            for skillName in (request.requiredSkillNames or [])
            if skillName and skillName.strip()
        ]
        requiredSkillNames = list(dict.fromkeys(requiredSkillNames))
        targetMembers: list[TeamMember] = []
        autoAssignmentOutcome = None
        if request.autoAssign:
            autoAssignmentOutcome = autoAssignTask(
                self.db,
                currentUser,
                team,
                membership,
                title,
                request.description,
                request.priority,
                requiredSkillNames,
                request.targetLevelMin,
                request.targetLevelMax,
            )
        else:
            if request.assignmentMode == AssignmentMode.SPECIFIC and not request.targetUserIds:
                raise validationError("Specific assignee mode requires at least one assignee")
            if request.assignmentMode == AssignmentMode.LEVEL_RANGE and (
                request.targetLevelMin is None or request.targetLevelMax is None
            ):
                raise validationError("Level range mode requires both minimum and maximum levels")
            targetMembers = resolveTargetMembers(
                self.db,
                teamId,
                request.targetUserIds,
                request.targetLevelMin,
                request.targetLevelMax,
            )
            requireCanCreateTask(membership, targetMembers)
        task = Task(
            teamId=teamId,
            subTeamId=subTeam.id if subTeam is not None else None,
            title=title,
            description=request.description,
            priority=request.priority,
            status=TaskStatus.PUBLISHED,
            assignmentMode=request.assignmentMode,
            acceptanceMode=request.acceptanceMode,
            targetLevelMin=request.targetLevelMin if request.assignmentMode == AssignmentMode.LEVEL_RANGE else None,
            targetLevelMax=request.targetLevelMax if request.assignmentMode == AssignmentMode.LEVEL_RANGE else None,
            dueAt=dueAt,
            createdBy=currentUser.id,
            autoAssigned=bool(autoAssignmentOutcome is not None and autoAssignmentOutcome.assigned),
            requiredSkillNames=",".join(requiredSkillNames) if requiredSkillNames else None,
        )
        self.taskRepository.add(task)
        acceptedTime = getCurrentTime()
        isMandatory = request.acceptanceMode == AcceptanceMode.MANDATORY
        if request.autoAssign:
            autoAssignedUserId = (
                autoAssignmentOutcome.assigneeUserId if autoAssignmentOutcome is not None else None
            )
            if autoAssignmentOutcome is not None and autoAssignmentOutcome.assigned and autoAssignedUserId:
                self.db.add(
                    TaskAssignment(
                        taskId=task.id,
                        userId=autoAssignedUserId,
                        status=AssignmentStatus.IN_PROGRESS
                        if isMandatory
                        else AssignmentStatus.PENDING_ACCEPTANCE,
                        acceptedAt=acceptedTime if isMandatory else None,
                        assignmentSource=AssignmentSource.AI.value,
                    )
                )
                autoAssignedNotifications: list[dict] = []
                for candidate in autoAssignmentOutcome.candidates:
                    isTopCandidate = candidate.userId == autoAssignedUserId
                    autoAssignedNotifications.append(
                        {
                            "userId": candidate.userId,
                            "type": NotificationType.TASK_AUTO_ASSIGNED
                            if isTopCandidate
                            else NotificationType.TASK_MATCH_REMINDER,
                            "title": "New Task Auto-assigned" if isTopCandidate else "New Task Match Reminder",
                            "content": (
                                f"The task '{title}' has been auto-assigned to you by AI (match score {candidate.score}). Please proceed."
                                if isTopCandidate
                                else f"New task '{title}' matches your skills (score {candidate.score}). Contact the publisher if you want to take it."
                            ),
                            "taskId": task.id,
                        }
                    )
                createNotifications(self.db, autoAssignedNotifications)
                self.db.flush()
                recomputeTaskStatus(task, self.taskRepository)
            else:
                failedReason = (
                    autoAssignmentOutcome.reason
                    if autoAssignmentOutcome is not None
                    else "No suitable assignee found"
                )
                createNotifications(
                    self.db,
                    [
                        {
                            "userId": currentUser.id,
                            "type": NotificationType.TASK_ASSIGN_FAILED,
                            "title": "Task Auto-assignment Failed",
                            "content": f"No eligible assignee was found for task '{title}' ({failedReason}). Please assign manually or adjust the required skills.",
                            "taskId": task.id,
                        }
                    ],
                )
                self.db.flush()
        else:
            for member in targetMembers:
                self.db.add(
                    TaskAssignment(
                        taskId=task.id,
                        userId=member.userId,
                        status=AssignmentStatus.IN_PROGRESS
                        if isMandatory
                        else AssignmentStatus.PENDING_ACCEPTANCE,
                        acceptedAt=acceptedTime if isMandatory else None,
                        assignmentSource=AssignmentSource.MANUAL.value,
                    )
                )
            self.db.flush()
            recomputeTaskStatus(task, self.taskRepository)
        self.commit()
        return self._reloadAndBuildDetail(task.id, currentUser, membership)

    def assignTaskMembers(self, currentUser: User, taskId: int, userIds: list[int]) -> dict:
        """手动指派执行人：用于 AI 自动分配无匹配或管理员改派无执行人的任务。"""
        task, membership, team = self._loadTaskForView(currentUser, taskId)
        if task.collaborationId is not None:
            raise validationError("Assignees for collaboration tasks must be assigned by the receiver liaison")
        if membership is None:
            raise forbidden("You are not a member of this team")
        requireTeamActiveForTasks(team)
        requireCanEditTask(task, currentUser, membership)
        if task.status in (TaskStatus.ARCHIVED, TaskStatus.CANCELLED):
            raise validationError("The task is archived or cancelled and cannot be assigned")
        activeAssignments = [
            assignment for assignment in task.assignments if assignment.status != AssignmentStatus.ARCHIVED
        ]
        if activeAssignments:
            raise validationError("The task already has an assignee and cannot be reassigned")
        targetMembers = resolveTargetMembers(self.db, task.teamId, userIds, None, None)
        requireCanCreateTask(membership, targetMembers)
        acceptedTime = getCurrentTime()
        isMandatory = task.acceptanceMode == AcceptanceMode.MANDATORY
        for member in targetMembers:
            self.db.add(
                TaskAssignment(
                    taskId=task.id,
                    userId=member.userId,
                    status=AssignmentStatus.IN_PROGRESS
                    if isMandatory
                    else AssignmentStatus.PENDING_ACCEPTANCE,
                    acceptedAt=acceptedTime if isMandatory else None,
                    assignmentSource=AssignmentSource.MANUAL.value,
                )
            )
        createNotifications(
            self.db,
            [
                {
                    "userId": member.userId,
                    "type": NotificationType.TASK_ASSIGNED,
                    "title": "New Task Assigned",
                    "content": f"The task '{task.title}' has been assigned to you. Please proceed.",
                    "taskId": task.id,
                }
                for member in targetMembers
            ],
        )
        self.db.flush()
        recomputeTaskStatus(task, self.taskRepository)
        self.commit()
        return self._reloadAndBuildDetail(task.id, currentUser, membership)

    def listTeamTasks(self, currentUser: User, teamId: int, query) -> dict:
        """团队任务分页列表：包含团队本级与协作任务，并按子团队可见性过滤。"""
        _team, membership = requireTeamMember(self.db, teamId, currentUser)
        filters = query.model_dump()
        subTeamIds = self._listUserSubTeamIds(teamId, currentUser.id)
        isManager = membership.role in (TeamRole.ADMIN, TeamRole.SUB_ADMIN)
        tasks, total = self.taskRepository.listTeamTasks(
            teamId, filters, query.page, query.pageSize, subTeamIds, isManager
        )
        relatedTeamIds = list(
            {teamKey for task in tasks for teamKey in (task.teamId, task.sourceTeamId) if teamKey}
        )
        memberships = self.taskRepository.listMemberships(currentUser.id, relatedTeamIds)
        items = []
        for task in tasks:
            taskMembership = memberships.get(task.teamId) or (
                memberships.get(task.sourceTeamId) if task.sourceTeamId is not None else None
            )
            items.append(buildTaskItem(task, currentUser, taskMembership))
        return {
            "items": items,
            "total": total,
            "page": query.page,
            "pageSize": query.pageSize,
        }

    def listMyTasks(self, currentUser: User, query) -> dict:
        """我的任务中心：role=created 我发布的 / assigned 我参与的 / 空为两者并集。"""
        filters = query.model_dump()
        tasks, total = self.taskRepository.listMyTasks(
            currentUser.id, query.role, filters, query.page, query.pageSize
        )
        teamIds = list(
            {teamKey for task in tasks for teamKey in (task.teamId, task.sourceTeamId) if teamKey}
        )
        memberships = self.taskRepository.listMemberships(currentUser.id, teamIds)
        return {
            "items": [
                buildTaskItem(
                    task,
                    currentUser,
                    memberships.get(task.teamId)
                    or (
                        memberships.get(task.sourceTeamId)
                        if task.sourceTeamId is not None
                        else None
                    ),
                )
                for task in tasks
            ],
            "total": total,
            "page": query.page,
            "pageSize": query.pageSize,
        }

    def getTaskDetail(self, currentUser: User, taskId: int, teamId: int | None = None) -> dict:
        """任务详情：普通任务/子团队任务/协作任务按各自可见性规则查看。"""
        task, membership, _team = self._loadTaskForView(currentUser, taskId, teamId)
        return buildTaskDetail(task, currentUser, membership)

    def updateTask(
        self, currentUser: User, teamId: int, taskId: int, request: UpdateTaskRequest
    ) -> dict:
        """修改任务：发布者或团队管理员可改，已归档/已取消任务禁止修改。"""
        task, membership = self._getTaskForMember(currentUser, taskId, teamId)
        if task.collaborationId is not None:
            raise validationError("Collaboration tasks must be handled in the Collaboration Center")
        requireCanEditTask(task, currentUser, membership)
        if task.status in (TaskStatus.ARCHIVED, TaskStatus.CANCELLED):
            raise validationError("The task is archived or cancelled and cannot be modified")
        updates = request.model_dump(exclude_unset=True)
        if "title" in updates:
            title = (updates["title"] or "").strip()
            if not 2 <= len(title) <= 200:
                raise validationError("Task title must be 2-200 characters")
            task.title = title
        if "description" in updates:
            task.description = updates["description"]
        if updates.get("priority") is not None:
            task.priority = updates["priority"]
        if updates.get("acceptanceMode") is not None:
            task.acceptanceMode = updates["acceptanceMode"]
        if "dueAt" in updates:
            dueAt = updates["dueAt"]
            if dueAt is not None:
                dueAt = dueAt.replace(tzinfo=None) if dueAt.tzinfo is not None else dueAt
                if dueAt <= getCurrentTime():
                    raise validationError("Due date must be later than the current time")
            task.dueAt = dueAt
        self.commit()
        return self._reloadAndBuildDetail(task.id, currentUser, membership)

    def cancelTask(self, currentUser: User, taskId: int) -> dict:
        """取消任务：发布者或团队管理员可取消未归档任务，取消后为终态。"""
        task, membership = self._getTaskForMember(currentUser, taskId)
        if task.collaborationId is not None:
            raise validationError("Collaboration tasks must be handled in the Collaboration Center")
        requireCanEditTask(task, currentUser, membership)
        if task.status == TaskStatus.CANCELLED:
            raise validationError("The task is already cancelled")
        if task.status == TaskStatus.ARCHIVED:
            raise validationError("Archived tasks cannot be cancelled")
        task.status = TaskStatus.CANCELLED
        self.commit()
        return self._reloadAndBuildDetail(task.id, currentUser, membership)
