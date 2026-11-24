"""仓储层父类：封装最基础的增删改查，供各模块子类继承。

设计原则：仓储只做数据访问，不包含权限与业务判断；业务判断放在服务层。
"""

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from TaskManagementBackend.models.baseModel import Base

# ORM 模型泛型参数
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """通用仓储父类：持有数据库会话与模型类型。"""

    model: type[ModelType]

    def __init__(self, db: Session) -> None:
        """注入请求级数据库会话。"""
        self.db = db

    def getById(self, entityId: int) -> ModelType | None:
        """按主键查询单条记录，不存在返回 None。"""
        return self.db.get(self.model, entityId)

    def add(self, entity: ModelType) -> ModelType:
        """新增记录并 flush 取得主键（事务由服务层提交）。"""
        self.db.add(entity)
        self.db.flush()
        return entity

    def delete(self, entity: ModelType) -> None:
        """删除记录（事务由服务层提交）。"""
        self.db.delete(entity)
        self.db.flush()

    def commit(self) -> None:
        """提交事务。"""
        self.db.commit()

    def rollback(self) -> None:
        """回滚事务。"""
        self.db.rollback()
