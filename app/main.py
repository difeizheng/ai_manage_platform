"""
AI 管理平台 - 主应用入口
"""
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional

from app.core.config import settings
from app.core.database import get_db, init_db
from app.api import api_router
from app.api.auth import get_token_from_request
from app.models.models import User


async def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """可选的当前用户（如果未登录返回 None）"""
    try:
        token = await get_token_from_request(request)
        from jose import jwt
        from app.core.config import settings
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except Exception:
        return None

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="人工智能管理平台 - 整合 AI 模型、算力、数据等资源，规范 AI 使用流程",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 注册路由
app.include_router(api_router)

# 启动时初始化数据库
@app.on_event("startup")
def startup_event():
    init_db()
    print("应用启动成功！访问 http://localhost:8000")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard")
async def dashboard(request: Request):
    """数据看板"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/applications")
async def applications(request: Request):
    """应用场景"""
    return templates.TemplateResponse("applications.html", {"request": request})

@app.get("/datasets")
async def datasets(request: Request):
    """数据集管理"""
    return templates.TemplateResponse("datasets.html", {"request": request})

@app.get("/models")
async def models(request: Request):
    """模型管理"""
    return templates.TemplateResponse("models.html", {"request": request})

@app.get("/agents")
async def agents(request: Request):
    """智能体管理"""
    return templates.TemplateResponse("agents.html", {"request": request})

@app.get("/app-store")
async def app_store(request: Request):
    """应用广场"""
    return templates.TemplateResponse("app_store.html", {"request": request})

@app.get("/compute")
async def compute(request: Request):
    """算力资源"""
    return templates.TemplateResponse("compute.html", {"request": request})

@app.get("/workflow")
async def workflow(request: Request):
    """业务流程"""
    return templates.TemplateResponse("workflow.html", {"request": request})

@app.get("/forum")
async def forum(request: Request):
    """AI 论坛"""
    return templates.TemplateResponse("forum.html", {"request": request})

@app.get("/workflow-design")
async def workflow_design(request: Request):
    """工作流设计"""
    return templates.TemplateResponse("workflow_design.html", {"request": request})


@app.get("/system")
async def system(request: Request):
    """系统配置"""
    return templates.TemplateResponse("system.html", {"request": request})


@app.get("/approvals")
async def approvals(request: Request):
    """我的待办审批"""
    return templates.TemplateResponse("approvals.html", {"request": request})


@app.get("/notifications")
async def notifications(request: Request):
    """站内通知"""
    return templates.TemplateResponse("notifications.html", {"request": request})


@app.get("/workbench")
async def workbench(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_optional)):
    """个人工作台"""
    from app.models.models import Application, WorkflowRecord, Notification

    # 获取统计数据
    user_id = current_user.id if current_user else None

    # 我的申请数量
    my_applications_count = 0
    if user_id:
        my_applications_count = db.query(Application).filter(Application.applicant_id == user_id).count()

    # 我的待办数量（简化版，实际应该根据工作流和角色计算）
    my_approvals_count = 0
    if user_id:
        # 这里简化处理，实际应该查询工作流记录
        pass

    # 未读通知数量
    unread_notifications_count = 0
    if user_id:
        unread_notifications_count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()

    # 应用场景总数
    applications_total = db.query(Application).count()

    # 用户名
    user_name = current_user.real_name or current_user.username if current_user else "访客"

    return templates.TemplateResponse("workbench.html", {
        "request": request,
        "user_name": user_name,
        "my_applications_count": my_applications_count,
        "my_approvals_count": my_approvals_count,
        "unread_notifications_count": unread_notifications_count,
        "applications_total": applications_total
    })
