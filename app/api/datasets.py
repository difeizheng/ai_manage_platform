"""
数据集管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any

from app.core.database import get_db
from app.models.models import Dataset, User, ApplicationRequest, WorkflowRecord, WorkflowDefinition, Notification
from app.schemas.schemas import DatasetCreate, DatasetUpdate, DatasetResponse, ApplicationRequestCreate, PaginatedResponse
from app.api.auth import get_current_user, can_edit_resource, can_delete_resource

router = APIRouter()


@router.get("/")
def list_datasets(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    business_domain: Optional[str] = Query(None, description="业务领域"),
    data_type: Optional[str] = Query(None, description="数据类型"),
    source: Optional[str] = Query(None, description="数据来源"),
    status: Optional[str] = Query(None, description="状态"),
    creator: Optional[str] = Query(None, description="创建人（'me' 为当前用户）"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取数据集列表 - 支持分页和多条件过滤"""
    query = db.query(Dataset)

    # 按业务领域过滤
    if business_domain:
        query = query.filter(Dataset.business_domain == business_domain)

    # 按数据类型过滤
    if data_type:
        query = query.filter(Dataset.data_type == data_type)

    # 按数据来源过滤
    if source:
        query = query.filter(Dataset.source == source)

    # 按状态过滤
    if status:
        query = query.filter(Dataset.status == status)

    # 按创建人过滤
    if creator == 'me':
        query = query.filter(Dataset.creator_id == current_user.id)
    elif creator and creator.isdigit():
        query = query.filter(Dataset.creator_id == int(creator))

    # 关键词搜索（名称或描述）
    if keyword:
        query = query.filter(
            (Dataset.name.contains(keyword)) |
            (Dataset.description.contains(keyword))
        )

    # 获取总数
    total = query.count()

    # 分页查询
    datasets = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()

    return PaginatedResponse.create(items=datasets, total=total, skip=skip, limit=limit)


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """获取数据集详情"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return dataset


@router.post("/", response_model=DatasetResponse)
def create_dataset(
    dataset_data: DatasetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建数据集"""
    # 提取工作流定义 ID
    workflow_definition_id = dataset_data.workflow_definition_id

    # 创建数据集
    dataset_dict = dataset_data.model_dump(exclude={'workflow_definition_id'})
    initial_status = "pending" if workflow_definition_id else "approved"

    dataset = Dataset(
        **dataset_dict,
        creator_id=current_user.id,
        status=initial_status
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # 如果绑定了工作流，自动启动审核流程
    if workflow_definition_id:
        workflow_def = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == workflow_definition_id,
            WorkflowDefinition.bind_type == "dataset"
        ).first()
        if not workflow_def:
            raise HTTPException(status_code=400, detail="工作流定义不存在或与数据集类型不匹配")

        # 创建工作流记录
        nodes = workflow_def.nodes or []
        edges = workflow_def.edges or []

        # 找到第一个节点
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
            record_type="dataset",
            record_id=dataset.id,
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

        # 更新数据集状态
        dataset.status = "under_review"
        dataset.workflow_record_id = workflow_record.id
        dataset.workflow_definition_id = workflow_definition_id
        db.commit()
        db.refresh(dataset)

    return dataset


@router.put("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(
    dataset_id: int,
    dataset_data: DatasetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新数据集"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

    # 权限检查：只有创建者、admin、reviewer 可以编辑
    if not can_edit_resource(dataset, current_user, db):
        raise HTTPException(status_code=403, detail="无权限修改此数据集")

    update_data = dataset_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dataset, key, value)

    db.commit()
    db.refresh(dataset)
    return dataset


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除数据集"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

    # 权限检查：只有 admin 或创建者可以删除
    if not can_delete_resource(dataset, current_user, db):
        raise HTTPException(status_code=403, detail="无权限删除此数据集")

    db.delete(dataset)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{dataset_id}/request")
def request_dataset_access(
    dataset_id: int,
    request_data: ApplicationRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """申请数据集使用权限 - DEBUG_v2"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

    # 检查数据集是否绑定了工作流 - DEBUG
    workflow_definition_id = dataset.workflow_definition_id
    print(f"=== DEBUG request_dataset_access: dataset_id={dataset_id}, workflow_definition_id={workflow_definition_id} ===")

    request = ApplicationRequest(
        request_type="dataset",
        resource_id=dataset_id,
        resource_name=dataset.name,
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
