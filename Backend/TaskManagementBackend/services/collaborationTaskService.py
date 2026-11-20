"""协作任务业务服务：创建、接收方确认指派、协作任务列表与详情。

协作任务状态机（tasks.collaboration_phase）：
    pendingConfirmation --接收方对接人确认--> executing --执行人提交(既有 /tasks/submit)--> targetReview
    targetReview --接收方审核--> sourceReview --发起方审核--> 任务归档（phase 置空）；任一审核驳回 --> executing；
    接收方拒绝接单 --> rejected（任务 cancelled）。
双审核动作（target-review / source-review）由 collaborationTaskReviewService 负责，本模块复用其共享序列化与通知函数。
"""

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import forbidden, notFound, validationError
from TaskManagementBackend.models import Task, TaskAssignment, User
from TaskManagementBackend.models.enums import (
    AcceptanceMode,
    AssignmentMode,
    AssignmentSource,
    AssignmentStatus,
    CollaborationPhase,
    CollaborationStatus,
    NotificationType,
    TaskStatus,
)
from TaskManagementBackend.repositories.collaborationRepository import CollaborationRepository
from TaskManagementBackend.repositories.taskRepository import TaskRepository
from TaskManagementBackend.schemas.collaborationSchema import (
    ConfirmCollaborationTaskRequest,
    CreateCollaborationTaskRequest,
)
from TaskManagementBackend.schemas.taskSchema import TaskListQuery
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.collaborationPermissionService import (
    CollaborationViewerContext,
    buildCollaborationUnit,
    enumValue,
    isUserUnitMember,
)
from TaskManagementBackend.services.collaborationSharedService import (
    buildCollaborationTaskDetail,
    buildCollaborationTaskItem,
    buildNotificationDefinitions,
    loadCollaborationTaskOrRaise,
    notifyInitiatorParticipants,
    requireCanViewCollaborationTask,
    splitAssigneeUserIds,
)
from TaskManagementBackend.services.notificationService import createNotifications
from TaskManagementBackend.services.taskService import recomputeTaskStatus
from TaskManagementBackend.utils.timeUtils import getCurrentTime

MIN_TASK_TITLE_LENGTH = 2
MAX_TASK_TITLE_LENGTH = 200


