"""
初始化测试数据脚本
用于创建测试角色和用户，方便测试工作流审核功能
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def login(username, password):
    """登录获取 token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": username, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    else:
        print(f"登录失败：{response.text}")
        return None

def init_test_data(token):
    """初始化测试数据"""
    headers = {"Authorization": f"Bearer {token}"}

    # 调用初始化接口
    response = requests.post(
        f"{BASE_URL}/api/system/init-test-data",
        headers=headers
    )
    if response.status_code == 200:
        result = response.json()
        print("=== 初始化完成 ===")
        print(f"创建的角色：{result.get('created_roles', [])}")
        print(f"创建的用户：{result.get('created_users', [])}")
    else:
        print(f"初始化失败：{response.text}")

def create_workflow(token):
    """创建应用场景审批工作流"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    workflow_data = {
        "name": "应用场景审批流程",
        "description": "标准的应用场景申报审核流程",
        "bind_type": "application",
        "bind_subtype": "new",
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
                "id": "node_submit",
                "type": "submit",
                "name": "提交申请",
                "x": 100,
                "y": 200,
                "config": {}
            },
            {
                "id": "node_department_review",
                "type": "review",
                "name": "部门审核",
                "x": 100,
                "y": 300,
                "config": {
                    "approver": "department_manager",
                    "approval_type": "any"
                }
            },
            {
                "id": "node_tech_review",
                "type": "review",
                "name": "技术审核",
                "x": 100,
                "y": 400,
                "config": {
                    "approver": "tech_reviewer",
                    "approval_type": "any"
                }
            },
            {
                "id": "node_end",
                "type": "end",
                "name": "结束",
                "x": 100,
                "y": 500,
                "config": {}
            }
        ],
        "edges": [
            {"source": "node_start", "target": "node_submit"},
            {"source": "node_submit", "target": "node_department_review"},
            {"source": "node_department_review", "target": "node_tech_review"},
            {"source": "node_tech_review", "target": "node_end"}
        ]
    }

    response = requests.post(
        f"{BASE_URL}/api/workflow-def/",
        headers=headers,
        json=workflow_data
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\n=== 工作流创建成功 ===")
        print(f"工作流 ID: {result.get('id')}")
        print(f"工作流名称：{result.get('name')}")
        return result.get('id')
    else:
        print(f"工作流创建失败：{response.text}")
        return None

def assign_role_to_user(token, user_id, role_id):
    """给用户分配角色"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{BASE_URL}/api/system/users/{user_id}/roles",
        headers=headers,
        json={"role_id": role_id}
    )

    if response.status_code == 200:
        print(f"角色分配成功")
        return True
    else:
        print(f"角色分配失败：{response.text}")
        return False

def main():
    print("=== AI 管理平台测试数据初始化 ===\n")

    # 1. 使用 admin 登录
    print("1. 使用 admin 登录...")
    admin_token = login("admin", "admin123")
    if not admin_token:
        print("admin 登录失败，请确保数据库已初始化")
        return
    print(f"admin 登录成功，token: {admin_token[:20]}...")

    # 2. 初始化测试数据（创建角色和用户）
    print("\n2. 初始化测试数据...")
    init_test_data(admin_token)

    # 3. 创建工作流
    print("\n3. 创建应用场景审批工作流...")
    workflow_id = create_workflow(admin_token)

    if workflow_id:
        print(f"\n=== 初始化完成 ===")
        print(f"工作流已创建，ID: {workflow_id}")
        print("\n测试账号信息:")
        print("  - admin / admin123 (管理员)")
        print("  - user1 / 123456 (技术部用户)")
        print("  - user2 / 123456 (财务部用户)")
        print("  - reviewer1 / 123456 (审核员)")
        print("\n访问 http://localhost:8000/workflow-design 查看工作流")
        print("访问 http://localhost:8000/approvals 进行审批")

if __name__ == "__main__":
    main()
