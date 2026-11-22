"""系统级配置数据访问层：system_settings 键值配置的查询与写入。

仓储只负责数据访问，不包含权限、掩码或默认值合并等业务判断（由 aiConfigService 处理）。
"""

from sqlalchemy import select

from TaskManagementBackend.models import SystemSetting
from TaskManagementBackend.repositories.baseRepository import BaseRepository


class SystemSettingRepository(BaseRepository[SystemSetting]):
    """系统配置仓储：按配置键批量/单个查询配置项。"""

    model = SystemSetting

    def listByKeys(self, configKeys: list[str]) -> list[SystemSetting]:
        """按配置键批量查询配置项（自动去重，不保证顺序）。"""
        if not configKeys:
            return []
        uniqueKeys = list(dict.fromkeys(configKeys))
        statement = select(SystemSetting).where(SystemSetting.configKey.in_(uniqueKeys))
        return list(self.db.execute(statement).scalars())

    def getByKey(self, configKey: str) -> SystemSetting | None:
        """按配置键查询单条配置，不存在返回 None。"""
        statement = select(SystemSetting).where(SystemSetting.configKey == configKey)
        return self.db.execute(statement).scalar_one_or_none()
