# AI 管理平台 - 项目状态

**更新时间**: 2026-03-23
**当前版本**: v1.3.0
**GitHub**: https://github.com/difeizheng/ai_manage_platform

---

## 最新版本变更 (v1.3.0)

### 新增功能
- **个人工作台** (`/workbench`) - 用户个人首页，汇总我的申请/我的待办/我的通知
- **站内通知页面** (`/notifications`) - 完整的通知管理功能
- **论坛评论** - 支持发表评论、查看评论、删除评论
- **资源申请工作流** - 资源申请可绑定工作流审批

### 核心改进
- **部门负责人审批逻辑** - 实现 `department_head` 和 `applicant_department` 审核人类型
- **系统配置** - 用户管理支持设置部门负责人

### 文件变更
- 新建 `app/api/application_requests.py` - 资源申请 API
- 新建 `templates/workbench.html` - 个人工作台
- 新建 `templates/notifications.html` - 通知中心
- 更新 `app/models/models.py` - 新增 ForumComment 模型，ApplicationRequest 新增工作流字段
- 更新 `app/api/forum.py` - 评论 API
- 更新 `templates/forum.html` - 评论功能
- 更新 `templates/base.html` - 导航栏

### 数据库变更
- `users` 表新增 `is_department_manager` 字段
- `application_requests` 表新增 `workflow_definition_id`、`workflow_record_id` 字段
- 新建 `forum_comments` 表

---

## 2026-03-23 问题修复

### 资源工作流审批功能修复
**问题**: 资源创建工作流绑定后审批 API 找不到待办审批

**修复**:
- 5 个资源 API 添加 `_get_next_node_id` 函数，自动推进到 review 节点
- `workflow_def.py` 添加资源状态更新逻辑

**涉及文件**:
- `app/api/datasets.py`, `app/api/models.py`, `app/api/agents.py`, `app/api/app_store.py`, `app/api/compute.py`
- `app/api/workflow_def.py`
- `tests/test_resource_workflow_simple.py`

### 个人工作台 500 错误修复
**问题**: 访问 `/workbench` 返回 500 错误

**修复**:
- 使用 `{% raw %}` 包裹 Vue.js 模板内容
- 修复 Vue.js 语法 (`||` 和 `?.`) 与 Jinja2 冲突
- 添加 `get_current_user_optional` 函数和统计数据传递

**涉及文件**:
- `templates/workbench.html`
- `app/main.py`

---

## 已完成功能模块

### 1. 用户认证系统
- JWT Token 认证
- 登录/登出功能
- 用户角色权限管理
- 测试账号：`admin / admin123`

### 2. 数据看板 (`/dashboard`)
- 统计数据展示（模型、应用、数据集、智能体数量）
- 算力资源统计

### 3. 应用场景管理 (`/applications`)
- 应用场景申报
- 审批流程
- 详情查看（含审批流程）
- 工作流绑定支持

### 4. 数据集管理 (`/datasets`)
- 数据集 CRUD
- 状态管理

### 5. 模型管理 (`/models`)
- 模型上传/CRUD
- 文件上传支持

### 6. 智能体管理 (`/agents`)
- 智能体 CRUD
- 关联模型/数据集

### 7. 应用广场 (`/app-store`)
- 应用发布/展示
- 使用统计

### 8. 算力资源 (`/compute`)
- 资源管理
- 使用统计

### 9. 业务流程 (`/workflow`)
- 流程记录查看

### 10. 工作流设计器 (`/workflow-design`)
- 可视化流程设计
- 节点配置（开始/提交/审核/结束）
- 边配置（流程流转）
- 审核人角色配置（从角色管理动态加载）
- 流程启动/执行

### 11. 我的待办审批 (`/approvals`)
- 应用场景审批
- 资源申请审批
- 工作流审批
- 三个标签页切换

### 12. AI 论坛 (`/forum`)
- 帖子发布
- 帖子列表
- 分类筛选
- **评论互动** (v1.3.0 新增)

### 13. 系统配置 (`/system`)
- 角色管理（CRUD、分配用户）
- 用户管理（CRUD、分配角色）
- **部门负责人设置** (v1.3.0 新增)

### 14. 站内通知
- 通知列表
- 未读计数
- 标记已读/删除
- 工作流通知自动发送

