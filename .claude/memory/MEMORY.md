# AI 管理平台 - 项目状态

**更新时间**: 2026-03-24
**当前版本**: v1.4.0
**GitHub**: https://github.com/difeizheng/ai_manage_platform

---

## 最新版本变更 (v1.4.0)

### 新增功能模块

#### 1. 用户权限增强
- **忘记密码功能** - 邮箱验证码重置密码（24 小时过期）
- **个人资料完善** - 个人简介、技能标签、项目经历
- **头像上传** - 支持 jpg/png/gif/webp，最大 5MB
- **职位管理** - 职位定义、用户职位分配
- **部门层级** - 多级部门树形结构

#### 2. 文件管理服务
- **文件上传** - 白名单校验、大小限制 (100MB)、哈希去重 (SHA256)
- **文件下载** - 权限控制（上传者/admin/公开）
- **文件删除** - 软删除模式
- **文件列表** - 我的文件、公开文件、分页过滤

#### 3. 数据分析与报表
- **报表管理** - 创建/更新/删除报表，支持 JSON/CSV 导出
- **趋势分析** - 应用场景、模型、数据集新增趋势
- **资源分析** - 算力使用情况、部门资源分布
- **审批效率** - 工作流审批统计

#### 4. 邮件通知
- **通知设置** - 邮件开关、免打扰时段
- **邮件发送** - SMTP 发送、模板系统
- **邮件日志** - 发送记录追踪

### 新增 API 端点

| 模块 | 端点 | 功能 |
|------|------|------|
| 用户认证 | `POST /api/auth/forgot-password` | 忘记密码 |
| 用户认证 | `POST /api/auth/reset-password` | 重置密码 |
| 用户认证 | `GET/PUT /api/auth/me/profile` | 个人资料 |
| 用户认证 | `POST /api/auth/me/avatar` | 头像上传 |
| 用户管理 | `GET/POST /api/users/positions` | 职位管理 |
| 用户管理 | `GET/POST /api/users/departments` | 部门管理 |
| 文件管理 | `POST /api/files/upload` | 上传文件 |
| 文件管理 | `GET /api/files/my` | 我的文件 |
| 数据分析 | `GET/POST /api/analytics/reports` | 报表管理 |
| 数据分析 | `GET /api/analytics/trend/*` | 趋势分析 |
| 通知 | `GET/PUT /api/notification/settings` | 通知设置 |
| 通知 | `POST /api/notification/send-email` | 发送邮件 |

### 数据库变更
- 新增 12 个表：
  - `files` - 文件管理
  - `email_logs` - 邮件日志
  - `notification_settings` - 通知设置
  - `reports` - 报表定义
  - `report_cache` - 报表数据缓存
  - `password_reset_tokens` - 密码重置令牌
  - `user_profiles` - 用户 profile 扩展
  - `positions` - 职位表
  - `user_positions` - 用户职位关联
  - `audit_logs` - 审计日志
  - `login_logs` - 登录日志
  - `application_requests` - 资源申请（新增工作流字段）

### 文件变更
- 新建 `app/api/auth.py` - 扩展忘记密码、个人资料 API
- 新建 `app/api/users.py` - 用户管理、职位、部门 API
- 新建 `app/api/files.py` - 文件管理 API
- 新建 `app/api/analytics.py` - 数据分析 API
- 更新 `app/api/notification.py` - 扩展邮件通知 API
- 更新 `app/models/models.py` - 新增 12 个模型类
- 更新 `app/schemas/schemas.py` - 新增对应 Schema
- 更新 `app/core/exceptions.py` - 修复 request.path 错误
- 新建 `migrate.py` - 数据库迁移脚本
- 新建 `docs/feature_roadmap.md` - 功能规划文档

---

## 上一版本变更 (v1.3.1)

### 新增功能
- **模型申请工作流** - 申请模型时自动启动工作流审批
- **智能体申请工作流** - 申请智能体时自动启动工作流审批
- **算力资源申请工作流** - 申请算力资源时自动启动工作流审批
- **应用广场申请工作流** - 申请应用时自动启动工作流审批

### 文件变更
- 更新 `app/api/models.py` - `request_model_access` 函数
- 更新 `app/api/agents.py` - `request_agent_access` 函数
- 更新 `app/api/compute.py` - `request_compute_resource` 函数
- 更新 `app/api/app_store.py` - 新增 `request_app_store_item_access` 函数

---

## 上一版本变更 (v1.3.0)

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

## 已完成功能模块

### 1. 用户认证系统
- JWT Token 认证
- 登录/登出功能
- 用户角色权限管理
- **忘记密码** - 邮箱验证码重置
- **个人资料** - 简介、技能、项目、头像
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
- 数据集申请工作流

### 5. 模型管理 (`/models`)
- 模型上传/CRUD
- 文件上传支持
- 模型申请工作流

### 6. 智能体管理 (`/agents`)
- 智能体 CRUD
- 状态管理
- 智能体申请工作流

### 7. 算力资源管理 (`/compute`)
- 资源类型管理
- 资源分配和调度
- 算力资源申请工作流

### 8. 应用广场管理 (`/app-store`)
- 应用发布/CRUD
- 应用申请工作流

### 9. 审批工作流系统
- 工作流定义和管理
- 多级审批支持
- 审批人类型：`admin`、`department_head`、`applicant_department`、角色 Code

### 10. 论坛系统
- 帖子发布和管理
- 评论功能（支持删除）

### 11. 通知中心
- 站内通知管理
- 通知与用户关联
- 邮件通知（SMTP）

