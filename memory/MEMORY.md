# AI 管理平台 - 记忆文件

**更新时间**: 2026-03-20
**当前版本**: v1.3.0
**GitHub**: https://github.com/difeizheng/ai_manage_platform

---

## 项目状态

完整的项目状态已保存到 `status.md`，包含：
- 所有已完成功能模块
- 测试数据和测试账号
- 项目结构和文件说明
- 待办任务

---

## 快速参考

**启动命令**: `python main.py`

**访问地址**:
- 个人工作台：/workbench（推荐首页）
- 站内通知：/notifications
- 应用场景：/applications
- 工作流设计：/workflow-design
- 系统配置：/system
- 我的待办：/approvals
- AI 论坛：/forum

**登录账号**: `admin / admin123`

---

## 主要功能

1. **用户认证** - JWT Token
2. **应用场景** - 申报/审批/详情查看（含审批流程）
3. **数据集/模型/智能体** - CRUD 管理
4. **工作流设计器** - 可视化流程配置
5. **我的待办** - 三类审批（应用场景/资源申请/工作流）
6. **系统配置** - 角色/用户管理（支持设置部门负责人）
7. **站内通知** - 通知列表/标记已读/删除
8. **个人工作台** - 我的申请/我的待办/我的通知/快捷入口
9. **资源申请工作流** - 资源申请支持绑定工作流审批
10. **AI 论坛** - 帖子发布/分类筛选/评论互动

---

## Git 状态

**分支**: master
**标签**: v1.0, v1.1.0, v1.2.0, v1.3.0
**最新提交**: `5aa5366` - feat: v1.3.0 个人工作台、通知中心、论坛评论等功能

---

## v1.3.0 新增内容 (2026-03-20)

### Phase 1 (紧急) ✅
1. **通知中心页面** - 完整的通知管理功能
2. **部门负责人逻辑** - 支持 `department_head` 和 `applicant_department` 审核人类型

### Phase 2 (重要) ✅
3. **资源申请工作流绑定** - 资源申请可绑定工作流审批
4. **个人工作台** - 用户个人首页，汇总申请/审批/通知

### Phase 3 (优化) ✅
5. **论坛评论功能** - 支持发表评论、查看评论、删除评论

---

## 剩余待办

| 优先级 | 任务 |
|--------|------|
| 🟢 低 | 工作流节点扩展（条件分支/并行/抄送/会签） |
| 🟢 低 | 数据统计与报表 |
| 🟢 低 | 文件上传完善 |
| 🟢 低 | 系统配置完善（部门管理） |

---

## 问题修复记录

### 2026-03-23: 资源工作流审批功能修复

**问题**: 资源（数据集、模型、智能体、应用广场、算力资源）创建工作流绑定时，创建后状态为 "under_review" 但审批 API 找不到待办审批。

**根本原因**:
1. 资源创建时工作流记录的 `current_node_id` 设置为 start 节点 ID，但 `get_my_approvals` API 只返回 type 为 `review/approve` 的节点
2. 工作流审批完成后没有更新资源状态

**修复方案**:
1. 在 5 个资源 API 文件添加 `_get_next_node_id` 辅助函数，创建 workflow_record 后自动推进到 review 节点
2. 在 `workflow_def.py` 的 `perform_action` 中添加资源状态更新逻辑，流程完成时更新资源状态为 available/published

**涉及文件**:
- `app/api/datasets.py`
- `app/api/models.py`
- `app/api/agents.py`
- `app/api/app_store.py`
- `app/api/compute.py`
- `app/api/workflow_def.py`
- `tests/test_resource_workflow_simple.py`

**测试结果**: 全部通过 ✅

---

### 2026-03-23: 个人工作台 500 错误修复

**问题**: 访问 `/workbench` 返回 500 Internal Server Error

**根本原因**:
1. 模板混用 Jinja2 (`{{ }}`) 和 Vue.js 语法，导致 Jinja2 解析失败
2. 路由没有传递必要的服务器端变量

**修复方案**:
1. 使用 `{% raw %}` 和 `{% endraw %}` 包裹 Vue.js 模板内容
2. 将 Vue.js 的 `{{ var || default }}` 改为 `<span v-text="var || 'default'"></span>`
3. 将 Vue.js 的 `{{ obj?.prop }}` 改为 `{% raw %}{{ obj.prop if obj else "" }}{% endraw %}`
4. 添加 `get_current_user_optional` 函数支持可选登录状态
5. 路由传递统计数据：user_name, my_applications_count, my_approvals_count, unread_notifications_count, applications_total

**涉及文件**:
- `templates/workbench.html`
- `app/main.py`

**测试结果**: 访问正常，返回 200 OK ✅
