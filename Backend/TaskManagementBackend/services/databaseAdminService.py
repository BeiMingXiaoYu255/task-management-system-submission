"""管理后台数据库直管业务服务：表清单、表数据浏览与单条 DML 执行。

安全约束：
    1. 表名必须存在于 ORM 元数据白名单，禁止任意表名；
    2. 仅允许单条 SELECT/INSERT/UPDATE/DELETE，禁止 DDL、多语句与文件/事务控制语句；
    3. 所有执行动作（成功或失败）都写入审计日志；
    4. 敏感列（密码哈希、令牌、邮箱、手机号）返回前脱敏。
"""

import re

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import AppException, notFound, validationError
from TaskManagementBackend.models import Base, User
from TaskManagementBackend.repositories.adminRepository import AdminRepository
from TaskManagementBackend.services.auditService import AuditService
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.utils.paginationUtils import normalizePagination

# 允许执行的语句类型（仅单条 DML）
ALLOWED_STATEMENT_TYPES = ("SELECT", "INSERT", "UPDATE", "DELETE")

# 禁止出现在 SQL 中的关键字（DDL、文件、事务控制、系统命令）
FORBIDDEN_SQL_KEYWORDS = (
    "DROP",
    "CREATE",
    "ALTER",
    "TRUNCATE",
    "RENAME",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "CALL",
    "HANDLER",
    "LOCK",
    "UNLOCK",
    "COMMIT",
    "ROLLBACK",
    "BEGIN",
    "START",
    "SAVEPOINT",
    "RELEASE",
    "LOAD",
    "OUTFILE",
    "DUMPFILE",
    "SHUTDOWN",
    "KILL",
    "FLUSH",
    "OPTIMIZE",
    "ANALYZE",
    "REPAIR",
    "TABLESPACE",
    "TRIGGER",
    "PROCEDURE",
    "FUNCTION",
    "EVENT",
    "DELIMITER",
)

# 需要整列脱敏的列名关键字（密码哈希、密钥、令牌）
SENSITIVE_COLUMN_KEYWORDS = ("password", "secret", "token")


def maskPhone(phoneValue: str) -> str:
    """手机号脱敏：保留前 3 位与后 4 位。"""
    if len(phoneValue) >= 7:
        return f"{phoneValue[:3]}****{phoneValue[-4:]}"
    return "***"


def maskEmail(emailValue: str) -> str:
    """邮箱脱敏：保留用户名首字符与域名。"""
    localPart, separator, domainPart = emailValue.partition("@")
    if not separator:
        return "***"
    return f"{localPart[0] if localPart else '*'}***@{domainPart}"


def maskSensitiveValue(columnName: str, value: object) -> object:
    """按列名对敏感数据脱敏，非敏感列原样返回。"""
    if value is None:
        return None
    normalizedColumnName = columnName.lower()
    if any(keyword in normalizedColumnName for keyword in SENSITIVE_COLUMN_KEYWORDS):
        return "******"
    if normalizedColumnName in ("phone", "mobile"):
        return maskPhone(str(value))
    if normalizedColumnName == "email":
        return maskEmail(str(value))
    return value


def maskRow(row: dict) -> dict:
    """对整行数据按列名脱敏。"""
    return {
        columnName: maskSensitiveValue(columnName, value)
        for columnName, value in row.items()
    }


def validateSqlStatement(sql: str) -> tuple[str, str]:
    """校验单条 DML 语句合法性，返回 (清理后的 SQL, 语句类型)。

    实现原理：去掉首尾空白与末尾分号后，若语句中仍存在分号即视为多语句；
    再校验首个关键字属于允许类型，并扫描是否存在被禁止的关键字。
    """
    sqlText = (sql or "").strip()
    while sqlText.endswith(";"):
        sqlText = sqlText[:-1].strip()
    if not sqlText:
        raise validationError("SQL statement cannot be empty")
    if ";" in sqlText:
        raise validationError("Multiple SQL statements are not allowed in one request")
    statementType = sqlText.split()[0].upper()
    if statementType not in ALLOWED_STATEMENT_TYPES:
        raise validationError("Only a single SELECT/INSERT/UPDATE/DELETE statement is allowed")
    upperSql = sqlText.upper()
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upperSql):
            raise validationError(f"SQL contains a forbidden keyword: {keyword}")
    return sqlText, statementType


class DatabaseAdminService(BaseService):
    """数据库直管服务：表清单、表数据分页浏览与单条 DML 执行。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化管理后台仓储与审计服务。"""
        super().__init__(db)
        self.adminRepository = AdminRepository(db)
        self.auditService = AuditService(db)

    def listTables(self) -> list[dict]:
        """数据库表清单：返回全部 ORM 业务表及行数。"""
        return [
            {"tableName": table.name, "rowCount": self.adminRepository.countTableRows(table.name)}
            for table in Base.metadata.sorted_tables
        ]

    def getTableRows(self, tableName: str, page: int, pageSize: int) -> dict:
        """分页浏览数据表内容，敏感列脱敏后返回。"""
        if tableName not in Base.metadata.tables:
            raise notFound("Table not found")
        normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
        columns, rows, total, actualPage, actualPageSize = (
            self.adminRepository.fetchTableRows(tableName, normalizedPage, normalizedPageSize)
        )
        return {
            "tableName": tableName,
            "columns": columns,
            "rows": [maskRow(row) for row in rows],
            "total": total,
            "page": actualPage,
            "pageSize": actualPageSize,
        }

    def executeSql(
        self, operator: User, sql: str, confirm: bool, clientIp: str
    ) -> dict:
        """执行单条 SQL：SELECT 返回行数据，写语句返回受影响行数；全程写审计日志。"""
        if not confirm:
            raise validationError("Confirm the SQL execution first")
        sqlText, statementType = validateSqlStatement(sql)
        try:
            if statementType == "SELECT":
                _, rows = self.adminRepository.executeSelectStatement(sqlText)
                maskedRows = [maskRow(row) for row in rows]
                result = {
                    "executed": True,
                    "statementType": statementType,
                    "affectedRows": len(maskedRows),
                    "rows": maskedRows,
                }
            else:
                affectedRows = self.adminRepository.executeWriteStatement(sqlText)
                result = {
                    "executed": True,
                    "statementType": statementType,
                    "affectedRows": affectedRows,
                    "rows": [],
                }
        except SQLAlchemyError as error:
            self.rollback()
            errorMessage = str(getattr(error, "orig", error))[:500]
            self.auditService.recordAuditLog(
                operator.id,
                "admin.database.execute",
                {
                    "sql": sqlText,
                    "statementType": statementType,
                    "success": False,
                    "error": errorMessage,
                },
                clientIp,
            )
            self.commit()
            raise AppException("DATABASE_ERROR", f"SQL execution failed: {errorMessage[:200]}", 500)
        self.auditService.recordAuditLog(
            operator.id,
            "admin.database.execute",
            {
                "sql": sqlText,
                "statementType": statementType,
                "affectedRows": result["affectedRows"],
                "success": True,
            },
            clientIp,
        )
        self.commit()
        return result
