"""
数据库迁移脚本 - 添加 is_department_manager 字段到 users 表
运行方式：python scripts/migrations/add_department_manager_field.py
"""
import sys
sys.path.append('D:/project_room/workspace2024/nantian/sx-ai/ai_manage_platform')

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
from app.core.database import Base

def migrate():
    """执行迁移"""
    # 创建数据库引擎
    engine = create_engine(settings.DATABASE_URL)

    # 检查字段是否已存在
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'is_department_manager' in columns:
        print("[OK] is_department_manager 字段已存在，无需迁移")
        return

    # 执行迁移
    with engine.connect() as conn:
        # 添加字段
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN is_department_manager BOOLEAN DEFAULT FALSE"
        ))
        conn.commit()

    print("[OK] 迁移完成：已添加 is_department_manager 字段到 users 表")


if __name__ == "__main__":
    migrate()
