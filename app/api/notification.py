"""
站内通知 API
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import Notification, User
from app.api.auth import get_current_user
from app.schemas.schemas import NotificationCreate, NotificationUpdate, NotificationResponse, NotificationListResponse

router = APIRouter()


@router.post("/")
async def create_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建通知（通常由系统或其他用户触发）
    只有管理员可以创建系统通知
    """
    if current_user.role not in ['admin'] and notification.type == 'system':
        raise HTTPException(status_code=403, detail="权限不足")

    db_notification = Notification(
        user_id=notification.user_id,
        title=notification.title,
        content=notification.content,
        type=notification.type,
        related_type=notification.related_type,
        related_id=notification.related_id
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


@router.get("/my")
def get_my_notifications(
    skip: int = 0,
    limit: int = 20,
    type: Optional[str] = None,
    is_read: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的通知列表
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if type:
        query = query.filter(Notification.type == type)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    # 获取总数
    total = query.count()

    # 获取未读数量
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    # 分页查询
    notifications = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()

    return {
        "items": notifications,
        "total": total,
        "unread_count": unread_count
    }


@router.get("/my/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的未读通知数量
    """
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return {"unread_count": count}


@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    标记通知为已读
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    notification.is_read = True
    notification.read_at = datetime.now()
    db.commit()
    return {"message": "已标记为已读"}


@router.post("/read-all")
def mark_all_as_read(
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    标记所有通知为已读
    """
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )
    if type:
        query = query.filter(Notification.type == type)

    count = query.count()
    query.update({
        Notification.is_read: True,
        Notification.read_at: datetime.now()
    }, synchronize_session=False)
    db.commit()

    return {"message": f"已标记 {count} 条通知为已读"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除通知
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    db.delete(notification)
    db.commit()
    return {"message": "删除成功"}


def send_workflow_notification(db: Session, user_id: int, workflow_name: str, node_name: str, related_type: str, related_id: int, submitter: str):
    """
    发送工作流通知工具函数
    """
    notification = Notification(
        user_id=user_id,
        title=f"待办审批：{workflow_name}",
        content=f"您有一个待审批的流程节点：{node_name}\n提交人：{submitter}",
        type="workflow",
        related_type=related_type,
        related_id=related_id
    )
    db.add(notification)
    return notification
