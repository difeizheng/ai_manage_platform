"""
初始化示例数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, init_db
from app.models import models
from app.core.security import get_password_hash
from datetime import datetime, timedelta
import random

def create_sample_data():
    """创建示例数据"""
    db = SessionLocal()

    try:
        # 检查是否已有数据
        if db.query(models.Model).count() > 0:
            print("示例数据已存在，跳过初始化")
            return

        print("开始创建示例数据...")

        # 获取用户
        admin = db.query(models.User).filter(models.User.username == 'admin').first()
        user = db.query(models.User).filter(models.User.username == 'user').first()

        if not admin or not user:
            print("用户不存在，请先运行数据库初始化")
            return

        # 创建示例模型
        model_types = ['NLP', 'CV', 'ASR', 'TTS', '推荐系统']
        frameworks = ['PyTorch', 'TensorFlow', 'ONNX', 'PaddlePaddle']

        for i in range(5):
            model = models.Model(
                name=f"AI 模型-{i+1}",
                description=f"这是一个示例 AI 模型，用于演示第 {i+1} 号场景",
                model_type=model_types[i % len(model_types)],
                framework=frameworks[i % len(frameworks)],
                version=f"{i+1}.0.0",
                business_scenarios=["场景 1", "场景 2"],
                creator_id=user.id,
                status="available",
                download_count=random.randint(0, 100)
            )
            db.add(model)

        # 创建示例数据集
        domains = ['finance', 'contract', 'utility', 'hr', 'other']
        domain_names = ['财务', '合同', '水电', '人力', '其他']

        for i in range(5):
            dataset = models.Dataset(
                name=f"示例数据集-{i+1}",
                description=f"这是{domain_names[i]}领域的示例数据集",
                business_domain=domains[i],
                data_type='structured' if i % 2 == 0 else 'unstructured',
                source='internal',
                record_count=random.randint(1000, 100000),
                creator_id=user.id,
                status="available"
            )
            db.add(dataset)

        # 创建示例智能体
        agent_types = ['MCP', 'AI+ 业务场景', '自动化助手']

        for i in range(4):
            agent = models.Agent(
                name=f"智能助手-{i+1}",
                description=f"这是一个示例智能体，提供第 {i+1} 类服务",
                agent_type=agent_types[i % len(agent_types)],
                business_domain=domains[i % len(domains)],
                development_status='released',
                creator_id=user.id,
                status="available"
            )
            db.add(agent)

        # 创建示例应用场景
        app_statuses = ['draft', 'submitted', 'under_review', 'approved', 'completed']

        for i in range(6):
            application = models.Application(
                title=f"应用场景申报-{i+1}",
                department=f"部门{chr(65+i)}",
                contact_info=f"1380000000{i}",
                business_background=f"这是业务背景描述 {i+1}",
                current_pain_points=f"当前痛点描述 {i+1}",
                expected_value=f"预期价值描述 {i+1}",
                applicant_id=user.id,
                status=app_statuses[i % len(app_statuses)]
            )
            db.add(application)

        # 创建示例算力资源
        resource_types = ['GPU', 'CPU', 'TPU']
        gpu_models = ['A100', 'H100', 'V100', 'T4']

        for i in range(4):
            resource = models.ComputeResource(
                name=f"算力资源-{i+1}",
                resource_type=resource_types[i % len(resource_types)],
                model_name=gpu_models[i % len(gpu_models)] if i % 3 == 0 else f"Model-{i+1}",
                memory_size=random.choice([16, 32, 64, 80]),
                total_compute=random.uniform(10, 100),
                used_compute=random.uniform(0, 30),
                location=f"机房{chr(65+i)}",
                owner_department=f"部门{chr(65+i)}",
                support_scenarios=['训练', '推理']
            )
            db.add(resource)

        # 创建示例应用广场项目
        categories = ['general', 'custom']

        for i in range(4):
            app_item = models.AppStoreItem(
                name=f"示例应用-{i+1}",
                description=f"这是一个示例应用，提供第 {i+1} 类功能",
                category=categories[i % 2],
                business_domain=domains[i % len(domains)],
                developer=f"开发者{i+1}",
                version=f"{i+1}.0.0",
                features=["功能 1", "功能 2"],
                usage_count=random.randint(0, 500),
                rating=random.uniform(3.5, 5.0)
            )
            db.add(app_item)

        # 创建示例论坛帖子
        post_categories = ['tech', 'case', 'qa', 'news']

        for i in range(5):
            post = models.ForumPost(
                title=f"示例帖子标题-{i+1}",
                content=f"这是示例帖子的内容...\n\nLorem ipsum dolor sit amet, consectetur adipiscing elit.\n" * (i+1),
                category=post_categories[i % len(post_categories)],
                author_id=user.id,
                tags=[f"标签{j+1}" for j in range(i+1)],
                view_count=random.randint(0, 1000),
                like_count=random.randint(0, 100),
                comment_count=random.randint(0, 50),
                is_pinned=i == 0  # 第一个帖子置顶
            )
            db.add(post)

        # 创建工作流记录
        actions = ['apply', 'review', 'approve', 'use']

        for i in range(10):
            record = models.WorkflowRecord(
                application_id=(i % 6) + 1,
                record_type=['application', 'dataset', 'model', 'agent', 'compute'][i % 5],
                record_id=i + 1,
                action=actions[i % len(actions)],
                actor_id=user.id,
                description=f"示例工作流记录 {i+1}"
            )
            db.add(record)

        db.commit()
        print("示例数据创建成功！")

    except Exception as e:
        db.rollback()
        print(f"创建示例数据失败：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # 先初始化数据库
    init_db()
    # 创建示例数据
    create_sample_data()
