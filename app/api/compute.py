"""
算力资源管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import ComputeResource, User, ApplicationRequest, WorkflowRecord, WorkflowDefinition, Notification
from app.schemas.schemas import ComputeResourceCreate, ComputeResourceResponse, ApplicationRequestCreate, PaginatedResponse
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/")
def list_compute_resources(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    status: Optional[str] = Query(None, description="状态"),
    owner_department: Optional[str] = Query(None, description="所属部门"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """获取算力资源列表 - 支持分页和多条件过滤"""
    query = db.query(ComputeResource)

    # 按资源类型过滤
    if resource_type:
        query = query.filter(ComputeResource.resource_type == resource_type)

    # 按状态过滤
    if status:
        query = query.filter(ComputeResource.status == status)

    # 按所属部门过滤
    if owner_department:
        query = query.filter(ComputeResource.owner_department == owner_department)

    # 关键词搜索（名称或型号）
    if keyword:
        query = query.filter(
            (ComputeResource.name.contains(keyword)) |
            (ComputeResource.model_name.contains(keyword))
        )

    # 获取总数
    total = query.count()

    # 分页查询
    resources = query.order_by(ComputeResource.created_at.desc()).offset(skip).limit(limit).all()

    return PaginatedResponse.create(items=resources, total=total, skip=skip, limit=limit)


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
    """申请算力资源使用权限 - 支持工作流审批"""
    resource = db.query(ComputeResource).filter(ComputeResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="算力资源不存在")

    # 检查算力资源是否绑定了工作流
    workflow_definition_id = resource.workflow_definition_id

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
        workflow_definition_id=workflow_definition_id,  # 绑定工作流
        status="under_review" if workflow_definition_id else "pending"
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    # 如果绑定了工作流，启动工作流
    if workflow_definition_id:
        workflow_def = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == workflow_definition_id
        ).first()

        if workflow_def:
            # 创建工作流记录
            nodes = workflow_def.nodes or []
            start_node = next((n for n in nodes if n.get('type') in ['start', 'submit']), None)
            if not start_node:
                start_node = {'id': 'node_1', 'type': 'submit', 'name': '提交'}

            workflow_record = WorkflowRecord(
                workflow_definition_id=workflow_def.id,
                current_node_id=start_node.get('id'),
                record_type='application_request',
                record_id=request.id,
                action=start_node.get('type'),
                actor_id=current_user.id,
                description=start_node.get('name'),
                node_status='completed'
            )
            db.add(workflow_record)
            db.commit()
            db.refresh(workflow_record)

            request.workflow_record_id = workflow_record.id

            # 获取下一个节点
            edges = workflow_def.edges or []
            from app.api.application_requests import get_next_node, get_approver_users
            next_node_info = get_next_node(nodes, start_node.get('id'), edges)
            next_node = next_node_info.get('next_node')

            if next_node and next_node.get('type') in ['review', 'approve']:
                workflow_record.current_node_id = next_node.get('id')

                # 获取审核人并发送通知
                approvers = get_approver_users(next_node.get('config', {}), db, current_user, None)

                for approver in approvers:
                    notification = Notification(
                        user_id=approver.id,
                        title=f"待办审批：{workflow_def.name} - {next_node.get('name')}",
                        content=f"您有一个待审批的资源申请\n申请人：{current_user.real_name or current_user.username}\n资源名称：{request.resource_name}\n申请用途：{request.purpose or '无'}",
                        type="workflow",
                        related_type="workflow_record",
                        related_id=workflow_record.id
                    )
                    db.add(notification)

                db.commit()

    return {"message": "申请已提交，等待审批", "request_id": request.id}


def _get_next_node_id(nodes, current_node_id, edges):
    """获取下一个节点的 ID（跳过条件边）"""
    for edge in edges:
        if edge.get('source') == current_node_id:
            # 跳过条件边
            if edge.get('condition'):
                continue
            return edge.get('target')
    return None
