"""
应用广场 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.models import AppStoreItem, User, WorkflowRecord, WorkflowDefinition
from app.schemas.schemas import AppStoreItemCreate, AppStoreItemResponse
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[AppStoreItemResponse])
def list_app_store_items(
    skip: int = 0,
    limit: int = 100,
    category: str = None,
    business_domain: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """获取应用广场列表"""
    query = db.query(AppStoreItem)

    if category:
        query = query.filter(AppStoreItem.category == category)
    if business_domain:
        query = query.filter(AppStoreItem.business_domain == business_domain)
    if status:
        query = query.filter(AppStoreItem.status == status)
    else:
        # 默认只显示已发布的应用
        query = query.filter(AppStoreItem.status == "published")

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
    # 提取工作流定义 ID
    workflow_definition_id = item_data.workflow_definition_id

    # 创建应用 - 使用 dict 解包方式设置 developer
    item_dict = item_data.model_dump(exclude={'workflow_definition_id', 'developer'})
    item = AppStoreItem(
        **item_dict,
        developer=current_user.real_name or current_user.username,
        status="pending" if workflow_definition_id else "published"
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # 如果绑定了工作流，自动启动审核流程
    if workflow_definition_id:
        workflow_def = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == workflow_definition_id,
            WorkflowDefinition.bind_type == "app_store"
        ).first()
        if not workflow_def:
            raise HTTPException(status_code=400, detail="工作流定义不存在或与应用类型不匹配")

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
            record_type="app_store",
            record_id=item.id,
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

        item.status = "under_review"
        item.workflow_record_id = workflow_record.id
        item.workflow_definition_id = workflow_definition_id
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


def _get_next_node_id(nodes, current_node_id, edges):
    """获取下一个节点的 ID（跳过条件边）"""
    for edge in edges:
        if edge.get('source') == current_node_id:
            # 跳过条件边
            if edge.get('condition'):
                continue
            return edge.get('target')
    return None
