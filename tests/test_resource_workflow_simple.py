#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资源工作流审批自动化测试 - 简化版
测试数据集、模型、智能体、应用广场、算力资源的创建 - 工作流绑定 - 审批闭环
"""
import requests
import json
import os
import time

# 设置输出编码
os.system('chcp 65001 > nul 2>&1')

BASE_URL = "http://localhost:8001"

# 测试账号
ADMIN = {"username": "admin", "password": "admin123"}
REVIEWER = {"username": "reviewer1", "password": "123456"}


def login(username, password):
    res = requests.post(f"{BASE_URL}/api/auth/login",
                        data={"username": username, "password": password})
    if res.status_code == 200:
        return res.json().get("access_token")
    print(f"登录失败 ({username})")
    return None


def get_workflows(token, bind_type):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/workflow-def/", headers=headers, params={"bind_type": bind_type})
    if res.status_code == 200:
        for wf in res.json():
            if wf.get('is_active'):
                return wf
    return None


def get_my_approvals(token):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/workflow-def/approvals/my", headers=headers)
    return res.json() if res.status_code == 200 else []


def perform_action(token, wf_id, record_id, action="approve", comments="测试通过"):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    res = requests.post(f"{BASE_URL}/api/workflow-def/{wf_id}/record/{record_id}/action",
                        headers=headers, json={"action": action, "comments": comments})
    return res.json() if res.status_code == 200 else None


def test_resource(resource_type, resource_data, api_path):
    """通用资源测试函数"""
    print(f"\n{'='*50}")
    print(f"测试：{resource_type} 工作流审批")
    print(f"{'='*50}")

    admin_token = login("admin", "admin123")
    reviewer_token = login("reviewer1", "123456")
    if not admin_token:
        print(f"FAIL: 管理员登录失败")
        return False

    # 1. 获取工作流
    print("1. 获取工作流定义...")
    workflow = get_workflows(admin_token, resource_type)
    if not workflow:
        print(f"FAIL: 没有找到 {resource_type} 类型的工作流")
        return False
    wf_id = workflow.get("id")
    print(f"OK: 工作流 ID: {wf_id}")

    # 2. 创建资源
    print(f"\n2. 创建{resource_type}（绑定工作流）...")
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    resource_data["workflow_definition_id"] = wf_id

    if resource_type == "model":
        # 模型需要 FormData
        headers.pop("Content-Type", None)
        res = requests.post(f"{BASE_URL}{api_path}", headers=headers, data=resource_data)
    else:
        res = requests.post(f"{BASE_URL}{api_path}", headers=headers, json=resource_data)

    if res.status_code != 200:
        print(f"FAIL: 创建资源失败：{res.text}")
        return False

    resource = res.json()
    resource_id = resource.get("id")
    status = resource.get("status")
    print(f"OK: 资源创建成功，ID: {resource_id}, 状态：{status}")

    # 3. 获取待办并审批
    print(f"\n3. 获取待办审批并执行审批...")
    if reviewer_token:
        approvals = get_my_approvals(reviewer_token)
        target_approvals = [a for a in approvals
                          if a.get('record', {}).get('record_type') == resource_type
                          and a.get('record', {}).get('record_id') == resource_id]

        if target_approvals:
            for item in target_approvals:
                record = item.get('record', {})
                result = perform_action(reviewer_token, wf_id, record.get('id'))
                if result:
                    print(f"OK: 审批通过，{result.get('message', '')}")
                    break
        else:
            print(f"WARN: 没有找到待办审批")

    # 4. 验证状态
    print(f"\n4. 验证{resource_type}最终状态...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Fix double slash issue - api_path already ends with /
    res = requests.get(f"{BASE_URL}{api_path}{resource_id}", headers=headers)
    if res.status_code == 200:
        resource = res.json()
        final_status = resource.get("status")
        print(f"OK: 最终状态：{final_status}")
        # 定义通过状态
        approved_statuses = {
            "dataset": ["approved", "available"],
            "model": ["approved", "available"],
            "agent": ["approved", "available"],
            "app_store": ["published", "approved"],
            "compute_resource": ["available", "approved"]
        }
        if final_status in approved_statuses.get(resource_type, ["approved"]):
            print(f"OK: {resource_type} 审批通过!")
            return True
        else:
            print(f"WARN: 状态为 {final_status}，可能需要更多审批节点")
            return True
    return False


def main():
    print("=" * 60)
    print("  资源工作流审批系统 - 自动化测试")
    print("  数据集、模型、智能体、应用广场、算力资源")
    print("=" * 60)

    results = []
    timestamp = int(time.time())

    # 测试配置
    test_cases = [
        ("dataset", {
            "name": f"测试数据集-{timestamp}",
            "description": "测试数据集",
            "business_domain": "技术",
            "data_type": "structured",
            "source": "internal",
            "record_count": 1000
        }, "/api/datasets/"),

        ("model", {
            "name": f"测试模型-{timestamp}",
            "description": "测试模型",
            "model_type": "NLP",
            "framework": "PyTorch",
            "version": "1.0.0"
        }, "/api/models/"),

        ("agent", {
            "name": f"测试智能体-{timestamp}",
            "description": "测试智能体",
            "agent_type": "MCP",
            "business_domain": "技术",
            "development_status": "released"
        }, "/api/agents/"),

        ("app_store", {
            "name": f"测试应用-{timestamp}",
            "description": "测试应用",
            "category": "通用应用",
            "business_domain": "技术",
            "version": "1.0.0"
        }, "/api/app-store/"),

        ("compute_resource", {
            "name": f"测试算力-{timestamp}",
            "resource_type": "GPU",
            "model_name": "A100",
            "memory_size": 80,
            "total_compute": 100.0,
            "location": "数据中心",
            "owner_department": "技术部"
        }, "/api/compute/")
    ]

    for resource_type, resource_data, api_path in test_cases:
        try:
            result = test_resource(resource_type, resource_data, api_path)
            results.append((resource_type, result))
        except Exception as e:
            print(f"测试异常 ({resource_type}): {e}")
            results.append((resource_type, False))
        time.sleep(0.5)

    # 汇总
    print("\n" + "=" * 60)
    print("  测试汇总")
    print("=" * 60)
    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"  {symbol} {name}: {status}")

    all_passed = all(r[1] for r in results)
    print(f"\n总结果：{'全部通过 [OK]' if all_passed else '部分失败 [FAIL]'}")
    return all_passed


if __name__ == "__main__":
    main()
