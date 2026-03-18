@echo off
REM Windows 启动脚本

echo 正在启动人工智能管理平台...

REM 创建必要目录
if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads
if not exist "static" mkdir static

REM 初始化数据库（如果不存在）
if not exist "data\ai_platform.db" (
    echo 初始化数据库...
    python init_data.py
)

REM 启动应用
echo 启动服务...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
