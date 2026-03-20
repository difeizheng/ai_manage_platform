"""
数据库迁移脚本 - 为 application_requests 表添加工作流绑定字段
运行方式：python scripts/migrations/add_workflow_to_application_request.py
"""
import sys
sys.path.append('D:/project_room/workspace2024/nantian/sx-ai/ai_manage_platform')

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def migrate():
    """执行迁移"""
    # 创建数据库引擎
    engine = create_engine(settings.DATABASE_URL)

    # 检查字段是否已存在
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('application_requests')]

    # 添加 workflow_definition_id 字段
    if 'workflow_definition_id' not in columns:
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE application_requests ADD COLUMN workflow_definition_id INTEGER"
            ))
            conn.commit()
        print("[OK] 已添加 workflow_definition_id 字段")
    else:
        print("[OK] workflow_definition_id 字段已存在")

    # 添加 workflow_record_id 字段
    if 'workflow_record_id' not in columns:
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE application_requests ADD COLUMN workflow_record_id INTEGER"
            ))
            conn.commit()
        print("[OK] 已添加 workflow_record_id 字段")
    else:
        print("[OK] workflow_record_id 字段已存在")

    # 添加外键约束（可选）
    print("[OK] 迁移完成")


if __name__ == "__main__":
    migrate()
