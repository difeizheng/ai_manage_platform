"""
资源申请 API - 数据/模型/智能体/算力资源的申请
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import ApplicationRequest, User, WorkflowDefinition, WorkflowRecord, Notification
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/")
def list_application_requests(
    request_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取资源申请列表"""
    query = db.query(ApplicationRequest)

    # 普通用户只能查看自己的申请
    if current_user.role not in ['admin', 'reviewer']:
        query = query.filter(ApplicationRequest.applicant_id == current_user.id)

    if request_type:
        query = query.filter(ApplicationRequest.request_type == request_type)
    if status:
        query = query.filter(ApplicationRequest.status == status)

    total = query.count()
    requests = query.order_by(ApplicationRequest.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": requests, "total": total}


@router.get("/my")
def list_my_application_requests(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的资源申请列表"""
    query = db.query(ApplicationRequest).filter(ApplicationRequest.applicant_id == current_user.id)
    total = query.count()
    requests = query.order_by(ApplicationRequest.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": requests, "total": total}


@router.get("/{req_id}")
def get_application_request(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取资源申请详情"""
    request_item = db.query(ApplicationRequest).filter(ApplicationRequest.id == req_id).first()
    if not request_item:
        raise HTTPException(status_code=404, detail="申请记录不存在")

    # 权限检查
    if current_user.role not in ['admin', 'reviewer'] and request_item.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看")

    return request_item


@router.post("/")
async def create_application_request(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建资源申请"""
    data = await request.json()

    request_item = ApplicationRequest(
        request_type=data.get('request_type'),  # dataset, model, agent, compute
        resource_id=data.get('resource_id'),
        resource_name=data.get('resource_name'),
        applicant_id=current_user.id,
        applicant_department=data.get('applicant_department', current_user.department),
        purpose=data.get('purpose'),
        expected_duration=data.get('expected_duration'),
        expected_frequency=data.get('expected_frequency'),
        related_application=data.get('related_application'),
        workflow_definition_id=data.get('workflow_definition_id')
    )

    db.add(request_item)
    db.commit()
    db.refresh(request_item)

    # 如果绑定了工作流，启动工作流
    if data.get('workflow_definition_id'):
        workflow_def = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == data.get('workflow_definition_id')
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
                record_id=request_item.id,
                action=start_node.get('type'),
                actor_id=current_user.id,
                description=start_node.get('name'),
                node_status='completed'
            )
            db.add(workflow_record)
            db.commit()
            db.refresh(workflow_record)

            request_item.workflow_record_id = workflow_record.id

            # 获取下一个节点
            edges = workflow_def.edges or []
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
                        content=f"您有一个待审批的资源申请\n申请人：{current_user.real_name or current_user.username}\n资源名称：{request_item.resource_name}\n申请用途：{request_item.purpose or '无'}",
                        type="workflow",
                        related_type="workflow_record",
                        related_id=workflow_record.id
                    )
                    db.add(notification)

                request_item.status = "under_review"

            db.commit()
            db.refresh(request_item)

    return request_item


def get_next_node(nodes, current_node_id, edges):
    """获取下一个节点"""
    for edge in edges:
        if edge.get('source') == current_node_id:
            if edge.get('condition'):
                continue
            next_node_id = edge.get('target')
            next_node = next((n for n in nodes if n.get('id') == next_node_id), None)
            if next_node:
                return {"next_node": next_node, "action": "proceed"}
    return {"next_node": None, "action": "complete"}


def get_approver_users(node_config, db, current_user=None, application=None):
    """根据节点配置获取审核人用户列表"""
    approver = node_config.get('approver')
    if not approver:
        return []

    from app.models.models import Role, UserRole

    # 部门负责人
    if approver == 'department_head':
        if not current_user or not current_user.department:
            return []
        dept_managers = db.query(User).filter(
            User.department == current_user.department,
            User.is_department_manager == True,
            User.is_active == True
        ).all()
        if dept_managers:
            return dept_managers
        manager_role = db.query(Role).filter(Role.code == 'department_manager').first()
        if manager_role:
            user_roles = db.query(UserRole).filter(UserRole.role_id == manager_role.id).all()
            user_ids = [ur.user_id for ur in user_roles]
            users = db.query(User).filter(
                User.id.in_(user_ids),
                User.department == current_user.department,
                User.is_active == True
            ).all()
            return users if users else []
        return []

    # 根据角色 code 查找用户
    role = db.query(Role).filter(Role.code == approver).first()
    if not role:
        return []

    user_roles = db.query(UserRole).filter(UserRole.role_id == role.id).all()
    user_ids = [ur.user_id for ur in user_roles]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    return users


@router.post("/{req_id}/review")
def review_application_request(
    req_id: int,
    approved: bool,
    comments: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """审批资源申请（简单审批模式，不通过工作流）"""
    if current_user.role not in ['admin', 'reviewer']:
        raise HTTPException(status_code=403, detail="权限不足")

    request_item = db.query(ApplicationRequest).filter(ApplicationRequest.id == req_id).first()
    if not request_item:
        raise HTTPException(status_code=404, detail="申请记录不存在")

    # 如果绑定了工作流，不能直接审批
    if request_item.workflow_definition_id:
        raise HTTPException(status_code=400, detail="该申请已绑定工作流，请在工作流中审批")

    request_item.status = "approved" if approved else "rejected"
    request_item.review_comments = comments
    request_item.reviewer_id = current_user.id
    request_item.approved_at = datetime.now()

    # 创建通知
    notification = Notification(
        user_id=request_item.applicant_id,
        title="资源申请审批结果",
        content=f"您的{request_item.resource_name}申请已{'通过' if approved else '拒绝'}。\n审批意见：{comments or ''}",
        type="workflow",
        related_type="application_request",
        related_id=request_item.id
    )
    db.add(notification)
    db.commit()

    return {"message": "审批成功" if approved else "审批拒绝"}
