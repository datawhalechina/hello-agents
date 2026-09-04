import uvicorn
from app.services.unsplash_service import UnsplashService
if __name__ == "__main__":
    # 启动Uvicorn服务器
    # --reload: 代码变更时自动重启，方便开发
    # --host 0.0.0.0: 监听所有网络接口，允许局域网访问
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    # service = UnsplashService(access_key="qoRz2cAQwJD5kPyrN7_2dqdn_1Kfp-DXq4TQKK_dgI8")
    # photos = service.search_photos("北京故宫", per_page=1)
    # print(photos)