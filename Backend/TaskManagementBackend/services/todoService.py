"""待办领域业务服务：待办列表/统计与接受、拒绝、提交完成、审核动作。

任务分配（task_assignments）即个人待办，本模块负责待办视角的业务动作；
审核通过/驳回会同步推进任务聚合状态（复用 taskService 的重算逻辑）。
"""

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import forbidden, notFound, validationError
from TaskManagementBackend.core.permissions import (
    requireCanReviewTask,
    requireTeamActiveForTasks,
    requireTeamMember,
)
from TaskManagementBackend.models import Task, TaskAssignment, TaskReview, TeamMember, User
from TaskManagementBackend.models.enums import (
    AcceptanceMode,
    AssignmentStatus,
    CollaborationPhase,
    NotificationType,
    ReviewResult,
    ReviewStage,
    TaskStatus,
)
from TaskManagementBackend.repositories.taskRepository import TaskRepository
from TaskManagementBackend.repositories.todoRepository import TodoRepository
from TaskManagementBackend.schemas.taskSchema import ReviewTaskRequest
from TaskManagementBackend.schemas.todoSchema import TodoListQuery
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.notificationService import createNotifications
from TaskManagementBackend.services.taskService import buildTaskDetail, recomputeTaskStatus
from TaskManagementBackend.utils.timeUtils import getCurrentTime, isOverdue


def enumValue(value) -> str:
    """把枚举或普通字符串统一转换为字符串值。"""
    return value.value if hasattr(value, "value") else str(value)


def buildTodoItem(assignment: TaskAssignment) -> dict:
    """把待办（任务分配）ORM 对象序列化为 TodoItem 字典。"""
    task = assignment.task
    creator = task.creator if task is not None else None
    dueAt = task.dueAt if task is not None else None
    return {
        "assignmentId": assignment.id,
        "taskId": assignment.taskId,
        "teamId": task.teamId,
        "teamName": task.team.name if task is not None and task.team is not None else "",
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "taskStatus": enumValue(task.status),
        "assignmentStatus": enumValue(assignment.status),
        "dueAt": dueAt,
        "createdByName": creator.nickname if creator is not None else "Deleted User",
        "acceptedAt": assignment.acceptedAt,
        "createdAt": assignment.createdAt,
        "overdue": isOverdue(dueAt, enumValue(assignment.status)),
        "collaborationId": task.collaborationId if task is not None else None,
        "collaborationPhase": task.collaborationPhase if task is not None else None,
        "sourceTeamName": (
            task.sourceTeam.name if task is not None and task.sourceTeam is not None else None
        ),
        "targetTeamName": (
            task.targetTeam.name if task is not None and task.targetTeam is not None else None
        ),
        "reviewStage": assignment.reviewStage,
    }


