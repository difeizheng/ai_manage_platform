"""
数据分析与报表 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import io

from app.core.database import get_db
from app.models.models import (
    User, Model, Dataset, Agent, Application, ComputeResource,
    ApplicationRequest, WorkflowRecord, Report, ReportCache
)
from app.schemas.schemas import ReportResponse, ReportCreate, ReportUpdate, PaginatedResponse
from app.api.auth import get_current_user, require_role

router = APIRouter()


# ============ 报表管理 ============

@router.get("/reports", response_model=PaginatedResponse)
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    report_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取报表列表"""
    query = db.query(Report)

    # 非管理员只能查看公开报表或自己创建的报表
    if current_user.role != 'admin':
        query = query.filter(
            (Report.is_public == True) | (Report.created_by == current_user.id)
        )

    if report_type:
        query = query.filter(Report.report_type == report_type)

    total = query.count()
    reports = query.order_by(desc(Report.created_at)).offset(skip).limit(limit).all()

    return PaginatedResponse.create(items=reports, total=total, skip=skip, limit=limit)


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取报表详情"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")

    # 权限检查
    if not report.is_public and report.created_by != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限查看此报表")

    return report


@router.post("/reports", response_model=ReportResponse)
def create_report(
    report_data: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建报表"""
    report = Report(
        name=report_data.name,
        description=report_data.description,
        report_type=report_data.report_type,
        config=report_data.config,
        is_public=report_data.is_public,
        created_by=current_user.id
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.put("/reports/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    report_data: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新报表"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")

    # 权限检查
    if report.created_by != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限更新此报表")

    # 更新字段
    for field, value in report_data.model_dump(exclude_unset=True).items():
        setattr(report, field, value)

    db.commit()
    db.refresh(report)
    return report


@router.delete("/reports/{report_id}")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除报表"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")

    # 权限检查
    if report.created_by != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限删除此报表")

    db.delete(report)
    db.commit()

    return {"message": "报表已删除"}


@router.get("/reports/{report_id}/data")
def get_report_data(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取报表数据（动态生成）"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")

    # 权限检查
    if not report.is_public and report.created_by != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限查看此报表")

    # 根据报表类型生成数据
    config = report.config or {}
    data = generate_report_data(db, report.report_type, config)

    return {
        "report_id": report.id,
        "report_name": report.name,
        "report_type": report.report_type,
        "data": data
    }


def generate_report_data(db: Session, report_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """根据报表类型生成数据"""
    if report_type == "resource_usage":
        # 资源使用报表
        resources = db.query(ComputeResource).all()
        return {
            "items": [
                {
                    "id": r.id,
                    "name": r.name,
                    "resource_type": r.resource_type,
                    "total_compute": r.total_compute,
                    "used_compute": r.used_compute,
                    "usage_rate": (r.used_compute / r.total_compute * 100) if r.total_compute else 0
                }
                for r in resources
            ],
            "summary": {
                "total": sum(r.total_compute or 0 for r in resources),
                "used": sum(r.used_compute or 0 for r in resources)
            }
        }

    elif report_type == "application_trend":
        # 应用场景申报趋势
        days = config.get("days", 30)
        start_date = datetime.now() - timedelta(days=days)

        result = db.query(
            func.date(Application.created_at).label("date"),
            func.count(Application.id).label("count")
        ).filter(
            Application.created_at >= start_date
        ).group_by(
            func.date(Application.created_at)
        ).order_by("date").all()

        return {
            "labels": [str(r.date) for r in result],
            "values": [r.count for r in result],
            "total": sum(r.count for r in result)
        }

    elif report_type == "department_stats":
        # 部门统计
        result = db.query(
            Application.department,
            func.count(Application.id).label("application_count"),
            func.count(Dataset.id).label("dataset_count"),
            func.count(Model.id).label("model_count")
        ).outerjoin(Dataset, Application.department == Dataset.business_domain
        ).outerjoin(Model, Application.department == Model.business_scenarios[0]
        ).group_by(Application.department).all()

        return {
            "items": [
                {
                    "department": r.department or "未分配",
                    "application_count": r.application_count,
                    "dataset_count": r.dataset_count,
                    "model_count": r.model_count
                }
                for r in result
            ]
        }

    elif report_type == "workflow_stats":
        # 工作流审批统计
        result = db.query(
            WorkflowRecord.record_type,
            func.count(WorkflowRecord.id).label("count")
        ).group_by(WorkflowRecord.record_type).all()

        return {
            "labels": [r.record_type for r in result],
            "values": [r.count for r in result]
        }

    else:
        # 默认返回空数据
        return {"items": []}


# ============ 趋势分析 ============

@router.get("/trend/applications")
def get_application_trend(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("day", regex="^(day|week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """应用场景申报趋势"""
    start_date = datetime.now() - timedelta(days=days)

    if group_by == "day":
        date_trunc = func.date(Application.created_at)
    elif group_by == "week":
        date_trunc = func.date(Application.created_at)
    else:
        date_trunc = func.strftime("%Y-%m", Application.created_at)

    result = db.query(
        date_trunc.label("period"),
        func.count(Application.id).label("count")
    ).filter(
        Application.created_at >= start_date
    ).group_by("period").order_by("period").all()

    return {
        "labels": [str(r.period) for r in result],
        "values": [r.count for r in result],
        "total": sum(r.count for r in result)
    }


@router.get("/trend/models")
def get_model_trend(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """模型新增趋势"""
    start_date = datetime.now() - timedelta(days=days)

    result = db.query(
        func.date(Model.created_at).label("date"),
        func.count(Model.id).label("count")
    ).filter(
        Model.created_at >= start_date
    ).group_by("date").order_by("date").all()

    return {
        "labels": [str(r.date) for r in result],
        "values": [r.count for r in result],
        "total": sum(r.count for r in result)
    }


@router.get("/trend/datasets")
def get_dataset_trend(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """数据集新增趋势"""
    start_date = datetime.now() - timedelta(days=days)

    result = db.query(
        func.date(Dataset.created_at).label("date"),
        func.count(Dataset.id).label("count")
    ).filter(
        Dataset.created_at >= start_date
    ).group_by("date").order_by("date").all()

    return {
        "labels": [str(r.date) for r in result],
        "values": [r.count for r in result],
        "total": sum(r.count for r in result)
    }


# ============ 资源使用分析 ============

@router.get("/resource/compute-usage")
def get_compute_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """算力资源使用情况"""
    resources = db.query(ComputeResource).all()

    total_compute = sum(r.total_compute or 0 for r in resources)
    used_compute = sum(r.used_compute or 0 for r in resources)

    return {
        "total": total_compute,
        "used": used_compute,
        "available": total_compute - used_compute,
        "usage_rate": (used_compute / total_compute * 100) if total_compute else 0,
        "by_resource": [
            {
                "id": r.id,
                "name": r.name,
                "total": r.total_compute,
                "used": r.used_compute,
                "usage_rate": (r.used_compute / r.total_compute * 100) if r.total_compute else 0
            }
            for r in resources
        ]
    }


@router.get("/resource/by-department")
def get_resource_by_department(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """资源按部门分布"""
    # 应用场景按部门统计
    app_result = db.query(
        Application.department,
        func.count(Application.id).label("count")
    ).group_by(Application.department).all()

    return {
        "applications": [
            {"department": r.department or "未分配", "count": r.count}
            for r in app_result
        ]
    }


# ============ 审批效率分析 ============

@router.get("/approval/efficiency")
def get_approval_efficiency(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """审批效率统计"""
    start_date = datetime.now() - timedelta(days=days)

    # 统计已完成的审批
    result = db.query(
        WorkflowRecord.record_type,
        func.count(WorkflowRecord.id).label("count")
    ).filter(
        WorkflowRecord.created_at >= start_date
    ).group_by(WorkflowRecord.record_type).all()

    return {
        "period_days": days,
        "by_type": [
            {"type": r.record_type, "count": r.count}
            for r in result
        ],
        "total": sum(r.count for r in result)
    }


# ============ 导出功能 ============

@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: int,
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出报表数据"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")

    # 权限检查
    if not report.is_public and report.created_by != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限导出此报表")

    # 获取报表数据
    config = report.config or {}
    data = generate_report_data(db, report.report_type, config)

    if format == "json":
        return JSONResponse(
            content=data,
            headers={
                "Content-Disposition": f"attachment; filename={report.name}.json"
            }
        )
    elif format == "csv":
        # 简单 CSV 导出
        import csv
        output = io.StringIO()
        items = data.get("items", [])
        if items:
            writer = csv.DictWriter(output, fieldnames=items[0].keys())
            writer.writeheader()
            writer.writerows(items)
            csv_content = output.getvalue()

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={report.name}.csv"
            }
        )


# 添加 Response 导入
from fastapi.responses import Response
