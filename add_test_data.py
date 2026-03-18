"""
添加测试数据脚本
"""
import requests

BASE_URL = "http://localhost:8000"

# 登录获取 token
login_resp = requests.post(f"{BASE_URL}/api/auth/login", data={
    "username": "admin",
    "password": "admin123"
})
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("=== 开始添加测试数据 ===\n")

# 1. 添加数据集
print("1. 添加数据集...")
datasets = [
    {
        "name": "客户评论情感分析数据集",
        "description": "包含 10 万条电商客户评论，已标注情感倾向（正面/负面/中性）",
        "business_domain": "电商客服",
        "data_type": "文本",
        "source": "某电商平台脱敏数据",
        "record_count": 100000,
        "field_schema": {"fields": [{"name": "comment_text", "type": "text"}, {"name": "sentiment", "type": "label"}]}
    },
    {
        "name": "产品图像分类数据集",
        "description": "包含 5 万张产品图片，覆盖 100 个商品类别",
        "business_domain": "智能货架",
        "data_type": "图像",
        "source": "公开数据集整合",
        "record_count": 50000,
        "field_schema": {"fields": [{"name": "image_path", "type": "string"}, {"name": "category", "type": "label"}]}
    },
    {
        "name": "智能问答知识库",
        "description": "包含 5000 个常见问答对，覆盖产品咨询、售后服务等场景",
        "business_domain": "智能客服",
        "data_type": "文本",
        "source": "客服工单整理",
        "record_count": 5000,
        "field_schema": {"fields": [{"name": "question", "type": "text"}, {"name": "answer", "type": "text"}]}
    }
]
for ds in datasets:
    resp = requests.post(f"{BASE_URL}/api/datasets/", json=ds, headers=headers)
    print(f"  - {ds['name']}: {resp.status_code}")

# 2. 添加模型
print("\n2. 添加模型...")
models = [
    {
        "name": "BERT 情感分析模型",
        "description": "基于 BERT 的中文情感分析模型，准确率 95%",
        "model_type": "NLP",
        "framework": "PyTorch",
        "version": "1.0.0",
        "business_scenarios": ["客户评论分析", "舆情监控"],
        "performance_metrics": {"accuracy": 0.95, "f1_score": 0.94},
        "has_api": True,
        "api_docs": "http://api.example.com/docs/sentiment"
    },
    {
        "name": "ResNet 图像分类模型",
        "description": "基于 ResNet50 的产品图像分类模型",
        "model_type": "CV",
        "framework": "TensorFlow",
        "version": "2.1.0",
        "business_scenarios": ["商品识别", "图像检索"],
        "performance_metrics": {"accuracy": 0.92, "top5_accuracy": 0.98},
        "has_api": True,
        "api_docs": "http://api.example.com/docs/image"
    },
    {
        "name": "智能问答生成模型",
        "description": "基于大语言模型的智能问答生成",
        "model_type": "NLP",
        "framework": "PyTorch",
        "version": "3.0.0",
        "business_scenarios": ["智能客服", "问答系统"],
        "performance_metrics": {"bleu": 0.45, "rouge": 0.52},
        "has_api": True,
        "api_docs": "http://api.example.com/docs/qa"
    }
]
for m in models:
    resp = requests.post(f"{BASE_URL}/api/models/", json=m, headers=headers)
    print(f"  - {m['name']}: {resp.status_code}")

# 3. 添加智能体
print("\n3. 添加智能体...")
agents = [
    {
        "name": "智能客服助手",
        "description": "7x24 小时在线的智能客服助手，自动回答用户咨询",
        "agent_type": "对话机器人",
        "business_domain": "客户服务",
        "development_status": "已上线",
        "required_models": [],
        "required_datasets": [],
        "api_endpoint": "http://api.example.com/customer-service"
    },
    {
        "name": "销售预测助手",
        "description": "基于历史数据预测未来销售趋势",
        "agent_type": "预测分析",
        "business_domain": "销售管理",
        "development_status": "测试中",
        "required_models": [],
        "required_datasets": [],
        "api_endpoint": "http://api.example.com/sales-forecast"
    },
    {
        "name": "文档智能审核助手",
        "description": "自动审核合同文档，识别风险条款",
        "agent_type": "文档分析",
        "business_domain": "法务合规",
        "development_status": "已上线",
        "required_models": [],
        "required_datasets": [],
        "api_endpoint": "http://api.example.com/doc-review"
    }
]
for a in agents:
    resp = requests.post(f"{BASE_URL}/api/agents/", json=a, headers=headers)
    print(f"  - {a['name']}: {resp.status_code}")

# 4. 添加应用场景
print("\n4. 添加应用场景...")
applications = [
    {
        "title": "智能客服系统建设",
        "department": "信息技术部",
        "contact_info": "张三 13800138000",
        "business_background": "客服部门每天接待大量客户咨询，人工成本高",
        "current_pain_points": "人工客服响应慢，无法 7x24 小时服务",
        "expected_value": "降低 50% 人工客服成本，提升客户满意度",
        "has_data": True,
        "has_model": False
    },
    {
        "title": "产品销量预测系统",
        "department": "运营管理部",
        "contact_info": "李四 13800138001",
        "business_background": "需要准确预测产品销量以优化库存管理",
        "current_pain_points": "库存积压和缺货问题频发",
        "expected_value": "降低 30% 库存成本，提升周转率",
        "has_data": True,
        "has_model": False
    }
]
for app in applications:
    resp = requests.post(f"{BASE_URL}/api/applications/", json=app, headers=headers)
    print(f"  - {app['title']}: {resp.status_code}")

