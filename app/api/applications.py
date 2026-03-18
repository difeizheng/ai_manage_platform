"""
应用场景 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import Application, User, WorkflowRecord, WorkflowDefinition
from app.schemas.schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[ApplicationResponse])
def list_applications(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    department: str = None,
    db: Session = Depends(get_db)
):
    """获取应用场景列表"""
    query = db.query(Application)

    if status:
        query = query.filter(Application.status == status)
    if department:
        query = query.filter(Application.department == department)

    applications = query.offset(skip).limit(limit).all()
    return applications


@router.get("/{app_id}", response_model=ApplicationResponse)
def get_application(app_id: int, db: Session = Depends(get_db)):
    """获取应用场景详情"""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="应用场景不存在")
    return application


@router.post("/", response_model=ApplicationResponse)
def create_application(
    app_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建应用场景申报"""
    application = Application(
        **app_data.model_dump(),
        applicant_id=current_user.id,
        status="submitted"
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    # 检查工作流绑定
    workflow_def_id = app_data.workflow_definition_id
    workflow_def = None
    if workflow_def_id:
        workflow_def = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_def_id).first()

    if workflow_def and workflow_def.nodes:
        # 使用自定义工作流
        nodes = workflow_def.nodes
        first_node = nodes[0] if nodes else None
        if first_node:
            workflow = WorkflowRecord(
                workflow_definition_id=workflow_def_id,
                application_id=application.id,
                current_node_id=first_node.get('id'),
                record_type="application",
                record_id=application.id,
                action=first_node.get('type', 'submit'),
                actor_id=current_user.id,
                description=f"提应用场景申报：{application.title} - 工作流：{workflow_def.name}",
                node_status='pending'
            )
    else:
        # 使用默认工作流
        workflow = WorkflowRecord(
            application_id=application.id,
            record_type="application",
            record_id=application.id,
            action="apply",
            actor_id=current_user.id,
            description=f"提交应用场景申报：{application.title}"
        )

    db.add(workflow)
    db.commit()

    return application


@router.put("/{app_id}", response_model=ApplicationResponse)
def update_application(
    app_id: int,
    app_data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新应用场景"""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="应用场景不存在")

    # 权限检查
    if application.applicant_id != current_user.id and current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="无权限修改此应用场景")

    update_data = app_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(application, key, value)

    db.commit()
    db.refresh(application)
    return application


@router.post("/{app_id}/review")
def review_application(
    app_id: int,
    approved: bool,
    comments: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """审核应用场景"""
    if current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="无权限审核")

    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="应用场景不存在")

    application.status = "approved" if approved else "rejected"
    application.review_comments = comments
    application.reviewer_id = current_user.id

    db.commit()

    # 创建工作流记录
    workflow = WorkflowRecord(
        application_id=app_id,
        record_type="application",
        record_id=app_id,
        action="review" if not approved else "approve",
        actor_id=current_user.id,
        description=f"审核应用场景：{'通过' if approved else '拒绝'} - {comments or ''}"
    )
    db.add(workflow)
    db.commit()

    return {"message": "审核成功" if approved else "审核拒绝"}


@router.delete("/{app_id}")
def delete_application(
    app_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除应用场景"""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="应用场景不存在")

    if application.applicant_id != current_user.id and current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="无权限删除此应用场景")

    db.delete(application)
    db.commit()
    return {"message": "删除成功"}
