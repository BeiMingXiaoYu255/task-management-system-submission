"""协作任务双审核服务：接收方审核与发起方审核的状态机、审核记录与通知。

从 collaborationTaskService 拆分而来：本模块只负责两个审核动作（target-review /
source-review）；任务创建、接收方确认接单与查询仍由 collaborationTaskService 负责。
审核通过/驳回会推进待办状态、重算任务聚合状态与协作阶段，并通知相关方。
"""

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import forbidden, notFound, validationError
from TaskManagementBackend.models import Task, TaskAssignment, User
from TaskManagementBackend.models.enums import (
    AssignmentStatus,
    CollaborationPhase,
    NotificationType,
    ReviewStage,
    TaskStatus,
)
from TaskManagementBackend.repositories.taskRepository import TaskRepository
from TaskManagementBackend.schemas.collaborationSchema import ReviewCollaborationTaskRequest
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.collaborationPermissionService import (
    CollaborationViewerContext,
    enumValue,
    requireCanSourceReview,
    resolveSourceReviewerUserIds,
)
from TaskManagementBackend.services.collaborationSharedService import (
    buildCollaborationTaskDetail,
    buildNotificationDefinitions,
    buildReviewRecord,
    loadCollaborationTaskOrRaise,
    notifyInitiatorParticipants,
    notifyTaskReviewResult,
    recomputeCollaborationPhase,
)
from TaskManagementBackend.services.notificationService import createNotifications
from TaskManagementBackend.services.taskService import recomputeTaskStatus
from TaskManagementBackend.utils.timeUtils import getCurrentTime


