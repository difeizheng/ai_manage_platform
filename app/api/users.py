"""
用户管理 API - 用户资料、职位管理等
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import User, UserProfile, Position, UserPosition, Department, Role
from app.schemas.schemas import (
    UserProfileResponse,
    UserProfileUpdate,
    PositionResponse,
    PositionCreate,
    PositionUpdate,
    UserPositionResponse,
    UserPositionAssign,
    PaginatedResponse
)
from app.api.auth import get_current_user, require_role

router = APIRouter()


# ============ 职位管理 ============

@router.get("/positions", response_model=List[PositionResponse])
def list_positions(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取职位列表"""
    query = db.query(Position)
    if is_active is not None:
        query = query.filter(Position.is_active == is_active)

    return query.order_by(Position.created_at.desc()).all()


@router.post("/positions", response_model=PositionResponse)
def create_position(
    position_data: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """创建职位（仅 admin）"""
    # 检查职位编码是否已存在
    existing = db.query(Position).filter(Position.code == position_data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="职位编码已存在")

    position = Position(**position_data.model_dump())
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


@router.get("/positions/{position_id}", response_model=PositionResponse)
def get_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取职位详情"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    return position


@router.put("/positions/{position_id}", response_model=PositionResponse)
def update_position(
    position_id: int,
    position_data: PositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """更新职位（仅 admin）"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    # 更新字段
    for field, value in position_data.model_dump(exclude_unset=True).items():
        setattr(position, field, value)

    db.commit()
    db.refresh(position)
    return position


@router.delete("/positions/{position_id}")
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """删除职位（软删除，仅 admin）"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    # 软删除
    position.is_active = False
    db.commit()

    return {"message": "职位已删除"}


# ============ 用户职位分配 ============

@router.get("/me/positions", response_model=List[UserPositionResponse])
def get_my_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的职位列表"""
    return db.query(UserPosition).filter(
        UserPosition.user_id == current_user.id
    ).all()


@router.post("/users/{user_id}/positions")
def assign_position(
    user_id: int,
    assign_data: UserPositionAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """为用户分配职位（仅 admin）"""
    # 检查用户是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查职位是否存在
    position = db.query(Position).filter(Position.id == assign_data.position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    # 如果指定了部门，检查部门是否存在
    if assign_data.department_id:
        department = db.query(Department).filter(Department.id == assign_data.department_id).first()
        if not department:
            raise HTTPException(status_code=404, detail="部门不存在")

    # 创建用户职位关联
    user_position = UserPosition(
        user_id=user_id,
        position_id=assign_data.position_id,
        department_id=assign_data.department_id,
        is_primary=assign_data.is_primary
    )
    db.add(user_position)

    # 如果是主要职位，取消该用户的其他主要职位
    if assign_data.is_primary:
        db.query(UserPosition).filter(
            UserPosition.user_id == user_id,
            UserPosition.is_primary == True
        ).update({"is_primary": False})

    db.commit()
    db.refresh(user_position)

    return {"message": "职位分配成功", "data": user_position}


@router.delete("/users/{user_id}/positions/{position_id}")
def remove_position(
    user_id: int,
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """移除用户的职位（仅 admin）"""
    user_position = db.query(UserPosition).filter(
        UserPosition.user_id == user_id,
        UserPosition.position_id == position_id
    ).first()

    if not user_position:
        raise HTTPException(status_code=404, detail="用户职位关联不存在")

    db.delete(user_position)
    db.commit()

    return {"message": "职位已移除"}


# ============ 部门管理 ============

@router.get("/departments", response_model=List[dict])
def list_departments(
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取部门列表（支持树形结构）"""
    query = db.query(Department).filter(Department.is_active == True)

    if parent_id is not None:
        query = query.filter(Department.parent_id == parent_id)

    departments = query.all()

    # 构建树形结构
    def build_tree(dept):
        children = [d for d in departments if d.parent_id == dept.id]
        result = {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "description": dept.description,
            "manager_id": dept.manager_id,
        }
        if children:
            result["children"] = [build_tree(child) for child in children]
        return result

    return [build_tree(dept) for dept in departments if dept.parent_id is None]


@router.post("/departments", response_model=dict)
def create_department(
    department_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """创建部门（仅 admin）"""
    # 检查部门编码是否已存在
    existing = db.query(Department).filter(Department.code == department_data["code"]).first()
    if existing:
        raise HTTPException(status_code=400, detail="部门编码已存在")

    department = Department(**department_data)
    db.add(department)
    db.commit()
    db.refresh(department)

    return {
        "id": department.id,
        "name": department.name,
        "code": department.code,
        "description": department.description,
        "parent_id": department.parent_id,
        "manager_id": department.manager_id,
        "is_active": department.is_active,
        "created_at": department.created_at
    }


@router.put("/departments/{department_id}")
def update_department(
    department_id: int,
    department_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """更新部门（仅 admin）"""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")

    # 更新字段
    for field, value in department_data.items():
        if hasattr(department, field):
            setattr(department, field, value)

    db.commit()
    db.refresh(department)

    return {
        "id": department.id,
        "name": department.name,
        "code": department.code,
        "description": department.description,
        "parent_id": department.parent_id,
        "manager_id": department.manager_id,
        "is_active": department.is_active
    }


@router.delete("/departments/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """删除部门（软删除，仅 admin）"""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")

    # 软删除
    department.is_active = False
    db.commit()

    return {"message": "部门已删除"}


# ============ 用户管理 ============

@router.get("/", response_model=PaginatedResponse)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    department: Optional[str] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "reviewer"]))
):
    """获取用户列表（仅 admin/reviewer）"""
    query = db.query(User)

    if keyword:
        query = query.filter(
            (User.username.contains(keyword)) |
            (User.real_name.contains(keyword)) |
            (User.email.contains(keyword))
        )

    if department:
        query = query.filter(User.department == department)

    if role:
        query = query.filter(User.role == role)

    total = query.count()
    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()

    return PaginatedResponse.create(items=users, total=total, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=dict)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户详情（包含个人资料和职位）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取个人资料
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    # 获取用户职位
    positions = db.query(UserPosition, Position).join(
        Position, UserPosition.position_id == Position.id
    ).filter(UserPosition.user_id == user_id).all()

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "email": user.email,
            "phone": user.phone,
            "department": user.department,
            "role": user.role,
            "is_active": user.is_active,
            "is_department_manager": user.is_department_manager,
            "created_at": user.created_at
        },
        "profile": profile,
        "positions": [
            {
                "id": up.id,
                "position": {
                    "id": p.id,
                    "name": p.name,
                    "code": p.code
                },
                "department_id": up.department_id,
                "is_primary": up.is_primary
            }
            for up, p in positions
        ]
    }


@router.put("/{user_id}")
def update_user(
    user_id: int,
    user_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """更新用户信息（仅 admin）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新字段
    allowed_fields = ["real_name", "email", "phone", "department", "is_department_manager"]
    for field, value in user_data.items():
        if field in allowed_fields and hasattr(user, field):
            setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "email": user.email,
        "phone": user.phone,
        "department": user.department,
        "role": user.role,
        "is_active": user.is_active,
        "is_department_manager": user.is_department_manager
    }


@router.post("/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """管理员重置用户密码（仅 admin）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    from app.core.security import get_password_hash
    user.password_hash = get_password_hash(new_password)
    db.commit()

    return {"message": f"用户 {user.username} 的密码已重置"}
