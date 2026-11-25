"""接口文档生成脚本：读取 FastAPI OpenAPI 规范并输出中文 Markdown 文档。

用途：
    后端路由完成后运行本脚本生成 docs/接口文档.md，保证接口文档与代码同源。
运行：
    cd Backend && .\.venv\Scripts\python.exe scripts\generateApiDocumentation.py
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 允许脚本方式运行：把 Backend 加入模块搜索路径
BACKEND_ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
PROJECT_ROOT_DIRECTORY = BACKEND_ROOT_DIRECTORY.parent
if str(BACKEND_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT_DIRECTORY))

from TaskManagementBackend.main import app  # noqa: E402

# 输出文件路径
OUTPUT_FILE_PATH = PROJECT_ROOT_DIRECTORY / "docs" / "接口文档.md"
# 展开 schema 引用的最大深度，避免递归 schema 无限展开
MAX_SCHEMA_DEPTH = 3
# HTTP 方法排序
METHOD_ORDER = ["get", "post", "put", "delete", "patch"]
# 接口分组展示顺序（按中文标签稳定输出）
TAG_ORDER = ["系统", "身份认证", "用户资料", "团队管理", "任务管理", "待办清单", "仪表盘", "系统设置", "AI 辅助", "管理后台"]


def resolveReference(schema: dict, specification: dict, depth: int = 0) -> dict:
    """展开 JSON Schema 的 $ref 引用（限制递归深度）。"""
    if not isinstance(schema, dict):
        return {}
    if "$ref" in schema and depth < MAX_SCHEMA_DEPTH:
        referenceName = schema["$ref"].split("/")[-1]
        referencedSchema = specification.get("components", {}).get("schemas", {}).get(referenceName, {})
        return resolveReference(referencedSchema, specification, depth + 1)
    return schema


def describeSchema(schema: dict, specification: dict, depth: int = 0) -> list[str]:
    """把 JSON Schema 递归描述为 Markdown 列表行。"""
    resolvedSchema = resolveReference(schema, specification)
    if not resolvedSchema:
        return []
    schemaType = resolvedSchema.get("type")
    if schemaType == "array":
        itemLines = describeSchema(resolvedSchema.get("items", {}), specification, depth)
        return ["- 数组元素："] + ["  " + line for line in itemLines] if itemLines else ["- 数组"]
    if schemaType == "object" or "properties" in resolvedSchema:
        requiredFields = set(resolvedSchema.get("required", []))
        lines: list[str] = []
        for propertyName, propertySchema in resolvedSchema.get("properties", {}).items():
            propertyResolved = resolveReference(propertySchema, specification)
            propertyType = propertyResolved.get("type", "object")
            if propertyType == "array":
                itemResolved = resolveReference(propertyResolved.get("items", {}), specification)
                propertyType = "array<" + itemResolved.get("type", "object") + ">"
            enumValues = propertyResolved.get("enum")
            description = propertyResolved.get("description") or propertyResolved.get("title") or ""
            requiredMark = "必填" if propertyName in requiredFields else "可选"
            enumText = ("，枚举：" + " / ".join(str(value) for value in enumValues)) if enumValues else ""
            detailText = ("：" + description) if description else ""
            lines.append(
                "- `" + propertyName + "`（" + propertyType + "，" + requiredMark + enumText + "）" + detailText
            )
            if propertyType.startswith("array<object>") or propertyType == "object":
                nestedLines = describeSchema(propertyResolved.get("items", propertyResolved), specification, depth + 1)
                lines.extend(["  " + nestedLine for nestedLine in nestedLines[:20]])
        return lines
    if schemaType:
        return ["- 类型：" + str(schemaType)]
    return []


def extractParameters(operation: dict, specification: dict) -> list[str]:
    """提取路径/查询参数描述。"""
    lines: list[str] = []
    for parameter in operation.get("parameters", []):
        parameterSchema = parameter.get("schema", {})
        parameterType = parameterSchema.get("type", "string")
        requiredMark = "必填" if parameter.get("required") else "可选"
        lines.append(
            "- `"
            + parameter.get("name", "")
            + "`（"
            + parameter.get("in", "query")
            + "，"
            + parameterType
            + "，"
            + requiredMark
            + "）："
            + (parameter.get("description") or "")
        )
    return lines


def extractRequestBody(operation: dict, specification: dict) -> list[str]:
    """提取请求体字段描述。"""
    requestBody = operation.get("requestBody", {})
    content = requestBody.get("content", {})
    jsonContent = content.get("application/json", {})
    schema = jsonContent.get("schema", {})
    if not schema:
        return []
    lines = ["**请求体：**", ""]
    lines.extend(describeSchema(schema, specification))
    return lines


def extractResponses(operation: dict, specification: dict) -> list[str]:
    """提取成功响应字段描述。"""
    responses = operation.get("responses", {})
    successResponse = responses.get("200") or responses.get("201") or {}
    content = successResponse.get("content", {})
    schema = content.get("application/json", {}).get("schema", {})
    lines = ["**成功响应：**", ""]
    if schema:
        lines.extend(describeSchema(schema, specification))
    else:
        lines.append("- 无响应体")
    return lines


def groupOperationsByTag(specification: dict) -> dict[str, list[tuple[str, str, dict]]]:
    """按标签分组全部接口：{标签: [(方法, 路径, 操作对象)]}。"""
    groupedOperations: dict[str, list[tuple[str, str, dict]]] = {}
    paths = specification.get("paths", {})
    for pathValue, pathItem in sorted(paths.items()):
        for method in METHOD_ORDER:
            operation = pathItem.get(method)
            if operation is None:
                continue
            operationTags = operation.get("tags") or ["其他"]
            for operationTag in operationTags:
                groupedOperations.setdefault(operationTag, []).append(
                    (method.upper(), pathValue, operation)
                )
    return groupedOperations


def buildDocumentation() -> str:
    """构建完整 Markdown 文档内容。"""
    specification = app.openapi()
    applicationInfo = specification.get("info", {})
    groupedOperations = groupOperationsByTag(specification)
    documentLines: list[str] = [
        "# 任务管理系统 · 接口文档",
        "",
        "> 本文档由 `Backend/scripts/generateApiDocumentation.py` 从 FastAPI OpenAPI 自动生成，"
        "与后端代码保持同步。",
        "> 生成时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "",
        "## 1. 基本信息",
        "",
        "- 应用名称：" + applicationInfo.get("title", ""),
        "- 版本：" + applicationInfo.get("version", ""),
        "- 基础路径：`/api/v1`",
        "- 交互式文档（Swagger UI）：`http://127.0.0.1:8765/api/docs`",
        "- OpenAPI 规范：`http://127.0.0.1:8765/api/openapi.json`",
        "",
        "### 认证方式",
        "",
        "除注册、登录与健康检查外，所有接口均需在请求头携带 JWT：",
        "",
        "```",
        "Authorization: Bearer <token>",
        "```",
        "",
        "### 统一响应约定",
        "",
        "- 成功：直接返回数据对象；分页返回 `{ items, total, page, pageSize }`。",
        "- 失败：HTTP 状态码 + `{ code, message, details }`，message 为中文提示。",
        "- 时间格式：ISO 8601 字符串（例：`2026-11-24T16:51:46`）。",
        "",
        "### 错误码",
        "",
        "| 错误码 | HTTP 状态码 | 说明 |",
        "| --- | --- | --- |",
        "| VALIDATION_ERROR | 400 | 请求参数校验失败 |",
        "| INVALID_CREDENTIALS | 401 | 未登录或凭证无效 |",
        "| TOKEN_EXPIRED | 401 | 登录过期需重新登录 |",
        "| FORBIDDEN | 403 | 没有权限 |",
        "| ACCOUNT_DISABLED | 403 | 账号被禁用 |",
        "| NOT_FOUND | 404 | 资源不存在 |",
        "| CONFLICT | 409 | 数据冲突 |",
        "| RATE_LIMITED | 429 | 登录过于频繁 |",
        "| DATABASE_ERROR / INTERNAL_ERROR | 500 | 服务端错误 |",
        "",
        "## 2. 接口总览",
        "",
        "| 分组 | 方法 | 路径 | 说明 |",
        "| --- | --- | --- | --- |",
    ]
    orderedTags = [tag for tag in TAG_ORDER if tag in groupedOperations]
    orderedTags += [tag for tag in groupedOperations if tag not in orderedTags]
    for operationTag in orderedTags:
        for method, pathValue, operation in groupedOperations[operationTag]:
            documentLines.append(
                "| "
                + operationTag
                + " | "
                + method
                + " | `"
                + pathValue
                + "` | "
                + (operation.get("summary") or operation.get("description") or "")
                + " |"
            )
    documentLines.append("")
    documentLines.append("## 3. 接口详情")
    for operationTag in orderedTags:
        documentLines.extend(["", "### 3." + str(orderedTags.index(operationTag) + 1) + " " + operationTag, ""])
        for method, pathValue, operation in groupedOperations[operationTag]:
            documentLines.extend(
                [
                    "#### " + (operation.get("summary") or pathValue),
                    "",
                    "`" + method + " " + pathValue + "`",
                    "",
                ]
            )
            description = operation.get("description")
            if description:
                documentLines.extend([description, ""])
            parameterLines = extractParameters(operation, specification)
            if parameterLines:
                documentLines.extend(["**路径/查询参数：**", ""] + parameterLines + [""])
            requestBodyLines = extractRequestBody(operation, specification)
            if requestBodyLines:
                documentLines.extend(requestBodyLines + [""])
            documentLines.extend(extractResponses(operation, specification) + [""])
    return "\n".join(documentLines) + "\n"


def main() -> None:
    """生成文档并写入 docs/接口文档.md。"""
    documentation = buildDocumentation()
    OUTPUT_FILE_PATH.write_text(documentation, encoding="utf-8")
    print("接口文档已生成：" + str(OUTPUT_FILE_PATH))
    print("文档行数：" + str(documentation.count("\n")))


if __name__ == "__main__":
    main()
