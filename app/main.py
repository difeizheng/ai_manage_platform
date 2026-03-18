"""
AI 管理平台 - 主应用入口
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import api_router

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
