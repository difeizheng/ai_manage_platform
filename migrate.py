"""
数据库迁移脚本 - 添加新增的表结构
运行方式：python migrate.py
"""
import sqlite3
from datetime import datetime

DATABASE_URL = "sqlite.db"

def migrate():
    """执行数据库迁移"""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("开始数据库迁移...")

    # 1. 文件表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename VARCHAR(255) NOT NULL,
        stored_name VARCHAR(255) NOT NULL,
        file_path VARCHAR(500) NOT NULL,
        file_size INTEGER NOT NULL,
        file_type VARCHAR(50),
        file_category VARCHAR(50),
        file_hash VARCHAR(64),
        uploader_id INTEGER NOT NULL,
        related_type VARCHAR(50),
        related_id INTEGER,
        is_public BOOLEAN DEFAULT FALSE,
        download_count INTEGER DEFAULT 0,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY (uploader_id) REFERENCES users(id)
    )
    """)
    print("[OK] 创建 files 表")

    # 2. 邮件日志表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient VARCHAR(100) NOT NULL,
        subject VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        template_name VARCHAR(100),
        status VARCHAR(20) DEFAULT 'pending',
        error_message TEXT,
        sent_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("[OK] 创建 email_logs 表")

    # 3. 通知设置表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notification_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        enable_email BOOLEAN DEFAULT TRUE,
        enable_workflow_email BOOLEAN DEFAULT TRUE,
        enable_system_email BOOLEAN DEFAULT TRUE,
        quiet_start VARCHAR(10),
        quiet_end VARCHAR(10),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    print("[OK] 创建 notification_settings 表")

    # 4. 报表定义表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        report_type VARCHAR(50) NOT NULL,
        config JSON,
        is_public BOOLEAN DEFAULT FALSE,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    """)
    print("[OK] 创建 reports 表")

    # 5. 报表数据缓存表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS report_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        cache_key VARCHAR(100) NOT NULL,
        cache_data JSON,
        expires_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (report_id) REFERENCES reports(id)
    )
    """)
    print("[OK] 创建 report_cache 表")

    # 6. 密码重置令牌表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token VARCHAR(100) UNIQUE NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    print("[OK] 创建 password_reset_tokens 表")

    # 7. 用户 profile 扩展表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        avatar_path VARCHAR(500),
        bio TEXT,
        skills JSON,
        projects JSON,
        phone_public BOOLEAN DEFAULT FALSE,
        email_public BOOLEAN DEFAULT FALSE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    print("[OK] 创建 user_profiles 表")

    # 8. 职位表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL,
        code VARCHAR(50) UNIQUE NOT NULL,
        description TEXT,
        parent_id INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES positions(id)
    )
    """)
    print("[OK] 创建 positions 表")

    # 9. 用户职位关联表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        position_id INTEGER NOT NULL,
        department_id INTEGER,
        is_primary BOOLEAN DEFAULT TRUE,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (position_id) REFERENCES positions(id),
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )
    """)
    print("[OK] 创建 user_positions 表")

    # 10. 审计日志表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action VARCHAR(50) NOT NULL,
        resource_type VARCHAR(50),
        resource_id INTEGER,
        resource_name VARCHAR(255),
        user_id INTEGER,
        username VARCHAR(100),
        request_ip VARCHAR(50),
        request_data JSON,
        status VARCHAR(20) DEFAULT 'success',
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("[OK] 创建 audit_logs 表")

    # 11. 登录日志表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(100) NOT NULL,
        user_id INTEGER,
        login_ip VARCHAR(50),
        user_agent VARCHAR(500),
        status VARCHAR(20) DEFAULT 'success',
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("[OK] 创建 login_logs 表")

    # 12. 论坛评论表（如果不存在）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        parent_id INTEGER,
        like_count INTEGER DEFAULT 0,
        is_deleted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES forum_posts(id),
        FOREIGN KEY (author_id) REFERENCES users(id)
    )
    """)
    print("[OK] 创建 forum_comments 表")

    # 13. 应用申请表（如果不存在）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_type VARCHAR(50) NOT NULL,
        resource_id INTEGER NOT NULL,
        resource_name VARCHAR(255) NOT NULL,
        purpose TEXT,
        expected_duration INTEGER,
        expected_frequency VARCHAR(50),
        related_application VARCHAR(255),
        applicant_id INTEGER,
        applicant_department VARCHAR(100),
        status VARCHAR(20) DEFAULT 'pending',
        reviewer_id INTEGER,
        review_comments TEXT,
        approved_at TIMESTAMP,
        workflow_definition_id INTEGER,
        workflow_record_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY (applicant_id) REFERENCES users(id)
    )
    """)
    print("[OK] 创建 application_requests 表")

    # 15. users 表新增 is_department_manager 字段（如果不存在则添加）
    # 注意：users 表应该由 init_db() 创建，这里仅做迁移检查
    try:
        # 先检查 users 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("[] users 表不存在，跳过 is_department_manager 字段添加")
        else:
            cursor.execute("""
            ALTER TABLE users ADD COLUMN is_department_manager BOOLEAN DEFAULT FALSE
            """)
            print("[OK] 添加 users.is_department_manager 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("[] users.is_department_manager 字段已存在")
        else:
            print(f"[ERROR] 添加字段失败：{e}")

    conn.commit()
    conn.close()

    print("\n迁移完成！")


if __name__ == "__main__":
    migrate()
