"""
算力资源管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import ComputeResource, User, ApplicationRequest
from app.schemas.schemas import ComputeResourceCreate, ComputeResourceResponse, ApplicationRequestCreate
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[ComputeResourceResponse])
def list_compute_resources(
    skip: int = 0,
    limit: int = 100,
    resource_type: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """获取算力资源列表"""
    query = db.query(ComputeResource)

    if resource_type:
        query = query.filter(ComputeResource.resource_type == resource_type)
    if status:
        query = query.filter(ComputeResource.status == status)

    resources = query.offset(skip).limit(limit).all()
    return resources


@router.get("/{resource_id}", response_model=ComputeResourceResponse)
def get_compute_resource(resource_id: int, db: Session = Depends(get_db)):
    """获取算力资源详情"""
    resource = db.query(ComputeResource).filter(ComputeResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="算力资源不存在")
    return resource


@router.post("/", response_model=ComputeResourceResponse)
def create_compute_resource(
    resource_data: ComputeResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加算力资源"""
    resource = ComputeResource(
        **resource_data.model_dump(),
        status="available"
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.put("/{resource_id}", response_model=ComputeResourceResponse)
def update_compute_resource(
    resource_id: int,
    resource_data: ComputeResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新算力资源"""
    resource = db.query(ComputeResource).filter(ComputeResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="算力资源不存在")

    update_data = resource_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(resource, key, value)

    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/{resource_id}")
def delete_compute_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除算力资源"""
    resource = db.query(ComputeResource).filter(ComputeResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="算力资源不存在")

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限删除此资源")

    db.delete(resource)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{resource_id}/request")
def request_compute_resource(
    resource_id: int,
    request_data: ApplicationRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """申请算力资源使用权限"""
    resource = db.query(ComputeResource).filter(ComputeResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="算力资源不存在")

    request = ApplicationRequest(
        request_type="compute",
        resource_id=resource_id,
        resource_name=resource.name,
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
