"""
数据集管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.models import Dataset, User, ApplicationRequest, WorkflowRecord, WorkflowDefinition
from app.schemas.schemas import DatasetCreate, DatasetUpdate, DatasetResponse, ApplicationRequestCreate
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[DatasetResponse])
def list_datasets(
    skip: int = 0,
    limit: int = 100,
    business_domain: str = None,
    data_type: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """获取数据集列表"""
    query = db.query(Dataset)

    if business_domain:
        query = query.filter(Dataset.business_domain == business_domain)
    if data_type:
        query = query.filter(Dataset.data_type == data_type)
    if status:
        query = query.filter(Dataset.status == status)

    datasets = query.offset(skip).limit(limit).all()
    return datasets


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

    if dataset.creator_id != current_user.id and current_user.role != "admin":
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
    """申请数据集使用权限"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

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
