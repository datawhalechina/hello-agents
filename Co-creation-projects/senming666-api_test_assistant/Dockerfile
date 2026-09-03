# ============================================================
# 智能API测试助手 - Docker 镜像配方(Dockerfile)
#
# 思路:一个集装箱装下「能跑起来的完整服务」。
# 你的服务其实只有一个进程:server.py
#   - 既当后端(FastAPI,处理 /api/test)
#   - 又托管前端(把编译好的 frontend/dist 发给浏览器)
# 所以容器只需要做一件事:让 server.py 跑起来,对外开 8000 端口。
#
# 前端要"编译"成静态文件(需要 Node),后端要"运行"(需要 Python),
# 两个集装箱环境都想要?Docker 的答案是"多阶段构建":
#   阶段一:用 Node 把 Vue 源码编译出 dist 成品
#   阶段二:用 Python 环境把 dist 搬进来,再跑 server.py
# 最终镜像只保留阶段二,阶段一的所有文件都会被丢弃(不占体积)。
# ============================================================

# ---------- 阶段 1:造前端(Node 集装箱) ----------
# 用 node:22-alpine(精简版)而非 node:22:功能足够、体积更小,
# 且本机已缓存该镜像,可避免从 Docker Hub 下载被网络卡住。
FROM node:22-alpine AS frontend-builder

# 工作目录:进了这个集装箱后的默认落点,后面的命令都在这里执行
WORKDIR /build

# 先只复制"依赖清单",然后 npm install。
# 故意拆两步,是为了吃 Docker 缓存:只要 package.json 没变,
# 下次 build 就直接复用上次装好的依赖,不用重新下载几百 MB。
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# 再复制全部前端源码,执行编译。Vite 会把成品输出到 /build/dist
COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2:跑后端(Python 集装箱) ----------
FROM python:3.12-slim

# 后端代码统一放在 /app 目录
WORKDIR /app

# 同样的缓存技巧:先装依赖,再拷代码
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码(server.py 和 src/ 包)
COPY server.py ./
COPY src/ ./src/

# 关键一步:把阶段一编译出的前端成品搬进 Python 集装箱。
# server.py 里找的是 ./frontend/dist,所以这个目录名不能改。
COPY --from=frontend-builder /build/dist ./frontend/dist

# 只是"说明书":声明容器对外开 8000 端口(真正开不开由运行时 -p 决定)
EXPOSE 8000

# 容器一启动就跑这条命令,等价于你本地 python server.py
# (server.py 内部会调 uvicorn,监听 0.0.0.0:8000)
CMD ["python", "server.py"]
