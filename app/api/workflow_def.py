"""
工作流定义 API - 支持自定义工作流审核流程
支持节点类型：开始/结束/提交/审核/审批/通知/条件分支/并行节点/抄送
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from sqlalchemy.inspection import inspect
import json

from app.core.database import get_db
from app.models.models import WorkflowDefinition, WorkflowRecord, Application, User, Role, UserRole, Notification, Dataset, Model, Agent, AppStoreItem, ComputeResource
from app.api.auth import get_current_user
from app.schemas.schemas import WorkflowDefinitionCreate, WorkflowDefinitionResponse
from app.core.audit import log_action
from app.api.email import send_workflow_notification_email, send_approval_email
from app.api.websocket import notify_user_sync

router = APIRouter()


def parse_json_param(value):
    """解析 JSON 字符串参数"""
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return None
    return value


@router.get("/")
def list_definitions(
    bind_type: Optional[str] = None,
    only_active: bool = True,
    db: Session = Depends(get_db)
):
    """获取工作流定义列表"""
    query = db.query(WorkflowDefinition)
    if bind_type:
        query = query.filter(WorkflowDefinition.bind_type == bind_type)
    if only_active:
        query = query.filter(WorkflowDefinition.is_active == True)
    definitions = query.order_by(WorkflowDefinition.created_at.desc()).all()
    return definitions


@router.get("/approvals/my")
def get_my_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的待办审批列表
    返回工作流记录、定义和当前节点的详细信息
    """
    from app.models.models import Notification, Role, UserRole

    # 首先查找通过通知关联的待办（未读通知）
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        Notification.type == "workflow"
    ).all()

    result = []
    seen_records = set()

    # 处理通知关联的待办
    for notif in notifications:
        if notif.related_type != "workflow_record" or not notif.related_id:
            continue

        record = db.query(WorkflowRecord).filter(WorkflowRecord.id == notif.related_id).first()
        if not record or not record.workflow_definition_id:
            continue

        if record.id in seen_records:
            continue
        seen_records.add(record.id)

        definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == record.workflow_definition_id).first()
        if not definition:
            continue

        nodes = definition.nodes or []
        current_node = next((n for n in nodes if n.get('id') == record.current_node_id), None)
        actor = db.query(User).filter(User.id == record.actor_id).first()

        result.append({
            "record": record,
            "definition": definition,
            "currentNode": current_node,
            "actor": actor
        })

    # 获取当前用户的所有角色
    user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    role_ids = [ur.role_id for ur in user_roles]
    role_codes = []
    if role_ids:
        roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
        role_codes = [r.code for r in roles]

    # 查找所有处于审核/审批节点的工作流记录
    # 根据节点配置中的 approver 角色匹配当前用户的角色
    all_records = db.query(WorkflowRecord).join(
        WorkflowDefinition,
        WorkflowRecord.workflow_definition_id == WorkflowDefinition.id
    ).filter(
        WorkflowRecord.node_status == 'completed'
    ).all()

    for record in all_records:
        if record.id in seen_records:
            continue

        definition = record.workflow_definition_rel if hasattr(record, 'workflow_definition_rel') else None
        if not definition:
            definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == record.workflow_definition_id).first()
        if not definition:
            continue

        nodes = definition.nodes or []
        current_node = next((n for n in nodes if n.get('id') == record.current_node_id), None)
        if not current_node:
            continue

        # 检查当前节点是否是审核/审批节点
        if current_node.get('type') not in ['review', 'approve']:
            continue

        # 检查当前节点的 approver 是否包含当前用户
        node_config = current_node.get('config', {})
        approver = node_config.get('approver')

        should_include = False

        if approver == 'department_head':
            # 部门负责人逻辑
            if current_user.is_department_manager:
                should_include = True
        elif approver == 'applicant_department':
            # 申请部门负责人逻辑 - 这里简化处理，只要是部门经理角色就包含
            if 'department_manager' in role_codes:
                should_include = True
        elif approver:
            # 根据角色 code 匹配
            if approver in role_codes:
                should_include = True
        else:
            # 没有配置 approver，默认包含
            should_include = True

        if should_include:
            seen_records.add(record.id)
            actor = db.query(User).filter(User.id == record.actor_id).first()
            result.append({
                "record": record,
                "definition": definition,
                "currentNode": current_node,
                "actor": actor
            })

    return result


