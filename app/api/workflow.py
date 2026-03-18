"""
业务流程管理 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import WorkflowRecord, Application, Dataset, Model, Agent, ComputeResource
from app.schemas.schemas import WorkflowRecordResponse
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[WorkflowRecordResponse])
def list_workflow_records(
    skip: int = 0,
    limit: int = 100,
    application_id: int = None,
    record_type: str = None,
    action: str = None,
    db: Session = Depends(get_db)
):
    """获取业务流程记录"""
    query = db.query(WorkflowRecord)

    if application_id:
        query = query.filter(WorkflowRecord.application_id == application_id)
    if record_type:
        query = query.filter(WorkflowRecord.record_type == record_type)
    if action:
        query = query.filter(WorkflowRecord.action == action)

    records = query.order_by(WorkflowRecord.created_at.desc()).offset(skip).limit(limit).all()
    return records


@router.get("/application/{application_id}")
def get_application_workflow(
    application_id: int,
    db: Session = Depends(get_db)
):
    """获取应用场景的完整流程"""
    # 获取应用场景
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        return {"error": "应用场景不存在"}

    # 获取相关工作流记录
    workflow_records = db.query(WorkflowRecord).filter(
        WorkflowRecord.application_id == application_id
    ).order_by(WorkflowRecord.created_at).all()

    # 获取关联的资源申请
    resource_requests = db.query(ApplicationRequest).filter(
        ApplicationRequest.related_application == application.title
    ).all()

    return {
        "application": application,
        "workflow_records": workflow_records,
        "resource_requests": resource_requests
    }


@router.get("/trace/{record_type}/{record_id}")
def trace_record(
    record_type: str,
    record_id: int,
    db: Session = Depends(get_db)
):
    """追溯资源的完整使用流程"""
    # 根据类型获取资源
    model_map = {
        "application": Application,
        "dataset": Dataset,
        "model": Model,
        "agent": Agent,
        "compute": ComputeResource
    }

    model_class = model_map.get(record_type)
    if not model_class:
        return {"error": "无效的记录类型"}

    record = db.query(model_class).filter(model_class.id == record_id).first()
    if not record:
        return {"error": "记录不存在"}

    # 获取相关工作流记录
    workflow_records = db.query(WorkflowRecord).filter(
        WorkflowRecord.record_type == record_type,
        WorkflowRecord.record_id == record_id
    ).order_by(WorkflowRecord.created_at).all()

    return {
        "record": record,
        "workflow_records": workflow_records
    }
