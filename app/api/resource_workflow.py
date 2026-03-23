"""
资源工作流审核 API - 支持数据集/模型/智能体/应用广场/算力资源的审核流程
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.models import (
    User, WorkflowDefinition, WorkflowRecord, Notification,
    Dataset, Model, Agent, AppStoreItem, ComputeResource, Role, UserRole
)
from app.api.auth import get_current_user

router = APIRouter()


# 资源类型映射
RESOURCE_TYPES = {
    "dataset": Dataset,
    "model": Model,
    "agent": Agent,
    "app_store": AppStoreItem,
    "compute_resource": ComputeResource
}


@router.get("/resource-approvals/my")
def get_my_resource_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的待办资源审批列表
    返回数据集/模型/智能体/应用广场/算力资源的待审批列表
    """
    result = []

    # 查找发送给当前用户的通知
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        Notification.type == "workflow",
        Notification.related_type == "workflow_record"
    ).all()

    seen_records = set()

    for notif in notifications:
        if not notif.related_id:
            continue

        record = db.query(WorkflowRecord).filter(WorkflowRecord.id == notif.related_id).first()
        if not record or not record.workflow_definition_id:
            continue

        if record.id in seen_records:
            continue
        seen_records.add(record.id)

        # 获取工作流定义
        definition = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == record.workflow_definition_id
        ).first()
        if not definition:
            continue

        # 根据资源类型获取资源信息
        resource_type = record.record_type
        resource_model = RESOURCE_TYPES.get(resource_type)
        if not resource_model:
            continue

        resource = db.query(resource_model).filter(resource_model.id == record.record_id).first()
        if not resource:
            continue

        # 获取提交人信息
        actor = db.query(User).filter(User.id == record.actor_id).first()

        # 获取当前节点信息
        nodes = definition.nodes or []
        current_node = next((n for n in nodes if n.get('id') == record.current_node_id), None)

        result.append({
            "workflow_record": record,
            "workflow_definition": definition,
            "current_node": current_node,
            "resource": resource,
            "resource_type": resource_type,
            "actor": actor
        })

    return result


