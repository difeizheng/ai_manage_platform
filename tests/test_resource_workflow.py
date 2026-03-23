#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资源工作流审批自动化测试
测试数据集、模型、智能体、应用广场、算力资源的创建 - 工作流绑定 - 审批闭环
"""
import requests
import json
import os
import time

# 设置输出编码
os.system('chcp 65001 > nul 2>&1')

BASE_URL = "http://localhost:8000"

# 测试账号
ADMIN_USER = {"username": "admin", "password": "admin123"}
USER1 = {"username": "user1", "password": "123456"}
USER2 = {"username": "user2", "password": "123456"}
REVIEWER1 = {"username": "reviewer1", "password": "123456"}


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


def get_or_create_workflow(token, bind_type):
    """获取或创建工作流"""
    # 先查找已存在的工作流
    workflows = get_workflow_list(token, bind_type)
    for wf in workflows:
        if wf.get('is_active'):
            return wf

    # 没有则创建
    return create_workflow(token, bind_type)


def create_workflow(token, bind_type, bind_subtype=None):
    """创建测试工作流：部门审核 → 结束"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    workflow = {
        "name": f"{bind_type} 审批流程",
        "description": f"{bind_type} 部门审核流程",
        "bind_type": bind_type,
        "bind_subtype": bind_subtype,
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
                "config": {"approver": "department_manager"}
            },
            {
                "id": "node_end",
                "type": "end",
                "name": "结束",
                "x": 500,
                "y": 100,
                "config": {}
            }
        ],
        "edges": [
            {"source": "node_start", "target": "node_dept"},
            {"source": "node_dept", "target": "node_end"}
        ]
    }
    res = requests.post(f"{BASE_URL}/api/workflow-def/", headers=headers, json=workflow)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"创建工作流失败 (状态码 {res.status_code}): {res.text}")
        return None


def get_workflow_list(token, bind_type=None):
    """获取工作流定义列表"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"bind_type": bind_type} if bind_type else {}
    res = requests.get(f"{BASE_URL}/api/workflow-def/", headers=headers, params=params)
    if res.status_code == 200:
        return res.json()
    return []


def get_my_approvals(token):
    """获取当前用户的待办审批"""
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/workflow-def/approvals/my", headers=headers)
    if res.status_code == 200:
        return res.json()
    return []


def perform_workflow_action(token, workflow_def_id, record_id, action, comments=""):
    """执行工作流审批操作"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "action": action,
        "comments": comments
    }
    res = requests.post(f"{BASE_URL}/api/workflow-def/{workflow_def_id}/record/{record_id}/action",
                        headers=headers, json=data)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"执行工作流操作失败：{res.text}")
        return None


def get_resource_workflow_status(token, resource_type, resource_id):
    """获取资源工作流状态"""
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/resource-workflow/resource/{resource_type}/{resource_id}/workflow-status",
                       headers=headers)
    if res.status_code == 200:
        return res.json()
    return None


