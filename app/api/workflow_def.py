"""
工作流定义 API - 支持自定义工作流审核流程
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from sqlalchemy.inspection import inspect

from app.core.database import get_db
from app.models.models import WorkflowDefinition, WorkflowRecord, Application, User, Role, UserRole, Notification
from app.api.auth import get_current_user
from app.schemas.schemas import WorkflowDefinitionCreate, WorkflowDefinitionResponse

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
    from app.models.models import Notification

    # 查找发送给当前用户的通知
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        Notification.type == "workflow"
    ).all()

    result = []
    seen_records = set()

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

        # 获取当前节点信息
        nodes = definition.nodes or []
        current_node = next((n for n in nodes if n.get('id') == record.current_node_id), None)

        # 获取提交人信息
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    执行工作流操作（通过/拒绝）并移动到下一个节点
    """
    data = await request.json()
    action = data.get('action')  # 'approve' or 'reject'
    comments = data.get('comments', '')

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

    # 获取下一个节点
    if action == 'reject':
        # 拒绝时查找拒绝路径
        next_node = None
        for edge in edges:
            if edge.get('source') == workflow_record.current_node_id and edge.get('condition') == 'reject':
                next_node = next((n for n in nodes if n.get('id') == edge.get('target')), None)
                break
        # 如果没有拒绝路径，流程结束，更新应用状态为拒绝
        if not next_node:
            # 更新应用状态
            if workflow_record.application_id:
                app = db.query(Application).filter(Application.id == workflow_record.application_id).first()
                if app:
                    app.status = "rejected"
                    app.review_comments = comments
                    app.reviewer_id = current_user.id
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
            # 获取申请信息用于部门负责人逻辑
            app = None
            if workflow_record.application_id:
                app = db.query(Application).filter(Application.id == workflow_record.application_id).first()

            approvers = get_approver_users(next_node.get('config', {}), db, current_user, app)

            # 获取申请信息用于通知内容
            app_info = ""
            if workflow_record.application_id:
                app = db.query(Application).filter(Application.id == workflow_record.application_id).first()
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
    else:
        # 没有下一个节点，流程完成，更新应用状态为通过
        if workflow_record.application_id:
            app = db.query(Application).filter(Application.id == workflow_record.application_id).first()
            if app:
                app.status = "approved"
                app.review_comments = comments
                app.reviewer_id = current_user.id
                app.approved_at = datetime.now()

    db.commit()

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
