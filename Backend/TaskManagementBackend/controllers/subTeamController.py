"""子团队接口控制器：子团队 CRUD、成员维护与子团队任务视图。

控制器只负责接收参数、调用服务与返回响应结构；权限校验与业务规则全部在 SubTeamService。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.commonSchema import MessageResponse, PageResult
from TaskManagementBackend.schemas.subTeamSchema import (
    CreateSubTeamRequest,
    SetSubTeamMembersRequest,
    SubTeamDetailResponse,
    SubTeamItemResponse,
    UpdateSubTeamRequest,
)
from TaskManagementBackend.schemas.taskSchema import TaskItemResponse, TaskListQuery
from TaskManagementBackend.services.subTeamService import SubTeamService

router = APIRouter(tags=["Sub-teams"])


@router.get(
    "/teams/{teamId}/sub-teams",
    response_model=list[SubTeamItemResponse],
    summary="Sub-team list",
)
def listSubTeams(
    teamId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> list[dict]:
    """子团队列表：父团队全体成员可查看，含负责人、成员数与当前用户角色。"""
    return SubTeamService(db).listSubTeams(currentUser, teamId)


@router.post(
    "/teams/{teamId}/sub-teams",
    response_model=SubTeamDetailResponse,
    summary="Create sub-team",
)
def createSubTeam(
    teamId: int,
    payload: CreateSubTeamRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """创建子团队：仅父团队管理员，可同时指定子负责人与初始成员。"""
    return SubTeamService(db).createSubTeam(currentUser, teamId, payload)


@router.get(
    "/teams/{teamId}/sub-teams/{subTeamId}",
    response_model=SubTeamDetailResponse,
    summary="Sub-team detail",
)
def getSubTeamDetail(
    teamId: int,
    subTeamId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """子团队详情：父团队全体成员可查看，含成员列表。"""
    return SubTeamService(db).getSubTeamDetail(currentUser, teamId, subTeamId)


@router.put(
    "/teams/{teamId}/sub-teams/{subTeamId}",
    response_model=SubTeamDetailResponse,
    summary="Update sub-team",
)
def updateSubTeam(
    teamId: int,
    subTeamId: int,
    payload: UpdateSubTeamRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """修改子团队：团队管理员可换负责人；子负责人可改名称/简介。"""
    return SubTeamService(db).updateSubTeam(currentUser, teamId, subTeamId, payload)


@router.delete(
    "/teams/{teamId}/sub-teams/{subTeamId}",
    response_model=MessageResponse,
    summary="Delete sub-team",
)
def deleteSubTeam(
    teamId: int,
    subTeamId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """删除子团队：仅父团队管理员；其任务 subTeamId 置空。"""
    return SubTeamService(db).deleteSubTeam(currentUser, teamId, subTeamId)


@router.put(
    "/teams/{teamId}/sub-teams/{subTeamId}/members",
    response_model=SubTeamDetailResponse,
    summary="Replace sub-team members",
)
def setSubTeamMembers(
    teamId: int,
    subTeamId: int,
    payload: SetSubTeamMembersRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """覆盖式设置子团队成员：成员必须是父团队成员，子负责人自动保留。"""
    return SubTeamService(db).setSubTeamMembers(currentUser, teamId, subTeamId, payload)


@router.get(
    "/teams/{teamId}/sub-teams/{subTeamId}/tasks",
    response_model=PageResult[TaskItemResponse],
    summary="Sub-team task list",
)
def listSubTeamTasks(
    teamId: int,
    subTeamId: int,
    query: Annotated[TaskListQuery, Query()],
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """子团队任务分页：子团队成员或父团队管理者可查看（复用团队任务列表逻辑）。"""
    return SubTeamService(db).listSubTeamTasks(currentUser, teamId, subTeamId, query)