# 5. 添加应用广场应用
print("\n5. 添加应用广场应用...")
app_store_items = [
    {
        "name": "智能客服系统",
        "description": "企业级智能客服解决方案",
        "icon": "🤖",
        "category": "客户服务",
        "business_domain": "客服自动化",
        "developer": "AI 团队",
        "version": "1.0.0",
        "features": ["7x24 小时在线", "多轮对话", "情感识别"],
        "usage_guide": "配置知识库后即可使用"
    },
    {
        "name": "文档智能分析工具",
        "description": "自动提取文档关键信息",
        "icon": "📄",
        "category": "办公效率",
        "business_domain": "文档处理",
        "developer": "数据团队",
        "version": "2.0.0",
        "features": ["OCR 识别", "关键信息提取", "格式转换"],
        "usage_guide": "上传文档即可自动分析"
    }
]
for item in app_store_items:
    resp = requests.post(f"{BASE_URL}/api/app-store/", json=item, headers=headers)
    print(f"  - {item['name']}: {resp.status_code}")

# 6. 添加算力资源
print("\n6. 添加算力资源...")
compute_resources = [
    {
        "name": "GPU 训练集群-A100",
        "resource_type": "GPU",
        "model_name": "NVIDIA A100",
        "memory_size": 80,
        "total_compute": 1000.0,
        "location": "数据中心 A",
        "owner_department": "信息技术部",
        "support_scenarios": ["大模型训练", "深度学习"]
    },
    {
        "name": "CPU 推理集群",
        "resource_type": "CPU",
        "model_name": "Intel Xeon",
        "memory_size": 256,
        "total_compute": 500.0,
        "location": "数据中心 B",
        "owner_department": "信息技术部",
        "support_scenarios": ["模型推理", "批量处理"]
    }
]
for r in compute_resources:
    resp = requests.post(f"{BASE_URL}/api/compute/", json=r, headers=headers)
    print(f"  - {r['name']}: {resp.status_code}")

# 7. 添加论坛帖子
print("\n7. 添加论坛帖子...")
posts = [
    {
        "title": "如何训练一个高效的情感分析模型？",
        "content": "最近在做情感分析项目，想请教一下大家，如何训练一个高效准确的情感分析模型？数据预处理有什么技巧吗？",
        "category": "tech",
        "tags": ["NLP", "情感分析", "BERT"]
    },
    {
        "title": "分享一个智能客服落地案例",
        "content": "我们最近上线了一个智能客服系统，日均接待 10000+ 咨询，准确率达到了 90%。分享一下实施过程中的经验和坑...",
        "category": "case",
        "tags": ["智能客服", "落地案例"]
    },
    {
        "title": "大模型时代，传统 ML 模型还有价值吗？",
        "content": "现在大模型这么火，很多传统机器学习模型是不是可以淘汰了？在一些资源受限的场景下，大家会如何选择？",
        "category": "qa",
        "tags": ["大模型", "机器学习", "讨论"]
    },
    {
        "title": "2026 年 AI 发展趋势展望",
        "content": "展望 2026 年，我认为 AI 发展会呈现以下几个趋势：1. 多模态成为标配 2. 边缘 AI 普及 3. AI 安全受到更多重视... 大家怎么看？",
        "category": "news",
        "tags": ["AI", "趋势", "2026"]
    }
]
for p in posts:
    resp = requests.post(f"{BASE_URL}/api/forum/", json=p, headers=headers)
    print(f"  - {p['title']}: {resp.status_code}")

# 8. 添加工作流定义
print("\n8. 添加工作流定义...")
workflow = {
    "name": "应用场景审批流程",
    "description": "标准的两级审批流程：部门经理审批 -> IT 总监审批",
    "bind_type": "application",
    "bind_subtype": "new",
    "is_active": True,
    "nodes": [
        {"id": "start", "type": "start", "name": "开始"},
        {"id": "submit", "type": "submit", "name": "提交申请"},
        {"id": "dept_review", "type": "review", "name": "部门经理审批", "config": {"approver": "dept_manager"}},
        {"id": "it_review", "type": "review", "name": "IT 总监审批", "config": {"approver": "it_director"}},
        {"id": "end", "type": "end", "name": "结束"}
    ],
    "edges": [
        {"source": "start", "target": "submit"},
        {"source": "submit", "target": "dept_review"},
        {"source": "dept_review", "target": "it_review"},
        {"source": "it_review", "target": "end"}
    ]
}
resp = requests.post(f"{BASE_URL}/api/workflow-def/", json=workflow, headers=headers)
print(f"  - {workflow['name']}: {resp.status_code}")

print("\n=== 测试数据添加完成 ===")
print("\n请刷新页面查看数据！")