class TodoService(BaseService):
    """待办业务服务：编排接受/拒绝/提交/审核动作与待办统计。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化任务、待办仓储。"""
        super().__init__(db)
        self.taskRepository = TaskRepository(db)
        self.todoRepository = TodoRepository(db)

    def _loadAssignmentContext(
        self, currentUser: User, taskId: int
    ) -> tuple[Task, TeamMember, TaskAssignment]:
        """加载任务与当前用户的待办分配，并校验团队成员身份。"""
        task = self.taskRepository.getTaskWithRelations(taskId)
        if task is None:
            raise notFound("Task not found")
        team, membership = requireTeamMember(self.db, task.teamId, currentUser)
        requireTeamActiveForTasks(team)
        assignment = next((item for item in task.assignments if item.userId == currentUser.id), None)
        if assignment is None:
            raise forbidden("You are not an assignee of this task")
        return task, membership, assignment

    def _reloadAndBuildDetail(self, taskId: int, currentUser: User, membership: TeamMember) -> dict:
        """提交事务后重新加载任务关系并序列化详情。"""
        self.db.expire_all()
        reloadedTask = self.taskRepository.getTaskWithRelations(taskId)
        return buildTaskDetail(reloadedTask, currentUser, membership)

    def listTodos(self, currentUser: User, query: TodoListQuery) -> dict:
        """我的待办分页：status 不传时返回全部未归档待办。"""
        filters = query.model_dump()
        assignments, total = self.todoRepository.listTodos(
            currentUser.id, filters, query.page, query.pageSize
        )
        return {
            "items": [buildTodoItem(assignment) for assignment in assignments],
            "total": total,
            "page": query.page,
            "pageSize": query.pageSize,
        }

    def getTodoStats(self, currentUser: User) -> dict:
        """我的待办统计：按待办状态计数，total 为未归档合计。"""
        counts = self.todoRepository.getStatusCounts(currentUser.id)
        pendingAcceptance = counts.get("pendingAcceptance", 0)
        inProgress = counts.get("inProgress", 0)
        pendingReview = counts.get("pendingReview", 0)
        return {
            "total": pendingAcceptance + inProgress + pendingReview,
            "pendingAcceptance": pendingAcceptance,
            "inProgress": inProgress,
            "pendingReview": pendingReview,
            "archived": counts.get("archived", 0),
            "overdue": self.todoRepository.countOverdue(currentUser.id),
        }

    def acceptTask(self, currentUser: User, taskId: int) -> dict:
        """接受可选任务：待办从待接受变为进行中（必须接受任务无需此操作）。"""
        task, membership, assignment = self._loadAssignmentContext(currentUser, taskId)
        if task.acceptanceMode != AcceptanceMode.OPTIONAL:
            raise validationError("This is a mandatory task and does not require manual acceptance")
        if assignment.status != AssignmentStatus.PENDING_ACCEPTANCE:
            raise validationError("The to-do cannot be accepted in its current status")
        assignment.status = AssignmentStatus.IN_PROGRESS
        assignment.acceptedAt = getCurrentTime()
        self.db.flush()
        recomputeTaskStatus(task, self.taskRepository)
        self.commit()
        return self._reloadAndBuildDetail(task.id, currentUser, membership)

    def declineTask(self, currentUser: User, taskId: int) -> dict:
        """拒绝可选任务：从任务中移除该待办；全部拒绝后任务自动取消。"""
        task, membership, assignment = self._loadAssignmentContext(currentUser, taskId)
        if task.acceptanceMode != AcceptanceMode.OPTIONAL:
            raise validationError("This is a mandatory task and cannot be declined")
        if assignment.status != AssignmentStatus.PENDING_ACCEPTANCE:
            raise validationError("The to-do cannot be declined in its current status")
        self.db.delete(assignment)
        self.db.flush()
        recomputeTaskStatus(task, self.taskRepository)
        self.commit()
        return self._reloadAndBuildDetail(task.id, currentUser, membership)

    def submitTask(self, currentUser: User, taskId: int) -> dict:
        """提交完成：待办进入待审核，等待任务发布者审核。"""
        task, membership, assignment = self._loadAssignmentContext(currentUser, taskId)
        if assignment.status != AssignmentStatus.IN_PROGRESS:
            raise validationError("Only in-progress tasks can be submitted for review")
        assignment.status = AssignmentStatus.PENDING_REVIEW
        assignment.submittedAt = getCurrentTime()
        assignment.reviewComment = None
        if task.collaborationId is not None:
            # 协作任务：进入接收方对接人审核阶段
            assignment.reviewStage = ReviewStage.TARGET.value
            task.collaborationPhase = CollaborationPhase.TARGET_REVIEW.value
            collaboration = task.collaboration
            if collaboration is not None and collaboration.targetLiaisonUserId is not None:
                createNotifications(
                    self.db,
                    [
                        {
                            "userId": collaboration.targetLiaisonUserId,
                            "type": NotificationType.COLLABORATION_TASK_TARGET_REVIEW,
                            "title": "Collaboration Task Pending Receiver Review",
                            "content": f"Collaboration task '{task.title}' has been submitted by the assignee. Please proceed with the receiver review.",
                            "taskId": task.id,
                            "collaborationId": collaboration.id,
                        }
                    ],
                )
        self.db.flush()
        recomputeTaskStatus(task, self.taskRepository)
        self.commit()
        return self._reloadAndBuildDetail(task.id, currentUser, membership)

    def reviewTask(self, currentUser: User, taskId: int, request: ReviewTaskRequest) -> dict:
        """审核待办：通过后待办归档（全部归档则任务归档），驳回回到进行中并记录意见。"""
        task = self.taskRepository.getTaskWithRelations(taskId)
        if task is None:
            raise notFound("Task not found")
        if task.collaborationId is not None:
            raise validationError("Use the collaboration two-stage review endpoints for collaboration tasks")
        team, membership = requireTeamMember(self.db, task.teamId, currentUser)
        requireTeamActiveForTasks(team)
        requireCanReviewTask(task, currentUser, membership)
        if task.status == TaskStatus.CANCELLED:
            raise validationError("The task is cancelled and cannot be reviewed")
        assignment = self.taskRepository.getAssignment(task.id, request.assignmentUserId)
        if assignment is None:
            raise notFound("The assignee's to-do was not found")
        if assignment.status != AssignmentStatus.PENDING_REVIEW:
            raise validationError("The to-do cannot be reviewed in its current status")
        reviewedTime = getCurrentTime()
        self.db.add(
            TaskReview(
                taskId=task.id,
                assignmentId=assignment.id,
                reviewerId=currentUser.id,
                result=ReviewResult.APPROVED if request.approved else ReviewResult.REJECTED,
                comment=request.comment,
                createdAt=reviewedTime,
            )
        )
        assignment.reviewedAt = reviewedTime
        assignment.reviewedBy = currentUser.id
        assignment.reviewComment = request.comment
        assignment.status = (
            AssignmentStatus.ARCHIVED if request.approved else AssignmentStatus.IN_PROGRESS
        )
        createNotifications(
            self.db,
            [
                {
                    "userId": assignment.userId,
                    "type": NotificationType.TASK_REVIEW_RESULT,
                    "title": "Task Approved" if request.approved else "Task Rejected",
                    "content": (
                        f"The task '{task.title}' has been approved and archived."
                        if request.approved
                        else f"The task '{task.title}' was rejected. Please revise and resubmit based on the feedback."
                        + (f" Comment: {request.comment}" if request.comment else "")
                    ),
                    "taskId": task.id,
                }
            ],
        )
        self.db.flush()
        recomputeTaskStatus(task, self.taskRepository)
        self.commit()
        return self._reloadAndBuildDetail(task.id, currentUser, membership)
