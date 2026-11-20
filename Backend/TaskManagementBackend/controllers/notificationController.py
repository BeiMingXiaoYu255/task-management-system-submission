"""通知中心接口控制器：通知分页、未读数与已读操作。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.commonSchema import MessageResponse, PageResult
from TaskManagementBackend.schemas.notificationSchema import (
    NotificationItemResponse,
    UnreadCountResponse,
)
from TaskManagementBackend.services.notificationService import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=PageResult[NotificationItemResponse], summary="List my notifications")
def listNotifications(
    unreadOnly: Annotated[bool, Query(description="Only return unread notifications")] = False,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """当前用户通知分页列表（时间倒序）。"""
    return NotificationService(db).listNotifications(currentUser, unreadOnly, page, pageSize)


@router.get("/unread-count", response_model=UnreadCountResponse, summary="Unread notification count")
def getUnreadCount(
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """当前用户未读通知数量（前端顶栏角标轮询）。"""
    return NotificationService(db).getUnreadCount(currentUser)


@router.put("/read-all", response_model=MessageResponse, summary="Mark all notifications as read")
def markAllRead(
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """把当前用户全部未读通知标记为已读。"""
    return NotificationService(db).markAllRead(currentUser)


@router.put("/{notificationId}/read", response_model=NotificationItemResponse, summary="Mark a notification as read")
def markRead(
    notificationId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """标记单条通知已读（仅限本人）。"""
    return NotificationService(db).markRead(currentUser, notificationId)
