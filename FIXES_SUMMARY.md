# 工作流审批系统修复总结

## 问题描述

用户 reviewer1 登录后可收到工作流审批通知，但在"我的待办"页面看不到待审批任务。

## 根本原因

1. **端点路径不匹配**: 前端调用 `/api/workflow/my-approvals`，但后端端点定义在 `workflow-def` 路由下
2. **路由冲突**: `/my-approvals` 路由定义在 `/{definition_id}` 路由之后，导致 FastAPI 将"my-approvals"解析为 `definition_id` 参数
3. **current_node_id 未更新**: `start_workflow` 函数中，工作流记录的 `current_node_id` 在创建时设置为 start 节点，但在获取下一个审核节点后没有更新

## 修复内容

### 1. app/api/workflow_def.py

- 将 `@router.get("/approvals/my")` 路由移动到文件顶部，在 `@router.get("/{definition_id}")` 之前定义
- 在 `start_workflow` 函数中添加代码，当有下一个审核节点时更新 `workflow_record.current_node_id`

```python
# 修复前
@router.post("/{definition_id}/start")
async def start_workflow(...):
    # ... 创建工作流记录，current_node_id 设置为 start_node
    # 获取下一个节点
    next_node_info = get_next_node(nodes, start_node.get('id'), edges)
    next_node = next_node_info.get('next_node')

    # 获取审核人列表并创建通知
    approvers = []
    if next_node and next_node.get('type') in ['review', 'approve']:
        approvers = get_approver_users(next_node.get('config', {}), db, current_user)
        # ... 创建通知
    db.commit()

# 修复后
@router.post("/{definition_id}/start")
async def start_workflow(...):
    # ... 创建工作流记录，current_node_id 设置为 start_node
    # 获取下一个节点
    next_node_info = get_next_node(nodes, start_node.get('id'), edges)
    next_node = next_node_info.get('next_node')

    # 获取审核人列表并创建通知
    approvers = []
    if next_node and next_node.get('type') in ['review', 'approve']:
        # 关键修复：更新当前流程记录的节点为下一个审核节点
        workflow_record.current_node_id = next_node.get('id')

        approvers = get_approver_users(next_node.get('config', {}), db, current_user)
        # ... 创建通知
    db.commit()
```

### 2. templates/approvals.html

- 将 `loadWorkflowApprovals()` 方法中的端点路径从 `/api/workflow/my-approvals` 改为 `/api/workflow-def/approvals/my`

```javascript
// 修复前
async loadWorkflowApprovals() {
    const res = await fetch('/api/workflow/my-approvals', {
        headers: { 'Authorization': 'Bearer ' + token }
    });
}

// 修复后
async loadWorkflowApprovals() {
    const res = await fetch('/api/workflow-def/approvals/my', {
        headers: { 'Authorization': 'Bearer ' + token }
    });
}
```

### 3. tests/test_workflow.py

- 更新 `get_my_approvals()` 函数使用正确的端点路径

```python
# 修复前
res = requests.get(f"{BASE_URL}/api/workflow/my-approvals", headers=headers)

# 修复后
res = requests.get(f"{BASE_URL}/api/workflow-def/approvals/my", headers=headers)
```

## 验证结果

1. 所有三个自动化测试通过：
   - 简单审批流程：PASS
   - 绑定工作流阻止简单审批：PASS
   - 完整工作流审批流程：PASS

2. reviewer1 用户可以正确获取待办审批列表
3. 工作流记录的 `current_node_id` 正确指向当前审核节点
4. 审批流程正确流转到下一个节点

## 注意事项

- 使用 `/approvals/my` 而不是 `/my-approvals` 是为了避免与 `/{definition_id}` 路由冲突
- 如需修改端点路径，请确保在 `api_router` 中注册时在动态参数路由之前定义
