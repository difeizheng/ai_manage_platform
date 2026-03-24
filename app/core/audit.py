"""
审计日志工具模块
"""
from fastapi import Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
import json

from app.models.models import AuditLog


def get_client_ip(request: Request) -> str:
    """获取客户端 IP 地址"""
    # 检查是否在代理后面
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "unknown"


def log_action(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    resource_name: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    request: Optional[Request] = None
):
    """
    记录用户操作日志

    Args:
        db: 数据库会话
        action: 操作类型 (CREATE, UPDATE, DELETE, LOGIN, EXPORT, etc.)
        resource_type: 资源类型 (application, dataset, model, agent, etc.)
        resource_id: 资源 ID
        resource_name: 资源名称
        user_id: 用户 ID
        username: 用户名
        extra_data: 额外数据（如修改前后的值）
        status: 操作状态 (success, failed)
        error_message: 错误信息
        request: FastAPI 请求对象（用于获取 IP 和 User-Agent）
    """
    ip_address = None
    user_agent = None

    if request:
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

    log_entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=extra_data,
        status=status,
        error_message=error_message
    )

    db.add(log_entry)
    db.commit()


def log_create(db: Session, resource_type: str, resource_id: int, resource_name: str,
               user_id: int, username: str, request: Request = None):
    """记录创建操作"""
    log_action(
        db=db,
        action="CREATE",
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        user_id=user_id,
        username=username,
        request=request
    )


def log_update(db: Session, resource_type: str, resource_id: int, resource_name: str,
               user_id: int, username: str, changes: Dict[str, Any] = None, request: Request = None):
    """记录更新操作"""
    log_action(
        db=db,
        action="UPDATE",
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        user_id=user_id,
        username=username,
        extra_data={"changes": changes} if changes else None,
        request=request
    )


def log_delete(db: Session, resource_type: str, resource_id: int, resource_name: str,
               user_id: int, username: str, request: Request = None):
    """记录删除操作"""
    log_action(
        db=db,
        action="DELETE",
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        user_id=user_id,
        username=username,
        request=request
    )


def log_login(db: Session, username: str, user_id: int, status: str = "success",
              error_message: str = None, request: Request = None):
    """记录登录操作"""
    log_action(
        db=db,
        action="LOGIN",
        resource_type="user",
        user_id=user_id,
        username=username,
        status=status,
        error_message=error_message,
        request=request
    )


def log_export(db: Session, resource_type: str, user_id: int, username: str,
               extra_data: Dict[str, Any] = None, request: Request = None):
    """记录导出操作"""
    log_action(
        db=db,
        action="EXPORT",
        resource_type=resource_type,
        user_id=user_id,
        username=username,
        extra_data=extra_data,
        request=request
    )
