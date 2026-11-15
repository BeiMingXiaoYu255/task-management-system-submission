"""用户界面设置 ORM 模型。"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from TaskManagementBackend.models.baseModel import Base, TimestampMixin, createEnumColumn
from TaskManagementBackend.models.enums import FontFamily, FontSize, ThemeMode


class UserSetting(Base, TimestampMixin):
    """用户界面设置：主题、字号、字体族。每个用户一条记录，不存在时使用默认值。"""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    userId = Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, comment="User"
    )
    theme = Column("theme", createEnumColumn(ThemeMode, "theme_mode"), nullable=False, default=ThemeMode.LIGHT)
    fontSize = Column(
        "font_size", createEnumColumn(FontSize, "font_size"), nullable=False, default=FontSize.MEDIUM
    )
    fontFamily = Column(
        "font_family",
        createEnumColumn(FontFamily, "font_family"),
        nullable=False,
        default=FontFamily.SYSTEM,
    )

    user = relationship("User", back_populates="setting")

    def __repr__(self) -> str:
        """调试输出：用户与主题。"""
        return f"<UserSetting user={self.userId} theme={self.theme}>"
