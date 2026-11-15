"""站内通知 ORM 模型：协作与 AI 模块共用。"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from TaskManagementBackend.models.baseModel import Base


class Notification(Base):
    """用户站内通知：任务分配、协作申请/确认、审核结果等事件。"""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    userId = Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="Recipient"
    )
    type = Column(String(50), nullable=False, comment="Notification type identifier")
    title = Column(String(200), nullable=False, comment="Notification title")
    content = Column(Text, nullable=True, comment="Notification content")
    taskId = Column(
        "task_id", Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, comment="Related task"
    )
    collaborationId = Column(
        "collaboration_id",
        Integer,
        ForeignKey("team_collaborations.id", ondelete="SET NULL"),
        nullable=True,
        comment="Related collaboration",
    )
    readFlag = Column("read_flag", Boolean, nullable=False, default=False, comment="Read flag")
    createdAt = Column("created_at", DateTime, nullable=False, default=datetime.now, index=True, comment="Creation time")

    user = relationship("User", back_populates="notifications")
    task = relationship("Task", foreign_keys=[taskId])
    collaboration = relationship("TeamCollaboration", foreign_keys=[collaborationId])

    def __repr__(self) -> str:
        """调试输出：通知主键与类型。"""
        return f"<Notification id={self.id} type={self.type} user={self.userId}>"
