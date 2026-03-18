# 人工智能管理平台

一个基于 FastAPI + Vue.js 的人工智能管理平台，用于整合 AI 模型、算力、数据等资源，规范 AI 使用流程。

## 功能模块

1. **数据看板** - 可视化展示平台核心指标
2. **应用场景申报** - 提交和管理 AI 应用场景
3. **数据集管理** - 数据集目录、上传和调用申请
4. **模型管理** - AI 模型仓库、上传和调用
5. **智能体管理** - MCP/Agent 等资源管理
6. **应用广场** - 发现和探索 AI 应用
7. **算力资源** - GPU 等算力资源调度
8. **业务流程** - 全生命周期追溯和查询
9. **AI 知识论坛** - 知识分享和交流

## 快速开始

### 方法一：直接运行

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据
python init_data.py

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 方法二：Docker 运行

```bash
# 构建并启动
docker-compose up --build

# 后台运行
docker-compose up -d
```

## 访问地址

- 前端界面：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 默认账户

- 管理员：admin / admin123
- 普通用户：user / user123

## 项目结构

```
ai_manage_platform/
├── app/
│   ├── api/          # API 路由
│   ├── core/         # 核心配置
│   ├── models/       # 数据库模型
│   ├── schemas/      # Pydantic Schema
│   └── main.py       # 应用入口
├── templates/        # 前端页面
├── static/           # 静态文件
├── data/             # 数据目录
├── init_data.py      # 初始化脚本
├── requirements.txt  # 依赖
├── Dockerfile
└── docker-compose.yml
```

## 技术栈

- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：Vue.js 3 + TailwindCSS + Chart.js
- 部署：Docker + Docker Compose

## 开发说明

### API 接口

所有 API 接口都在 `app/api/` 目录下，每个模块对应一个路由文件。

### 数据库

默认使用 SQLite，数据文件存储在 `data/ai_platform.db`。

如需使用 PostgreSQL，修改 `.env` 文件中的 `DATABASE_URL`：

```
DATABASE_URL=postgresql://user:password@localhost:5432/ai_platform
```

### 添加新模块

1. 在 `app/models/models.py` 中添加模型
2. 在 `app/schemas/schemas.py` 中添加 Schema
3. 在 `app/api/` 中添加路由
4. 在 `app/api/__init__.py` 中注册路由
5. 在 `templates/` 中添加页面
6. 在 `app/main.py` 中添加页面路由

## License

MIT
