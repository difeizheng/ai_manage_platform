import os
import sys

def main():
    """主启动函数"""
    # 创建必要的目录
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/uploads", exist_ok=True)

    # 启动应用
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