class CollaborationTaskReviewService(BaseService):
    """协作任务双审核业务服务：编排审核状态机、审核记录与通知。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化任务仓储。"""
        super().__init__(db)
        self.taskRepository = TaskRepository(db)

    def _loadViewerContext(self, currentUser: User) -> CollaborationViewerContext:
        """加载当前用户的协作可见范围上下文。"""
        return CollaborationViewerContext.load(self.db, currentUser)

    def _reloadAndBuildDetail(self, taskId: int, viewerContext: CollaborationViewerContext) -> dict:
        """提交事务后重新加载任务关系并构建协作任务详情。"""
        self.db.expire_all()
        task = self.taskRepository.getTaskWithRelations(taskId)
        return buildCollaborationTaskDetail(task, viewerContext)

    def _requireReviewPhase(self, task: Task, stageLabel: str) -> None:
        """校验任务聚合阶段处于双审核阶段之一，否则返回 400。"""
        currentPhase = enumValue(task.collaborationPhase)
        if currentPhase not in (
            CollaborationPhase.TARGET_REVIEW.value,
            CollaborationPhase.SOURCE_REVIEW.value,
        ):
            raise validationError(f"The task is not ready for {stageLabel}")

    def _loadAssignmentForReview(
        self, task: Task, assignmentUserId: int, expectedStage: ReviewStage
    ) -> TaskAssignment:
        """加载待审核执行人的待办并校验其处于指定双审核阶段。"""
        assignment = self.taskRepository.getAssignment(task.id, assignmentUserId)
        if assignment is None:
            raise notFound("To-do item for this assignee was not found")
        if (
            assignment.status != AssignmentStatus.PENDING_REVIEW
            or assignment.reviewStage != expectedStage.value
        ):
            raise validationError("The to-do item is not at the expected review stage")
        return assignment

    def _recordTaskReview(
        self,
        task: Task,
        assignment: TaskAssignment,
        currentUser: User,
        request: ReviewCollaborationTaskRequest,
    ) -> None:
        """写入一条双审核记录（通过/驳回均留痕）。"""
        self.db.add(
            buildReviewRecord(
                task.id, assignment.id, currentUser.id, request.approved, request.comment
            )
        )

    def targetReview(
        self, currentUser: User, taskId: int, request: ReviewCollaborationTaskRequest
    ) -> dict:
        """接收方对接人审核执行人提交：通过进入发起方审核，驳回回到执行中。"""
        task = loadCollaborationTaskOrRaise(self.db, taskId)
        collaboration = task.collaboration
        viewerContext = self._loadViewerContext(currentUser)
        targetTeamId = task.targetTeamId or task.teamId
        if (
            collaboration.targetLiaisonUserId != currentUser.id
            or not viewerContext.isUnitMember(targetTeamId, task.targetSubTeamId)
        ):
            raise forbidden("Only the receiver liaison can review this collaboration task")
        if task.status == TaskStatus.CANCELLED:
            raise validationError("A cancelled task cannot be reviewed")
        self._requireReviewPhase(task, "receiver review")
        assignment = self._loadAssignmentForReview(task, request.assignmentUserId, ReviewStage.TARGET)
        reviewedTime = getCurrentTime()
        self._recordTaskReview(task, assignment, currentUser, request)
        assignment.targetReviewedAt = reviewedTime
        assignment.targetReviewerId = currentUser.id
        assignment.targetReviewComment = request.comment
        if request.approved:
            assignment.reviewStage = ReviewStage.SOURCE.value
            createNotifications(
                self.db,
                buildNotificationDefinitions(
                    resolveSourceReviewerUserIds(self.db, task),
                    NotificationType.COLLABORATION_TASK_SOURCE_REVIEW,
                    "Collaboration task pending initiator review",
                    f'The collaboration task "{task.title}" passed the receiver review. Complete the initiator review.',
                    taskId=task.id,
                    collaborationId=collaboration.id,
                ),
            )
        else:
            assignment.status = AssignmentStatus.IN_PROGRESS
            assignment.reviewStage = None
            assignment.reviewedAt = reviewedTime
            assignment.reviewedBy = currentUser.id
            assignment.reviewComment = request.comment
            notifyTaskReviewResult(self.db, assignment, task, False)
        self.db.flush()
        recomputeTaskStatus(task, self.taskRepository)
        recomputeCollaborationPhase(task)
        self.commit()
        return self._reloadAndBuildDetail(task.id, viewerContext)

    def sourceReview(
        self, currentUser: User, taskId: int, request: ReviewCollaborationTaskRequest
    ) -> dict:
        """发起方审核：通过后待办归档（全部归档则任务归档），驳回回到执行中。"""
        task = loadCollaborationTaskOrRaise(self.db, taskId)
        collaboration = task.collaboration
        viewerContext = self._loadViewerContext(currentUser)
        requireCanSourceReview(task, currentUser, viewerContext)
        if task.status == TaskStatus.CANCELLED:
            raise validationError("A cancelled task cannot be reviewed")
        self._requireReviewPhase(task, "initiator review")
        assignment = self._loadAssignmentForReview(task, request.assignmentUserId, ReviewStage.SOURCE)
        reviewedTime = getCurrentTime()
        self._recordTaskReview(task, assignment, currentUser, request)
        if request.approved:
            assignment.status = AssignmentStatus.ARCHIVED
        else:
            assignment.status = AssignmentStatus.IN_PROGRESS
        assignment.reviewStage = None
        assignment.reviewedAt = reviewedTime
        assignment.reviewedBy = currentUser.id
        assignment.reviewComment = request.comment
        notifyTaskReviewResult(self.db, assignment, task, request.approved)
        self.db.flush()
        recomputeTaskStatus(task, self.taskRepository)
        recomputeCollaborationPhase(task)
        if request.approved and task.status == TaskStatus.ARCHIVED:
            notifyInitiatorParticipants(
                self.db,
                collaboration,
                NotificationType.COLLABORATION_TASK_ARCHIVED,
                "Collaboration task archived",
                f'The collaboration task "{task.title}" passed both reviews and has been archived.',
                taskId=task.id,
            )
        self.commit()
        return self._reloadAndBuildDetail(task.id, viewerContext)
