# =========================================================================
# 智能股票分析助手 — 前端 Dockerfile（多阶段构建）
# 
# 第一阶段: Node.js 构建 Vue3 应用
# 第二阶段: Nginx 提供静态文件 + API 反向代理
# 构建: docker build -t stock-analyzer-frontend -f frontend/Dockerfile .
# =========================================================================

# ---- 构建阶段 ----
FROM node:20-alpine AS build

WORKDIR /app

# 复制依赖文件并安装
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci || npm install

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build

# ---- 生产阶段 ----
FROM nginx:alpine

# 复制构建产物到 Nginx 静态目录
COPY --from=build /app/dist /usr/share/nginx/html

# 复制 Nginx 配置（SPA路由 + API反向代理）
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
