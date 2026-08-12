import uvicorn

if __name__ == "__main__":
    # 指定 app 实例的位置：api.routes.main:app
    uvicorn.run("api.routes.main:app", host="0.0.0.0", port=8000, reload=True)