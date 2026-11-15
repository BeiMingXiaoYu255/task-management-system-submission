"""统一业务异常与全局异常处理器。

设计说明：
    业务层只抛 AppException（携带错误码/中文提示/HTTP 状态码），
    由 FastAPI 全局异常处理器转换成统一 JSON：
        { "code": "ERROR_CODE", "message": "中文提示", "details": null }
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHttpException

logger = logging.getLogger("taskManagement")


class AppException(Exception):
    """业务异常：所有可预期错误都通过该异常向接口层传递。"""

    def __init__(
        self,
        code: str,
        message: str,
        statusCode: int = 400,
        details: object | None = None,
    ) -> None:
        """构造异常。

        参数：
            code：机器可读错误码；
            message：中文错误提示；
            statusCode：HTTP 状态码；
            details：附加信息。
        """
        self.code = code
        self.message = message
        self.statusCode = statusCode
        self.details = details
        super().__init__(message)


def validationError(message: str) -> AppException:
    """快捷构造参数校验异常（400）。"""
    return AppException("VALIDATION_ERROR", message, 400)


def unauthorized(message: str = "Not signed in or session expired") -> AppException:
    """快捷构造未认证异常（401）。"""
    return AppException("INVALID_CREDENTIALS", message, 401)


def forbidden(message: str = "You do not have permission to perform this action") -> AppException:
    """快捷构造无权限异常（403）。"""
    return AppException("FORBIDDEN", message, 403)


def notFound(message: str = "Resource not found") -> AppException:
    """快捷构造资源不存在异常（404）。"""
    return AppException("NOT_FOUND", message, 404)


def conflict(message: str = "Data conflict") -> AppException:
    """快捷构造数据冲突异常（409）。"""
    return AppException("CONFLICT", message, 409)


def buildErrorResponse(code: str, message: str, details: object | None = None) -> dict:
    """构造统一错误响应体。"""
    return {"code": code, "message": message, "details": details}


def registerExceptionHandlers(app: FastAPI) -> None:
    """向 FastAPI 应用注册全部全局异常处理器。"""

    @app.exception_handler(AppException)
    async def handleAppException(request: Request, exception: AppException) -> JSONResponse:
        """业务异常：按异常自带状态码与错误码原样返回。"""
        return JSONResponse(
            status_code=exception.statusCode,
            content=buildErrorResponse(exception.code, exception.message, exception.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handleValidationException(
        request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        """参数校验异常：把 Pydantic 错误整理为中文提示。"""
        firstError = exception.errors()[0] if exception.errors() else {}
        location = ".".join(str(item) for item in firstError.get("loc", [])[1:])
        reason = firstError.get("msg", "Invalid parameter")
        message = f"Request validation failed: {location} {reason}".strip()
        return JSONResponse(
            status_code=400,
            content=buildErrorResponse("VALIDATION_ERROR", message, exception.errors()),
        )

    @app.exception_handler(StarletteHttpException)
    async def handleHttpException(request: Request, exception: StarletteHttpException) -> JSONResponse:
        """HTTP 异常：统一为业务错误结构（保留状态码）。"""
        message = exception.detail if isinstance(exception.detail, str) else "Request processing failed"
        code = "NOT_FOUND" if exception.status_code == 404 else "HTTP_ERROR"
        return JSONResponse(
            status_code=exception.status_code,
            content=buildErrorResponse(code, message),
        )

    @app.exception_handler(Exception)
    async def handleUnexpectedException(request: Request, exception: Exception) -> JSONResponse:
        """未预期异常：记录日志并返回 500，不泄漏内部细节。"""
        logger.exception("Unhandled exception: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=buildErrorResponse("INTERNAL_ERROR", "Internal server error. Please try again later."),
        )
