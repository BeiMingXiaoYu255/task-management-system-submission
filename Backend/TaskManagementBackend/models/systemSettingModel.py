"""系统级配置 ORM 模型：键值对存储全局配置（当前用于 AI/LLM 配置）。

设计说明：
    1. config_key 唯一，例如 ai.llmBaseUrl、ai.dispatchMode；
    2. config_value 使用 TEXT 存储字符串，数值/枚举在服务层转换；
    3. apiKey 属于敏感配置，接口返回时只给出掩码；仅全局管理员可读取/修改完整配置；
    4. updated_by 记录最后修改人，便于审计与展示。
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from TaskManagementBackend.models.baseModel import Base, TimestampMixin


class SystemSetting(Base, TimestampMixin):
    """系统级键值配置：与用户级 UserSetting（主题/字号）区分，全局共享。"""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    configKey = Column("config_key", String(100), unique=True, nullable=False, index=True, comment="Configuration key")
    configValue = Column("config_value", Text, nullable=True, comment="Configuration value (stored as string)")
    updatedBy = Column(
        "updated_by", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Last modified by"
    )

    updater = relationship("User", foreign_keys=[updatedBy], lazy="joined")

    def __repr__(self) -> str:
        """调试输出：配置键（不输出值，避免泄露敏感配置）。"""
        return f"<SystemSetting key={self.configKey}>"
