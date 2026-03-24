"""
邮件服务模块 - 发送邮件通知
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class MailService:
    """邮件服务类"""

    def __init__(self):
        self.server = None
        self.connected = False

    def connect(self):
        """连接到 SMTP 服务器"""
        if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
            logger.warning("邮件配置不完整，无法发送邮件")
            return False

        try:
            if settings.MAIL_USE_TLS:
                self.server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
                self.server.starttls()
            else:
                self.server = smtplib.SMTP_SSL(settings.MAIL_SERVER, settings.MAIL_PORT)

            self.server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            self.connected = True
            logger.info("邮件服务连接成功")
            return True
        except Exception as e:
            logger.error(f"邮件服务连接失败：{e}")
            self.connected = False
            return False

    def disconnect(self):
        """断开连接"""
        if self.server:
            self.server.quit()
            self.connected = False

    def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        发送邮件

        Args:
            to: 收件人
            subject: 邮件主题
            html_content: HTML 内容
            cc: 抄送列表
            bcc: 密送列表

        Returns:
            bool: 是否发送成功
        """
        if not self.connected:
            if not self.connect():
                return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.MAIL_DEFAULT_SENDER
            msg['To'] = to

            if cc:
                msg['Cc'] = ', '.join(cc)

            # 添加纯文本版本（可选）
            # text_part = MIMEText(html_to_text(html_content), 'plain', 'utf-8')
            # msg.attach(text_part)

            # 添加 HTML 版本
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # 构建收件人列表
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            self.server.sendmail(settings.MAIL_DEFAULT_SENDER, recipients, msg.as_string())
            logger.info(f"邮件发送成功：{to}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败：{e}")
            return False


# 全局邮件服务实例
mail_service = MailService()


def get_mail_service() -> MailService:
    """获取邮件服务实例"""
    return mail_service


# ============ 邮件模板 ============

def render_approval_template(
    applicant_name: str,
    app_title: str,
    status: str,
    comments: str,
    approver_name: str,
    approve_time: str
) -> str:
    """
    渲染审批结果邮件模板

    Args:
        applicant_name: 申请人姓名
        app_title: 申请标题
        status: 状态（通过/拒绝）
        comments: 审批意见
        approver_name: 审批人姓名
        approve_time: 审批时间

    Returns:
        str: HTML 邮件内容
    """
    status_color = "#10B981" if status == "通过" else "#EF4444"
    status_icon = "✓" if status == "通过" else "✗"

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .status {{ display: inline-block; padding: 8px 20px; border-radius: 20px; color: white; font-weight: bold; }}
        .approved {{ background: {status_color}; }}
        .rejected {{ background: {status_color}; }}
        .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">审批结果通知</h1>
        </div>
        <div class="content">
            <p>尊敬的 {applicant_name}：</p>
            <p>您的申请已有审批结果，详情如下：</p>

            <div class="info-box">
                <p><strong>申请标题：</strong>{app_title}</p>
                <p><strong>审批状态：</strong>
                    <span class="status {'approved' if status == '通过' else 'rejected'}">
                        {status_icon} {status}
                    </span>
                </p>
                <p><strong>审批意见：</strong>{comments or '无'}</p>
                <p><strong>审批人：</strong>{approver_name}</p>
                <p><strong>审批时间：</strong>{approve_time}</p>
            </div>

            <p>如有任何疑问，请联系审批人或系统管理员。</p>
            <p style="text-align: right;">人工智能管理平台</p>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复</p>
        </div>
    </div>
</body>
</html>
"""


def render_workflow_notification(
    recipient_name: str,
    workflow_name: str,
    node_name: str,
    submitter_name: str,
    app_title: str,
    submit_time: str
) -> str:
    """
    渲染工作流待办通知邮件模板
    """
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .action-btn {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; margin-top: 20px; }}
        .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">待办审批通知</h1>
        </div>
        <div class="content">
            <p>尊敬的 {recipient_name}：</p>
            <p>您有一个待审批的流程，详情如下：</p>

            <div class="info-box">
                <p><strong>流程名称：</strong>{workflow_name}</p>
                <p><strong>当前节点：</strong>{node_name}</p>
                <p><strong>申请标题：</strong>{app_title}</p>
                <p><strong>提交人：</strong>{submitter_name}</p>
                <p><strong>提交时间：</strong>{submit_time}</p>
            </div>

            <p>请及时登录系统进行处理。</p>
            <p style="text-align: right;">人工智能管理平台</p>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复</p>
        </div>
    </div>
</body>
</html>
"""
