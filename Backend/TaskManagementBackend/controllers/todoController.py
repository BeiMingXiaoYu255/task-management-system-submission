"""待办清单接口控制器：我的待办分页列表与待办统计。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.commonSchema import PageResult
from TaskManagementBackend.schemas.todoSchema import (
    TodoItemResponse,
    TodoListQuery,
    TodoStatsResponse,
)
from TaskManagementBackend.services.todoService import TodoService

# 待办路由统一前缀 /todos
router = APIRouter(tags=["To-dos"], prefix="/todos")


@router.get("", response_model=PageResult[TodoItemResponse], summary="My To-dos")
def listTodos(
    query: Annotated[TodoListQuery, Query()],
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """我的待办分页列表：status 不传时默认返回全部未归档待办。"""
    return TodoService(db).listTodos(currentUser, query)


@router.get("/stats", response_model=TodoStatsResponse, summary="To-do Statistics")
def getTodoStats(
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """我的待办统计：各状态数量、已归档数量与逾期数量。"""
    return TodoService(db).getTodoStats(currentUser)
