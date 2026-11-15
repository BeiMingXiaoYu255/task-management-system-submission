"""管理操作审计日志 ORM 模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from TaskManagementBackend.models.baseModel import Base


class AuditLog(Base):
    """审计日志：记录超级用户/全局管理员的后台操作与数据库直管操作。"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    userId = Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Operator"
    )
    action = Column(String(100), nullable=False, comment="Action identifier")
    detail = Column(Text, nullable=True, comment="Operation details JSON")
    ip = Column(String(50), nullable=True, comment="Source IP")
    createdAt = Column("created_at", DateTime, nullable=False, default=datetime.now, comment="Operation time")

    operator = relationship("User", foreign_keys=[userId])

    @property
    def operatorName(self) -> str:
        """操作人昵称，注销后显示“已注销用户”。"""
        if self.operator is None:
            return "Deleted user"
        return self.operator.nickname

    def __repr__(self) -> str:
        """调试输出：动作与操作人。"""
        return f"<AuditLog id={self.id} action={self.action} user={self.userId}>"
