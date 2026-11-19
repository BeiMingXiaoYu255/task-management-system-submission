"""团队协作接口控制器：协作目录、协作申请、协作任务与双审核。

控制器只负责参数接收与服务调用；权限校验、单位解析与状态机全部在协作领域服务层。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.collaborationSchema import (
    CollaborationDirectoryItemResponse,
    CollaborationItemResponse,
    CollaborationListQuery,
    CollaborationTaskDetailResponse,
    CollaborationTaskItemResponse,
    CollaborationUnitCandidateResponse,
    ConfirmCollaborationRequest,
    ConfirmCollaborationTaskRequest,
    CreateCollaborationRequest,
    CreateCollaborationTaskRequest,
    EndCollaborationRequest,
    ReviewCollaborationTaskRequest,
)
from TaskManagementBackend.schemas.commonSchema import PageResult
from TaskManagementBackend.schemas.taskSchema import TaskListQuery
from TaskManagementBackend.services.collaborationService import CollaborationService
from TaskManagementBackend.services.collaborationTaskReviewService import (
    CollaborationTaskReviewService,
)
from TaskManagementBackend.services.collaborationTaskService import CollaborationTaskService

router = APIRouter(tags=["Collaboration"])


@router.get(
    "/collaboration/directory",
    response_model=list[CollaborationDirectoryItemResponse],
    summary="Collaboration directory",
)
def getCollaborationDirectory(
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> list[dict]:
    """可申请协作的团队/子团队目录：仅已认证团队，含成员数、子团队与负责人。"""
    return CollaborationService(db).getDirectory(currentUser)


@router.get(
    "/collaborations/units/members",
    response_model=list[CollaborationUnitCandidateResponse],
    summary="Collaboration unit candidates",
)
def listUnitCandidates(
    teamId: Annotated[int, Query(gt=0, description="Team ID")],
    subTeamId: Annotated[int | None, Query(gt=0, description="Sub-team ID; omit for team level")] = None,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> list[dict]:
    """团队/子团队候选成员：用于选择对接人与指派执行人（要求当前用户是团队成员）。"""
    return CollaborationService(db).listUnitCandidates(currentUser, teamId, subTeamId)


@router.post("/collaborations", response_model=CollaborationItemResponse, summary="Create collaboration request")
def createCollaboration(
    payload: CreateCollaborationRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """发起协作申请：发起单位管理员指定己方对接人，申请进入 pending。"""
    return CollaborationService(db).createCollaboration(currentUser, payload)


@router.get(
    "/collaborations",
    response_model=PageResult[CollaborationItemResponse],
    summary="My collaborations",
)
def listCollaborations(
    query: Annotated[CollaborationListQuery, Query()],
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """与我相关的协作关系分页（我所在单位、我管理的单位或我作为对接人）。"""
    return CollaborationService(db).listCollaborations(currentUser, query)


@router.get(
    "/collaborations/{collaborationId}",
    response_model=CollaborationItemResponse,
    summary="Collaboration detail",
)
def getCollaborationDetail(
    collaborationId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """协作详情：参与单位成员可查看，含当前用户可执行动作标记。"""
    return CollaborationService(db).getCollaborationDetail(currentUser, collaborationId)


@router.post(
    "/collaborations/{collaborationId}/confirm",
    response_model=CollaborationItemResponse,
    summary="Confirm or reject collaboration",
)
def confirmCollaboration(
    collaborationId: int,
    payload: ConfirmCollaborationRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """接收单位管理员确认（并指定接收方对接人）或拒绝协作申请。"""
    return CollaborationService(db).confirmCollaboration(currentUser, collaborationId, payload)


@router.post(
    "/collaborations/{collaborationId}/end",
    response_model=CollaborationItemResponse,
    summary="End collaboration",
)
def endCollaboration(
    collaborationId: int,
    payload: EndCollaborationRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """任一单位管理员结束已生效协作，已派发任务仍按原流程完成。"""
    return CollaborationService(db).endCollaboration(currentUser, collaborationId, payload)


@router.post(
    "/collaborations/{collaborationId}/tasks",
    response_model=CollaborationTaskDetailResponse,
    summary="Create collaboration task",
)
def createCollaborationTask(
    collaborationId: int,
    payload: CreateCollaborationTaskRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """发起单位管理员或发起方对接人发布协作任务（任务进入待接收方确认）。"""
    return CollaborationTaskService(db).createCollaborationTask(
        currentUser, collaborationId, payload
    )


@router.get(
    "/collaborations/{collaborationId}/tasks",
    response_model=PageResult[CollaborationTaskItemResponse],
    summary="Collaboration task list",
)
def listCollaborationTasks(
    collaborationId: int,
    query: Annotated[TaskListQuery, Query()],
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """协作任务分页：参与单位成员可查看，支持筛选与排序。"""
    return CollaborationTaskService(db).listCollaborationTasks(
        currentUser, collaborationId, query
    )


@router.get(
    "/collaboration-tasks/{taskId}",
    response_model=CollaborationTaskDetailResponse,
    summary="Collaboration task detail",
)
def getCollaborationTaskDetail(
    taskId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """协作任务详情：参与单位成员可查看，含双审核信息与权限标记。"""
    return CollaborationTaskService(db).getCollaborationTaskDetail(currentUser, taskId)


@router.post(
    "/collaboration-tasks/{taskId}/confirm",
    response_model=CollaborationTaskDetailResponse,
    summary="Accept collaboration task",
)
def confirmCollaborationTask(
    taskId: int,
    payload: ConfirmCollaborationTaskRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """接收方对接人确认接单并从接收单位成员中指派 1-N 名执行人；拒绝则任务取消。"""
    return CollaborationTaskService(db).confirmCollaborationTask(currentUser, taskId, payload)


@router.post(
    "/collaboration-tasks/{taskId}/target-review",
    response_model=CollaborationTaskDetailResponse,
    summary="Receiver review",
)
def targetReviewCollaborationTask(
    taskId: int,
    payload: ReviewCollaborationTaskRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """接收方对接人审核执行人提交：通过进入发起方审核，驳回回到执行中。"""
    return CollaborationTaskReviewService(db).targetReview(currentUser, taskId, payload)


@router.post(
    "/collaboration-tasks/{taskId}/source-review",
    response_model=CollaborationTaskDetailResponse,
    summary="Initiator review",
)
def sourceReviewCollaborationTask(
    taskId: int,
    payload: ReviewCollaborationTaskRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """任务发布者（发布者注销时为发起单位管理员）最终审核：通过归档，驳回回到执行中。"""
    return CollaborationTaskReviewService(db).sourceReview(currentUser, taskId, payload)
