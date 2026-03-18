"""
系统配置 API - 用户管理、角色管理
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import User, Role, UserRole
from app.api.auth import get_current_user
from app.schemas.schemas import UserResponse, RoleCreate, RoleUpdate, RoleResponse, UserRoleAssign

router = APIRouter()


# ============ 角色管理 ============
@router.get("/roles")
def list_roles(
    is_active: Optional[bool] = None,
    is_system: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取角色列表"""
    query = db.query(Role)
    if is_active is not None:
        query = query.filter(Role.is_active == is_active)
    if is_system is not None:
        query = query.filter(Role.is_system == is_system)
    roles = query.order_by(Role.created_at.desc()).all()
    return roles


@router.get("/roles/{role_id}")
def get_role(
    role_id: int,
    db: Session = Depends(get_db)
):
    """获取角色详情"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return role


@router.post("/roles")
async def create_role(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新角色"""
    if current_user.role not in ['admin']:
        raise HTTPException(status_code=403, detail="权限不足")

    data = await request.json()

    # 检查角色编码是否已存在
    existing = db.query(Role).filter(Role.code == data.get('code')).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色编码已存在")

    role = Role(
        name=data.get('name'),
        code=data.get('code'),
        description=data.get('description', ''),
        permissions=data.get('permissions', []),
        is_system=data.get('is_system', False),
        is_active=data.get('is_active', True)
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新角色"""
    if current_user.role not in ['admin']:
        raise HTTPException(status_code=403, detail="权限不足")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可修改")

    data = await request.json()

    if 'name' in data:
        role.name = data['name']
    if 'description' in data:
        role.description = data['description']
    if 'permissions' in data:
        role.permissions = data['permissions']
    if 'is_active' in data:
        role.is_active = data['is_active']

    db.commit()
    db.refresh(role)
    return role


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除角色"""
    if current_user.role not in ['admin']:
        raise HTTPException(status_code=403, detail="权限不足")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可删除")

    # 检查是否有用户使用此角色
    user_count = db.query(UserRole).filter(UserRole.role_id == role_id).count()
    if user_count > 0:
        raise HTTPException(status_code=400, detail=f"有{user_count}个用户正在使用此角色，无法删除")

    db.delete(role)
    db.commit()
    return {"message": "删除成功"}


# ============ 用户角色管理 ============
@router.get("/users/{user_id}/roles")
def get_user_roles(
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取用户的角色列表"""
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    role_ids = [ur.role_id for ur in user_roles]
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    return roles


@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """给用户分配角色"""
    if current_user.role not in ['admin']:
        raise HTTPException(status_code=403, detail="权限不足")

    # 检查用户是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    data = await request.json()
    role_id = data.get('role_id')

    # 检查角色是否存在
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 检查是否已分配
    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户已拥有此角色")

    user_role = UserRole(
        user_id=user_id,
        role_id=role_id,
        assigned_by=current_user.id,
        expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None
    )
    db.add(user_role)
    db.commit()
    db.refresh(user_role)
    return user_role


@router.delete("/users/{user_id}/roles/{role_id}")
def remove_role_from_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """移除用户的角色"""
    if current_user.role not in ['admin']:
        raise HTTPException(status_code=403, detail="权限不足")

    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    ).first()
    if not user_role:
        raise HTTPException(status_code=404, detail="用户没有此角色")

    db.delete(user_role)
    db.commit()
    return {"message": "移除成功"}


# ============ 用户管理 ============
@router.get("/users")
def list_users(
    username: Optional[str] = None,
    department: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    query = db.query(User)

    if username:
        query = query.filter(User.username.like(f"%{username}%"))
    if department:
        query = query.filter(User.department == department)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.order_by(User.created_at.desc()).all()
    return users


@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取用户详情"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新用户信息"""
    if current_user.role not in ['admin', 'reviewer']:
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    data = await request.json()

    if 'real_name' in data:
        user.real_name = data['real_name']
    if 'email' in data:
        user.email = data['email']
    if 'phone' in data:
        user.phone = data['phone']
    if 'department' in data:
        user.department = data['department']
    if 'role' in data and current_user.role == 'admin':
        user.role = data['role']
    if 'is_active' in data and current_user.role == 'admin':
        user.is_active = data['is_active']

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除用户"""
    if current_user.role not in ['admin']:
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.username == 'admin':
        raise HTTPException(status_code=400, detail="超级管理员不可删除")

    db.delete(user)
    db.commit()
    return {"message": "删除成功"}


# ============ 角色用户查询 ============
@router.get("/roles/{role_id}/users")
def get_role_users(
    role_id: int,
    db: Session = Depends(get_db)
):
    """获取拥有某角色的所有用户"""
    user_roles = db.query(UserRole).filter(UserRole.role_id == role_id).all()
    user_ids = [ur.user_id for ur in user_roles]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    return users


@router.get("/roles/by-code/{role_code}/users")
def get_users_by_role_code(
    role_code: str,
    db: Session = Depends(get_db)
):
    """根据角色 code 获取拥有该角色的所有用户"""
    # 先根据 code 查找角色
    role = db.query(Role).filter(Role.code == role_code).first()
    if not role:
        return []  # 角色不存在，返回空列表

    # 查询拥有该角色的用户
    user_roles = db.query(UserRole).filter(UserRole.role_id == role.id).all()
    user_ids = [ur.user_id for ur in user_roles]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    return users
