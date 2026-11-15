"""ORM 声明式基类与公共字段定义（所有模型文件的父类）。"""

from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型继承的声明式基类。

    SQLAlchemy 2.0 风格：Base 同时承担元数据注册与类型映射职责。
    """


class TimestampMixin:
    """创建时间与更新时间公共字段混入类，供需要时间戳的表继承。"""

    createdAt = Column(
        "created_at",
        DateTime,
        nullable=False,
        default=datetime.now,
        comment="Creation time",
    )
    updatedAt = Column(
        "updated_at",
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="Update time",
    )


def createEnumColumn(enumClass, columnName: str) -> SqlEnum:
    """创建以枚举字符串值（camelCase）落库的 MySQL 枚举列。

    参数：
        enumClass：Python 枚举类；
        columnName：数据库枚举类型名称（需全库唯一）。
    返回：
        SQLAlchemy Enum 列类型对象。
    """
    return SqlEnum(
        enumClass,
        name=columnName,
        values_callable=lambda enumMembers: [member.value for member in enumMembers],
    )
