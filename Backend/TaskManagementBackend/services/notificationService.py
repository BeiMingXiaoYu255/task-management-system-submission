"""站内通知业务服务：通知创建、分页查询、未读数与已读操作。

其他模块（协作、任务、AI）在各自事务内调用 createNotification / createNotifications，
通知与业务数据同事务提交；查询与已读操作由通知控制器直接调用本服务。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import notFound
from TaskManagementBackend.models import Notification, User
from TaskManagementBackend.models.enums import NotificationType
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.utils.paginationUtils import normalizePagination


def buildNotificationItem(notification: Notification) -> dict:
    """把通知 ORM 对象序列化为响应字典。"""
    return {
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "content": notification.content,
        "taskId": notification.taskId,
        "collaborationId": notification.collaborationId,
        "readFlag": bool(notification.readFlag),
        "createdAt": notification.createdAt,
    }


def createNotification(
    db: Session,
    userId: int | None,
    notificationType: str | NotificationType,
    title: str,
    content: str | None = None,
    taskId: int | None = None,
    collaborationId: int | None = None,
) -> Notification | None:
    """创建一条站内通知并 flush（事务由调用方提交）；接收人不存在时跳过。"""
    if userId is None:
        return None
    resolvedType = notificationType.value if hasattr(notificationType, "value") else str(notificationType)
    notification = Notification(
        userId=userId,
        type=resolvedType,
        title=title,
        content=content,
        taskId=taskId,
        collaborationId=collaborationId,
        readFlag=False,
    )
    db.add(notification)
    db.flush()
    return notification


def createNotifications(db: Session, notificationDefinitions: list[dict]) -> list[Notification]:
    """批量创建通知；每项结构见 createNotification 参数。"""
    createdNotifications: list[Notification] = []
    for definition in notificationDefinitions:
        createdNotification = createNotification(
            db,
            definition.get("userId"),
            definition.get("type", NotificationType.TASK_ASSIGNED),
            definition.get("title", "System Notification"),
            definition.get("content"),
            definition.get("taskId"),
            definition.get("collaborationId"),
        )
        if createdNotification is not None:
            createdNotifications.append(createdNotification)
    return createdNotifications


class NotificationService(BaseService):
    """通知查询服务：当前用户的通知列表、未读数与已读操作。"""

    def listNotifications(
        self, currentUser: User, unreadOnly: bool, page: int, pageSize: int
    ) -> dict:
        """当前用户通知分页（时间倒序）。"""
        normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
        baseCondition = Notification.userId == currentUser.id
        if unreadOnly:
            baseCondition = baseCondition & (Notification.readFlag.is_(False))
        total = int(
            self.db.execute(select(func.count(Notification.id)).where(baseCondition)).scalar_one()
        )
        statement = (
            select(Notification)
            .where(baseCondition)
            .order_by(Notification.createdAt.desc(), Notification.id.desc())
            .offset((normalizedPage - 1) * normalizedPageSize)
            .limit(normalizedPageSize)
        )
        notifications = list(self.db.execute(statement).scalars())
        return {
            "items": [buildNotificationItem(notification) for notification in notifications],
            "total": total,
            "page": normalizedPage,
            "pageSize": normalizedPageSize,
        }

    def getUnreadCount(self, currentUser: User) -> dict:
        """当前用户未读通知数量。"""
        count = int(
            self.db.execute(
                select(func.count(Notification.id)).where(
                    Notification.userId == currentUser.id, Notification.readFlag.is_(False)
                )
            ).scalar_one()
        )
        return {"count": count}

    def markRead(self, currentUser: User, notificationId: int) -> dict:
        """标记单条通知已读；非本人或不存在均按不存在处理。"""
        notification = self.db.get(Notification, notificationId)
        if notification is None or notification.userId != currentUser.id:
            raise notFound("Notification not found")
        if not notification.readFlag:
            notification.readFlag = True
            self.commit()
        return buildNotificationItem(notification)

    def markAllRead(self, currentUser: User) -> dict:
        """把当前用户全部未读通知标记为已读。"""
        notifications = list(
            self.db.execute(
                select(Notification).where(
                    Notification.userId == currentUser.id, Notification.readFlag.is_(False)
                )
            ).scalars()
        )
        for notification in notifications:
            notification.readFlag = True
        self.commit()
        return {"message": "All notifications marked as read"}
