---
name: 2026-04-02 Bug 修复
description: 应用场景列表显示、站内通知页面、工作流审批问题修复
type: feedback
---

## 2026-04-02 Bug 修复记录

### 问题 1: 应用场景列表不显示数据

**现象**: 访问 `/applications` 页面，列表无数据

**根本原因**:
1. API 返回 `PaginatedResponse` 格式（包含 `items`、`total` 等字段），前端直接赋值 `data` 而非 `data.items`
2. `PaginatedResponse.create()` 方法传入 SQLAlchemy 模型，Pydantic 无法序列化

**修复方案**:
1. 前端：`this.applications = data.items || data;`
2. 后端：使用 `PaginatedResponse[ApplicationResponse].model_validate({...})` 指定泛型类型

**涉及文件**:
- `templates/applications.html` - 第 386 行
- `app/api/applications.py` - 第 80-85 行

---

### 问题 2: 站内通知页面 500 错误

**现象**: 访问 `/notifications` 页面报 500 错误

**根本原因**:
1. 模态框在 `{% endraw %}` 标签外，Vue.js 语法 `{{ selectedItem?.title }}` 被 Jinja2 解析
2. `{{ }}` 中的 `?.` 可选链语法导致 Jinja2 报错 `unexpected char '?'`
3. API 路径错误：前端使用 `/notification/my` 但实际是 `/api/notification/my`
4. 多余的 `</div>` 闭合标签

**修复方案**:
1. 模态框移入 `{% raw %}` 标签内
2. `{{ x?.y }}` 改为 `v-text="x ? x.y : ''"`
3. 所有 API 路径添加 `/api` 前缀
4. 移除多余的 `</div>`

**涉及文件**:
- `templates/notifications.html` - 整体重构

---

### 问题 3: 工作流审批失败

**现象**: 点击"通过"提交审批，弹框提示"请稍后重试或联系管理员"

**根本原因**: `log_action()` 调用时传入 `user=current_user` 但函数参数是 `user_id` 和 `username`

**修复方案**: 
```python
log_action(
    db=db,
    user_id=current_user.id,
    username=current_user.username,
    # ...
)
```

**涉及文件**:
- `app/api/workflow_def.py` - 第 961-969 行

---

### 版本信息
- **Tag**: v1.4.1
- **Commit**: 7618ebd


---

## 最新版本变更 (v1.4.0)

### 新增功能模块

#### 1. 邮件通知服务
- **邮件发送** - SMTP 发送、HTML 模板渲染
- **审批结果邮件** - 美观的审批通过/拒绝邮件模板
- **工作流通知邮件** - 待办审批通知邮件
- **邮件设置** - 用户可配置邮件开关、免打扰时段
- **邮件日志** - 发送记录追踪（成功/失败状态）

#### 2. WebSocket 实时通知
- **实时连接** - JWT 认证的 WebSocket 端点
- **连接管理器** - 支持多端连接、在线状态管理
- **心跳机制** - 客户端心跳保活
- **实时推送** - 审批通知、系统通知实时送达
- **在线用户** - 获取在线用户列表 API

#### 3. 工作流通知集成
- **启动通知** - 工作流启动时通知审核人
- **节点通知** - 审核/审批节点通知（普通、并行、条件分支）
- **抄送通知** - 抄送节点自动通知
- **结果通知** - 审批通过/拒绝时通知申请人
- **多渠道通知** - 站内通知 + WebSocket + 邮件

#### 4. 文件管理服务 🆕
- **文件上传** - 白名单校验、大小限制 (100MB)、哈希去重 (SHA256)
- **文件下载** - 权限控制（上传者/admin/公开）
- **文件删除** - 软删除模式
- **文件列表** - 我的文件、公开文件、分页过滤

#### 5. 数据分析与报表 🆕
- **报表管理** - 创建/更新/删除报表，支持 JSON/CSV 导出
- **趋势分析** - 应用场景、模型、数据集新增趋势
- **资源分析** - 算力使用情况、部门资源分布
- **审批效率** - 工作流审批统计

### 新增 API 端点

| 模块 | 端点 | 功能 |
|------|------|------|
| 邮件通知 | `GET /api/email/settings` | 获取邮件设置 |
| 邮件通知 | `PUT /api/email/settings` | 更新邮件设置 |
| 邮件通知 | `POST /api/email/test` | 发送测试邮件 |
| 邮件通知 | `GET /api/email/logs` | 邮件发送记录 |
| WebSocket | `GET /api/ws/notifications` | WebSocket 通知端点 |
| WebSocket | `GET /api/ws/online-users` | 在线用户列表 |
| 文件管理 | `POST /api/files/upload` | 上传文件 |
| 文件管理 | `GET /api/files/{id}` | 下载文件 |
| 文件管理 | `DELETE /api/files/{id}` | 删除文件 |
| 文件管理 | `GET /api/files/my` | 我的文件 |
| 数据分析 | `GET /api/analytics/reports` | 报表列表 |
| 数据分析 | `POST /api/analytics/reports` | 创建报表 |
| 数据分析 | `GET /api/analytics/trend/*` | 趋势分析 |
| 数据分析 | `GET /api/analytics/resource/*` | 资源分析 |
| 数据分析 | `GET /api/analytics/workflow/*` | 审批效率 |

### 文件变更
- 新建 `app/core/mail.py` - 邮件服务核心模块
- 新建 `app/api/email.py` - 邮件通知 API
- 新建 `app/api/websocket.py` - WebSocket 实时通知
- 新建 `app/api/files.py` - 文件管理 API
- 新建 `app/api/analytics.py` - 数据分析 API
- 更新 `app/api/workflow_def.py` - 集成邮件和 WebSocket 通知
- 更新 `app/api/__init__.py` - 注册新路由
- 更新 `app/schemas/schemas.py` - 修复 ConfigDict 导入
- 新建 `.env.example` - 环境变量配置示例
- 新建 `NOTIFICATION_FEATURES.md` - 功能使用说明

### 数据库变更
- 新增 `email_logs` 表 - 邮件发送日志
- 新增 `notification_settings` 表 - 用户通知设置
- 新增 `files` 表 - 文件元数据
- 新增 `reports` 表 - 报表定义
- 新增 `report_cache` 表 - 报表数据缓存

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
- 邮件通知（SMTP）🆕
- WebSocket 实时通知 🆕
- 通知设置（免打扰时段）

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
- 邮件配置：复制 `.env.example` 为 `.env` 并配置 SMTP 参数

## 邮件配置示例

```env
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=noreply@example.com
```

## WebSocket 前端连接示例

```javascript
const token = localStorage.getItem('token');
const ws = new WebSocket(`ws://localhost:8000/api/ws/notifications?token=${token}`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'notification') {
        // 显示通知
    }
};
```

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
