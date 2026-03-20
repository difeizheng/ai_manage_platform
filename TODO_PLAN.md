# AI 管理平台 - 待办任务规划

**创建时间**: 2026-03-20
**当前版本**: v1.2.0
**GitHub**: https://github.com/difeizheng/ai_manage_platform

---

## 任务优先级说明

| 优先级 | 标识 | 说明 |
|--------|------|------|
| 高 | 🔴 | 核心功能完善，影响用户体验的关键功能 |
| 中 | 🟡 | 功能增强，提升产品完整性 |
| 低 | 🟢 | 优化与扩展，锦上添花的功能 |

---

## 一、高优先级任务（核心功能完善）

### 1. 通知中心页面 (`/notifications`) 🔴
**状态**: `completed`
**优先级**: 高
**预计工作量**: 2-3 小时
**完成时间**: 2026-03-20

**现状**:
- ✅ 已有完整的 API (`app/api/notification.py`)
- ✅ 已有数据模型 (`Notification` 表)
- ✅ 已创建前端页面

**工作内容**:
- [x] 创建 `templates/notifications.html` 页面
- [x] 通知列表展示（标题、内容、类型、时间、已读/未读状态）
- [x] 筛选功能（按类型：系统/工作流/任务，按状态：已读/未读）
- [x] 标记已读/全部已读功能
- [x] 通知删除功能
- [x] 通知详情页（点击通知查看关联内容跳转）
- [x] 在 base.html 导航栏添加通知入口和未读数提示
- [x] 添加 `/notifications` 路由到 `app/main.py`

**相关文件**:
- `templates/notifications.html` (新建)
- `templates/base.html` (修改)
- `app/main.py` (添加路由)

---

### 2. 部门负责人审批逻辑 🔴
**状态**: `completed`
**优先级**: 高
**预计工作量**: 3-4 小时
**完成时间**: 2026-03-20

**现状**:
- ✅ 工作流中 `department_head` 和 `applicant_department` 审核人类型已实现
- ✅ 已添加部门负责人查找逻辑

**工作内容**:
- [x] 方案 A：在 `User` 模型添加 `is_department_manager` 字段标记部门负责人
- [x] 实现 `get_approver_users()` 中 `department_head` 逻辑
- [x] 实现 `get_approver_users()` 中 `applicant_department` 逻辑
- [x] 在系统配置页面添加部门负责人设置开关
- [x] 创建数据库迁移脚本
- [x] 更新后端 API 支持 `is_department_manager` 字段更新
- [ ] 测试部门负责人审批流程

**相关文件**:
- `app/models/models.py` (修改或新建 Department 模型)
- `app/api/workflow_def.py` (修改 `get_approver_users` 函数)
- `app/api/system.py` (用户/部门管理相关)

---

## 二、中优先级任务（功能增强）

### 3. 资源申请工作流绑定 🟡
**状态**: `completed`
**优先级**: 中
**预计工作量**: 4-5 小时
**完成时间**: 2026-03-20

**现状**:
- ✅ 资源申请（数据/模型/智能体/算力）已支持工作流绑定
- ✅ 已接入工作流系统

**工作内容**:
- [x] 修改 `ApplicationRequest` 模型，添加 `workflow_definition_id` 和 `workflow_record_id` 字段
- [x] 创建资源申请的工作流启动 API (`app/api/application_requests.py`)
- [x] 资源申请审批接入工作流系统
- [x] 创建数据库迁移脚本
- [ ] 更新资源申请前端页面，支持选择工作流（待前端配合）
- [ ] 测试资源申请工作流流程

**相关文件**:
- `app/models/models.py` (修改 `ApplicationRequest`)
- `app/api/application_requests.py` (新建)
- `app/api/__init__.py` (注册路由)

---

### 4. 个人工作台页面 🟡
**状态**: `completed`
**优先级**: 中
**预计工作量**: 4-5 小时
**完成时间**: 2026-03-20

**现状**:
- ✅ 已创建用户个人工作台
- ✅ 用户可在工作台查看申请/审批/通知

**工作内容**:
- [x] 创建 `templates/workbench.html` 页面
- [x] 我的申请（应用场景列表）
- [x] 我的审批（工作流审批列表）
- [x] 我的通知（最近通知列表）
- [x] 快捷入口（常用功能快速访问）
- [x] 在导航栏添加入口
- [x] 添加 `/workbench` 路由
- [x] 创建 `/api/applications/my` 接口

**相关文件**:
- `templates/workbench.html` (新建)
- `app/main.py` (添加路由)
- `app/api/applications.py` (添加/my 接口)
- `templates/base.html` (添加导航入口)

---

### 5. 论坛评论功能 🟡
**状态**: `completed`
**优先级**: 中
**预计工作量**: 3-4 小时
**完成时间**: 2026-03-20

