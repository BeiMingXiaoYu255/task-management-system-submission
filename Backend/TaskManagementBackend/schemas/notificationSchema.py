"""站内通知 Pydantic 数据模型。"""

from datetime import datetime

from pydantic import BaseModel


class NotificationItemResponse(BaseModel):
    """单条通知响应结构。"""

    id: int
    type: str
    title: str
    content: str | None = None
    taskId: int | None = None
    collaborationId: int | None = None
    readFlag: bool
    createdAt: datetime


class UnreadCountResponse(BaseModel):
    """未读通知数量响应。"""

    count: int
