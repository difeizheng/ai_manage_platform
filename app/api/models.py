"""
模型管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Model, User, ApplicationRequest
from app.schemas.schemas import ModelCreate, ModelUpdate, ModelResponse, ApplicationRequestCreate
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[ModelResponse])
def list_models(
    skip: int = 0,
    limit: int = 100,
    model_type: str = None,
    framework: str = None,
    db: Session = Depends(get_db)
):
    """获取模型列表"""
    query = db.query(Model)

    if model_type:
        query = query.filter(Model.model_type == model_type)
    if framework:
        query = query.filter(Model.framework == framework)

    models = query.offset(skip).limit(limit).all()
    return models


@router.get("/{model_id}", response_model=ModelResponse)
def get_model(model_id: int, db: Session = Depends(get_db)):
    """获取模型详情"""
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model


@router.post("/", response_model=ModelResponse)
def create_model(
    name: str,
    description: str = None,
    model_type: str = None,
    framework: str = None,
    business_scenarios: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    source_file: UploadFile = File(None)
):
    """创建/上传模型"""
    import json

    # 处理文件上传
    source_file_path = None
    if source_file:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        source_file_path = f"{settings.UPLOAD_DIR}/{source_file.filename}"
        with open(source_file_path, "wb") as f:
            f.write(source_file.file.read())

    # 解析 JSON 字段
    def parse_json(field):
        if field:
            try:
                return json.loads(field)
            except:
                return None
        return None

    model = Model(
        name=name,
        description=description,
        model_type=model_type,
        framework=framework,
        business_scenarios=parse_json(business_scenarios),
        creator_id=current_user.id,
        source_file_path=source_file_path,
        status="available"
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.put("/{model_id}", response_model=ModelResponse)
def update_model(
    model_id: int,
    model_data: ModelUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新模型"""
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    update_data = model_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(model, key, value)

    db.commit()
    db.refresh(model)
    return model


@router.delete("/{model_id}")
def delete_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除模型"""
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    if model.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限删除此模型")

    # 删除文件
    if model.source_file_path and os.path.exists(model.source_file_path):
        os.remove(model.source_file_path)

    db.delete(model)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{model_id}/request")
def request_model_access(
    model_id: int,
    request_data: ApplicationRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """申请模型使用权限"""
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    request = ApplicationRequest(
        request_type="model",
        resource_id=model_id,
        resource_name=model.name,
        applicant_id=current_user.id,
        applicant_department=current_user.department,
        purpose=request_data.purpose,
        expected_duration=request_data.expected_duration,
        expected_frequency=request_data.expected_frequency,
        related_application=request_data.related_application,
        status="pending"
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return {"message": "申请已提交", "request_id": request.id}
