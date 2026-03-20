#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用场景工作流审批自动化测试
"""
import requests
import json
import os

# 设置输出编码
os.system('chcp 65001 > nul 2>&1')

BASE_URL = "http://localhost:8000"

# 测试账号
ADMIN_USER = {"username": "admin", "password": "admin123"}
REVIEWER_USER = {"username": "reviewer1", "password": "123456"}
TECH_REVIEWER = {"username": "user1", "password": "123456"}  # 假设有技术审核员账号


def login(username, password):
    """登录并获取 token"""
    res = requests.post(f"{BASE_URL}/api/auth/login",
                        data={"username": username, "password": password},
                        headers={"Content-Type": "application/x-www-form-urlencoded"})
    if res.status_code == 200:
        data = res.json()
        return data.get("access_token")
    else:
        print(f"登录失败 ({username}): {res.text}")
        return None


def create_test_application(token, workflow_id=None):
    """创建测试应用"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "title": f"测试应用 - 工作流审批 {workflow_id or '简单审批'}",
        "department": "技术部",
        "contact_info": "test@example.com",
        "business_background": "这是一个测试应用场景",
        "current_pain_points": "测试痛点",
        "expected_value": "测试价值",
        "workflow_definition_id": workflow_id
    }
    res = requests.post(f"{BASE_URL}/api/applications/", headers=headers, json=data)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"创建应用失败：{res.text}")
        return None


def create_workflow(token):
    """创建测试工作流：部门审核 → 技术审核 → 结束"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    workflow = {
        "name": "应用场景审批流程",
        "description": "部门审核和技术审核两个节点",
        "bind_type": "application",
        "nodes": [
            {
                "id": "node_start",
                "type": "start",
                "name": "开始",
                "x": 100,
                "y": 100,
                "config": {}
            },
            {
                "id": "node_dept",
                "type": "review",
                "name": "部门审核",
                "x": 300,
                "y": 100,
                "config": {"approver": "department_manager"}  # 部门经理角色
            },
            {
                "id": "node_tech",
                "type": "review",
                "name": "技术审核",
                "x": 500,
                "y": 100,
                "config": {"approver": "tech_reviewer"}  # 技术审核员角色
            },
            {
                "id": "node_end",
                "type": "end",
                "name": "结束",
                "x": 700,
                "y": 100,
                "config": {}
            }
        ],
        "edges": [
            {"source": "node_start", "target": "node_dept"},
            {"source": "node_dept", "target": "node_tech"},
            {"source": "node_tech", "target": "node_end"}
        ]
    }
    res = requests.post(f"{BASE_URL}/api/workflow-def/", headers=headers, json=workflow)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"创建工作流失败 (状态码 {res.status_code}): {res.text}")
        return None


def start_workflow(token, workflow_def_id, app_id):
    """启动工作流"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "record_type": "application",
        "record_id": app_id,
        "application_id": app_id
    }
    res = requests.post(f"{BASE_URL}/api/workflow-def/{workflow_def_id}/start",
                        headers=headers, json=data)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"启动工作流失败：{res.text}")
        return None


def get_workflow_records(token, app_id):
    """获取应用的工作流记录"""
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/applications/{app_id}/workflow-records", headers=headers)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"获取工作流记录失败：{res.text}")
        return None


def get_my_approvals(token):
    """获取当前用户的待办审批"""
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/workflow-def/approvals/my", headers=headers)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"获取待办审批失败：{res.text}")
        return None


