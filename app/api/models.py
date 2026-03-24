"""
模型管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any
import os
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Model, User, ApplicationRequest, WorkflowRecord, WorkflowDefinition, Notification
from app.schemas.schemas import ModelCreate, ModelUpdate, ModelResponse, ApplicationRequestCreate, PaginatedResponse
from app.api.auth import get_current_user, can_edit_resource, can_delete_resource

router = APIRouter()


@router.get("/")
def list_models(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    model_type: Optional[str] = Query(None, description="模型类型"),
    framework: Optional[str] = Query(None, description="框架"),
    status: Optional[str] = Query(None, description="状态"),
    creator: Optional[str] = Query(None, description="创建人（'me' 为当前用户）"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模型列表 - 支持分页和多条件过滤"""
    query = db.query(Model)

    # 按模型类型过滤
    if model_type:
        query = query.filter(Model.model_type == model_type)

    # 按框架过滤
    if framework:
        query = query.filter(Model.framework == framework)

    # 按状态过滤
    if status:
        query = query.filter(Model.status == status)

    # 按创建人过滤
    if creator == 'me':
        query = query.filter(Model.creator_id == current_user.id)
    elif creator and creator.isdigit():
        query = query.filter(Model.creator_id == int(creator))

    # 关键词搜索（名称或描述）
    if keyword:
        query = query.filter(
            (Model.name.contains(keyword)) |
            (Model.description.contains(keyword))
        )

    # 获取总数
    total = query.count()

    # 分页查询
    models = query.order_by(Model.created_at.desc()).offset(skip).limit(limit).all()

    return PaginatedResponse.create(items=models, total=total, skip=skip, limit=limit)


@router.get("/{model_id}", response_model=ModelResponse)
def get_model(model_id: int, db: Session = Depends(get_db)):
    """获取模型详情"""
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model


@router.post("/", response_model=ModelResponse)
def create_model(
    name: str = Form(...),
    description: str = Form(None),
    model_type: str = Form(None),
    framework: str = Form(None),
    business_scenarios: str = Form(None),
    workflow_definition_id: int = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    source_file: UploadFile = File(None)
):
    """创建/上传模型"""
    import json
    from datetime import datetime

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

    # 创建模型
    model = Model(
        name=name,
        description=description,
        model_type=model_type,
        framework=framework,
        business_scenarios=parse_json(business_scenarios),
        creator_id=current_user.id,
        source_file_path=source_file_path,
        status="pending" if workflow_definition_id else "approved"
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    # 如果绑定了工作流，自动启动审核流程
    if workflow_definition_id:
        workflow_def = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == workflow_definition_id,
            WorkflowDefinition.bind_type == "model"
        ).first()
        if not workflow_def:
            raise HTTPException(status_code=400, detail="工作流定义不存在或与模型类型不匹配")

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
            record_type="model",
            record_id=model.id,
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

        model.status = "under_review"
        model.workflow_record_id = workflow_record.id
        model.workflow_definition_id = workflow_definition_id
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

    # 权限检查：只有创建者、admin、reviewer 可以编辑
    if not can_edit_resource(model, current_user, db):
        raise HTTPException(status_code=403, detail="无权限修改此模型")

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

    # 权限检查：只有 admin 或创建者可以删除
    if not can_delete_resource(model, current_user, db):
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
    """申请模型使用权限 - 支持工作流审批"""
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 检查模型是否绑定了工作流
    workflow_definition_id = model.workflow_definition_id

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
