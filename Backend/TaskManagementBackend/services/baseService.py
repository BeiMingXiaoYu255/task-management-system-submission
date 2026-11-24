"""业务服务父类：统一事务提交/回滚入口，供各模块服务子类继承。"""

from sqlalchemy.orm import Session


class BaseService:
    """通用业务服务父类：持有数据库会话。"""

    def __init__(self, db: Session) -> None:
        """注入请求级数据库会话。"""
        self.db = db

    def commit(self) -> None:
        """提交当前事务。"""
        self.db.commit()

    def rollback(self) -> None:
        """回滚当前事务。"""
        self.db.rollback()
