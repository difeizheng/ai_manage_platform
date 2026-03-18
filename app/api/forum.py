"""
AI 知识论坛 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import ForumPost, User
from app.schemas.schemas import ForumPostCreate, ForumPostUpdate, ForumPostResponse
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[ForumPostResponse])
def list_forum_posts(
    skip: int = 0,
    limit: int = 100,
    category: str = None,
    db: Session = Depends(get_db)
):
    """获取论坛帖子列表"""
    query = db.query(ForumPost).filter(ForumPost.status == "published")

    if category:
        query = query.filter(ForumPost.category == category)

    # 优先显示置顶帖
    posts = query.order_by(ForumPost.is_pinned.desc(), ForumPost.created_at.desc()).offset(skip).limit(limit).all()
    return posts


@router.get("/{post_id}", response_model=ForumPostResponse)
def get_forum_post(post_id: int, db: Session = Depends(get_db)):
    """获取帖子详情"""
    post = db.query(ForumPost).filter(ForumPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 增加浏览量
    post.view_count += 1
    db.commit()
    db.refresh(post)
    return post


@router.post("/", response_model=ForumPostResponse)
def create_forum_post(
    post_data: ForumPostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布帖子"""
    post = ForumPost(
        **post_data.model_dump(),
        author_id=current_user.id,
        status="published"
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.put("/{post_id}", response_model=ForumPostResponse)
def update_forum_post(
    post_id: int,
    post_data: ForumPostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新帖子"""
    post = db.query(ForumPost).filter(ForumPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限修改此帖子")

    update_data = post_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(post, key, value)

    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}")
def delete_forum_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除帖子"""
    post = db.query(ForumPost).filter(ForumPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限删除此帖子")

    db.delete(post)
    db.commit()
    return {"message": "删除成功"}