@router.post("/resource/{resource_type}/{resource_id}/start-workflow")
async def start_resource_workflow(
    resource_type: str,
    resource_id: int,
    workflow_definition_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    为资源启动工作流审核流程
    资源类型：dataset, model, agent, app_store, compute_resource
    """
    # 验证资源类型
    resource_model = RESOURCE_TYPES.get(resource_type)
    if not resource_model:
        raise HTTPException(status_code=400, detail=f"不支持的资源类型：{resource_type}")

    # 获取资源
    resource = db.query(resource_model).filter(resource_model.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    # 获取工作流定义
    definition = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.id == workflow_definition_id
    ).first()
    if not definition:
        raise HTTPException(status_code=404, detail="工作流定义不存在")

    # 检查工作流是否绑定到该资源类型
    if definition.bind_type != resource_type:
        raise HTTPException(status_code=400, detail="工作流与资源类型不匹配")

    # 获取节点和边
    nodes = definition.nodes or []
    edges = definition.edges or []

    # 找到第一个节点
    start_node = None
    for node in nodes:
        if node.get('type') in ['start', 'submit']:
            start_node = node
            break

    if not start_node:
        start_node = nodes[0] if nodes else {'id': 'node_1', 'type': 'submit', 'name': '提交'}

    # 创建工作流记录
    workflow_record = WorkflowRecord(
        workflow_definition_id=workflow_definition_id,
        current_node_id=start_node.get('id'),
        record_type=resource_type,
        record_id=resource_id,
        action=start_node.get('type'),
        actor_id=current_user.id,
        description=start_node.get('name'),
        node_status='completed'
    )
    db.add(workflow_record)

    # 更新资源状态
    resource.status = "under_review"
    resource.workflow_record_id = workflow_record.id

    # 获取下一个节点（审核节点）
    next_node_info = get_next_node(nodes, start_node.get('id'), edges)
    next_node = next_node_info.get('next_node')

    # 获取审核人列表并创建通知
    approvers = []
    if next_node and next_node.get('type') in ['review', 'approve']:
        workflow_record.current_node_id = next_node.get('id')

        approvers = get_approver_users(next_node.get('config', {}), db, current_user)

        # 获取资源名称
        resource_name = resource.name

        # 为每个审核人创建站内通知
        for approver in approvers:
            notification = Notification(
                user_id=approver.id,
                title=f"待办审批：{definition.name} - {next_node.get('name')}",
                content=f"您有一个待审批的{resource_type}：{resource_name}\n"
                        f"提交人：{current_user.real_name or current_user.username}\n"
                        f"提交时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                type="workflow",
                related_type="workflow_record",
                related_id=workflow_record.id
            )
            db.add(notification)

    db.commit()

    return {
        "workflow_record": workflow_record,
        "next_node": next_node,
        "approvers": approvers,
        "message": f"流程已启动，已通知 {len(approvers)} 位审核人"
    }


@router.post("/approval/{workflow_record_id}/action")
async def perform_resource_approval_action(
    workflow_record_id: int,
    action: str,  # 'approve' or 'reject'
    comments: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    执行资源审核操作（通过/拒绝）并移动到下一个节点
    """
    # 获取当前流程记录
    workflow_record = db.query(WorkflowRecord).filter(
        WorkflowRecord.id == workflow_record_id
    ).first()
    if not workflow_record:
        raise HTTPException(status_code=404, detail="流程记录不存在")

    definition = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.id == workflow_record.workflow_definition_id
    ).first()
    if not definition:
        raise HTTPException(status_code=404, detail="工作流定义不存在")

    nodes = definition.nodes or []
    edges = definition.edges or []

    # 获取当前节点
    current_node = next((n for n in nodes if n.get('id') == workflow_record.current_node_id), None)
    if not current_node:
        raise HTTPException(status_code=404, detail="当前节点不存在")

    # 获取资源
    resource_model = RESOURCE_TYPES.get(workflow_record.record_type)
    if not resource_model:
        raise HTTPException(status_code=400, detail=f"不支持的资源类型：{workflow_record.record_type}")

    resource = db.query(resource_model).filter(resource_model.id == workflow_record.record_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    # 创建工作流操作记录
    action_record = WorkflowRecord(
        workflow_definition_id=definition.id,
        current_node_id=workflow_record.current_node_id,
        record_type=workflow_record.record_type,
        record_id=workflow_record.record_id,
        action=action,
        actor_id=current_user.id,
        description=f"{current_user.real_name or current_user.username}: {action} - {comments}",
        node_status='completed'
    )
    db.add(action_record)

    # 获取下一个节点
    next_node = None
    if action == 'reject':
        # 拒绝时查找拒绝路径
        for edge in edges:
            if edge.get('source') == workflow_record.current_node_id and edge.get('condition') == 'reject':
                next_node = next((n for n in nodes if n.get('id') == edge.get('target')), None)
                break
        # 如果没有拒绝路径，流程结束，更新资源状态为拒绝
        if not next_node:
            resource.status = "rejected"
            resource.review_comments = comments
            resource.reviewer_id = current_user.id
            resource.workflow_record_id = None
            db.commit()
            return {"message": "已拒绝，流程结束", "next_node": None}
    else:
        # 通过时查找正常路径
        next_node_info = get_next_node(nodes, workflow_record.current_node_id, edges)
        next_node = next_node_info.get('next_node')

    # 如果有下一个节点，创建通知
    if next_node:
        workflow_record.current_node_id = next_node.get('id')

        # 如果下一个节点是审核节点，通知审核人
        if next_node.get('type') in ['review', 'approve']:
            approvers = get_approver_users(next_node.get('config', {}), db, current_user)

            resource_name = resource.name

            for approver in approvers:
                notification = Notification(
                    user_id=approver.id,
                    title=f"待办审批：{definition.name} - {next_node.get('name')}",
                    content=f"您有一个待审批的{workflow_record.record_type}：{resource_name}\n"
                            f"提交人：{current_user.real_name or current_user.username}\n"
                            f"审批意见：{comments if comments else '无'}\n"
                            f"操作时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    type="workflow",
                    related_type="workflow_record",
                    related_id=workflow_record.id
                )
                db.add(notification)
    else:
        # 没有下一个节点，流程完成，更新资源状态为通过
        resource.status = "approved"
        resource.review_comments = comments
        resource.reviewer_id = current_user.id
        resource.approved_at = datetime.now()
        resource.workflow_record_id = None

    db.commit()

    return {
        "message": f"操作成功，{'流程结束' if not next_node else '已进入下一节点：' + (next_node.get('name') if next_node else '无')}",
        "next_node": next_node
    }


@router.get("/resource/{resource_type}/{resource_id}/workflow-status")
def get_resource_workflow_status(
    resource_type: str,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取资源的工作流审核状态
    """
    # 验证资源类型
    resource_model = RESOURCE_TYPES.get(resource_type)
    if not resource_model:
        raise HTTPException(status_code=400, detail=f"不支持的资源类型：{resource_type}")

    # 获取资源
    resource = db.query(resource_model).filter(resource_model.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    # 获取当前工作流记录
    workflow_record = None
    if resource.workflow_record_id:
        workflow_record = db.query(WorkflowRecord).filter(
            WorkflowRecord.id == resource.workflow_record_id
        ).first()

    if not workflow_record:
        return {
            "has_workflow": False,
            "resource": resource,
            "message": "该资源没有进行中的工作流"
        }

    # 获取工作流定义
    definition = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.id == workflow_record.workflow_definition_id
    ).first()

    # 获取当前节点信息
    nodes = definition.nodes or []
    current_node = next((n for n in nodes if n.get('id') == workflow_record.current_node_id), None)

    # 获取操作历史记录
    history = db.query(WorkflowRecord).filter(
        WorkflowRecord.workflow_definition_id == definition.id,
        WorkflowRecord.record_type == resource_type,
        WorkflowRecord.record_id == resource_id
    ).order_by(WorkflowRecord.created_at.desc()).all()

    return {
        "has_workflow": True,
        "resource": resource,
        "workflow_definition": definition,
        "current_record": workflow_record,
        "current_node": current_node,
        "history": history
    }


def get_next_node(nodes, current_node_id, edges):
    """获取下一个节点"""
    for edge in edges:
        if edge.get('source') == current_node_id:
            # 跳过条件边
            if edge.get('condition'):
                continue
            next_node_id = edge.get('target')
            next_node = next((n for n in nodes if n.get('id') == next_node_id), None)
            if next_node:
                return {"next_node": next_node, "action": "proceed"}
    return {"next_node": None, "action": "complete"}


def get_approver_users(node_config, db, current_user=None):
    """
    根据节点配置获取审核人用户列表
    """
    approver = node_config.get('approver')
    if not approver:
        return []

    # 特殊处理：部门负责人
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
        # 查找部门经理角色
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
