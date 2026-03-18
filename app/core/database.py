"""
数据库配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# SQLite 需要 check_same_thread=False
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """初始化数据库，创建所有表"""
    # 导入所有模型以确保它们被注册到 Base
    from app.models import models
    Base.metadata.create_all(bind=engine)

    # 创建默认管理员用户
    from app.core.security import get_password_hash
    from sqlalchemy.orm import Session

    db = SessionLocal()
    try:
        # 检查是否已有管理员
        admin = db.query(models.User).filter(models.User.role == 'admin').first()
        if not admin:
            admin = models.User(
                username='admin',
                password_hash=get_password_hash('admin123'),
                real_name='系统管理员',
                email='admin@example.com',
                role='admin',
                is_active=True
            )
            db.add(admin)

            # 创建测试用户
            user = models.User(
                username='user',
                password_hash=get_password_hash('user123'),
                real_name='测试用户',
                email='user@example.com',
                department='技术部',
                role='user',
                is_active=True
            )
            db.add(user)

            db.commit()
            print("默认用户创建成功：admin/admin123, user/user123")
    finally:
        db.close()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
