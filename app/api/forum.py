"""
AI 知识论坛 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import ForumPost, ForumComment, User
from app.schemas.schemas import ForumPostCreate, ForumPostUpdate, ForumPostResponse, ForumCommentCreate, ForumCommentResponse
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


# ============ 评论相关 ============
@router.get("/{post_id}/comments")
def list_post_comments(
    post_id: int,
    db: Session = Depends(get_db)
):
    """获取帖子的评论列表"""
    comments = db.query(ForumComment).filter(
        ForumComment.post_id == post_id,
        ForumComment.is_deleted == False
    ).order_by(ForumComment.created_at.asc()).all()
    return comments


@router.post("/{post_id}/comments")
def create_comment(
    post_id: int,
    content: str,
    parent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布评论"""
    # 检查帖子是否存在
    post = db.query(ForumPost).filter(ForumPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    comment = ForumComment(
        post_id=post_id,
        author_id=current_user.id,
        parent_id=parent_id,
        content=content
    )
    db.add(comment)

    # 更新帖子的评论数
    post.comment_count += 1
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除评论（软删除）"""
    comment = db.query(ForumComment).filter(ForumComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    # 只有作者或管理员可以删除
    if comment.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限删除此评论")

    comment.is_deleted = True
    db.commit()
    return {"message": "删除成功"}
