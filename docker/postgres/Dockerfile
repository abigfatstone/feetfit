# 足底压力可视化数据库Dockerfile
FROM pgvector/pgvector:pg17

# 更新系统包
RUN apt-get update && apt-get upgrade -y

# 设置环境变量
ENV POSTGRES_USER=holistic_user
ENV POSTGRES_PASSWORD=holistic_password
ENV POSTGRES_DB=holistic_db

# 复制启动脚本
COPY ./start.sh /start.sh
RUN chmod +x /start.sh

# 暴露PostgreSQL端口
EXPOSE 5432

# 使用启动脚本作为入口点
ENTRYPOINT ["/start.sh"]
