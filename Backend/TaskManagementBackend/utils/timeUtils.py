"""时间工具：统一使用本地时间（naive datetime），与 MySQL DATETIME 对应。"""

from datetime import datetime


def getCurrentTime() -> datetime:
    """获取当前本地时间（去掉微秒，便于展示与比较）。"""
    return datetime.now().replace(microsecond=0)


def isOverdue(dueAt: datetime | None, statusValue: str | None = None) -> bool:
    """判断截止时间是否已过；已归档状态的任务不算逾期。"""
    if dueAt is None:
        return False
    if statusValue == "archived":
        return False
    return dueAt < getCurrentTime()