### 12. 文件管理 (`/api/files`) 🆕
- 文件上传（白名单、哈希去重）
- 文件下载/删除
- 文件列表

### 13. 用户管理 (`/api/users`) 🆕
- 职位管理
- 部门管理（树形）
- 用户列表/详情

### 14. 数据分析 (`/api/analytics`) 🆕
- 报表管理
- 趋势分析
- 资源使用分析

---

## 技术栈
- **后端**: Python FastAPI
- **前端**: HTML + Bootstrap + Jinja2 模板
- **数据库**: SQLite (`data/ai_platform.db`)
- **认证**: JWT

---

## 常用命令
- 启动服务：`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- 初始化数据：`python init_data.py`
- 数据库迁移：`python migrate.py`
- 运行测试：`python test_new_api.py`

---

## 重要修复记录 (2026-03-24)

### 问题 1: 数据集申请未进入工作流审批
**问题描述**: 用户申请数据集后，申请记录状态为 `pending`，未启动工作流，审批人收不到通知。

**根本原因**:
1. 服务器进程无法热重载代码，需要使用 `kill -9` 强制重启
2. 数据库路径是 `data/ai_platform.db`，不是项目根目录下的 `ai_platform.db`

**解决方案**:
1. 修改 `app/api/datasets.py` 的 `request_dataset_access` 函数，在创建 ApplicationRequest 时：
   - 从数据集读取 `workflow_definition_id`
   - 如果有工作流绑定，创建 WorkflowRecord 并发送通知给审核人
2. 添加 `Notification` 模型导入
3. 强制重启服务器使代码生效

**代码变更**:
```python
# app/api/datasets.py - request_dataset_access 函数
# 新增：检查数据集的工作流绑定并启动审批流程
workflow_definition_id = dataset.workflow_definition_id
if workflow_definition_id:
    # 创建工作流记录
    # 获取下一个审核节点
    # 发送通知给审核人
```

### 问题 2: 审批人通知逻辑
**问题描述**: 通知发送给了 `reviewer1` 用户，而不是 `admin` 用户。

**原因**: 工作流配置的审核人是 `department_manager` 角色，`admin` 用户没有该角色。

**解决方案**: 给 `admin` 用户添加 `department_manager` 角色，并设置部门信息。

### 问题 3: 模型/智能体/应用广场/算力资源申请不走工作流
**问题描述**: 2026-03-24 修改代码后，申请模型、智能体、应用广场、算力资源时，没有触发工作流审批。

**根本原因**:
1. 早期创建的资源记录（模型 ID 1-3、智能体 ID 1-5、应用广场 ID 1-2、算力资源 ID 1-3）没有绑定工作流定义
2. 数据集已经绑定了工作流 (ID 10)，所以数据集申请正常

**解决方案**:
1. 批量更新现有资源，绑定对应的工作流定义：
   - 模型 -> 工作流 ID 11 (model 审批流程)
   - 智能体 -> 工作流 ID 12 (agent 审批流程)
   - 应用广场 -> 工作流 ID 13 (app_store 审批流程)
   - 算力资源 -> 工作流 ID 14 (compute_resource 审批流程)
2. 修改 API 代码，为申请接口添加工作流审批逻辑
3. 重启服务使更改生效

**代码变更**:
- `app/api/models.py` - `request_model_access` 函数
- `app/api/agents.py` - `request_agent_access` 函数
- `app/api/compute.py` - `request_compute_resource` 函数
- `app/api/app_store.py` - 新增 `request_app_store_item_access` 函数

---

## API 端点摘要

### 数据集相关
- `GET /api/datasets/` - 获取数据集列表
- `GET /api/datasets/{id}` - 获取数据集详情
- `POST /api/datasets/` - 创建数据集
- `POST /api/datasets/{id}/request` - 申请数据集使用权限（自动启动工作流）

### 模型相关
- `GET /api/models/` - 获取模型列表
- `GET /api/models/{id}` - 获取模型详情
- `POST /api/models/` - 创建/上传模型
- `POST /api/models/{id}/request` - 申请模型使用权限（自动启动工作流）

### 智能体相关
- `GET /api/agents/` - 获取智能体列表
- `GET /api/agents/{id}` - 获取智能体详情
- `POST /api/agents/` - 创建智能体
- `POST /api/agents/{id}/request` - 申请智能体使用权限（自动启动工作流）

### 算力资源相关
- `GET /api/compute/` - 获取算力资源列表
- `GET /api/compute/{id}` - 获取算力资源详情
- `POST /api/compute/` - 创建算力资源
- `POST /api/compute/{id}/request` - 申请算力资源使用权限（自动启动工作流）

### 应用广场相关
- `GET /api/app-store/` - 获取应用广场列表
- `GET /api/app-store/{id}` - 获取应用详情
- `POST /api/app-store/` - 发布应用
- `POST /api/app-store/{id}/request` - 申请应用使用权限（自动启动工作流）

### 资源申请相关
- `GET /api/application-requests/` - 获取资源申请列表
- `GET /api/application-requests/my` - 获取我的资源申请
- `POST /api/application-requests/` - 创建资源申请

### 工作流相关
- `GET /api/workflow-def/approvals/my` - 获取我的待办审批
- `POST /api/resource-workflow/resource/{type}/{id}/start-workflow` - 启动资源工作流
- `GET /api/resource-workflow/resource-approvals/my` - 获取我的资源审批

### 通知相关
- `GET /api/notification/my` - 获取我的通知
- `PUT /api/notification/{id}/read` - 标记通知为已读
- `DELETE /api/notification/{id}` - 删除通知
