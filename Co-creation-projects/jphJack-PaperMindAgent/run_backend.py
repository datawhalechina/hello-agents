"""项目根目录启动脚本：python run_backend.py 启动 uvicorn 服务

    host=0.0.0.0, port=8000
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
