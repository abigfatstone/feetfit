# 足底压力可视化前端Dockerfile
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1

# 安装系统依赖
RUN apk add --no-cache \
    libc6-compat \
    curl

# 复制package文件
COPY pressure-viz-web/package*.json ./

# 安装依赖
RUN npm ci --only=production --silent

# 创建非root用户
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# 创建必要的目录并设置权限
RUN mkdir -p /app/.next && \
    chown -R nextjs:nodejs /app

# 暴露端口
EXPOSE 3060

# 切换到非root用户
USER nextjs

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3060 || exit 1

# 启动命令（开发模式，支持热重载）
CMD ["npm", "run", "dev"]
