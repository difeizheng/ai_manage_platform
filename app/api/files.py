"""
文件管理 API - 统一文件上传、下载、管理服务
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import hashlib
from datetime import datetime
import mimetypes

from app.core.database import get_db
from app.core.config import settings
from app.models.models import File as FileModel, User
from app.schemas.schemas import FileResponse, PaginatedResponse
from app.api.auth import get_current_user
from app.core.audit import log_action

router = APIRouter()


# 允许的文件类型白名单
ALLOWED_EXTENSIONS = {
    # 图片
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
    # 文档
    'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md'],
    # 压缩包
    'archive': ['.zip', '.rar', '.7z', '.tar', '.gz'],
    # 代码
    'code': ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.sql', '.json', '.yaml', '.yml'],
    # 模型文件
    'model': ['.pt', '.pth', '.onnx', '.pb', '.h5', '.pickle', '.pkl', '.bin', '.safetensors'],
    # 数据文件
    'data': ['.csv', '.parquet', '.feather', '.db', '.sqlite'],
}

# 文件大小限制 (默认 100MB)
MAX_FILE_SIZE = settings.MAX_FILE_SIZE


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower()


def get_file_category(filename: str) -> str:
    """根据文件扩展名判断文件类别"""
    ext = get_file_extension(filename)
    for category, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return category
    return 'other'


def calculate_file_hash(file_content: bytes) -> str:
    """计算文件 SHA256 hash"""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_content)
    return sha256_hash.hexdigest()


def check_file_exists(file_hash: str) -> Optional[FileModel]:
    """检查文件是否已存在（基于 hash 去重）"""
    # 这个函数需要在数据库查询中使用
    pass


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_category: Optional[str] = Query(None, description="文件类别"),
    related_type: Optional[str] = Query(None, description="关联类型"),
    related_id: Optional[int] = Query(None, description="关联 ID"),
    is_public: bool = Query(False, description="是否公开"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传文件
    - 支持文件类型白名单校验
    - 自动计算文件 hash 用于去重
    - 支持文件关联业务对象
    """
    # 检查文件大小
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置指针

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({MAX_FILE_SIZE / 1024 / 1024:.1f}MB)"
        )

    # 检查文件扩展名
    ext = get_file_extension(file.filename)
    if not ext:
        raise HTTPException(status_code=400, detail="无法识别文件类型")

    # 检查是否在白名单中
    allowed = False
    for extensions in ALLOWED_EXTENSIONS.values():
        if ext in extensions:
            allowed = True
            break

    if not allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型：{ext}"
        )

    # 读取文件内容
    file_content = file.file.read()

    # 计算文件 hash
    file_hash = calculate_file_hash(file_content)

    # 检查文件是否已存在（去重）
    existing_file = db.query(FileModel).filter(FileModel.file_hash == file_hash).first()
    if existing_file:
        # 文件已存在，返回已有文件信息
        return existing_file

    # 生成存储文件名
    stored_name = f"{uuid.uuid4().hex}{ext}"

    # 确保上传目录存在
    upload_dir = os.path.join(settings.UPLOAD_DIR, datetime.now().strftime("%Y/%m/%d"))
    os.makedirs(upload_dir, exist_ok=True)

    # 保存文件
    file_path = os.path.join(upload_dir, stored_name)
    with open(file_path, "wb") as f:
        f.write(file_content)

    # 确定文件类别
    if not file_category:
        file_category = get_file_category(file.filename)

    # 获取文件 MIME 类型
    file_type, _ = mimetypes.guess_type(file.filename)

    # 创建文件记录
    db_file = FileModel(
        filename=file.filename,
        stored_name=stored_name,
        file_path=file_path,
        file_size=file_size,
        file_type=file_type,
        file_category=file_category,
        file_hash=file_hash,
        uploader_id=current_user.id,
        related_type=related_type,
        related_id=related_id,
        is_public=is_public,
        status="active"
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # 记录审计日志
    log_action(
        db=db,
        action="CREATE",
        resource_type="file",
        resource_id=db_file.id,
        resource_name=file.filename,
        user_id=current_user.id,
        username=current_user.username
    )

    return db_file


@router.get("/my", response_model=PaginatedResponse)
def list_my_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    file_category: Optional[str] = Query(None),
    related_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的文件列表"""
    query = db.query(FileModel).filter(
        FileModel.uploader_id == current_user.id,
        FileModel.status == "active"
    )

    if file_category:
        query = query.filter(FileModel.file_category == file_category)

    if related_type:
        query = query.filter(FileModel.related_type == related_type)

    total = query.count()
    files = query.order_by(FileModel.created_at.desc()).offset(skip).limit(limit).all()

    return PaginatedResponse.create(items=files, total=total, skip=skip, limit=limit)


@router.get("/{file_id}", response_model=FileResponse)
def get_file_info(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取文件信息"""
    file_obj = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 权限检查：只有文件上传者、admin 或公开文件可以访问
    if not file_obj.is_public and file_obj.uploader_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限访问此文件")

    return file_obj


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载文件"""
    file_obj = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 权限检查
    if not file_obj.is_public and file_obj.uploader_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限下载此文件")

    # 检查文件是否存在
    if not os.path.exists(file_obj.file_path):
        raise HTTPException(status_code=404, detail="文件已被删除")

    # 增加下载次数
    file_obj.download_count += 1
    db.commit()

    # 返回文件
    return FileResponse(
        path=file_obj.file_path,
        filename=file_obj.filename,
        media_type=file_obj.file_type
    )


@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除文件（软删除）"""
    file_obj = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 权限检查：只有文件上传者或 admin 可以删除
    if file_obj.uploader_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限删除此文件")

    # 软删除：只更新状态
    file_obj.status = "deleted"
    db.commit()

    # 记录审计日志
    log_action(
        db=db,
        action="DELETE",
        resource_type="file",
        resource_id=file_obj.id,
        resource_name=file_obj.filename,
        user_id=current_user.id,
        username=current_user.username
    )

    return {"message": "文件已删除"}


@router.get("/", response_model=PaginatedResponse)
def list_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    file_category: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取文件列表（仅公开文件，admin 可查看所有）"""
    query = db.query(FileModel).filter(FileModel.status == "active")

    # 非管理员只能查看公开文件
    if current_user.role != 'admin':
        query = query.filter(FileModel.is_public == True)

    if file_category:
        query = query.filter(FileModel.file_category == file_category)

    if keyword:
        query = query.filter(FileModel.filename.contains(keyword))

    total = query.count()
    files = query.order_by(FileModel.created_at.desc()).offset(skip).limit(limit).all()

    return PaginatedResponse.create(items=files, total=total, skip=skip, limit=limit)
