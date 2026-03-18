#!/bin/bash
# 启动脚本

echo "正在启动人工智能管理平台..."

# 创建必要目录
mkdir -p data data/uploads static

# 初始化数据库（如果不存在）
if [ ! -f "data/ai_platform.db" ]; then
    echo "初始化数据库..."
    python init_data.py
fi

# 启动应用
echo "启动服务..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
