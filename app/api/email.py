"""
邮件通知 API - 邮件发送、邮件模板管理
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import User, Application, EmailLog, NotificationSetting, WorkflowDefinition, WorkflowRecord
from app.api.auth import get_current_user
from app.core.mail import (
    mail_service, render_approval_template, render_workflow_notification
)

router = APIRouter()


@router.get("/settings")
def get_email_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的邮件通知设置"""
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).first()

    if not settings:
        # 创建默认设置
        settings = NotificationSetting(
            user_id=current_user.id,
            enable_email=True,
            enable_workflow_email=True,
            enable_system_email=True
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.put("/settings")
def update_email_settings(
    enable_email: bool = True,
    enable_workflow_email: bool = True,
    enable_system_email: bool = True,
    quiet_start: Optional[str] = None,
    quiet_end: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新邮件通知设置"""
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).first()

    if not settings:
        settings = NotificationSetting(user_id=current_user.id)
        db.add(settings)

    settings.enable_email = enable_email
    settings.enable_workflow_email = enable_workflow_email
    settings.enable_system_email = enable_system_email
    settings.quiet_start = quiet_start
    settings.quiet_end = quiet_end

    db.commit()
    db.refresh(settings)

    return settings


@router.post("/test")
def send_test_email(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送测试邮件"""
    if not current_user.email:
        raise HTTPException(status_code=400, detail="请先设置邮箱地址")

    subject = "【测试邮件】人工智能管理平台"
    content = f"""
    <html>
    <body>
        <h2>邮件测试</h2>
        <p>尊敬的 {current_user.real_name or current_user.username}：</p>
        <p>这是一封测试邮件，如果您收到此邮件，说明邮件服务配置正确。</p>
        <p>发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <p style="color: #999; font-size: 12px;">此邮件由系统自动发送</p>
    </body>
    </html>
    """

    # 记录邮件日志
    email_log = EmailLog(
        recipient=current_user.email,
        subject=subject,
        content=content,
        template_name="test",
        status="pending"
    )
    db.add(email_log)
    db.commit()

    # 异步发送
    background_tasks.add_task(send_email_async, current_user.email, subject, content, email_log.id, db)

    return {"message": "测试邮件已加入发送队列"}


def send_email_async(to: str, subject: str, content: str, log_id: int, db: Session):
    """异步发送邮件"""
    try:
        success = mail_service.send_email(to=to, subject=subject, html_content=content)

        email_log = db.query(EmailLog).filter(EmailLog.id == log_id).first()
        if email_log:
            if success:
                email_log.status = "sent"
                email_log.sent_at = datetime.now()
            else:
                email_log.status = "failed"
                email_log.error_message = "发送失败"
            db.commit()
    except Exception as e:
        email_log = db.query(EmailLog).filter(EmailLog.id == log_id).first()
        if email_log:
            email_log.status = "failed"
            email_log.error_message = str(e)
            db.commit()


def send_approval_email(
    background_tasks: BackgroundTasks,
    db: Session,
    applicant: User,
    app: Application,
    status: str,
    approver: User,
    comments: str
):
    """
    发送审批结果邮件

    Args:
        background_tasks: 后台任务
        db: 数据库会话
        applicant: 申请人
        app: 申请记录
        status: 状态（通过/拒绝）
        approver: 审批人
        comments: 审批意见
    """
    if not applicant.email:
        return

    # 检查用户邮件设置
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == applicant.id,
        NotificationSetting.enable_email == True
    ).first()

    if not settings:
        return

    subject = f"【审批结果】{app.title}"
    content = render_approval_template(
        applicant_name=applicant.real_name or applicant.username,
        app_title=app.title,
        status=status,
        comments=comments or '',
        approver_name=approver.real_name or approver.username,
        approve_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    # 记录邮件日志
    email_log = EmailLog(
        recipient=applicant.email,
        subject=subject,
        content=content,
        template_name="approval_result",
        status="pending"
    )
    db.add(email_log)
    db.commit()

    background_tasks.add_task(send_email_async, applicant.email, subject, content, email_log.id, db)


def send_workflow_notification_email(
    background_tasks: BackgroundTasks,
    db: Session,
    recipient: User,
    workflow: WorkflowDefinition,
    node_name: str,
    submitter: User,
    app: Application
):
    """
    发送工作流待办通知邮件

    Args:
        background_tasks: 后台任务
        db: 数据库会话
        recipient: 收件人（审批人）
        workflow: 工作流定义
        node_name: 节点名称
        submitter: 提交人
        app: 申请记录
    """
    if not recipient.email:
        return

    # 检查用户邮件设置
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == recipient.id,
        NotificationSetting.enable_workflow_email == True
    ).first()

    if not settings:
        return

    subject = f"【待办审批】{workflow.name} - {node_name}"
    content = render_workflow_notification(
        recipient_name=recipient.real_name or recipient.username,
        workflow_name=workflow.name,
        node_name=node_name,
        submitter_name=submitter.real_name or submitter.username,
        app_title=app.title,
        submit_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    # 记录邮件日志
    email_log = EmailLog(
        recipient=recipient.email,
        subject=subject,
        content=content,
        template_name="workflow_notification",
        status="pending"
    )
    db.add(email_log)
    db.commit()

    background_tasks.add_task(send_email_async, recipient.email, subject, content, email_log.id, db)


@router.get("/logs")
def list_email_logs(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取邮件发送记录（仅管理员）"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限查看")

    query = db.query(EmailLog)
    if status:
        query = query.filter(EmailLog.status == status)

    logs = query.order_by(EmailLog.created_at.desc()).offset(skip).limit(limit).all()
    total = query.count()

    return {"items": logs, "total": total}
