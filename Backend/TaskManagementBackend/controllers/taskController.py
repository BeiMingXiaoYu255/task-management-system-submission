"""任务管理接口控制器：团队任务 CRUD、我的任务中心与任务动作接口。

控制器只负责接收参数、调用服务与返回统一响应结构；
权限校验与状态机全部在 TaskService / TodoService 中完成。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.commonSchema import PageResult
from TaskManagementBackend.schemas.taskSchema import (
    AssignTaskMembersRequest,
    CreateTaskRequest,
    MyTaskListQuery,
    ReviewTaskRequest,
    TaskDetailResponse,
    TaskItemResponse,
    TaskListQuery,
    UpdateTaskRequest,
)
from TaskManagementBackend.services.taskService import TaskService
from TaskManagementBackend.services.todoService import TodoService

router = APIRouter(tags=["Tasks"])


@router.post("/teams/{teamId}/tasks", response_model=TaskDetailResponse, summary="Publish Task")
def createTask(
    teamId: int,
    payload: CreateTaskRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """发布任务：校验发布权限与目标成员，创建任务与分配记录。"""
    return TaskService(db).createTask(currentUser, teamId, payload)


@router.get("/teams/{teamId}/tasks", response_model=PageResult[TaskItemResponse], summary="Team Tasks")
def listTeamTasks(
    teamId: int,
    query: Annotated[TaskListQuery, Query()],
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """团队任务列表：团队成员可查看，支持筛选与排序分页。"""
    return TaskService(db).listTeamTasks(currentUser, teamId, query)


@router.get("/teams/{teamId}/tasks/{taskId}", response_model=TaskDetailResponse, summary="Team Task Detail")
def getTeamTaskDetail(
    teamId: int,
    taskId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """团队任务详情：同团队成员可查看，含审核记录。"""
    return TaskService(db).getTaskDetail(currentUser, taskId, teamId)


@router.put("/teams/{teamId}/tasks/{taskId}", response_model=TaskDetailResponse, summary="Update Task")
def updateTask(
    teamId: int,
    taskId: int,
    payload: UpdateTaskRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """修改任务：仅发布者或团队管理员可操作，已归档/已取消任务禁止修改。"""
    return TaskService(db).updateTask(currentUser, teamId, taskId, payload)


@router.post("/tasks/{taskId}/assignments", response_model=TaskDetailResponse, summary="Assign Assignee")
def assignTaskMembers(
    taskId: int,
    payload: AssignTaskMembersRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """为无执行人的任务手动指派成员（AI 自动分配无匹配或管理员改派场景）。"""
    return TaskService(db).assignTaskMembers(currentUser, taskId, payload.userIds)


@router.get("/tasks", response_model=PageResult[TaskItemResponse], summary="My Tasks")
def listMyTasks(
    query: Annotated[MyTaskListQuery, Query()],
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """我的任务中心：role=created 我发布的 / assigned 我参与的。"""
    return TaskService(db).listMyTasks(currentUser, query)


@router.get("/tasks/{taskId}", response_model=TaskDetailResponse, summary="Task Detail")
def getTaskDetail(
    taskId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """任务详情（同团队成员）：含分配、我的待办与审核记录。"""
    return TaskService(db).getTaskDetail(currentUser, taskId)


@router.post("/tasks/{taskId}/cancel", response_model=TaskDetailResponse, summary="Cancel Task")
def cancelTask(
    taskId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """取消任务：发布者或团队管理员取消未归档任务。"""
    return TaskService(db).cancelTask(currentUser, taskId)


@router.post("/tasks/{taskId}/acceptance", response_model=TaskDetailResponse, summary="Accept Task")
def acceptTask(
    taskId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """接受可选任务：待办从待接受变为进行中。"""
    return TodoService(db).acceptTask(currentUser, taskId)


@router.post("/tasks/{taskId}/decline", response_model=TaskDetailResponse, summary="Decline Task")
def declineTask(
    taskId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """拒绝可选任务：从任务移除该待办，全部拒绝后任务自动取消。"""
    return TodoService(db).declineTask(currentUser, taskId)


@router.post("/tasks/{taskId}/submit", response_model=TaskDetailResponse, summary="Submit for Review")
def submitTask(
    taskId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """提交完成：待办进入待审核状态。"""
    return TodoService(db).submitTask(currentUser, taskId)


@router.post("/tasks/{taskId}/review", response_model=TaskDetailResponse, summary="Review Task")
def reviewTask(
    taskId: int,
    payload: ReviewTaskRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """审核待办：通过归档 / 驳回回到进行中并记录审核意见。"""
    return TodoService(db).reviewTask(currentUser, taskId, payload)
