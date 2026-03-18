"""
数据看板 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.models import Model, Application, Dataset, Agent, ComputeResource, User

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取仪表盘统计数据"""
    stats = {
        "model_count": db.query(Model).count(),
        "application_count": db.query(Application).count(),
        "dataset_count": db.query(Dataset).count(),
        "agent_count": db.query(Agent).count(),
        "user_count": db.query(User).filter(User.is_active == True).count(),
    }

    # 算力资源统计
    compute_resources = db.query(
        func.sum(ComputeResource.total_compute).label("total"),
        func.sum(ComputeResource.used_compute).label("used")
    ).first()

    stats["compute_total"] = compute_resources.total or 0.0
    stats["compute_used"] = compute_resources.used or 0.0

    return stats


@router.get("/models/chart")
def get_models_chart(db: Session = Depends(get_db)):
    """模型类型分布"""
    from sqlalchemy import distinct

    # 按模型类型统计
    result = db.query(
        Model.model_type,
        func.count(Model.id).label("count")
    ).group_by(Model.model_type).all()

    return {
        "labels": [r.model_type or "未分类" for r in result],
        "values": [r.count for r in result]
    }


@router.get("/applications/chart")
def get_applications_chart(db: Session = Depends(get_db)):
    """应用场景按部门分布"""
    result = db.query(
        Application.department,
        func.count(Application.id).label("count")
    ).group_by(Application.department).all()

    return {
        "labels": [r.department or "未分配" for r in result],
        "values": [r.count for r in result]
    }


@router.get("/datasets/chart")
def get_datasets_chart(db: Session = Depends(get_db)):
    """数据集按业务领域分布"""
    result = db.query(
        Dataset.business_domain,
        func.count(Dataset.id).label("count")
    ).group_by(Dataset.business_domain).all()

    return {
        "labels": [r.business_domain or "未分类" for r in result],
        "values": [r.count for r in result]
    }


@router.get("/recent/applications")
def get_recent_applications(db: Session = Depends(get_db)):
    """最近的应用场景申报"""
    applications = db.query(Application).order_by(
        Application.created_at.desc()
    ).limit(5).all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "department": a.department,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in applications
    ]


@router.get("/recent/models")
def get_recent_models(db: Session = Depends(get_db)):
    """最近的模型"""
    models = db.query(Model).order_by(
        Model.created_at.desc()
    ).limit(5).all()

    return [
        {
            "id": m.id,
            "name": m.name,
            "model_type": m.model_type,
            "version": m.version,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in models
    ]
