"""
统一异常处理模块
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


class BusinessException(Exception):
    """业务异常基类"""
    def __init__(self, message: str, code: int = 400, detail: str = None):
        self.message = message
        self.code = code
        self.detail = detail or message
        super().__init__(self.message)


class ResourceNotFoundException(BusinessException):
    """资源不存在异常"""
    def __init__(self, resource_type: str = "资源", resource_id: int = None):
        message = f"{resource_type}不存在"
        if resource_id:
            message = f"{resource_type}（ID: {resource_id}）不存在"
        super().__init__(message=message, code=404)


class PermissionDeniedException(BusinessException):
    """权限不足异常"""
    def __init__(self, message: str = "权限不足，无法执行此操作"):
        super().__init__(message=message, code=403)


class InvalidParameterException(BusinessException):
    """参数无效异常"""
    def __init__(self, message: str = "参数无效"):
        super().__init__(message=message, code=400)


class ResourceConflictException(BusinessException):
    """资源冲突异常（如重复创建）"""
    def __init__(self, message: str = "资源已存在或冲突"):
        super().__init__(message=message, code=409)


class WorkflowException(BusinessException):
    """工作流异常"""
    def __init__(self, message: str):
        super().__init__(message=message, code=400)


def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器"""

    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        """处理业务异常"""
        logger.warning(f"业务异常：{exc.message}, 路径：{request.url.path}")
        return JSONResponse(
            status_code=exc.code,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求参数验证异常"""
        logger.warning(f"参数验证异常：{exc.errors()}, 路径：{request.url.path}")
        errors = []
        for error in exc.errors():
            field = ".".join(str(x) for x in error.get("loc", []))
            errors.append(f"{field}: {error.get('msg', '参数错误')}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": 400,
                "message": "参数验证失败",
                "detail": "; ".join(errors)
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """处理数据库异常"""
        logger.error(f"数据库异常：{str(exc)}, 路径：{request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": 500,
                "message": "数据库操作失败",
                "detail": "请稍后重试或联系管理员"
            }
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
        """处理 Pydantic 验证异常"""
        logger.warning(f"Pydantic 验证异常：{exc.errors()}, 路径：{request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": 400,
                "message": "数据格式错误",
                "detail": str(exc.errors())
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """处理全局未捕获异常"""
        logger.error(f"未捕获异常：{str(exc)}, 路径：{request.url.path}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "detail": "请稍后重试或联系管理员"
            }
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """处理 404 错误"""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "code": 404,
                "message": "请求的资源不存在",
                "detail": f"{request.method} {request.url.path}"
            }
        )
