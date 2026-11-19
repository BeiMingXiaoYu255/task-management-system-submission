"""协作领域共享服务：响应序列化、协作任务加载/可见性校验、阶段重算与通知分发。

协作关系与协作任务两个业务服务共用本模块的纯函数，避免序列化与通知代码重复；
本模块不直接暴露 REST 接口，也不持有事务提交职责（由调用方服务提交事务）。
"""

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import forbidden, notFound, validationError
from TaskManagementBackend.models import Task, TaskAssignment, TaskReview, TeamCollaboration
from TaskManagementBackend.models.enums import (
    AssignmentStatus,
    CollaborationPhase,
    CollaborationStatus,
    NotificationType,
    ReviewResult,
    ReviewStage,
    TaskStatus,
)
from TaskManagementBackend.repositories.taskRepository import TaskRepository
from TaskManagementBackend.services.collaborationPermissionService import (
    CollaborationViewerContext,
    buildCollaborationTaskFlags,
    buildCollaborationUnit,
    enumValue,
    listUnitAdminUserIds,
)
from TaskManagementBackend.services.notificationService import createNotifications
from TaskManagementBackend.services.taskService import buildTaskDetail, buildTaskItem
from TaskManagementBackend.utils.timeUtils import getCurrentTime


def buildCollaborationItem(
    collaboration: TeamCollaboration, viewerContext: CollaborationViewerContext
) -> dict:
    """把协作关系 ORM 对象序列化为 CollaborationItem 字典（含当前用户动作标记）。"""
    initiatorSubTeamId = collaboration.initiatorSubTeamId
    targetSubTeamId = collaboration.targetSubTeamId
    status = enumValue(collaboration.status)
    isInitiatorAdmin = viewerContext.isUnitAdmin(collaboration.initiatorTeamId, initiatorSubTeamId)
    isTargetAdmin = viewerContext.isUnitAdmin(collaboration.targetTeamId, targetSubTeamId)
    isInitiatorLiaison = collaboration.initiatorLiaisonUserId == viewerContext.userId
    initiatorLiaison = collaboration.initiatorLiaison
    targetLiaison = collaboration.targetLiaison
    creator = collaboration.creator
    return {
        "id": collaboration.id,
        "initiatorUnit": buildCollaborationUnit(
            collaboration.initiatorTeam, collaboration.initiatorSubTeam
        ),
        "targetUnit": buildCollaborationUnit(
            collaboration.targetTeam, collaboration.targetSubTeam
        ),
        "initiatorLiaisonUserId": collaboration.initiatorLiaisonUserId,
        "initiatorLiaisonNickname": (
            initiatorLiaison.nickname if initiatorLiaison is not None else None
        ),
        "targetLiaisonUserId": collaboration.targetLiaisonUserId,
        "targetLiaisonNickname": targetLiaison.nickname if targetLiaison is not None else None,
        "status": status,
        "message": collaboration.message,
        "rejectComment": collaboration.rejectComment,
        "createdByName": creator.nickname if creator is not None else "Deleted User",
        "createdAt": collaboration.createdAt,
        "updatedAt": collaboration.updatedAt,
        "canConfirm": status == CollaborationStatus.PENDING.value and isTargetAdmin,
        "canEnd": status == CollaborationStatus.ACTIVE.value and (isInitiatorAdmin or isTargetAdmin),
        "canCreateTask": status == CollaborationStatus.ACTIVE.value
        and (isInitiatorAdmin or isInitiatorLiaison),
        "myUnitRole": viewerContext.resolveMyUnitRole(
            collaboration.initiatorTeamId,
            initiatorSubTeamId,
            collaboration.targetTeamId,
            targetSubTeamId,
        ),
    }


def buildCollaborationTaskItem(task: Task, viewerContext: CollaborationViewerContext) -> dict:
    """构建协作任务列表项：任务基础字段 + 双方单位 + 双审核权限标记。"""
    item = buildTaskItem(task, viewerContext.requireCurrentUser, None)
    item["sourceUnit"] = buildCollaborationUnit(task.sourceTeam, task.sourceSubTeam)
    item["targetUnit"] = buildCollaborationUnit(task.targetTeam, task.targetSubTeam)
    item.update(buildCollaborationTaskFlags(task, viewerContext))
    return item


def buildCollaborationTaskDetail(task: Task, viewerContext: CollaborationViewerContext) -> dict:
    """构建协作任务详情：列表项字段 + 审核记录。"""
    detail = buildTaskDetail(task, viewerContext.requireCurrentUser, None)
    detail["sourceUnit"] = buildCollaborationUnit(task.sourceTeam, task.sourceSubTeam)
    detail["targetUnit"] = buildCollaborationUnit(task.targetTeam, task.targetSubTeam)
    detail.update(buildCollaborationTaskFlags(task, viewerContext))
    return detail