@router.get("/{definition_id}")
def get_definition(
    definition_id: int,
    db: Session = Depends(get_db)
):
    """获取单个工作流定义详情"""
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == definition_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="工作流定义不存在")
    return definition


@router.post("/")
async def create_definition(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新的工作流定义"""
    if current_user.role not in ['admin', 'reviewer']:
        raise HTTPException(status_code=403, detail="权限不足")

    data = await request.json()
    definition = WorkflowDefinition(
        name=data.get('name'),
        description=data.get('description'),
        bind_type=data.get('bind_type'),
        bind_subtype=data.get('bind_subtype'),
        nodes=data.get('nodes', []),
        edges=data.get('edges', []),
        created_by=current_user.id
    )
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return definition


@router.put("/{definition_id}")
async def update_definition(
    definition_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新工作流定义"""
    if current_user.role not in ['admin', 'reviewer']:
        raise HTTPException(status_code=403, detail="权限不足")

    data = await request.json()
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == definition_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="工作流定义不存在")

    # 更新字段
    if 'name' in data:
        definition.name = data.get('name')
    if 'description' in data:
        definition.description = data.get('description')
    if 'nodes' in data:
        definition.nodes = data.get('nodes')
    if 'edges' in data:
        definition.edges = data.get('edges')
    if 'is_active' in data:
        definition.is_active = data.get('is_active')

    db.commit()
    db.refresh(definition)

    # 手动构建响应字典，处理 datetime 类型
    mapper = inspect(definition)
    result = {}
    for column in mapper.columns:
        key = column.key
        value = getattr(definition, key)
        if isinstance(value, datetime):
            result[key] = value.isoformat() if value else None
        elif value is None:
            result[key] = None
        else:
            result[key] = value

    return JSONResponse(content=result)


