"""
应用场景 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import Application, User, WorkflowRecord, WorkflowDefinition, Role, UserRole
from app.schemas.schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse, PaginatedResponse
from app.api.auth import get_current_user, can_edit_resource, can_delete_resource

router = APIRouter()


@router.get("/my")
def list_my_applications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的应用场景列表"""
    query = db.query(Application).filter(Application.applicant_id == current_user.id)
    applications = query.order_by(Application.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": applications, "total": len(applications)}


@router.get("/")
def list_applications(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    status: Optional[str] = Query(None, description="状态"),
    department: Optional[str] = Query(None, description="部门"),
    creator: Optional[str] = Query(None, description="创建人（'me' 为当前用户）"),
    reviewer_id_filter: Optional[str] = Query(None, description="审批人（'me' 为当前用户）"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取应用场景列表 - 支持分页、多条件过滤和数据权限控制"""
    query = db.query(Application)

    # 数据权限控制：普通用户只能查看自己的应用
    if current_user.role not in ['admin', 'reviewer']:
        query = query.filter(Application.applicant_id == current_user.id)

    # 按创建人过滤
    if creator == 'me':
        query = query.filter(Application.applicant_id == current_user.id)
    elif creator and creator.isdigit():
        query = query.filter(Application.applicant_id == int(creator))

    # 按审批人过滤（我审批的应用）
    if reviewer_id_filter == 'me':
        query = query.filter(Application.reviewer_id == current_user.id)
    elif reviewer_id_filter and reviewer_id_filter.isdigit():
        query = query.filter(Application.reviewer_id == int(reviewer_id_filter))

    # 按状态过滤
    if status:
        query = query.filter(Application.status == status)

    # 按部门过滤
    if department:
        query = query.filter(Application.department == department)

    # 关键词搜索（标题或业务背景）
    if keyword:
        query = query.filter(
            (Application.title.contains(keyword)) |
            (Application.business_background.contains(keyword))
        )

    # 获取总数
    total = query.count()

    # 分页查询
    applications = query.order_by(Application.created_at.desc()).offset(skip).limit(limit).all()

    return PaginatedResponse.create(items=applications, total=total, skip=skip, limit=limit)


def get_node_pending_users(node_config, db, applicant_department=None):
    """
    根据节点配置获取待审核人员列表
    返回：{"role_name": "角色名称", "users": ["用户 1", "用户 2", ...]}
    """
    from sqlalchemy import and_

    approver = node_config.get('approver')
    if not approver:
        return {"role_name": "未配置角色", "users": []}

    # 特殊处理：部门负责人、申请部门负责人
    if approver == 'department_head':
        # 根据申请人部门查找部门负责人
        if not applicant_department:
            return {"role_name": "部门负责人", "users": []}
        # 查找该部门的部门负责人（is_department_manager=True）
        dept_managers = db.query(User).filter(
            User.department == applicant_department,
            User.is_department_manager == True,
            User.is_active == True
        ).all()
        if dept_managers:
            return {
                "role_name": "部门负责人",
                "users": [u.real_name or u.username for u in dept_managers]
            }
        # 如果没有明确标记的部门负责人，查找部门经理角色
        manager_role = db.query(Role).filter(Role.code == 'department_manager').first()
        if manager_role:
            user_roles = db.query(UserRole).filter(UserRole.role_id == manager_role.id).all()
            user_ids = [ur.user_id for ur in user_roles]
            users = db.query(User).filter(
                User.id.in_(user_ids),
                User.department == applicant_department,
                User.is_active == True
            ).all()
            if users:
                return {
                    "role_name": "部门负责人",
                    "users": [u.real_name or u.username for u in users]
                }
        return {"role_name": "部门负责人", "users": []}
    elif approver == 'applicant_department':
        # 根据申请部门查找该部门的负责人
        if not applicant_department:
            return {"role_name": "申请部门负责人", "users": []}
        # 查找该部门的部门负责人（is_department_manager=True）
        dept_managers = db.query(User).filter(
            User.department == applicant_department,
            User.is_department_manager == True,
            User.is_active == True
        ).all()
        if dept_managers:
            return {
                "role_name": f"{applicant_department}部门负责人",
                "users": [u.real_name or u.username for u in dept_managers]
            }
        # 如果没有明确标记的部门负责人，查找部门经理角色
        manager_role = db.query(Role).filter(Role.code == 'department_manager').first()
        if manager_role:
            user_roles = db.query(UserRole).filter(UserRole.role_id == manager_role.id).all()
            user_ids = [ur.user_id for ur in user_roles]
            users = db.query(User).filter(
                User.id.in_(user_ids),
                User.department == applicant_department,
                User.is_active == True
            ).all()
            if users:
                return {
                    "role_name": f"{applicant_department}部门负责人",
                    "users": [u.real_name or u.username for u in users]
                }
        return {"role_name": f"{applicant_department}部门负责人", "users": []}

    # 根据角色 code 查找角色
    role = db.query(Role).filter(Role.code == approver).first()
    if not role:
        return {"role_name": f"未知角色 ({approver})", "users": []}

    # 查询拥有该角色的用户
    user_roles = db.query(UserRole).filter(UserRole.role_id == role.id).all()
    user_ids = [ur.user_id for ur in user_roles]
    if not user_ids:
        return {"role_name": role.name, "users": []}

    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_names = [u.real_name or u.username for u in users]

    return {"role_name": role.name, "users": user_names}


@router.get("/{app_id}/workflow-records")
def get_application_workflow_records(
    app_id: int,
    db: Session = Depends(get_db)
):
    """获取应用的工作流记录和审批详情"""
    # 获取应用详情
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="应用场景不存在")

    # 获取工作流定义
    workflow_def = None
    if application.workflow_definition_id:
        workflow_def = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == application.workflow_definition_id
        ).first()

    # 获取所有工作流记录
    workflow_records = db.query(WorkflowRecord).filter(
        WorkflowRecord.application_id == app_id
    ).order_by(WorkflowRecord.created_at.asc()).all()

    # 构建审批流程信息
    flow_nodes = []
    if workflow_def and workflow_def.nodes:
        nodes = workflow_def.nodes
        edges = workflow_def.edges or []

        # 获取所有审核人 ID
        reviewer_ids = set()
        for record in workflow_records:
            if record.actor_id:
                reviewer_ids.add(record.actor_id)

        # 批量获取用户信息
        users = db.query(User).filter(User.id.in_(reviewer_ids)).all() if reviewer_ids else []
        user_map = {user.id: user for user in users}

        # 为每个节点构建信息
        for i, node in enumerate(nodes):
            node_info = {
                "id": node.get("id"),
                "name": node.get("name", "节点"),
                "type": node.get("type"),
                "index": i,
                "status": "pending",  # pending, completed, current
                "action": None,
                "actor": None,
                "actor_name": None,
                "comments": None,
                "created_at": None
            }

            # 查找该节点的审批记录
            for record in workflow_records:
                if record.current_node_id == node.get("id"):
                    # start、submit 节点：只要有记录就标记为已完成
                    if node.get("type") in ["start", "submit"]:
                        if record.actor_id and record.actor_id in user_map:
                            actor = user_map[record.actor_id]
                            node_info["actor_name"] = actor.real_name or actor.username
                            node_info["created_at"] = record.created_at
                            node_info["status"] = "completed"
                        # 即使没有 actor_id，只要有记录也标记为已完成
                        elif record.node_status == 'completed':
                            node_info["status"] = "completed"
                            node_info["created_at"] = record.created_at
                    # 审核节点
                    elif node.get("type") in ["review", "approve"]:
                        if record.action in ["approve", "reject"]:
                            node_info["status"] = "completed"
                            node_info["action"] = record.action
                            node_info["comments"] = record.description
                            node_info["created_at"] = record.created_at
                            if record.actor_id and record.actor_id in user_map:
                                actor = user_map[record.actor_id]
                                node_info["actor"] = record.actor_id
                                node_info["actor_name"] = actor.real_name or actor.username
                    # end 节点：只要有记录就标记为已完成
                    elif node.get("type") == "end":
                        node_info["status"] = "completed"
                        node_info["created_at"] = record.created_at

            # 添加待处理角色和待审核人员信息
            node_config = node.get('config', {})
            pending_info = get_node_pending_users(node_config, db, application.department)
            node_info["pending_role"] = pending_info["role_name"]
            node_info["pending_users"] = pending_info["users"]

            # 如果是 start、submit 或 end 节点，待处理信息为空
            if node.get("type") in ["start", "submit", "end"]:
                node_info["pending_role"] = None
                node_info["pending_users"] = []

            flow_nodes.append(node_info)

    # 如果没有工作流定义，使用默认流程
    if not workflow_def:
        for record in workflow_records:
            actor_name = None
            if record.actor_id:
                actor = db.query(User).filter(User.id == record.actor_id).first()
                if actor:
                    actor_name = actor.real_name or actor.username

            flow_nodes.append({
                "id": record.id,
                "name": record.action,
                "type": record.action,
                "status": "completed",
                "action": record.action,
                "actor_name": actor_name,
                "comments": record.description,
                "created_at": record.created_at
            })

    return {
        "application": application,
        "workflow_definition": workflow_def,
        "flow_nodes": flow_nodes
    }


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
    # 检查工作流绑定
    workflow_def_id = app_data.workflow_definition_id
    workflow_def = None
    if workflow_def_id:
        workflow_def = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_def_id).first()

    # 绑定了工作流的应用，状态设为 under_review；否则设为 submitted
    application_status = "under_review" if workflow_def and workflow_def.nodes else "submitted"

    application = Application(
        **app_data.model_dump(),
        applicant_id=current_user.id,
        status=application_status
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    if workflow_def and workflow_def.nodes:
        # 使用自定义工作流 - 启动工作流并通知审核人
        from app.api.workflow_def import get_next_node, get_approver_users
        from app.models.models import Notification

        nodes = workflow_def.nodes
        edges = workflow_def.edges or []

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
            workflow_definition_id=workflow_def_id,
            application_id=application.id,
            current_node_id=start_node.get('id'),
            record_type="application",
            record_id=application.id,
            action=start_node.get('type', 'submit'),
            actor_id=current_user.id,
            description=f"提交应用场景申报：{application.title} - 工作流：{workflow_def.name}",
            node_status='completed'
        )
        db.add(workflow_record)

        # 获取下一个节点
        next_node_info = get_next_node(nodes, start_node.get('id'), edges)
        next_node = next_node_info.get('next_node')

        # 如果是审核节点，通知审核人
        approvers = []
        if next_node and next_node.get('type') in ['review', 'approve']:
            # 更新当前流程记录的节点为下一个审核节点
            workflow_record.current_node_id = next_node.get('id')

            approvers = get_approver_users(next_node.get('config', {}), db, current_user)

            # 获取申请信息用于通知内容
            app_info = f"\n申请名称：{application.title}\n申报部门：{application.department or '未分配'}"

            # 为每个审核人创建站内通知
            for approver in approvers:
                notification = Notification(
                    user_id=approver.id,
                    title=f"待办审批：{workflow_def.name} - {next_node.get('name')}",
                    content=f"您有一个待审批的流程节点：{next_node.get('name')}\n提交人：{current_user.real_name or current_user.username}{app_info}\n提交时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    type="workflow",
                    related_type="workflow_record",
                    related_id=workflow_record.id
                )
                db.add(notification)

        db.commit()
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

    # 权限检查：只有创建者、admin、reviewer 可以编辑
    if not can_edit_resource(application, current_user, db):
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

    # 检查是否绑定了工作流
    if application.workflow_definition_id:
        # 绑定了工作流的应用，应该通过工作流接口审批
        raise HTTPException(
            status_code=400,
            detail="此应用已绑定工作流，请在'我的待办'中进行审批"
        )

    # 没有绑定工作流，使用简单审批
    application.status = "approved" if approved else "rejected"
    application.review_comments = comments
    application.reviewer_id = current_user.id

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

    # 权限检查：只有 admin 或创建者可以删除
    if not can_delete_resource(application, current_user, db):
        raise HTTPException(status_code=403, detail="无权限删除此应用场景")

    db.delete(application)
    db.commit()
    return {"message": "删除成功"}
