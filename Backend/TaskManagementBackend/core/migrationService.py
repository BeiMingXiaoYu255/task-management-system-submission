"""数据库结构升级服务：v1.0 → v1.1 幂等迁移。

设计说明：
    1. initDatabase 先执行 Base.metadata.create_all 创建 v1.1 新增表；
    2. 本服务用 SQLAlchemy Inspector 检查已有表是否缺少 v1.1 新增列，缺则 ALTER TABLE 补齐；
    3. 只做“加列/加索引”，不修改既有列与枚举，保证 v1.0 旧数据与安装版可直接升级；
    4. 全部操作幂等，重复启动不会报错。
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("taskManagement.migration")

# 需要为 v1.0 已存在的表补充的列（表名 -> [(列名, 列定义)]）
REQUIRED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "tasks": [
        ("sub_team_id", "INT NULL COMMENT 'Sub-team'"),
        ("source_team_id", "INT NULL COMMENT 'Collaboration initiator team'"),
        ("source_sub_team_id", "INT NULL COMMENT 'Collaboration initiator sub-team'"),
        ("target_team_id", "INT NULL COMMENT 'Collaboration receiver team'"),
        ("target_sub_team_id", "INT NULL COMMENT 'Collaboration receiver sub-team'"),
        ("collaboration_id", "INT NULL COMMENT 'Collaboration'"),
        ("collaboration_phase", "VARCHAR(32) NULL COMMENT 'Collaboration task phase'"),
        ("collaboration_comment", "TEXT NULL COMMENT 'Receiver confirmation comment'"),
        ("auto_assigned", "TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'AI auto-assigned'"),
        ("required_skill_names", "TEXT NULL COMMENT 'Required skill tags for AI assignment'"),
    ],
    "task_assignments": [
        ("review_stage", "VARCHAR(16) NULL COMMENT 'Two-stage review phase: target/source'"),
        ("target_reviewed_at", "DATETIME NULL COMMENT 'Receiver review time'"),
        ("target_reviewer_id", "INT NULL COMMENT 'Receiver reviewer'"),
        ("target_review_comment", "TEXT NULL COMMENT 'Receiver review comment'"),
        ("assignment_source", "VARCHAR(16) NOT NULL DEFAULT 'manual' COMMENT 'Assignment source'"),
    ],
}

# 需要补充的索引（表名 -> [(索引名, 列定义)]）
REQUIRED_INDEXES: dict[str, list[tuple[str, str]]] = {
    "tasks": [
        ("idx_tasks_sub_team_id", "sub_team_id"),
        ("idx_tasks_source_team_id", "source_team_id"),
        ("idx_tasks_target_team_id", "target_team_id"),
        ("idx_tasks_collaboration_id", "collaboration_id"),
    ],
    "task_assignments": [
        ("idx_assignments_review_stage", "review_stage"),
    ],
}


def addMissingColumns(engine: Engine) -> int:
    """为已有表补齐缺失列，返回新增列数量。"""
    inspector = inspect(engine)
    existingTables = set(inspector.get_table_names())
    addedCount = 0
    for tableName, columnDefinitions in REQUIRED_COLUMNS.items():
        if tableName not in existingTables:
            continue
        existingColumnNames = {column["name"] for column in inspector.get_columns(tableName)}
        for columnName, columnDefinition in columnDefinitions:
            if columnName in existingColumnNames:
                continue
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE `" + tableName + "` ADD COLUMN `" + columnName + "` " + columnDefinition)
                )
            logger.info("Database upgrade: added column %s to table %s", columnName, tableName)
            addedCount += 1
    return addedCount


def addMissingIndexes(engine: Engine) -> int:
    """为已有表补齐缺失索引，返回新增索引数量。"""
    inspector = inspect(engine)
    existingTables = set(inspector.get_table_names())
    addedCount = 0
    for tableName, indexDefinitions in REQUIRED_INDEXES.items():
        if tableName not in existingTables:
            continue
        existingIndexNames = {index["name"] for index in inspector.get_indexes(tableName)}
        for indexName, columnExpression in indexDefinitions:
            if indexName in existingIndexNames:
                continue
            with engine.begin() as connection:
                connection.execute(
                    text("CREATE INDEX `" + indexName + "` ON `" + tableName + "` (" + columnExpression + ")")
                )
            logger.info("Database upgrade: added index %s to table %s", indexName, tableName)
            addedCount += 1
    return addedCount


def upgradeDatabaseSchema(engine: Engine) -> None:
    """执行 v1.0 → v1.1 数据库结构升级（幂等）。"""
    addedColumnCount = addMissingColumns(engine)
    addedIndexCount = addMissingIndexes(engine)
    if addedColumnCount or addedIndexCount:
        logger.info("Database schema upgrade completed: %s columns and %s indexes added", addedColumnCount, addedIndexCount)
    else:
        logger.info("Database schema is up to date (v1.1.1)")