@router.delete("/{definition_id}")
def delete_definition(
    definition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除工作流定义"""
    if current_user.role not in ['admin', 'reviewer']:
        raise HTTPException(status_code=403, detail="权限不足")

    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == definition_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="工作流定义不存在")

    db.delete(definition)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{definition_id}/execute")
def execute_workflow(
    definition_id: int,
    record_type: str,
    record_id: int,
    application_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """执行工作流 - 创建初始流程记录"""
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == definition_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="工作流定义不存在")

    # 找到第一个节点
    nodes = definition.nodes or []
    start_node = None
    for node in nodes:
        if node.get('type') in ['start', 'submit']:
            start_node = node
            break

    if not start_node:
        start_node = nodes[0] if nodes else {'id': 'node_1', 'type': 'submit', 'name': '提交'}

    # 创建工作流记录
    workflow_record = WorkflowRecord(
        workflow_definition_id=definition_id,
        application_id=application_id,
        current_node_id=start_node.get('id'),
        record_type=record_type,
        record_id=record_id,
        action=start_node.get('type'),
        actor_id=current_user.id,
        description=start_node.get('name'),
        node_status='completed'
    )
    db.add(workflow_record)
    db.commit()
    db.refresh(workflow_record)

    return {
        "workflow_record": workflow_record,
        "next_node": get_next_node(nodes, start_node.get('id'), definition.edges or [])
    }


@router.get("/{definition_id}/next")
def get_next_step(
    definition_id: int,
    current_node_id: str,
    action: str,  # approve 或 reject
    db: Session = Depends(get_db)
):
    """获取工作流下一步"""
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == definition_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="工作流定义不存在")

    nodes = definition.nodes or []
    edges = definition.edges or []

    if action == 'reject':
        # 拒绝时查找是否有拒绝路径
        for edge in edges:
            if edge.get('source') == current_node_id and edge.get('condition') == 'reject':
                next_node = next((n for n in nodes if n.get('id') == edge.get('target')), None)
                if next_node:
                    return {"next_node": next_node, "action": "reject"}
        # 没有拒绝路径，返回结束
        return {"next_node": None, "action": "reject"}
    else:
        # 通过时查找正常路径
        next_node_info = get_next_node(nodes, current_node_id, edges)
        return next_node_info


def get_next_node(nodes, current_node_id, edges):
    """获取下一个节点"""
    for edge in edges:
        if edge.get('source') == current_node_id:
            # 跳过条件边（条件边有 condition 属性）
            if edge.get('condition'):
                continue
            next_node_id = edge.get('target')
            next_node = next((n for n in nodes if n.get('id') == next_node_id), None)
            if next_node:
                return {"next_node": next_node, "action": "proceed"}
    return {"next_node": None, "action": "complete"}


@router.post("/{definition_id}/start")
async def start_workflow(
    definition_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    启动工作流 - 创建流程记录并获取第一个审核节点和审核人
    返回当前节点信息和需要通知的审核人列表
    """
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == definition_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="工作流定义不存在")

    data = await request.json()
    record_type = data.get('record_type')
    record_id = data.get('record_id')
    application_id = data.get('application_id')

    nodes = definition.nodes or []
    edges = definition.edges or []

    # 找到第一个节点（开始或提交节点）
    start_node = None
    for node in nodes:
        if node.get('type') in ['start', 'submit']:
            start_node = node
            break

    if not start_node:
        start_node = nodes[0] if nodes else {'id': 'node_1', 'type': 'submit', 'name': '提交'}

    # 创建工作流记录
    workflow_record = WorkflowRecord(
        workflow_definition_id=definition_id,
        application_id=application_id,
        current_node_id=start_node.get('id'),
        record_type=record_type,
        record_id=record_id,
        action=start_node.get('type'),
        actor_id=current_user.id,
        description=start_node.get('name'),
        node_status='completed'
    )
    db.add(workflow_record)
    db.commit()
    db.refresh(workflow_record)

    # 获取下一个节点（审核节点）
    next_node_info = get_next_node(nodes, start_node.get('id'), edges)
    next_node = next_node_info.get('next_node')

    # 获取审核人列表并创建通知
    approvers = []
    if next_node and next_node.get('type') in ['review', 'approve']:
        # 更新当前流程记录的节点为下一个审核节点
        workflow_record.current_node_id = next_node.get('id')

        # 获取申请信息用于部门负责人逻辑
        app = None
        if application_id:
            app = db.query(Application).filter(Application.id == application_id).first()

        approvers = get_approver_users(next_node.get('config', {}), db, current_user, app)

        # 获取申请信息用于通知内容
        app_info = ""
        if application_id:
            app = db.query(Application).filter(Application.id == application_id).first()
            if app:
                app_info = f"\n申请名称：{app.title}\n申报部门：{app.department or '未分配'}"

        # 为每个审核人创建站内通知
        for approver in approvers:
            notification = Notification(
                user_id=approver.id,
                title=f"待办审批：{definition.name} - {next_node.get('name')}",
                content=f"您有一个待审批的流程节点：{next_node.get('name')}\n提交人：{current_user.real_name or current_user.username}{app_info}\n提交时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                type="workflow",
                related_type="workflow_record",
                related_id=workflow_record.id
            )
            db.add(notification)

            # 发送 WebSocket 实时通知
            notify_user_sync(
                user_id=approver.id,
                notification_title=f"待办审批：{definition.name} - {next_node.get('name')}",
                notification_content=f"您有一个待审批的流程节点",
                notification_id=notification.id
            )

            # 发送邮件通知（异步）
            if app:
                send_workflow_notification_email(
                    background_tasks=background_tasks,
                    db=db,
                    recipient=approver,
                    workflow=definition,
                    node_name=next_node.get('name'),
                    submitter=current_user,
                    app=app
                )

    db.commit()

    return {
        "workflow_record": workflow_record,
        "next_node": next_node,
        "approvers": approvers,
        "message": f"流程已启动，已通知 {len(approvers)} 位审核人"
    }


