"""
数据看板 API - 支持数据统计与报表
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, extract, case, and_, or_
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.models.models import (
    Model, Application, Dataset, Agent, ComputeResource, User,
    WorkflowRecord, WorkflowDefinition, ApplicationRequest,
    ForumPost, AuditLog
)

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


@router.get("/workflow/stats")
def get_workflow_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db)
):
    """工作流审批统计"""
    cutoff_date = datetime.now() - timedelta(days=days)

    # 审批记录统计
    records = db.query(WorkflowRecord).filter(
        WorkflowRecord.created_at >= cutoff_date,
        WorkflowRecord.action.in_(['approve', 'reject'])
    ).all()

    total = len(records)
    approved = sum(1 for r in records if r.action == 'approve')
    rejected = sum(1 for r in records if r.action == 'reject')

    # 按工作流定义分组统计
    workflow_stats = db.query(
        WorkflowDefinition.name,
        func.count(WorkflowRecord.id).label('total'),
        func.sum(case((WorkflowRecord.action == 'approve', 1), else_=0)).label('approved'),
        func.sum(case((WorkflowRecord.action == 'reject', 1), else_=0)).label('rejected')
    ).join(
        WorkflowDefinition,
        WorkflowRecord.workflow_definition_id == WorkflowDefinition.id
    ).filter(
        WorkflowRecord.created_at >= cutoff_date,
        WorkflowRecord.action.in_(['approve', 'reject'])
    ).group_by(WorkflowDefinition.name).all()

    return {
        "period_days": days,
        "total_approvals": total,
        "approved": approved,
        "rejected": rejected,
        "approval_rate": round(approved / total * 100, 2) if total > 0 else 0,
        "by_workflow": [
            {
                "workflow": s.name,
                "total": s.total,
                "approved": s.approved,
                "rejected": s.rejected
            }
            for s in workflow_stats
        ]
    }


@router.get("/workflow/efficiency")
def get_workflow_efficiency(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db)
):
    """工作流效率分析"""
    cutoff_date = datetime.now() - timedelta(days=days)

    # 计算平均审批时长（从提交到通过的时间）
    approved_apps = db.query(Application).filter(
        Application.status == 'approved',
        Application.approved_at >= cutoff_date,
        Application.approved_at.isnot(None)
    ).all()

    durations = []
    for app in approved_apps:
        if app.created_at and app.approved_at:
            duration = (app.approved_at - app.created_at).total_seconds() / 3600  # 小时
            durations.append(duration)

    avg_duration = sum(durations) / len(durations) if durations else 0
    max_duration = max(durations) if durations else 0
    min_duration = min(durations) if durations else 0

    # 按部门统计审批时长
    dept_stats = db.query(
        Application.department,
        func.avg(
            extract('epoch', Application.approved_at) - extract('epoch', Application.created_at)
        ).label('avg_hours')
    ).filter(
        Application.status == 'approved',
        Application.approved_at >= cutoff_date,
        Application.department.isnot(None)
    ).group_by(Application.department).all()

    return {
        "period_days": days,
        "avg_duration_hours": round(avg_duration, 2),
        "max_duration_hours": round(max_duration, 2),
        "min_duration_hours": round(min_duration, 2),
        "by_department": [
            {"department": s.department, "avg_hours": round(s.avg_hours / 3600, 2) if s.avg_hours else 0}
            for s in dept_stats
        ]
    }


@router.get("/resource/stats")
def get_resource_stats(db: Session = Depends(get_db)):
    """资源使用统计"""
    # 算力资源统计
    compute_stats = db.query(
        ComputeResource.resource_type,
        func.count(ComputeResource.id).label('count'),
        func.sum(ComputeResource.total_compute).label('total_compute'),
        func.sum(ComputeResource.used_compute).label('used_compute')
    ).group_by(ComputeResource.resource_type).all()

    # 资源申请统计
    request_stats = db.query(
        ApplicationRequest.request_type,
        func.count(ApplicationRequest.id).label('total'),
        func.sum(case((ApplicationRequest.status == 'approved', 1), else_=0)).label('approved'),
        func.sum(case((ApplicationRequest.status == 'rejected', 1), else_=0)).label('rejected'),
        func.sum(case((ApplicationRequest.status == 'pending', 1), else_=0)).label('pending')
    ).group_by(ApplicationRequest.request_type).all()

    # 各部门资源分布
    dept_compute = db.query(
        ComputeResource.owner_department,
        func.count(ComputeResource.id).label('count'),
        func.sum(ComputeResource.total_compute).label('total')
    ).group_by(ComputeResource.owner_department).all()

    return {
        "compute_by_type": [
            {
                "type": s.resource_type,
                "count": s.count,
                "total_compute": s.total_compute or 0,
                "used_compute": s.used_compute or 0,
                "usage_rate": round((s.used_compute or 0) / (s.total_compute or 1) * 100, 2)
            }
            for s in compute_stats
        ],
        "requests_by_type": [
            {
                "type": s.request_type,
                "total": s.total,
                "approved": s.approved,
                "rejected": s.rejected,
                "pending": s.pending
            }
            for s in request_stats
        ],
        "compute_by_department": [
            {
                "department": s.owner_department or "未分配",
                "count": s.count,
                "total_compute": s.total or 0
            }
            for s in dept_compute
        ]
    }


@router.get("/application/stats")
def get_application_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db)
):
    """应用场景申报统计"""
    cutoff_date = datetime.now() - timedelta(days=days)

    # 按状态统计
    status_stats = db.query(
        Application.status,
        func.count(Application.id).label('count')
    ).filter(
        Application.created_at >= cutoff_date
    ).group_by(Application.status).all()

    # 按部门统计
    dept_stats = db.query(
        Application.department,
        func.count(Application.id).label('count')
    ).filter(
        Application.created_at >= cutoff_date,
        Application.department.isnot(None)
    ).group_by(Application.department).all()

    # 趋势统计（按天）
    trend_stats = db.query(
        func.date(Application.created_at).label('date'),
        func.count(Application.id).label('count')
    ).filter(
        Application.created_at >= cutoff_date
    ).group_by(func.date(Application.created_at)).order_by(func.date(Application.created_at)).all()

    return {
        "period_days": days,
        "total": sum(s.count for s in status_stats),
        "by_status": [{"status": s.status, "count": s.count} for s in status_stats],
        "by_department": [{"department": s.department or "未分配", "count": s.count} for s in dept_stats],
        "trend": [{"date": str(s.date), "count": s.count} for s in trend_stats]
    }


@router.get("/overview")
def get_overview_stats(db: Session = Depends(get_db)):
    """全局概览统计"""
    # 资源总数统计
    stats = {
        "model_count": db.query(Model).count(),
        "application_count": db.query(Application).count(),
        "dataset_count": db.query(Dataset).count(),
        "agent_count": db.query(Agent).count(),
        "user_count": db.query(User).filter(User.is_active == True).count(),
        "workflow_count": db.query(WorkflowDefinition).count(),
        "forum_posts": db.query(ForumPost).filter(ForumPost.is_deleted == False).count(),
    }

    # 待处理申请
    stats["pending_applications"] = db.query(Application).filter(
        Application.status.in_(['submitted', 'under_review'])
    ).count()

    stats["pending_requests"] = db.query(ApplicationRequest).filter(
        ApplicationRequest.status == 'pending'
    ).count()

    # 算力资源统计
    compute = db.query(
        func.sum(ComputeResource.total_compute).label("total"),
        func.sum(ComputeResource.used_compute).label("used")
    ).first()

    stats["compute_total"] = compute.total or 0.0
    stats["compute_used"] = compute.used or 0.0
    stats["compute_usage_rate"] = round((compute.used or 0) / (compute.total or 1) * 100, 2)

    return stats


@router.get("/audit-logs/stats")
def get_audit_logs_stats(
    days: int = Query(7, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db)
):
    """审计日志统计"""
    cutoff_date = datetime.now() - timedelta(days=days)

    # 按操作类型统计
    action_stats = db.query(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.created_at >= cutoff_date
    ).group_by(AuditLog.action).all()

    # 按用户统计
    user_stats = db.query(
        AuditLog.username,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.created_at >= cutoff_date,
        AuditLog.username.isnot(None)
    ).group_by(AuditLog.username).order_by(func.count(AuditLog.id).desc()).limit(10).all()

    # 按资源类型统计
    resource_stats = db.query(
        AuditLog.resource_type,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.created_at >= cutoff_date,
        AuditLog.resource_type.isnot(None)
    ).group_by(AuditLog.resource_type).all()

    return {
        "period_days": days,
        "total_actions": sum(s.count for s in action_stats),
        "by_action": [{"action": s.action, "count": s.count} for s in action_stats],
        "top_users": [{"username": s.username, "count": s.count} for s in user_stats],
        "by_resource": [{"resource_type": s.resource_type, "count": s.count} for s in resource_stats]
    }
