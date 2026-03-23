"""
算力资源管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.models import ComputeResource, User, ApplicationRequest, WorkflowRecord, WorkflowDefinition
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
    from datetime import datetime

    # 提取工作流定义 ID
    workflow_definition_id = resource_data.workflow_definition_id

    # 创建算力资源
    resource_dict = resource_data.model_dump(exclude={'workflow_definition_id'})
    resource = ComputeResource(
        **resource_dict,
        status="pending" if workflow_definition_id else "available"
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # 如果绑定了工作流，自动启动审核流程
    if workflow_definition_id:
        workflow_def = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == workflow_definition_id,
            WorkflowDefinition.bind_type == "compute_resource"
        ).first()
        if not workflow_def:
            raise HTTPException(status_code=400, detail="工作流定义不存在或与算力资源类型不匹配")

        nodes = workflow_def.nodes or []
        edges = workflow_def.edges or []

        start_node = None
        for node in nodes:
            if node.get('type') in ['start', 'submit']:
                start_node = node
                break
        if not start_node:
            start_node = nodes[0] if nodes else {'id': 'node_1', 'type': 'submit', 'name': '提交'}

        workflow_record = WorkflowRecord(
            workflow_definition_id=workflow_definition_id,
            current_node_id=start_node.get('id'),
            record_type="compute_resource",
            record_id=resource.id,
            action=start_node.get('type'),
            actor_id=current_user.id,
            description=start_node.get('name'),
            node_status='completed'
        )
        db.add(workflow_record)
        db.commit()  # 先提交 workflow_record 以生成 ID

        # 获取下一个节点（审核节点）
        next_node_id = _get_next_node_id(nodes, start_node.get('id'), edges)
        if next_node_id:
            workflow_record.current_node_id = next_node_id
            db.commit()

        resource.status = "under_review"
        resource.workflow_record_id = workflow_record.id
        resource.workflow_definition_id = workflow_definition_id
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


def _get_next_node_id(nodes, current_node_id, edges):
    """获取下一个节点的 ID（跳过条件边）"""
    for edge in edges:
        if edge.get('source') == current_node_id:
            # 跳过条件边
            if edge.get('condition'):
                continue
            return edge.get('target')
    return None
