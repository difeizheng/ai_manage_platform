"""
数据库迁移脚本 - 创建论坛评论表
运行方式：python scripts/migrations/create_forum_comments.py
"""
import sys
sys.path.append('D:/project_room/workspace2024/nantian/sx-ai/ai_manage_platform')

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def migrate():
    """执行迁移"""
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)

    # 检查表是否存在
    tables = inspector.get_table_names()

    if 'forum_comments' in tables:
        print("[OK] forum_comments 表已存在")
        return

    # 创建表
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE forum_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                parent_id INTEGER,
                content TEXT NOT NULL,
                like_count INTEGER DEFAULT 0,
                is_deleted BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                FOREIGN KEY (post_id) REFERENCES forum_posts(id),
                FOREIGN KEY (author_id) REFERENCES users(id),
                FOREIGN KEY (parent_id) REFERENCES forum_comments(id)
            )
        """))
        conn.commit()

    print("[OK] 已创建 forum_comments 表")


if __name__ == "__main__":
    migrate()
