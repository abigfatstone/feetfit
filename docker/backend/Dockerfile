# 足底压力可视化后端Dockerfile
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件并安装Python依赖
COPY pressure-viz-web/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 创建必要的目录
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# 暴露端口
EXPOSE 3080

# 切换到非root用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3080/health || exit 1

# 启动命令
CMD ["python", "pressure-viz-web/backend/main.py"]
