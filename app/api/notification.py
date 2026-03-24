"""
站内通知 API
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Notification, User, NotificationSetting, EmailLog
from app.api.auth import get_current_user
from app.schemas.schemas import NotificationCreate, NotificationUpdate, NotificationResponse, NotificationListResponse, NotificationSettingResponse, NotificationSettingCreate, EmailLogResponse

router = APIRouter()


# ============ 站内通知 ============

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


# ============ 通知设置 ============

@router.get("/settings", response_model=NotificationSettingResponse)
def get_notification_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的通知设置"""
    settings_obj = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).first()

    if not settings_obj:
        # 创建默认设置
        settings_obj = NotificationSetting(
            user_id=current_user.id,
            enable_email=True,
            enable_workflow_email=True,
            enable_system_email=True
        )
        db.add(settings_obj)
        db.commit()
        db.refresh(settings_obj)

    return settings_obj


@router.put("/settings", response_model=NotificationSettingResponse)
def update_notification_settings(
    settings_data: NotificationSettingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新通知设置"""
    settings_obj = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).first()

    if not settings_obj:
        settings_obj = NotificationSetting(user_id=current_user.id)
        db.add(settings_obj)

    settings_obj.enable_email = settings_data.enable_email
    settings_obj.enable_workflow_email = settings_data.enable_workflow_email
    settings_obj.enable_system_email = settings_data.enable_system_email
    settings_obj.quiet_start = settings_data.quiet_start
    settings_obj.quiet_end = settings_data.quiet_end

    db.commit()
    db.refresh(settings_obj)
    return settings_obj


# ============ 邮件通知 ============

def _send_email_internal(
    db: Session,
    recipient: str,
    subject: str,
    content: str,
    template_name: Optional[str] = None
) -> bool:
    """
    内部邮件发送函数
    返回是否发送成功
    """
    # 检查是否在免打扰时段（简化实现，不检查）

    try:
        # 获取 SMTP 配置
        smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", smtp_username)

        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = recipient
        msg['Subject'] = subject

        # 添加 HTML 内容
        html_content = f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">{subject}</h2>
                <div style="color: #666; line-height: 1.6;">
                    {content.replace(chr(10), '<br>')}
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin-top: 20px;">
                <p style="color: #999; font-size: 12px;">
                    此邮件由 AI 管理平台自动发送，请勿直接回复。
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # 发送邮件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        # 记录错误
        return False


@router.post("/send-email")
async def send_email_notification(
    recipient_email: str,
    subject: str,
    content: str,
    template_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发送邮件通知
    只有管理员可以发送邮件通知
    """
    if current_user.role not in ['admin']:
        raise HTTPException(status_code=403, detail="权限不足")

    # 创建邮件日志记录
    email_log = EmailLog(
        recipient=recipient_email,
        subject=subject,
        content=content,
        template_name=template_name,
        status="pending"
    )
    db.add(email_log)
    db.commit()
    db.refresh(email_log)

    # 发送邮件
    success = _send_email_internal(db, recipient_email, subject, content, template_name)

    if success:
        email_log.status = "sent"
        email_log.sent_at = datetime.now()
        db.commit()
        return {"message": "邮件发送成功", "log_id": email_log.id}
    else:
        email_log.status = "failed"
        email_log.error_message = "SMTP 发送失败，请检查配置"
        db.commit()
        raise HTTPException(status_code=500, detail="邮件发送失败")


@router.get("/email-logs", response_model=List[EmailLogResponse])
def list_email_logs(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取邮件发送记录（仅 admin）"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="权限不足")

    query = db.query(EmailLog)
    if status:
        query = query.filter(EmailLog.status == status)

    return query.order_by(desc(EmailLog.created_at)).offset(skip).limit(limit).all()


# ============ 邮件模板 ============

EMAIL_TEMPLATES = {
    "workflow_approval": {
        "subject": "待办审批：{workflow_name}",
        "content": """
尊敬的 {user_name}：

您有一个待审批的流程节点：{node_name}
工作流名称：{workflow_name}
提交人：{submitter}
提交时间：{submit_time}

请登录系统进行审批操作。

此致
敬礼
AI 管理平台
"""
    },
    "approval_result": {
        "subject": "申请审批结果通知",
        "content": """
尊敬的用户：

您的申请已审批完成。
审批结果：{result}
审批意见：{comments}

此致
敬礼
AI 管理平台
"""
    },
    "system_notice": {
        "subject": "系统通知：{title}",
        "content": """
尊敬的用户：

{content}

此致
敬礼
AI 管理平台
"""
    }
}


@router.get("/email-templates")
def get_email_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取邮件模板列表"""
    return {"templates": list(EMAIL_TEMPLATES.keys())}


@router.get("/email-templates/{template_name}")
def get_email_template(
    template_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取邮件模板详情"""
    if template_name not in EMAIL_TEMPLATES:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {"template": EMAIL_TEMPLATES[template_name]}