class CollaborationTaskService(BaseService):
    """协作任务业务服务：编排创建、接收方确认指派与查询响应。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化任务、协作仓储。"""
        super().__init__(db)
        self.taskRepository = TaskRepository(db)
        self.collaborationRepository = CollaborationRepository(db)

    def _loadViewerContext(self, currentUser: User) -> CollaborationViewerContext:
        """加载当前用户的协作可见范围上下文。"""
        return CollaborationViewerContext.load(self.db, currentUser)

    def _loadCollaborationOrRaise(self, collaborationId: int):
        """加载协作关系（预加载双方单位与对接人），不存在时抛 404。"""
        collaboration = self.collaborationRepository.getWithDetails(collaborationId)
        if collaboration is None:
            raise notFound("Collaboration not found")
        return collaboration

    def _reloadAndBuildDetail(self, taskId: int, viewerContext: CollaborationViewerContext) -> dict:
        """提交事务后重新加载任务关系并构建协作任务详情。"""
        self.db.expire_all()
        task = self.taskRepository.getTaskWithRelations(taskId)
        return buildCollaborationTaskDetail(task, viewerContext)

    def createCollaborationTask(
        self, currentUser: User, collaborationId: int, request: CreateCollaborationTaskRequest
    ) -> dict:
        """发布协作任务：仅发起单位管理员或发起方对接人，任务进入待接收方确认阶段。"""
        collaboration = self._loadCollaborationOrRaise(collaborationId)
        if collaboration.status != CollaborationStatus.ACTIVE:
            raise validationError("Only an active collaboration can have tasks created")
        viewerContext = self._loadViewerContext(currentUser)
        isInitiatorAdmin = viewerContext.isUnitAdmin(
            collaboration.initiatorTeamId, collaboration.initiatorSubTeamId
        )
        isInitiatorLiaison = collaboration.initiatorLiaisonUserId == currentUser.id
        if not isInitiatorAdmin and not isInitiatorLiaison:
            raise forbidden("Only an initiating unit admin or the initiator liaison can create collaboration tasks")
        title = (request.title or "").strip()
        if not MIN_TASK_TITLE_LENGTH <= len(title) <= MAX_TASK_TITLE_LENGTH:
            raise validationError("Task title must be 2-200 characters")
        dueAt = request.dueAt
        if dueAt is not None:
            dueAt = dueAt.replace(tzinfo=None) if dueAt.tzinfo is not None else dueAt
            if dueAt <= getCurrentTime():
                raise validationError("Due date must be later than now")
        task = Task(
            teamId=collaboration.targetTeamId,
            subTeamId=None,
            title=title,
            description=request.description,
            priority=request.priority,
            status=TaskStatus.PUBLISHED,
            assignmentMode=AssignmentMode.SPECIFIC,
            acceptanceMode=request.acceptanceMode,
            dueAt=dueAt,
            createdBy=currentUser.id,
            sourceTeamId=collaboration.initiatorTeamId,
            sourceSubTeamId=collaboration.initiatorSubTeamId,
            targetTeamId=collaboration.targetTeamId,
            targetSubTeamId=collaboration.targetSubTeamId,
            collaborationId=collaboration.id,
            collaborationPhase=CollaborationPhase.PENDING_CONFIRMATION.value,
        )
        self.taskRepository.add(task)
        if collaboration.targetLiaisonUserId is not None:
            initiatorUnitName = buildCollaborationUnit(
                collaboration.initiatorTeam, collaboration.initiatorSubTeam
            )["unitName"]
            createNotifications(
                self.db,
                buildNotificationDefinitions(
                    [collaboration.targetLiaisonUserId],
                    NotificationType.COLLABORATION_TASK_RECEIVED,
                    "Collaboration task pending confirmation",
                    f'"{initiatorUnitName}" assigned the collaboration task "{title}". Confirm it and assign assignees.',
                    taskId=task.id,
                    collaborationId=collaboration.id,
                ),
            )
        self.commit()
        return self._reloadAndBuildDetail(task.id, viewerContext)

    def listCollaborationTasks(
        self, currentUser: User, collaborationId: int, query: TaskListQuery
    ) -> dict:
        """协作任务分页列表：参与单位成员可查看，支持筛选与排序。"""
        collaboration = self._loadCollaborationOrRaise(collaborationId)
        viewerContext = self._loadViewerContext(currentUser)
        canView = viewerContext.canViewUnit(
            collaboration.initiatorTeamId, collaboration.initiatorSubTeamId
        ) or viewerContext.canViewUnit(collaboration.targetTeamId, collaboration.targetSubTeamId)
        if not canView:
            raise forbidden("You are not a member of this collaboration")
        filters = query.model_dump()
        tasks, total = self.collaborationRepository.listCollaborationTasks(
            collaborationId, filters, query.page, query.pageSize
        )
        return {
            "items": [buildCollaborationTaskItem(task, viewerContext) for task in tasks],
            "total": total,
            "page": query.page,
            "pageSize": query.pageSize,
        }

    def getCollaborationTaskDetail(self, currentUser: User, taskId: int) -> dict:
        """协作任务详情：参与单位成员可查看，含双审核信息与权限标记。"""
        task = loadCollaborationTaskOrRaise(self.db, taskId)
        viewerContext = self._loadViewerContext(currentUser)
        requireCanViewCollaborationTask(task, viewerContext)
        return buildCollaborationTaskDetail(task, viewerContext)

    def confirmCollaborationTask(
        self, currentUser: User, taskId: int, request: ConfirmCollaborationTaskRequest
    ) -> dict:
        """接收方对接人确认接单并从接收单位成员中指派 1-N 名执行人；拒绝则任务取消。"""
        task = loadCollaborationTaskOrRaise(self.db, taskId)
        collaboration = task.collaboration
        viewerContext = self._loadViewerContext(currentUser)
        targetTeamId = task.targetTeamId or task.teamId
        if (
            collaboration.targetLiaisonUserId != currentUser.id
            or not viewerContext.isUnitMember(targetTeamId, task.targetSubTeamId)
        ):
            raise forbidden("Only the receiver liaison can accept this collaboration task")
        if enumValue(task.collaborationPhase) != CollaborationPhase.PENDING_CONFIRMATION.value:
            raise validationError("This collaboration task cannot be accepted at its current stage")
        if not request.approved:
            task.status = TaskStatus.CANCELLED
            task.collaborationPhase = CollaborationPhase.REJECTED.value
            task.collaborationComment = request.comment
            notifyInitiatorParticipants(
                self.db,
                collaboration,
                NotificationType.COLLABORATION_TASK_REJECTED,
                "Collaboration task rejected",
                f'The receiver rejected the collaboration task "{task.title}". The task has been cancelled.',
                taskId=task.id,
            )
            self.commit()
            return self._reloadAndBuildDetail(task.id, viewerContext)
        assigneeUserIds = splitAssigneeUserIds(request.assigneeUserIds)
        if not assigneeUserIds:
            raise validationError("At least one assignee is required to accept the task")
        invalidUserIds = [
            userId
            for userId in assigneeUserIds
            if not isUserUnitMember(self.db, targetTeamId, task.targetSubTeamId, userId)
        ]
        if invalidUserIds:
            raise validationError("Assignees must be members of the receiving unit: " + ",".join(map(str, invalidUserIds)))
        acceptedTime = getCurrentTime()
        isMandatory = task.acceptanceMode == AcceptanceMode.MANDATORY
        for assigneeUserId in assigneeUserIds:
            self.db.add(
                TaskAssignment(
                    taskId=task.id,
                    userId=assigneeUserId,
                    status=AssignmentStatus.IN_PROGRESS
                    if isMandatory
                    else AssignmentStatus.PENDING_ACCEPTANCE,
                    acceptedAt=acceptedTime if isMandatory else None,
                    assignmentSource=AssignmentSource.COLLABORATION.value,
                )
            )
        task.collaborationPhase = CollaborationPhase.EXECUTING.value
        task.collaborationComment = request.comment
        self.db.flush()
        recomputeTaskStatus(task, self.taskRepository)
        createNotifications(
            self.db,
            buildNotificationDefinitions(
                assigneeUserIds,
                NotificationType.TASK_ASSIGNED,
                "New collaboration task assigned",
                f'The collaboration task "{task.title}" has been assigned to you. Please work on it.',
                taskId=task.id,
            ),
        )
        notifyInitiatorParticipants(
            self.db,
            collaboration,
            NotificationType.COLLABORATION_TASK_CONFIRMED,
            "Collaboration task accepted",
            f'The receiver accepted the collaboration task "{task.title}" and assigned assignees.',
            taskId=task.id,
        )
        self.commit()
        return self._reloadAndBuildDetail(task.id, viewerContext)
