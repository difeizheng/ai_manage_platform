# AI 管理平台 - 项目状态

**更新时间**: 2026-03-19
**当前版本**: v1.1.0
**GitHub**: https://github.com/difeizheng/ai_manage_platform

---

## 最新版本变更 (v1.1.0)

### 新增功能
- **应用场景详情查看** - 点击"查看"按钮弹出模态框展示完整信息
- **审批流程可视化** - 显示每个审批节点的状态、审批人、审批意见
- **工作流记录查询 API** - `/api/applications/{app_id}/workflow-records`

### 文件变更
- `app/api/applications.py` - 新增 workflow-records 接口
- `templates/applications.html` - 添加详情模态框

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
- **详情查看（含审批流程）**
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

### 13. 系统配置 (`/system`)
- 角色管理（CRUD、分配用户）
- 用户管理（CRUD、分配角色）

### 14. 站内通知
- 通知列表
- 未读计数
- 标记已读/删除
- 工作流通知自动发送

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
│   │   └── notification.py
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
│   └── notifications.html (待创建)
├── scripts/              # 工具脚本
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

---

## 待办任务

1. **部门负责人逻辑** - 工作流中 `department_head` 和 `applicant_department` 审核人类型需要根据用户部门查找负责人
2. **通知详情页** - `/notifications` 页面尚未创建
3. **资源申请工作流绑定** - 资源申请目前使用简单审批，可绑定工作流

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
- `1b7af2c` - feat: 优化应用场景查看详情，显示审批流程信息 (v1.1.0)
- `b8c2c3f` - feat: 添加完整的 AI 管理平台功能 (v1.0)

**当前分支**: master
**标签**: v1.0, v1.1.0
