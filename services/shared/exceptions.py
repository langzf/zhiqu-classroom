"""全局异常定义 & FastAPI 异常处理器"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


# ── 业务异常 ──────────────────────────────────────────

class AppError(Exception):
    """业务异常基类"""

    def __init__(self, code: int = -1, message: str = "error", status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str = "resource", id: str = ""):
        super().__init__(
            code=404,
            message=f"{resource} not found: {id}" if id else f"{resource} not found",
            status_code=404,
        )


class UnauthorizedError(AppError):
    def __init__(self, message: str = "unauthorized"):
        super().__init__(code=401, message=message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "forbidden"):
        super().__init__(code=403, message=message, status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str = "conflict"):
        super().__init__(code=409, message=message, status_code=409)


class ValidationError(AppError):
    def __init__(self, message: str = "validation error"):
        super().__init__(code=422, message=message, status_code=422)


class BusinessError(AppError):
    """通用业务逻辑错误"""
    def __init__(self, message: str = "business error", code: int = -1, status_code: int = 400):
        super().__init__(code=code, message=message, status_code=status_code)


# ── 异常处理器注册 ────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            code=exc.code,
            message=exc.message,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_error",
            path=str(request.url),
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "internal server error", "data": None},
        )
