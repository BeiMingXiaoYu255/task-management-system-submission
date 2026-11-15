"""分页工具：统一页码/页大小规范化与查询分页。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def normalizePagination(page: int, pageSize: int) -> tuple[int, int]:
    """规范化分页参数：页码至少 1，页大小限制 1-100。"""
    normalizedPage = max(1, int(page or 1))
    normalizedPageSize = max(1, min(100, int(pageSize or 20)))
    return normalizedPage, normalizedPageSize


def paginateStatement(
    db: Session,
    statement,
    page: int,
    pageSize: int,
) -> tuple[list, int]:
    """对 Select 语句分页执行，返回 (当页数据, 总数)。"""
    normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
    countStatement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(db.execute(countStatement).scalar_one())
    rows = list(
        db.execute(
            statement.offset((normalizedPage - 1) * normalizedPageSize).limit(normalizedPageSize)
        ).scalars()
    )
    return rows, total
