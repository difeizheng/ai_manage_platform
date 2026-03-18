"""
应用广场 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import AppStoreItem, User
from app.schemas.schemas import AppStoreItemCreate, AppStoreItemResponse
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[AppStoreItemResponse])
def list_app_store_items(
    skip: int = 0,
    limit: int = 100,
    category: str = None,
    business_domain: str = None,
    db: Session = Depends(get_db)
):
    """获取应用广场列表"""
    query = db.query(AppStoreItem).filter(AppStoreItem.status == "published")

    if category:
        query = query.filter(AppStoreItem.category == category)
    if business_domain:
        query = query.filter(AppStoreItem.business_domain == business_domain)

    items = query.offset(skip).limit(limit).all()
    return items


@router.get("/{item_id}", response_model=AppStoreItemResponse)
def get_app_store_item(item_id: int, db: Session = Depends(get_db)):
    """获取应用详情"""
    item = db.query(AppStoreItem).filter(AppStoreItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="应用不存在")

    # 增加使用次数
    item.usage_count += 1
    db.commit()
    db.refresh(item)
    return item


@router.post("/", response_model=AppStoreItemResponse)
def create_app_store_item(
    item_data: AppStoreItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布应用"""
    item = AppStoreItem(
        **item_data.model_dump(),
        developer=current_user.real_name or current_user.username
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=AppStoreItemResponse)
def update_app_store_item(
    item_id: int,
    item_data: AppStoreItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新应用"""
    item = db.query(AppStoreItem).filter(AppStoreItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="应用不存在")

    update_data = item_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_app_store_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下架应用"""
    item = db.query(AppStoreItem).filter(AppStoreItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="应用不存在")

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限下架此应用")

    db.delete(item)
    db.commit()
    return {"message": "下架成功"}
