"""
API 路由汇总
"""
from fastapi import APIRouter

from app.api import dashboard, applications, datasets, models, agents, app_store, compute, workflow, forum, auth, workflow_def, system, notification

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/api/dashboard", tags=["数据看板"])
api_router.include_router(applications.router, prefix="/api/applications", tags=["应用场景"])
api_router.include_router(datasets.router, prefix="/api/datasets", tags=["数据集管理"])
api_router.include_router(models.router, prefix="/api/models", tags=["模型管理"])
api_router.include_router(agents.router, prefix="/api/agents", tags=["智能体管理"])
api_router.include_router(app_store.router, prefix="/api/app-store", tags=["应用广场"])
api_router.include_router(compute.router, prefix="/api/compute", tags=["算力资源"])
api_router.include_router(workflow.router, prefix="/api/workflow", tags=["业务流程"])
api_router.include_router(workflow_def.router, prefix="/api/workflow-def", tags=["工作流定义"])
api_router.include_router(forum.router, prefix="/api/forum", tags=["AI 论坛"])
api_router.include_router(auth.router, prefix="/api/auth", tags=["用户认证"])
api_router.include_router(system.router, prefix="/api/system", tags=["系统配置"])
api_router.include_router(notification.router, prefix="/api/notification", tags=["站内通知"])