### 15. 个人工作台 (`/workbench`) (v1.3.0 新增)
- 我的申请（应用场景列表）
- 我的待办（工作流审批列表）
- 我的通知（最近通知列表）
- 快捷入口

---

## 测试数据

**数据记录**:
- 数据集：3 条
- 模型：3 条
- 智能体：3 条
- 应用场景：2 条
- 应用广场：2 条
- 算力资源：2 条
- 论坛帖子：4 条
- 工作流定义：1 条（应用场景审批流程）

**测试用户**:
| 用户名 | 密码 | 角色 | 部门 |
|--------|------|------|------|
| admin | admin123 | admin | - |
| user1 | 123456 | user | 技术部 |
| user2 | 123456 | user | 财务部 |
| reviewer1 | 123456 | reviewer | 审核部 |

**测试角色**:
- `finance_reviewer` - 财务审核员
- `department_manager` - 部门经理
- `tech_reviewer` - 技术审核员
- `project_manager` - 项目经理

---

## 项目结构

```
ai_manage_platform/
├── app/
│   ├── api/              # API 路由
│   │   ├── applications.py
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── datasets.py
│   │   ├── models.py
│   │   ├── agents.py
│   │   ├── app_store.py
│   │   ├── compute.py
│   │   ├── workflow.py
│   │   ├── workflow_def.py
│   │   ├── forum.py
│   │   ├── system.py
│   │   ├── notification.py
│   │   └── application_requests.py
│   ├── core/             # 核心配置
│   │   ├── config.py
│   │   └── database.py
│   ├── models/           # 数据模型
│   │   └── models.py
│   ├── schemas/          # Pydantic Schema
│   │   └── schemas.py
│   └── main.py           # 主入口
├── templates/            # 前端模板
│   ├── base.html         # 基础模板
│   ├── index.html
│   ├── dashboard.html
│   ├── applications.html
│   ├── datasets.html
│   ├── models.html
│   ├── agents.html
│   ├── app_store.html
│   ├── compute.html
│   ├── workflow.html
│   ├── workflow_design.html
│   ├── forum.html
│   ├── system.html
│   ├── approvals.html
│   ├── notifications.html
│   └── workbench.html
├── scripts/              # 工具脚本
│   ├── init_test_data.py
│   └── migrations/
│       ├── add_department_manager_field.py
│       ├── add_workflow_to_application_request.py
│       └── create_forum_comments.py
├── tests/                # 测试文件
└── main.py               # 启动入口
```

---

## 重要说明

### 前端优化
- 所有 `alert/confirm/prompt` 已替换为自定义美化的 Toast/Confirm/Prompt 组件
- Toast 类型：success, error, warning, info
- Confirm 支持自定义确认/取消按钮文本
- Prompt 支持自定义标题和默认值

### 工作流审批流程
1. 用户提交应用场景申报
2. 选择绑定的工作流（可选）
3. 工作流启动，根据节点配置通知审核人
4. 审核人在"我的待办"中审批
5. 每个节点的审批记录可追溯查看

### 部门负责人逻辑
- 在系统配置页面为用户设置"部门负责人"开关
- 工作流节点配置 `department_head` 自动查找当前用户部门负责人
- 工作流节点配置 `applicant_department` 自动查找申请部门负责人

### API 路由前缀
- `/api/applications` - 应用场景
- `/api/datasets` - 数据集
- `/api/models` - 模型
- `/api/agents` - 智能体
- `/api/app-store` - 应用广场
- `/api/compute` - 算力资源
- `/api/workflow` - 业务流程
- `/api/workflow-def` - 工作流定义
- `/api/auth` - 用户认证
- `/api/system` - 系统配置
- `/api/notification` - 站内通知
- `/api/dashboard` - 数据看板
- `/api/forum` - AI 论坛
- `/api/application-requests` - 资源申请

---

## 待办任务

详见 `TODO_PLAN.md`

---

## 快速启动

```bash
# 启动服务器
python main.py

# 访问系统
http://localhost:8000

# 登录
admin / admin123
```

---

## Git 记录

**最新提交**:
- `5aa5366` - feat: v1.3.0 个人工作台、通知中心、论坛评论等功能

**当前分支**: master
**标签**: v1.0, v1.1.0, v1.2.0, v1.3.0