def buildNotificationDefinitions(
    userIds,
    notificationType: NotificationType,
    title: str,
    content: str,
    taskId: int | None = None,
    collaborationId: int | None = None,
) -> list[dict]:
    """把通知接收人集合展开为 notificationService.createNotifications 所需的定义列表。"""
    return [
        {
            "userId": userId,
            "type": notificationType,
            "title": title,
            "content": content,
            "taskId": taskId,
            "collaborationId": collaborationId,
        }
        for userId in sorted({int(userId) for userId in userIds})
    ]


def buildInitiatorNotificationRecipients(
    db: Session, collaboration: TeamCollaboration
) -> list[int]:
    """解析发起方通知接收人：发起方对接人 + 发起单位管理员 + 申请人（去重排序）。"""
    recipientUserIds = set(
        listUnitAdminUserIds(
            db, collaboration.initiatorTeamId, collaboration.initiatorSubTeamId
        )
    )
    if collaboration.initiatorLiaisonUserId is not None:
        recipientUserIds.add(int(collaboration.initiatorLiaisonUserId))
    if collaboration.createdBy is not None:
        recipientUserIds.add(int(collaboration.createdBy))
    return sorted(recipientUserIds)


def notifyInitiatorParticipants(
    db: Session,
    collaboration: TeamCollaboration,
    notificationType: NotificationType,
    title: str,
    content: str,
    taskId: int | None = None,
) -> None:
    """通知发起方相关人（发起单位管理员 + 发起方对接人 + 申请人）。"""
    createNotifications(
        db,
        buildNotificationDefinitions(
            buildInitiatorNotificationRecipients(db, collaboration),
            notificationType,
            title,
            content,
            taskId=taskId,
            collaborationId=collaboration.id,
        ),
    )


def notifyTaskReviewResult(
    db: Session, assignment: TaskAssignment, task: Task, approved: bool
) -> None:
    """把审核结果通知执行人（任一审核阶段驳回均会触发返工）。"""
    createNotifications(
        db,
        buildNotificationDefinitions(
            [assignment.userId],
            NotificationType.TASK_REVIEW_RESULT,
            "Task approved" if approved else "Changes requested",
            f'The collaboration task "{task.title}" has been approved.'
            if approved
            else f'Changes were requested for the collaboration task "{task.title}". Revise it and submit again.',
            taskId=task.id,
        ),
    )


def loadCollaborationTaskOrRaise(db: Session, taskId: int) -> Task:
    """加载协作任务并预加载团队/分配/审核记录；不存在或非协作任务时抛异常。"""
    task = TaskRepository(db).getTaskWithRelations(taskId)
    if task is None:
        raise notFound("Collaboration task not found")
    if task.collaborationId is None:
        raise validationError("This task is not a collaboration task")
    return task


def requireCanViewCollaborationTask(task: Task, viewerContext: CollaborationViewerContext) -> None:
    """校验协作任务查看权限：发起方或接收方单位成员（子团队含父团队管理员）。"""
    canView = viewerContext.canViewUnit(
        task.sourceTeamId or task.teamId, task.sourceSubTeamId
    ) or viewerContext.canViewUnit(task.targetTeamId or task.teamId, task.targetSubTeamId)
    if not canView:
        raise forbidden("You are not a member of this collaboration task")


def recomputeCollaborationPhase(task: Task) -> None:
    """按待办双审核阶段重算协作任务聚合阶段（支持多执行人异步审核）。"""
    assignments = list(task.assignments)
    hasTargetPending = any(
        assignment.status == AssignmentStatus.PENDING_REVIEW
        and assignment.reviewStage == ReviewStage.TARGET.value
        for assignment in assignments
    )
    hasSourcePending = any(
        assignment.status == AssignmentStatus.PENDING_REVIEW
        and assignment.reviewStage == ReviewStage.SOURCE.value
        for assignment in assignments
    )
    if hasTargetPending:
        task.collaborationPhase = CollaborationPhase.TARGET_REVIEW.value
    elif hasSourcePending:
        task.collaborationPhase = CollaborationPhase.SOURCE_REVIEW.value
    elif task.status == TaskStatus.ARCHIVED:
        task.collaborationPhase = None
    else:
        task.collaborationPhase = CollaborationPhase.EXECUTING.value


def splitAssigneeUserIds(assigneeUserIds: list[int] | None) -> list[int]:
    """执行人用户主键去重（保留传入顺序）。"""
    return list(dict.fromkeys(int(userId) for userId in (assigneeUserIds or [])))


def buildReviewRecord(
    taskId: int, assignmentId: int, reviewerId: int, approved: bool, comment: str | None
) -> TaskReview:
    """构造一条双审核记录 ORM 对象（通过/驳回均留痕，事务由调用方提交）。"""
    return TaskReview(
        taskId=taskId,
        assignmentId=assignmentId,
        reviewerId=reviewerId,
        result=ReviewResult.APPROVED if approved else ReviewResult.REJECTED,
        comment=comment,
        createdAt=getCurrentTime(),
    )
