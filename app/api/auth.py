"""
用户认证 API
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from typing import List, Optional
import os
import uuid
import secrets
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.core.audit import log_login
from app.models.models import User, Role, UserRole, PasswordResetToken, UserProfile
from app.schemas.schemas import UserCreate, UserResponse, Token, UserLogin, PasswordResetRequest, PasswordResetConfirm, UserProfileResponse, UserProfileUpdate

router = APIRouter()


async def get_token_from_request(request: Request):
    """从 Authorization header 获取 token"""
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ")[1]


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """获取当前用户"""
    token = await get_token_from_request(request)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户是否存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建用户
    user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        real_name=user_data.real_name,
        email=user_data.email,
        phone=user_data.phone,
        department=user_data.department,
        role=user_data.role or "user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db), request: Request = None):
    """用户登录"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        # 记录登录失败日志
        log_login(db=db, username=form_data.username, user_id=None, status="failed",
                  error_message="用户名或密码错误", request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        # 记录登录失败日志（用户被禁用）
        log_login(db=db, username=form_data.username, user_id=user.id, status="failed",
                  error_message="用户已被禁用", request=request)
        raise HTTPException(status_code=400, detail="用户已被禁用")

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # 记录登录成功日志
    log_login(db=db, username=user.username, user_id=user.id, status="success", request=request)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


# ============ 权限控制依赖注入 ============

def require_role(required_roles: List[str]):
    """
    依赖注入：要求用户拥有指定角色之一
    用法：current_user: User = Depends(require_role(["admin", "reviewer"]))
    """
    async def role_checker(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        if current_user.role in required_roles:
            return current_user

        # 检查用户是否拥有指定角色
        user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
        role_ids = [ur.role_id for ur in user_roles]
        if role_ids:
            roles = db.query(Role).filter(Role.id.in_(role_ids), Role.code.in_(required_roles)).all()
            if roles:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足，需要以下角色之一：{', '.join(required_roles)}"
        )
    return role_checker


def has_permission(permission: str):
    """
    依赖注入：要求用户拥有指定权限
    用法：current_user: User = Depends(has_permission("dataset.create"))
    """
    async def permission_checker(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        # admin 和 reviewer 拥有所有权限
        if current_user.role in ["admin", "reviewer"]:
            return current_user

        # 检查用户角色是否拥有指定权限
        user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
        role_ids = [ur.role_id for ur in user_roles]
        if role_ids:
            roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
            for role in roles:
                permissions = role.permissions or []
                if permission in permissions or "*" in permissions:
                    return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足：{permission}"
        )
    return permission_checker


def check_resource_owner(resource_model, resource_id_path: str = "resource_id"):
    """
    依赖注入：检查用户是否拥有指定资源的所有权
    用法：current_user: User = Depends(check_resource_owner(Application, "app_id"))
    """
    async def owner_checker(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        # admin 和 reviewer 拥有所有权限
        if current_user.role in ["admin", "reviewer"]:
            return current_user

        # 从路径参数中获取资源 ID（需要在路由中通过 context 传递）
        # 这里简化处理，由路由自己判断
        return current_user
    return owner_checker


def can_edit_resource(resource, current_user: User, db: Session) -> bool:
    """
    检查用户是否可以编辑指定资源
    规则：
    1. admin/reviewer 可以编辑所有资源
    2. 创建者可以编辑自己的资源
    3. 部门负责人可以编辑本部门资源（如果 is_department_manager=True）
    """
    if current_user.role in ["admin", "reviewer"]:
        return True

    # 检查是否是创建者
    if hasattr(resource, "creator_id") and resource.creator_id == current_user.id:
        return True

    if hasattr(resource, "applicant_id") and resource.applicant_id == current_user.id:
        return True

    # 检查是否是部门负责人
    if current_user.is_department_manager:
        if hasattr(resource, "creator_id"):
            creator = db.query(User).filter(User.id == resource.creator_id).first()
            if creator and creator.department == current_user.department:
                return True

    return False


def can_delete_resource(resource, current_user: User, db: Session) -> bool:
    """
    检查用户是否可以删除指定资源
    规则：
    1. admin 可以删除所有资源
    2. 创建者可以删除自己的资源
    3. reviewer 不能删除资源（只能审核）
    """
    if current_user.role == "admin":
        return True

    # 检查是否是创建者
    if hasattr(resource, "creator_id") and resource.creator_id == current_user.id:
        return True

    if hasattr(resource, "applicant_id") and resource.applicant_id == current_user.id:
        return True

    return False


# ============ 用户权限增强 ============

import secrets
from datetime import datetime, timedelta
from fastapi import BackgroundTasks
import smtplib
from email.mime.text import MIMEText


@router.post("/forgot-password")
async def forgot_password(
    request_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    忘记密码 - 发送重置密码邮件
    """
    # 查找用户
    user = db.query(User).filter(User.email == request_data.email).first()
    if not user or not user.is_active:
        # 为了安全，不提示用户是否存在
        return {"message": "如果邮箱已注册，重置密码邮件将发送至该邮箱"}

    # 生成重置令牌
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=24)

    # 创建重置令牌记录
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()

    # 发送重置密码邮件
    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", smtp_username)

        reset_link = f"http://localhost:8000/reset-password?token={token}"
        content = f"""
尊敬的 {user.real_name or user.username}：

您已申请重置密码。请点击以下链接重置密码：

{reset_link}

该链接将在 24 小时后过期。

如非本人操作，请忽略此邮件。

此致
敬礼
AI 管理平台
"""

        msg = MIMEText(content, 'plain', 'utf-8')
        msg['Subject'] = '重置密码 - AI 管理平台'
        msg['From'] = smtp_from
        msg['To'] = request_data.email

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()

        return {"message": "重置密码邮件已发送，请查收"}
    except Exception as e:
        # 邮件发送失败，删除令牌
        db.delete(reset_token)
        db.commit()
        return {"message": "重置密码邮件发送失败，请稍后重试"}


@router.post("/reset-password")
async def reset_password(
    request_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    重置密码 - 使用重置令牌设置新密码
    """
    # 验证令牌
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request_data.token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.now()
    ).first()

    if not reset_token:
        raise HTTPException(status_code=400, detail="重置令牌无效或已过期")

    # 获取用户
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="用户不存在或已被禁用")

    # 更新密码
    user.password_hash = get_password_hash(request_data.new_password)
    db.commit()

    # 标记令牌为已使用
    reset_token.used = True
    db.commit()

    return {"message": "密码重置成功"}


@router.get("/me/profile", response_model=UserProfileResponse)
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的个人资料
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        # 创建默认个人资料
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile


@router.put("/me/profile", response_model=UserProfileResponse)
def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户的个人资料
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    # 更新字段
    if profile_data.bio is not None:
        profile.bio = profile_data.bio
    if profile_data.skills is not None:
        profile.skills = profile_data.skills
    if profile_data.projects is not None:
        profile.projects = profile_data.projects
    if profile_data.phone_public is not None:
        profile.phone_public = profile_data.phone_public
    if profile_data.email_public is not None:
        profile.email_public = profile_data.email_public

    db.commit()
    db.refresh(profile)

    return profile


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传个人头像
    支持 jpg, png, gif 格式，最大 5MB
    """
    # 检查文件类型
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持图片格式")

    # 检查文件大小
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(status_code=400, detail="文件大小超过 5MB 限制")

    # 生成存储文件名
    stored_name = f"avatar_{current_user.id}_{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, stored_name)

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    # 更新或创建个人资料
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id, avatar_path=file_path)
        db.add(profile)
    else:
        profile.avatar_path = file_path

    db.commit()

    return {"message": "头像上传成功", "avatar_path": file_path}
