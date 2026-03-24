"""
测试新增的 API 功能
"""
import requests

BASE_URL = "http://localhost:8001"

# 1. 测试登录
print("=" * 50)
print("1. 测试登录 API")
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    data={"username": "admin", "password": "admin123"}
)
print(f"登录状态：{login_response.status_code}")
if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print(f"获取 Token: {token[:50]}...")
    headers = {"Authorization": f"Bearer {token}"}
else:
    print("登录失败，跳过后续测试")
    exit(1)

# 2. 测试获取当前用户信息
print("\n" + "=" * 50)
print("2. 测试获取当前用户信息")
user_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
print(f"用户信息：{user_response.json()}")

# 3. 测试获取个人资料
print("\n" + "=" * 50)
print("3. 测试获取个人资料")
profile_response = requests.get(f"{BASE_URL}/api/auth/me/profile", headers=headers)
print(f"个人资料：{profile_response.json()}")

# 4. 测试更新个人资料
print("\n" + "=" * 50)
print("4. 测试更新个人资料")
update_data = {
    "bio": "这是一个测试简介",
    "skills": ["Python", "FastAPI", "机器学习"],
    "phone_public": True,
    "email_public": False
}
update_response = requests.put(
    f"{BASE_URL}/api/auth/me/profile",
    headers=headers,
    json=update_data
)
print(f"更新结果：{update_response.json()}")

# 5. 测试职位列表
print("\n" + "=" * 50)
print("5. 测试职位列表 API")
positions_response = requests.get(f"{BASE_URL}/api/users/positions", headers=headers)
print(f"职位列表：{positions_response.json()}")

# 6. 测试文件列表
print("\n" + "=" * 50)
print("6. 测试文件列表 API")
files_response = requests.get(f"{BASE_URL}/api/files/my", headers=headers)
print(f"我的文件：{files_response.json()}")

# 7. 测试数据分析 - 应用场景趋势
print("\n" + "=" * 50)
print("7. 测试数据分析 API - 应用场景趋势")
trend_response = requests.get(f"{BASE_URL}/api/analytics/trend/applications", headers=headers)
print(f"应用场景趋势：{trend_response.json()}")

# 8. 测试数据分析 - 算力使用情况
print("\n" + "=" * 50)
print("8. 测试数据分析 API - 算力使用情况")
compute_response = requests.get(f"{BASE_URL}/api/analytics/resource/compute-usage", headers=headers)
print(f"算力使用：{compute_response.json()}")

# 9. 测试报表列表
print("\n" + "=" * 50)
print("9. 测试报表列表 API")
reports_response = requests.get(f"{BASE_URL}/api/analytics/reports", headers=headers)
print(f"报表列表：{reports_response.json()}")

# 10. 测试通知设置
print("\n" + "=" * 50)
print("10. 测试通知设置 API")
settings_response = requests.get(f"{BASE_URL}/api/notification/settings", headers=headers)
print(f"通知设置：{settings_response.json()}")

# 11. 测试邮件模板列表
print("\n" + "=" * 50)
print("11. 测试邮件模板列表 API")
templates_response = requests.get(f"{BASE_URL}/api/notification/email-templates", headers=headers)
print(f"邮件模板：{templates_response.json()}")

# 12. 测试创建报表
print("\n" + "=" * 50)
print("12. 测试创建报表 API")
report_data = {
    "name": "测试报表",
    "description": "这是一个测试报表",
    "report_type": "resource_usage",
    "config": {"days": 30},
    "is_public": True
}
create_report_response = requests.post(
    f"{BASE_URL}/api/analytics/reports",
    headers=headers,
    json=report_data
)
print(f"创建报表结果：{create_report_response.json()}")

print("\n" + "=" * 50)
print("所有测试完成!")
