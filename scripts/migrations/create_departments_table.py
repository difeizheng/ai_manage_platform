"""
数据库迁移脚本 - 创建部门表
"""
import sys
sys.path.append('.')

from sqlalchemy import create_engine, text
from app.core.database import engine, Base
from app.models.models import Department


def run_migration():
    """运行迁移"""
    with engine.connect() as conn:
        # 检查表是否已存在
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='departments'"
        ))
        if result.fetchone():
            print("部门表已存在，跳过创建")
            return

        # 创建部门表
        Base.metadata.create_all(bind=engine)
        print("部门表创建成功！")

        # 在 users 表中添加 department_id 字段
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN department_id INTEGER REFERENCES departments(id)"
            ))
            print("users 表 department_id 字段添加成功！")
        except Exception as e:
            print(f"users 表 department_id 字段已存在或添加失败：{e}")


if __name__ == "__main__":
    run_migration()