def perform_workflow_action(token, workflow_def_id, record_id, action, comments=""):
    """执行工作流审批操作"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "action": action,  # "approve" or "reject"
        "comments": comments
    }
    res = requests.post(f"{BASE_URL}/api/workflow-def/{workflow_def_id}/record/{record_id}/action",
                        headers=headers, json=data)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"执行工作流操作失败：{res.text}")
        return None


def get_application(token, app_id):
    """获取应用详情"""
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/applications/{app_id}", headers=headers)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"获取应用详情失败：{res.text}")
        return None


def print_separator(title=""):
    print(f"\n{'='*60}")
    if title:
        print(f"  {title}")
    print(f"{'='*60}\n")


def test_workflow_flow():
    """测试完整工作流审批流程"""

    print_separator("测试：应用场景工作流审批流程")

    # 1. 管理员登录
    print("1. 管理员登录...")
    admin_token = login("admin", "admin123")
    if not admin_token:
        print("FAIL: 管理员登录失败")
        return False
    print(f"OK: 管理员登录成功，token: {admin_token[:20]}...")

    # 2. 创建工作流
    print("\n2. 创建测试工作流（部门审核 → 技术审核）...")
    workflow_def = create_workflow(admin_token)
    if not workflow_def:
        print("FAIL: 创建工作流失败")
        return False
    workflow_def_id = workflow_def.get("id")
    print(f"OK: 工作流创建成功，ID: {workflow_def_id}")

    # 3. 创建应用（绑定工作流）
    print("\n3. 创建应用场景（绑定工作流）...")
    app = create_test_application(admin_token, workflow_def_id)
    if not app:
        print("FAIL: 创建应用失败")
        return False
    app_id = app.get("id")
    app_status = app.get("status")
    print(f"OK: 应用创建成功，ID: {app_id}, 状态：{app_status}")

    # 验证：绑定工作流的应用状态应该是 under_review
    if app_status != "under_review":
        print(f"FAIL: 绑定工作流的应用状态应该是 'under_review'，但实际是 '{app_status}'")
        return False
    print("OK: 应用状态正确 (under_review)")

    # 4. 启动工作流
    print("\n4. 启动工作流...")
    workflow_result = start_workflow(admin_token, workflow_def_id, app_id)
    if not workflow_result:
        print("FAIL: 启动工作流失败")
        return False
    print(f"OK: 工作流启动成功，已通知 {workflow_result.get('message', '')}")

    # 5. 获取工作流记录，查看节点状态
    print("\n5. 获取工作流记录...")
    records = get_workflow_records(admin_token, app_id)
    if not records:
        print("FAIL: 获取工作流记录失败")
        return False

    flow_nodes = records.get("flow_nodes", [])
    print(f"OK: 共有 {len(flow_nodes)} 个节点")
    for node in flow_nodes:
        print(f"   - {node.get('name')}: 状态={node.get('status')}, 待处理角色={node.get('pending_role')}")

    # 6. 获取待办审批列表
    print("\n6. 获取待办审批列表（使用部门经理角色）...")
    # 首先给部门经理角色分配用户
    dept_mgr_token = login("user1", "123456")  # 假设 user1 是部门经理
    if dept_mgr_token:
        approvals = get_my_approvals(dept_mgr_token)
        if approvals:
            print(f"OK: 找到 {len(approvals)} 个待办审批")
            for item in approvals:
                print(f"   - 流程：{item.get('definition', {}).get('name')}")
                print(f"     当前节点：{item.get('currentNode', {}).get('name')}")
                print(f"     记录 ID: {item.get('record', {}).get('id')}")
        else:
            print("WARN: 没有找到待办审批（可能需要先分配角色）")
    else:
        print("WARN: 部门经理登录失败")

    # 7. 验证应用状态保持 under_review
    print("\n7. 验证应用状态（工作流进行中）...")
    app_detail = get_application(admin_token, app_id)
    if app_detail:
        status = app_detail.get("status")
        print(f"OK: 应用状态：{status}")
        if status != "under_review":
            print(f"FAIL: 工作流进行中，应用状态应该保持 'under_review'")
            return False
        print("OK: 应用状态正确 (under_review)")

    print_separator("测试通过!")
    print(f"\n测试应用 ID: {app_id}")
    print(f"工作流定义 ID: {workflow_def_id}")
    print("\n手动继续测试:")
    print("1. 访问 /approvals 页面")
    print("2. 在'工作流审批'标签页找到待办")
    print("3. 点击审批，选择'通过'")
    print("4. 重复直到所有节点完成")
    print("5. 验证应用最终状态变为 'approved'")

    return True


def test_simple_approval():
    """测试简单审批流程（不绑定工作流）"""

    print_separator("测试：简单审批流程（不绑定工作流）")

    # 1. 管理员登录
    print("1. 管理员登录...")
    admin_token = login("admin", "admin123")
    if not admin_token:
        print("FAIL: 管理员登录失败")
        return False
    print("OK: 管理员登录成功")

    # 2. 创建应用（不绑定工作流）
    print("\n2. 创建应用场景（不绑定工作流）...")
    app = create_test_application(admin_token, None)
    if not app:
        print("FAIL: 创建应用失败")
        return False
    app_id = app.get("id")
    app_status = app.get("status")
    print(f"OK: 应用创建成功，ID: {app_id}, 状态：{app_status}")

    # 验证：不绑定工作流的应用状态应该是 submitted
    if app_status != "submitted":
        print(f"FAIL: 不绑定工作流的应用状态应该是 'submitted'，但实际是 '{app_status}'")
        return False
    print("OK: 应用状态正确 (submitted)")

    # 3. 使用简单审批接口审批
    print("\n3. 使用简单审批接口审批...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = requests.post(f"{BASE_URL}/api/applications/{app_id}/review?approved=true&comments=测试通过",
                        headers=headers)
    if res.status_code == 200:
        print(f"OK: 审批成功")
    else:
        print(f"FAIL: 审批失败：{res.text}")
        return False

    # 4. 验证应用状态变为 approved
    print("\n4. 验证应用状态...")
    app_detail = get_application(admin_token, app_id)
    if app_detail:
        status = app_detail.get("status")
        print(f"OK: 应用状态：{status}")
        if status != "approved":
            print(f"FAIL: 简单审批后，应用状态应该是 'approved'，但实际是 '{status}'")
            return False
        print("OK: 应用状态正确 (approved)")

    print_separator("测试通过!")
    return True


def test_workflow_block_simple_review():
    """测试：绑定工作流的应用不能被简单审批接口审批"""

    print_separator("测试：绑定工作流的应用阻止简单审批")

    # 1. 管理员登录
    admin_token = login("admin", "admin123")
    if not admin_token:
        print("FAIL: 登录失败")
        return False

    # 2. 创建工作流
    workflow_def = create_workflow(admin_token)
    if not workflow_def:
        print("FAIL: 创建工作流失败")
        return False
    workflow_def_id = workflow_def.get("id")

    # 3. 创建应用（绑定工作流）
    app = create_test_application(admin_token, workflow_def_id)
    if not app:
        print("FAIL: 创建应用失败")
        return False
    app_id = app.get("id")

    # 4. 尝试使用简单审批接口（应该失败）
    print(f"尝试对绑定工作流的应用 (ID: {app_id}) 使用简单审批接口...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = requests.post(f"{BASE_URL}/api/applications/{app_id}/review?approved=true&comments=测试",
                        headers=headers)

    if res.status_code == 400:
        print(f"OK: 接口正确返回错误 (400)")
        print(f"   错误信息：{res.json().get('detail', '')}")
        return True
    else:
        print(f"FAIL: 接口应该返回 400 错误，但实际返回 {res.status_code}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("  应用场景工作流审批系统 - 自动化测试")
    print("=" * 60)

    results = []

    # 测试 1：简单审批流程
    results.append(("简单审批流程", test_simple_approval()))

    # 测试 2：绑定工作流阻止简单审批
    results.append(("绑定工作流阻止简单审批", test_workflow_block_simple_review()))

    # 测试 3：完整工作流流程
    results.append(("完整工作流审批流程", test_workflow_flow()))

    # 打印汇总
    print_separator("测试汇总")
    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"  {symbol} {name}: {status}")

    all_passed = all(r[1] for r in results)
    result_text = "全部通过 [OK]" if all_passed else "部分失败 [FAIL]"
    print(f"\n总结果：{result_text}")