@router.get("/{definition_id}/node/{node_id}/approvers")
def get_node_approvers(
    definition_id: int,
    node_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定节点的审核人列表
    """
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == definition_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="工作流定义不存在")

    nodes = definition.nodes or []
    node = next((n for n in nodes if n.get('id') == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if node.get('type') not in ['review', 'approve']:
        return {"approvers": [], "message": "该节点不是审核节点"}

    approvers = get_approver_users(node.get('config', {}), db)
    return {
        "node": node,
        "approvers": approvers
    }


@router.post("/{definition_id}/record/{record_id}/action")
async def perform_action(
    definition_id: int,
    record_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    执行工作流操作（通过/拒绝）并移动到下一个节点
    支持条件分支、并行节点（会签/或签）、抄送节点
    支持邮件通知和 WebSocket 实时通知
    """
    from sqlalchemy import and_

    data = await request.json()
    action = data.get('action')  # 'approve' or 'reject'
    comments = data.get('comments', '')
    condition_result = data.get('condition_result')  # 条件分支的结果

    # 获取当前流程记录
    workflow_record = db.query(WorkflowRecord).filter(
        WorkflowRecord.id == record_id,
        WorkflowRecord.workflow_definition_id == definition_id
    ).first()
    if not workflow_record:
        raise HTTPException(status_code=404, detail="流程记录不存在")

    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == definition_id).first()
    nodes = definition.nodes or []
    edges = definition.edges or []

    # 获取当前节点
    current_node = next((n for n in nodes if n.get('id') == workflow_record.current_node_id), None)
    if not current_node:
        raise HTTPException(status_code=404, detail="当前节点不存在")

    # 创建工作流操作记录
    action_record = WorkflowRecord(
        workflow_definition_id=definition_id,
        application_id=workflow_record.application_id,
        current_node_id=workflow_record.current_node_id,
        record_type=workflow_record.record_type,
        record_id=workflow_record.record_id,
        action=action,
        actor_id=current_user.id,
        description=f"{current_user.real_name or current_user.username}: {action} - {comments}",
        node_status='completed'
    )
    db.add(action_record)

    # 拒绝处理
    if action == 'reject':
        # 拒绝时查找拒绝路径
        next_node = None
        for edge in edges:
            if edge.get('source') == workflow_record.current_node_id and edge.get('condition') == 'reject':
                next_node = next((n for n in nodes if n.get('id') == edge.get('target')), None)
                break
        # 如果没有拒绝路径，流程结束，更新应用状态为拒绝
        if not next_node:
            if workflow_record.application_id:
                app = db.query(Application).filter(Application.id == workflow_record.application_id).first()
                if app:
                    app.status = "rejected"
                    app.review_comments = comments
                    app.reviewer_id = current_user.id

                    # 发送审批结果通知给申请人
                    applicant = db.query(User).filter(User.id == app.applicant_id).first()
                    if applicant:
                        # 创建站内通知
                        notification = Notification(
                            user_id=applicant.id,
                            title=f"审批结果：{app.title}",
                            content=f"您的申请未通过审批\n申请标题：{app.title}\n审批意见：{comments if comments else '无'}\n审批人：{current_user.real_name or current_user.username}\n审批时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            type="workflow",
                            related_type="application",
                            related_id=app.id
                        )
                        db.add(notification)

                        # 发送 WebSocket 实时通知
                        notify_user_sync(
                            user_id=applicant.id,
                            notification_title=f"审批结果：{app.title}",
                            notification_content=f"您的申请未通过审批",
                            notification_id=notification.id
                        )

                        # 发送邮件通知（异步）
                        send_approval_email(
                            background_tasks=background_tasks,
                            db=db,
                            applicant=applicant,
                            app=app,
                            status="拒绝",
                            approver=current_user,
                            comments=comments
                        )

            db.commit()
            return {"message": "已拒绝，流程结束", "next_node": None}
    else:
        # 通过时查找下一个节点（支持条件分支）
        next_node_info = get_next_node_with_condition(nodes, workflow_record.current_node_id, edges, condition_result)
        next_node = next_node_info.get('next_node')

    # 处理抄送节点 - 自动流转
    while next_node and next_node.get('type') == 'cc':
        # 抄送节点只需通知，不需要审批，自动流转到下一个节点
        # 创建抄送通知
        app = None
        if workflow_record.application_id:
            app = db.query(Application).filter(Application.id == workflow_record.application_id).first()

        node_config = next_node.get('config', {})
        approvers = get_approver_users(node_config, db, current_user, app)

        app_info = ""
        if app:
            app_info = f"\n申请名称：{app.title}\n申报部门：{app.department or '未分配'}"

        for approver in approvers:
            notification = Notification(
                user_id=approver.id,
                title=f"抄送通知：{definition.name} - {next_node.get('name')}",
                content=f"您收到一个抄送通知：{next_node.get('name')}\n提交人：{current_user.real_name or current_user.username}{app_info}\n操作时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                type="workflow",
                related_type="workflow_record",
                related_id=workflow_record.id
            )
            db.add(notification)

            # 发送 WebSocket 实时通知
            notify_user_sync(
                user_id=approver.id,
                notification_title=f"抄送通知：{definition.name} - {next_node.get('name')}",
                notification_content=f"您收到一个抄送通知",
                notification_id=None  # 将在提交后获取
            )

            # 发送邮件通知（异步）
            if app:
                send_workflow_notification_email(
                    background_tasks=background_tasks,
                    db=db,
                    recipient=approver,
                    workflow=definition,
                    node_name=next_node.get('name'),
                    submitter=current_user,
                    app=app
                )

        # 创建抄送记录
        cc_record = WorkflowRecord(
            workflow_definition_id=definition_id,
            application_id=workflow_record.application_id,
            current_node_id=next_node.get('id'),
            record_type=workflow_record.record_type,
            record_id=workflow_record.record_id,
            action='cc',
            actor_id=None,
            description=f"抄送：{next_node.get('name')}",
            node_status='completed'
        )
        db.add(cc_record)

        # 继续查找下一个节点
        next_node_info = get_next_node_with_condition(nodes, next_node.get('id'), edges)
        next_node = next_node_info.get('next_node')

    # 如果有下一个节点
    if next_node:
        workflow_record.current_node_id = next_node.get('id')

        # 处理并行节点（会签/或签）
        if next_node.get('type') == 'parallel':
            # 并行节点需要等待多个审批人完成
            # 获取所有审核人并创建通知
            node_config = next_node.get('config', {})
            app = None
            if workflow_record.application_id:
                app = db.query(Application).filter(Application.id == workflow_record.application_id).first()

            approvers = get_approver_users(node_config, db, current_user, app)

            app_info = ""
            if app:
                app_info = f"\n申请名称：{app.title}\n申报部门：{app.department or '未分配'}"

            for approver in approvers:
                notification = Notification(
                    user_id=approver.id,
                    title=f"待办审批：{definition.name} - {next_node.get('name')}",
                    content=f"您有一个待审批的并行节点：{next_node.get('name')}\n提交人：{current_user.real_name or current_user.username}{app_info}\n操作时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    type="workflow",
                    related_type="workflow_record",
                    related_id=workflow_record.id
                )
                db.add(notification)

                # 发送 WebSocket 实时通知
                notify_user_sync(
                    user_id=approver.id,
                    notification_title=f"待办审批：{definition.name} - {next_node.get('name')}",
                    notification_content=f"您有一个待审批的并行节点",
                    notification_id=notification.id
                )

                # 发送邮件通知（异步）
                if app:
                    send_workflow_notification_email(
                        background_tasks=background_tasks,
                        db=db,
                        recipient=approver,
                        workflow=definition,
                        node_name=next_node.get('name'),
                        submitter=current_user,
                        app=app
                    )

            # 更新流程记录的当前节点，但不立即提交，等待并行节点完成
            db.commit()
            return {
                "message": f"已进入并行节点：{next_node.get('name')}，等待 {len(approvers)} 位审核人审批",
                "next_node": next_node,
                "parallel": True,
                "approvers_count": len(approvers)
            }

        # 处理条件分支节点
        if next_node.get('type') == 'condition':
            # 条件分支节点根据条件评估结果自动选择路径
            node_config = next_node.get('config', {})
            condition_expr = node_config.get('condition', '')

            # 获取上下文数据用于条件评估
            context_data = {}
            if workflow_record.application_id and app:
                context_data['amount'] = getattr(app, 'cost_estimate', None)
                context_data['department'] = app.department if app else None
                context_data['priority'] = node_config.get('priority', 'normal')

            # 评估条件
            eval_result = evaluate_condition(condition_expr, context_data) if condition_expr else condition_result

            # 根据评估结果选择路径
            next_node_info = get_next_node_with_condition(nodes, next_node.get('id'), edges, eval_result)
            next_node = next_node_info.get('next_node')

            # 创建条件评估记录
            cond_record = WorkflowRecord(
                workflow_definition_id=definition_id,
                application_id=workflow_record.application_id,
                current_node_id=next_node.get('id') if next_node else None,
                record_type=workflow_record.record_type,
                record_id=workflow_record.record_id,
                action='condition',
                actor_id=current_user.id,
                description=f"条件评估：{condition_expr} = {eval_result}",
                node_status='completed'
            )
            db.add(cond_record)

            # 如果下一个节点还是审核节点，通知审核人
            if next_node and next_node.get('type') in ['review', 'approve', 'parallel']:
                node_config = next_node.get('config', {})
                approvers = get_approver_users(node_config, db, current_user, app)

                app_info = ""
                if app:
                    app_info = f"\n申请名称：{app.title}\n申报部门：{app.department or '未分配'}"

                for approver in approvers:
                    notification = Notification(
                        user_id=approver.id,
                        title=f"待办审批：{definition.name} - {next_node.get('name')}",
                        content=f"您有一个待审批的流程节点：{next_node.get('name')}\n提交人：{current_user.real_name or current_user.username}{app_info}\n条件评估：{condition_expr} = {eval_result}\n操作时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        type="workflow",
                        related_type="workflow_record",
                        related_id=workflow_record.id
                    )
                    db.add(notification)

                    # 发送 WebSocket 实时通知
                    notify_user_sync(
                        user_id=approver.id,
                        notification_title=f"待办审批：{definition.name} - {next_node.get('name')}",
                        notification_content=f"您有一个待审批的流程节点",
                        notification_id=notification.id
                    )

                    # 发送邮件通知（异步）
                    if app:
                        send_workflow_notification_email(
                            background_tasks=background_tasks,
                            db=db,
                            recipient=approver,
                            workflow=definition,
                            node_name=next_node.get('name'),
                            submitter=current_user,
                            app=app
                        )

            db.commit()
            return {
                "message": f"条件评估完成，{condition_expr} = {eval_result}，进入节点：{next_node.get('name') if next_node else '结束'}",
                "next_node": next_node,
                "condition_result": eval_result
            }

        # 普通审核节点
        if next_node.get('type') in ['review', 'approve']:
            node_config = next_node.get('config', {})
            app = None
            if workflow_record.application_id:
                app = db.query(Application).filter(Application.id == workflow_record.application_id).first()

            approvers = get_approver_users(node_config, db, current_user, app)

            app_info = ""
            if app:
                app_info = f"\n申请名称：{app.title}\n申报部门：{app.department or '未分配'}"

            for approver in approvers:
                notification = Notification(
                    user_id=approver.id,
                    title=f"待办审批：{definition.name} - {next_node.get('name')}",
                    content=f"您有一个待审批的流程节点：{next_node.get('name')}\n提交人：{current_user.real_name or current_user.username}{app_info}\n审批意见：{comments if comments else '无'}\n操作时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    type="workflow",
                    related_type="workflow_record",
                    related_id=workflow_record.id
                )
                db.add(notification)

                # 发送 WebSocket 实时通知
                notify_user_sync(
                    user_id=approver.id,
                    notification_title=f"待办审批：{definition.name} - {next_node.get('name')}",
                    notification_content=f"您有一个待审批的流程节点",
                    notification_id=notification.id
                )

                # 发送邮件通知（异步）
                if app:
                    send_workflow_notification_email(
                        background_tasks=background_tasks,
                        db=db,
                        recipient=approver,
                        workflow=definition,
                        node_name=next_node.get('name'),
                        submitter=current_user,
                        app=app
                    )

    else:
        # 没有下一个节点，流程完成
        # 查找 end 节点并创建工作流记录
        end_node = next((n for n in nodes if n.get('type') == 'end'), None)
        if end_node:
            end_record = WorkflowRecord(
                workflow_definition_id=definition_id,
                application_id=workflow_record.application_id,
                current_node_id=end_node.get('id'),
                record_type=workflow_record.record_type,
                record_id=workflow_record.record_id,
                action='end',
                actor_id=current_user.id,
                description=f"流程结束：{definition.name}",
                node_status='completed'
            )
            db.add(end_record)

        # 更新当前流程记录的 node_status 为 completed
        workflow_record.node_status = 'completed'

        # 更新应用状态为通过
        if workflow_record.application_id:
            app = db.query(Application).filter(Application.id == workflow_record.application_id).first()
            if app:
                app.status = "approved"
                app.review_comments = comments
                app.reviewer_id = current_user.id
                app.approved_at = datetime.now()

                # 发送审批结果通知给申请人
                applicant = db.query(User).filter(User.id == app.applicant_id).first()
                if applicant:
                    # 创建站内通知
                    notification = Notification(
                        user_id=applicant.id,
                        title=f"审批结果：{app.title}",
                        content=f"您的申请已通过审批\n申请标题：{app.title}\n审批意见：{comments if comments else '无'}\n审批人：{current_user.real_name or current_user.username}\n审批时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        type="workflow",
                        related_type="application",
                        related_id=app.id
                    )
                    db.add(notification)

                    # 发送 WebSocket 实时通知
                    notify_user_sync(
                        user_id=applicant.id,
                        notification_title=f"审批结果：{app.title}",
                        notification_content=f"您的申请已通过审批",
                        notification_id=notification.id
                    )

                    # 发送邮件通知（异步）
                    send_approval_email(
                        background_tasks=background_tasks,
                        db=db,
                        applicant=applicant,
                        app=app,
                        status="通过",
                        approver=current_user,
                        comments=comments
                    )

        # 更新资源状态（如果是资源类型的工作流）
        record_type = workflow_record.record_type
        resource_id = workflow_record.record_id
        if record_type and resource_id:
            resource_models = {
                'dataset': Dataset,
                'model': Model,
                'agent': Agent,
                'app_store': AppStoreItem,
                'compute_resource': ComputeResource
            }
            resource_model = resource_models.get(record_type)
            if resource_model:
                resource = db.query(resource_model).filter(resource_model.id == resource_id).first()
                if resource:
                    approved_status_map = {
                        'dataset': 'available',
                        'model': 'available',
                        'agent': 'available',
                        'app_store': 'published',
                        'compute_resource': 'available'
                    }
                    resource.status = approved_status_map.get(record_type, 'approved')
                    db.commit()

    db.commit()

    # 记录审计日志
    log_action(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        action="WORKFLOW_APPROVE",
        resource_type="workflow",
        resource_id=definition_id,
        resource_name=definition.name,
        extra_data={"record_id": record_id, "action": action, "node": current_node.get('name')}
    )

    return {
        "message": f"操作成功，{'流程结束' if not next_node else '已进入下一节点：' + (next_node.get('name') if next_node else '无')}",
        "next_node": next_node
    }