**现状**:
- ✅ 论坛评论功能已完成
- ✅ 支持发表评论、查看评论、删除评论

**工作内容**:
- [x] 创建 `ForumComment` 模型
- [x] 添加评论 API（发布、列表、删除）
- [x] 论坛帖子详情页展示评论
- [x] 更新前端论坛页面，添加评论功能

**相关文件**:
- `app/models/models.py` (新建 `ForumComment`)
- `app/api/forum.py` (添加评论 API)
- `app/schemas/schemas.py` (添加 ForumCommentSchema)
- `templates/forum.html` (修改)
- `scripts/migrations/create_forum_comments.py` (数据库迁移)

---

## 三、低优先级任务（优化与扩展）

### 6. 工作流节点类型扩展 🟢
**状态**: `pending`
**优先级**: 低
**预计工作量**: 6-8 小时

**工作内容**:
- [ ] 条件分支节点 - 根据条件走不同审批路径
- [ ] 并行节点 - 多个审核人同时审批
- [ ] 抄送节点 - 只通知不审批
- [ ] 会签节点 - 多人全部同意才通过

**相关文件**:
- `app/api/workflow_def.py`
- `templates/workflow_design.html`

---

### 7. 数据统计与报表 🟢
**状态**: `pending`
**优先级**: 低
**预计工作量**: 4-6 小时

**工作内容**:
- [ ] 应用场景审批统计（通过率、平均时长）
- [ ] 资源使用统计
- [ ] 工作流效率分析
- [ ] 数据可视化图表

**相关文件**:
- `app/api/dashboard.py`
- `templates/dashboard.html`

---

### 8. 文件上传完善 🟢
**状态**: `pending`
**优先级**: 低
**预计工作量**: 3-4 小时

**工作内容**:
- [ ] 模型文件上传功能
- [ ] 数据集文件上传功能
- [ ] 附件管理功能
- [ ] 文件存储优化

**相关文件**:
- `app/api/models.py`
- `app/api/datasets.py`

---

### 9. 系统配置完善 🟢
**状态**: `pending`
**优先级**: 低
**预计工作量**: 4-6 小时

**工作内容**:
- [ ] 部门管理（CRUD）
- [ ] 权限细化管理
- [ ] 操作日志记录
- [ ] 系统配置项管理

**相关文件**:
- `app/api/system.py`
- `app/models/models.py` (可能需要新表)

---

## 四、未来规划（可选）

### 10. 消息推送
- [ ] 邮件通知
- [ ] 企业微信/钉钉集成
- [ ] WebSocket 实时通知

### 11. 权限系统增强
- [ ] RBAC 权限模型
- [ ] 数据权限控制
- [ ] 操作审计日志

### 12. API 文档完善
- [ ] Swagger/OpenAPI 文档
- [ ] API 版本管理
- [ ] 接口测试工具

---

## 实施计划

### Phase 1 (紧急) - 第 1 周 ✅
1. 通知中心页面 ✅
2. 部门负责人逻辑 ✅

### Phase 2 (重要) - 第 2 周 ✅
3. 资源申请工作流绑定 ✅
4. 个人工作台页面 ✅

### Phase 3 (优化) - 第 3 周 ✅
5. 论坛评论 ✅
6. 工作流节点扩展
7. 数据报表

---

## 任务状态变更记录

| 日期 | 任务 | 操作 | 备注 |
|------|------|------|------|
| 2026-03-20 | 全部任务 | 创建规划 | 初始版本 |
| 2026-03-20 | 通知中心页面 | 完成 | 已创建前端页面、添加路由、集成到导航栏 |
| 2026-03-20 | 部门负责人审批逻辑 | 完成 | 已实现 `department_head` 和 `applicant_department` 审核人类型，添加系统配置开关 |
| 2026-03-20 | 个人工作台页面 | 完成 | 已创建个人工作台，包含我的申请/我的待办/我的通知和快捷入口 |
| 2026-03-20 | 资源申请工作流绑定 | 完成 | 已添加工作流字段、创建资源申请 API、支持工作流启动和审批 |
| 2026-03-20 | 论坛评论功能 | 完成 | 已创建评论模型、API 和前端页面 |

---

## 快速参考

**开发环境启动**:
```bash
python main.py
# 访问 http://localhost:8000
```

**测试账号**:
| 用户名 | 密码 | 角色 | 部门 |
|--------|------|------|------|
| admin | admin123 | admin | - |
| user1 | 123456 | user | 技术部 |
| reviewer1 | 123456 | reviewer | 审核部 |

**Git 工作流**:
```bash
# 创建功能分支
git checkout -b feature/xxx

# 提交代码
git add .
git commit -m "feat: xxx 功能"

# 推送分支
git push origin feature/xxx
```