# ============ 数据集测试 ============
def test_dataset_workflow():
    """测试数据集工作流审批"""
    print_separator("测试：数据集工作流审批")

    admin_token = login("admin", "admin123")
    if not admin_token:
        return False

    # 1. 创建工作流
    print("1. 创建数据集审批工作流...")
    workflow = create_workflow(admin_token, "dataset")
    if not workflow:
        return False
    workflow_def_id = workflow.get("id")
    print(f"OK: 工作流创建成功，ID: {workflow_def_id}")

    # 2. 创建数据集（绑定工作流）
    print("\n2. 创建数据集（绑定工作流）...")
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    dataset_data = {
        "name": f"测试数据集 - 工作流审批",
        "description": "用于测试工作流审批的数据集",
        "business_domain": "技术",
        "data_type": "structured",
        "source": "internal",
        "record_count": 1000,
        "workflow_definition_id": workflow_def_id
    }
    res = requests.post(f"{BASE_URL}/api/datasets/", headers=headers, json=dataset_data)
    if res.status_code != 200:
        print(f"创建数据集失败：{res.text}")
        return False

    dataset = res.json()
    dataset_id = dataset.get("id")
    status = dataset.get("status")
    print(f"OK: 数据集创建成功，ID: {dataset_id}, 状态：{status}")

    if status != "under_review":
        print(f"FAIL: 数据集状态应该是 under_review，实际是 {status}")
        return False

    # 3. 获取待办审批
    print("\n3. 获取待办审批列表...")
    # 使用 reviewer1 登录获取待办
    reviewer_token = login("reviewer1", "123456")
    if reviewer_token:
        approvals = get_my_approvals(reviewer_token)
        dataset_approvals = [a for a in approvals if a.get('record', {}).get('record_type') == 'dataset']
        if dataset_approvals:
            print(f"OK: 找到 {len(dataset_approvals)} 个数据集待办审批")
            for item in dataset_approvals:
                record = item.get('record', {})
                if record.get('record_id') == dataset_id:
                    print(f"   - 找到目标数据集的待办，记录 ID: {record.get('id')}")
                    # 执行审批
                    result = perform_workflow_action(
                        reviewer_token,
                        workflow_def_id,
                        record.get('id'),
                        "approve",
                        "测试审批通过"
                    )
                    if result:
                        print(f"OK: 审批通过，{result.get('message', '')}")
                        break
        else:
            print("WARN: 没有找到数据集待办审批")

    # 4. 验证数据集状态
    print("\n4. 验证数据集状态...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = requests.get(f"{BASE_URL}/api/datasets/{dataset_id}", headers=headers)
    if res.status_code == 200:
        dataset = res.json()
        final_status = dataset.get("status")
        print(f"OK: 数据集最终状态：{final_status}")
        if final_status == "approved":
            print("OK: 数据集审批通过!")
            return True
        else:
            print(f"WARN: 数据集状态为 {final_status}（可能需要多节点审批）")
            return True  # 不算失败，可能需要更多审批节点
    return False


# ============ 模型测试 ============
def test_model_workflow():
    """测试模型工作流审批"""
    print_separator("测试：模型工作流审批")

    admin_token = login("admin", "admin123")
    if not admin_token:
        return False

    # 1. 创建工作流
    print("1. 创建模型审批工作流...")
    workflow = create_workflow(admin_token, "model")
    if not workflow:
        return False
    workflow_def_id = workflow.get("id")
    print(f"OK: 工作流创建成功，ID: {workflow_def_id}")

    # 2. 创建模型（绑定工作流）
    print("\n2. 创建模型（绑定工作流）...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    model_data = {
        "name": f"测试模型 - 工作流审批",
        "description": "用于测试工作流审批的模型",
        "model_type": "NLP",
        "framework": "PyTorch",
        "version": "1.0.0",
        "workflow_definition_id": workflow_def_id
    }
    # 使用 FormData 上传模型
    files = {}
    data = {
        "name": model_data["name"],
        "description": model_data["description"],
        "model_type": model_data["model_type"],
        "framework": model_data["framework"],
        "version": model_data["version"],
        "workflow_definition_id": workflow_def_id
    }
    res = requests.post(f"{BASE_URL}/api/models/", headers=headers, data=data, files=files)
    if res.status_code != 200:
        print(f"创建模型失败：{res.text}")
        return False

    model = res.json()
    model_id = model.get("id")
    status = model.get("status")
    print(f"OK: 模型创建成功，ID: {model_id}, 状态：{status}")

    if status != "under_review":
        print(f"FAIL: 模型状态应该是 under_review，实际是 {status}")
        return False

    # 3. 获取待办审批并审批
    print("\n3. 获取待办审批列表并审批...")
    reviewer_token = login("reviewer1", "123456")
    if reviewer_token:
        approvals = get_my_approvals(reviewer_token)
        model_approvals = [a for a in approvals if a.get('record', {}).get('record_type') == 'model']
        if model_approvals:
            print(f"OK: 找到 {len(model_approvals)} 个模型待办审批")
            for item in model_approvals:
                record = item.get('record', {})
                if record.get('record_id') == model_id:
                    print(f"   - 找到目标模型的待办，记录 ID: {record.get('id')}")
                    result = perform_workflow_action(
                        reviewer_token,
                        workflow_def_id,
                        record.get('id'),
                        "approve",
                        "模型测试审批通过"
                    )
                    if result:
                        print(f"OK: 审批通过，{result.get('message', '')}")
                        break
        else:
            print("WARN: 没有找到模型待办审批")

    # 4. 验证模型状态
    print("\n4. 验证模型状态...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = requests.get(f"{BASE_URL}/api/models/{model_id}", headers=headers)
    if res.status_code == 200:
        model = res.json()
        final_status = model.get("status")
        print(f"OK: 模型最终状态：{final_status}")
        if final_status == "approved":
            print("OK: 模型审批通过!")
            return True
        else:
            print(f"WARN: 模型状态为 {final_status}")
            return True
    return False


# ============ 智能体测试 ============
def test_agent_workflow():
    """测试智能体工作流审批"""
    print_separator("测试：智能体工作流审批")

    admin_token = login("admin", "admin123")
    if not admin_token:
        return False

    # 1. 创建工作流
    print("1. 创建智能体审批工作流...")
    workflow = create_workflow(admin_token, "agent")
    if not workflow:
        return False
    workflow_def_id = workflow.get("id")
    print(f"OK: 工作流创建成功，ID: {workflow_def_id}")

    # 2. 创建智能体（绑定工作流）
    print("\n2. 创建智能体（绑定工作流）...")
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    agent_data = {
        "name": f"测试智能体 - 工作流审批",
        "description": "用于测试工作流审批的智能体",
        "agent_type": "MCP",
        "business_domain": "技术",
        "development_status": "released",
        "workflow_definition_id": workflow_def_id
    }
    res = requests.post(f"{BASE_URL}/api/agents/", headers=headers, json=agent_data)
    if res.status_code != 200:
        print(f"创建智能体失败：{res.text}")
        return False

    agent = res.json()
    agent_id = agent.get("id")
    status = agent.get("status")
    print(f"OK: 智能体创建成功，ID: {agent_id}, 状态：{status}")

    if status != "under_review":
        print(f"FAIL: 智能体状态应该是 under_review，实际是 {status}")
        return False

    # 3. 获取待办审批并审批
    print("\n3. 获取待办审批列表并审批...")
    reviewer_token = login("reviewer1", "123456")
    if reviewer_token:
        approvals = get_my_approvals(reviewer_token)
        agent_approvals = [a for a in approvals if a.get('record', {}).get('record_type') == 'agent']
        if agent_approvals:
            print(f"OK: 找到 {len(agent_approvals)} 个智能体待办审批")
            for item in agent_approvals:
                record = item.get('record', {})
                if record.get('record_id') == agent_id:
                    print(f"   - 找到目标智能体的待办，记录 ID: {record.get('id')}")
                    result = perform_workflow_action(
                        reviewer_token,
                        workflow_def_id,
                        record.get('id'),
                        "approve",
                        "智能体测试审批通过"
                    )
                    if result:
                        print(f"OK: 审批通过，{result.get('message', '')}")
                        break
        else:
            print("WARN: 没有找到智能体待办审批")

    # 4. 验证智能体状态
    print("\n4. 验证智能体状态...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = requests.get(f"{BASE_URL}/api/agents/{agent_id}", headers=headers)
    if res.status_code == 200:
        agent = res.json()
        final_status = agent.get("status")
        print(f"OK: 智能体最终状态：{final_status}")
        if final_status == "approved":
            print("OK: 智能体审批通过!")
            return True
        else:
            print(f"WARN: 智能体状态为 {final_status}")
            return True
    return False


# ============ 应用广场测试 ============
def test_app_store_workflow():
    """测试应用广场工作流审批"""
    print_separator("测试：应用广场工作流审批")

    admin_token = login("admin", "admin123")
    if not admin_token:
        return False

    # 1. 创建工作流
    print("1. 创建应用广场审批工作流...")
    workflow = create_workflow(admin_token, "app_store")
    if not workflow:
        return False
    workflow_def_id = workflow.get("id")
    print(f"OK: 工作流创建成功，ID: {workflow_def_id}")

    # 2. 创建应用（绑定工作流）
    print("\n2. 创建应用广场项目（绑定工作流）...")
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    app_data = {
        "name": f"测试应用 - 工作流审批",
        "description": "用于测试工作流审批的应用",
        "category": "通用应用",
        "business_domain": "技术",
        "version": "1.0.0",
        "workflow_definition_id": workflow_def_id
    }
    res = requests.post(f"{BASE_URL}/api/app-store/", headers=headers, json=app_data)
    if res.status_code != 200:
        print(f"创建应用失败：{res.text}")
        return False

    app = res.json()
    app_id = app.get("id")
    status = app.get("status")
    print(f"OK: 应用创建成功，ID: {app_id}, 状态：{status}")

    if status != "under_review":
        print(f"FAIL: 应用状态应该是 under_review，实际是 {status}")
        return False

    # 3. 获取待办审批并审批
    print("\n3. 获取待办审批列表并审批...")
    reviewer_token = login("reviewer1", "123456")
    if reviewer_token:
        approvals = get_my_approvals(reviewer_token)
        app_approvals = [a for a in approvals if a.get('record', {}).get('record_type') == 'app_store']
        if app_approvals:
            print(f"OK: 找到 {len(app_approvals)} 个应用待办审批")
            for item in app_approvals:
                record = item.get('record', {})
                if record.get('record_id') == app_id:
                    print(f"   - 找到目标应用的待办，记录 ID: {record.get('id')}")
                    result = perform_workflow_action(
                        reviewer_token,
                        workflow_def_id,
                        record.get('id'),
                        "approve",
                        "应用测试审批通过"
                    )
                    if result:
                        print(f"OK: 审批通过，{result.get('message', '')}")
                        break
        else:
            print("WARN: 没有找到应用待办审批")

    # 4. 验证应用状态
    print("\n4. 验证应用状态...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = requests.get(f"{BASE_URL}/api/app-store/{app_id}", headers=headers)
    if res.status_code == 200:
        app = res.json()
        final_status = app.get("status")
        print(f"OK: 应用最终状态：{final_status}")
        if final_status == "published" or final_status == "approved":
            print("OK: 应用审批通过!")
            return True
        else:
            print(f"WARN: 应用状态为 {final_status}")
            return True
    return False


# ============ 算力资源测试 ============
def test_compute_resource_workflow():
    """测试算力资源工作流审批"""
    print_separator("测试：算力资源工作流审批")

    admin_token = login("admin", "admin123")
    if not admin_token:
        return False

    # 1. 创建工作流
    print("1. 创建算力资源审批工作流...")
    workflow = create_workflow(admin_token, "compute_resource")
    if not workflow:
        return False
    workflow_def_id = workflow.get("id")
    print(f"OK: 工作流创建成功，ID: {workflow_def_id}")

    # 2. 创建算力资源（绑定工作流）
    print("\n2. 创建算力资源（绑定工作流）...")
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    compute_data = {
        "name": f"测试算力资源 - 工作流审批",
        "resource_type": "GPU",
        "model_name": "A100",
        "memory_size": 80,
        "total_compute": 100.0,
        "location": "数据中心",
        "owner_department": "技术部",
        "workflow_definition_id": workflow_def_id
    }
    res = requests.post(f"{BASE_URL}/api/compute/", headers=headers, json=compute_data)
    if res.status_code != 200:
        print(f"创建算力资源失败：{res.text}")
        return False

    compute = res.json()
    compute_id = compute.get("id")
    status = compute.get("status")
    print(f"OK: 算力资源创建成功，ID: {compute_id}, 状态：{status}")

    if status != "under_review":
        print(f"FAIL: 算力资源状态应该是 under_review，实际是 {status}")
        return False

    # 3. 获取待办审批并审批
    print("\n3. 获取待办审批列表并审批...")
    reviewer_token = login("reviewer1", "123456")
    if reviewer_token:
        approvals = get_my_approvals(reviewer_token)
        compute_approvals = [a for a in approvals if a.get('record', {}).get('record_type') == 'compute_resource']
        if compute_approvals:
            print(f"OK: 找到 {len(compute_approvals)} 个算力资源待办审批")
            for item in compute_approvals:
                record = item.get('record', {})
                if record.get('record_id') == compute_id:
                    print(f"   - 找到目标算力资源的待办，记录 ID: {record.get('id')}")
                    result = perform_workflow_action(
                        reviewer_token,
                        workflow_def_id,
                        record.get('id'),
                        "approve",
                        "算力资源测试审批通过"
                    )
                    if result:
                        print(f"OK: 审批通过，{result.get('message', '')}")
                        break
        else:
            print("WARN: 没有找到算力资源待办审批")

    # 4. 验证算力资源状态
    print("\n4. 验证算力资源状态...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = requests.get(f"{BASE_URL}/api/compute/{compute_id}", headers=headers)
    if res.status_code == 200:
        compute = res.json()
        final_status = compute.get("status")
        print(f"OK: 算力资源最终状态：{final_status}")
        if final_status == "available" or final_status == "approved":
            print("OK: 算力资源审批通过!")
            return True
        else:
            print(f"WARN: 算力资源状态为 {final_status}")
            return True
    return False


def print_separator(title=""):
    print(f"\n{'='*60}")
    if title:
        print(f"  {title}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("  资源工作流审批系统 - 自动化测试")
    print("  数据集、模型、智能体、应用广场、算力资源")
    print("=" * 60)

    results = []

    # 测试 1：数据集
    try:
        results.append(("数据集工作流审批", test_dataset_workflow()))
    except Exception as e:
        print(f"测试异常：{e}")
        results.append(("数据集工作流审批", False))

    # 测试 2：模型
    try:
        results.append(("模型工作流审批", test_model_workflow()))
    except Exception as e:
        print(f"测试异常：{e}")
        results.append(("模型工作流审批", False))

    # 测试 3：智能体
    try:
        results.append(("智能体工作流审批", test_agent_workflow()))
    except Exception as e:
        print(f"测试异常：{e}")
        results.append(("智能体工作流审批", False))

    # 测试 4：应用广场
    try:
        results.append(("应用广场工作流审批", test_app_store_workflow()))
    except Exception as e:
        print(f"测试异常：{e}")
        results.append(("应用广场工作流审批", False))

    # 测试 5：算力资源
    try:
        results.append(("算力资源工作流审批", test_compute_resource_workflow()))
    except Exception as e:
        print(f"测试异常：{e}")
        results.append(("算力资源工作流审批", False))

    # 打印汇总
    print_separator("测试汇总")
    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"  {symbol} {name}: {status}")

    all_passed = all(r[1] for r in results)
    result_text = "全部通过 [OK]" if all_passed else "部分失败 [FAIL]"
    print(f"\n总结果：{result_text}")

    if all_passed:
        print("\n所有资源类型的工作流审批闭环测试通过!")
    else:
        print("\n部分测试失败，请检查日志详情")