def get_approver_users(node_config, db, current_user=None, application=None):
    """
    根据节点配置获取审核人用户列表
    node_config: 节点配置，包含 approver (角色 code) 字段
    current_user: 当前用户（用于部门负责人逻辑）
    application: 应用场景（用于申请部门负责人逻辑）
    """
    approver = node_config.get('approver')
    if not approver:
        return []

    # 特殊处理：部门负责人（查找当前用户所在部门的负责人）
    if approver == 'department_head':
        if not current_user or not current_user.department:
            return []
        # 查找当前用户所在部门的部门负责人
        dept_managers = db.query(User).filter(
            User.department == current_user.department,
            User.is_department_manager == True,
            User.is_active == True
        ).all()
        if dept_managers:
            return dept_managers
        # 如果没有明确标记的部门负责人，查找部门经理角色
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

    # 特殊处理：申请部门负责人（查找申请人所在部门的负责人）
    elif approver == 'applicant_department':
        if not application:
            # 尝试从 current_user 获取部门
            if current_user and current_user.department:
                dept = current_user.department
            else:
                return []
        else:
            dept = application.department if application.department else current_user.department if current_user else None
        if not dept:
            return []
        # 查找申请部门的部门负责人
        dept_managers = db.query(User).filter(
            User.department == dept,
            User.is_department_manager == True,
            User.is_active == True
        ).all()
        if dept_managers:
            return dept_managers
        # 如果没有明确标记的部门负责人，查找部门经理角色
        manager_role = db.query(Role).filter(Role.code == 'department_manager').first()
        if manager_role:
            user_roles = db.query(UserRole).filter(UserRole.role_id == manager_role.id).all()
            user_ids = [ur.user_id for ur in user_roles]
            users = db.query(User).filter(
                User.id.in_(user_ids),
                User.department == dept,
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


def evaluate_condition(condition_expr, context_data):
    """
    评估条件表达式
    condition_expr: 条件表达式字符串，如 "amount > 10000" 或 "department == '技术部'"
    context_data: 上下文数据字典，包含可用变量
    返回：True/False
    """
    if not condition_expr:
        return True

    try:
        # 安全的表达式评估（只允许简单比较）
        # 创建安全的命名空间
        safe_dict = {
            '__builtins__': {},
            **context_data
        }
        return bool(eval(condition_expr, safe_dict, {}))
    except Exception as e:
        print(f"条件评估失败：{condition_expr}, 错误：{e}")
        return False


def get_next_node_with_condition(nodes, current_node_id, edges, condition_result=None):
    """
    获取下一个节点（支持条件分支）
    condition_result: 条件评估结果（True/False），用于条件分支节点
    """
    current_node = next((n for n in nodes if n.get('id') == current_node_id), None)
    if not current_node:
        return {"next_node": None, "action": "complete"}

    node_type = current_node.get('type')

    # 条件分支节点：根据条件结果选择路径
    if node_type == 'condition':
        for edge in edges:
            if edge.get('source') == current_node_id:
                edge_condition = edge.get('condition')  # 'true' 或 'false' 或表达式
                if edge_condition == 'true' and condition_result:
                    next_node = next((n for n in nodes if n.get('id') == edge.get('target')), None)
                    if next_node:
                        return {"next_node": next_node, "action": "proceed"}
                elif edge_condition == 'false' and not condition_result:
                    next_node = next((n for n in nodes if n.get('id') == edge.get('target')), None)
                    if next_node:
                        return {"next_node": next_node, "action": "proceed"}
                elif edge_condition and edge_condition not in ['true', 'false']:
                    # 自定义条件表达式
                    if condition_result is not None:
                        if (edge_condition == 'true') == condition_result:
                            next_node = next((n for n in nodes if n.get('id') == edge.get('target')), None)
                            if next_node:
                                return {"next_node": next_node, "action": "proceed"}
        return {"next_node": None, "action": "complete"}

    # 抄送节点：只需记录，不需要审批，自动流向下一个节点
    if node_type == 'cc':
        for edge in edges:
            if edge.get('source') == current_node_id and not edge.get('condition'):
                next_node_id = edge.get('target')
                next_node = next((n for n in nodes if n.get('id') == next_node_id), None)
                if next_node:
                    return {"next_node": next_node, "action": "proceed"}
        return {"next_node": None, "action": "complete"}

    # 并行节点：需要等待所有分支完成（由外部逻辑处理）
    if node_type == 'parallel':
        # 并行节点的配置包含 approval_type: 'all' (会签) 或 'any' (或签)
        # 这里只返回下一个节点，实际并行处理在 perform_action 中
        for edge in edges:
            if edge.get('source') == current_node_id and not edge.get('condition'):
                next_node_id = edge.get('target')
                next_node = next((n for n in nodes if n.get('id') == next_node_id), None)
                if next_node:
                    return {"next_node": next_node, "action": "proceed"}
        return {"next_node": None, "action": "complete"}

    # 普通节点：查找无条件边
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


def check_parallel_node_complete(nodes, current_node_id, workflow_records, db):
    """
    检查并行节点是否完成
    - 会签 (all): 所有人都同意
    - 或签 (any): 任意一人同意
    返回：(是否完成，是否通过)
    """
    current_node = next((n for n in nodes if n.get('id') == current_node_id), None)
    if not current_node:
        return (True, True)

    node_config = current_node.get('config', {})
    approval_type = node_config.get('approval_type', 'any')  # 'all' 或 'any'

    # 获取该节点的审核人列表
    approvers = get_approver_users(node_config, db)
    if not approvers:
        return (True, True)

    approver_ids = set(a.id for a in approvers)

    # 查找该节点的所有审批记录
    node_records = [r for r in workflow_records if r.current_node_id == current_node_id and r.action in ['approve', 'reject']]

    approved_users = set()
    rejected_users = set()

    for record in node_records:
        if record.actor_id:
            if record.action == 'approve':
                approved_users.add(record.actor_id)
            elif record.action == 'reject':
                rejected_users.add(record.actor_id)

    if approval_type == 'all':
        # 会签：所有人都同意才算通过
        if rejected_users:
            return (True, False)  # 有人拒绝，直接不通过
        if approved_users >= approver_ids:
            return (True, True)  # 所有人都同意了
        return (False, False)  # 等待更多人审批
    else:
        # 或签：任意一人同意即可
        if approved_users:
            return (True, True)
        if rejected_users >= approver_ids:
            return (True, False)  # 所有人都拒绝
        return (False, False)  # 等待审批
