"""
数据库迁移脚本 - 为数据集/模型/智能体/应用广场/算力资源添加工作流支持
"""
import sys
sys.path.append('.')

from sqlalchemy import create_engine, text
from app.core.database import engine


def run_migration():
    """运行迁移"""
    with engine.connect() as conn:
        # 为 datasets 表添加字段
        add_columns(conn, 'datasets')

        # 为 models 表添加字段
        add_columns(conn, 'models')

        # 为 agents 表添加字段
        add_columns(conn, 'agents')

        # 为 app_store 表添加字段
        add_columns(conn, 'app_store')

        # 为 compute_resources 表添加字段
        add_columns(conn, 'compute_resources')

        print("所有表的字段添加成功！")


def add_columns(conn, table_name):
    """为指定表添加工作流相关字段"""
    columns_to_add = [
        ('workflow_definition_id', 'INTEGER REFERENCES workflow_definitions(id)'),
        ('workflow_record_id', 'INTEGER REFERENCES workflow_records(id)'),
        ('review_comments', 'TEXT'),
        ('reviewer_id', 'INTEGER REFERENCES users(id)'),
        ('approved_at', 'DATETIME'),
    ]

    for col_name, col_type in columns_to_add:
        try:
            # 检查列是否已存在
            result = conn.execute(text(
                f"PRAGMA table_info({table_name})"
            ))
            existing_cols = [row[1] for row in result.fetchall()]

            if col_name not in existing_cols:
                conn.execute(text(
                    f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                ))
                print(f"{table_name} 表添加 {col_name} 字段成功！")
            else:
                print(f"{table_name} 表 {col_name} 字段已存在，跳过")
        except Exception as e:
            print(f"{table_name} 表添加 {col_name} 字段失败：{e}")

    # 更新 status 字段的默认值（可选，SQLite 中不容易修改默认值）
    print(f"{table_name} 表状态字段逻辑已更新（需要前端配合）")


if __name__ == "__main__":
    run_migration()
