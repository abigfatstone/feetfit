# PostgreSQL数据库容器
FROM postgres:15-alpine

# 设置环境变量
ENV POSTGRES_DB=holistic_db
ENV POSTGRES_USER=holistic_user
ENV POSTGRES_PASSWORD=holistic_password
ENV PGDATA=/var/lib/postgresql/data/pgdata

# 安装额外的扩展
RUN apk add --no-cache \
    postgresql-contrib \
    postgresql-dev

# 创建数据目录
RUN mkdir -p /var/lib/postgresql/data/pgdata && \
    chown -R postgres:postgres /var/lib/postgresql/data

# 复制初始化脚本
COPY init-scripts/ /docker-entrypoint-initdb.d/

# 复制配置文件
COPY postgresql.conf /etc/postgresql/postgresql.conf
COPY pg_hba.conf /etc/postgresql/pg_hba.conf

# 设置权限
RUN chmod 644 /etc/postgresql/postgresql.conf && \
    chmod 644 /etc/postgresql/pg_hba.conf

# 暴露端口
EXPOSE 5432

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pg_isready -U $POSTGRES_USER -d $POSTGRES_DB || exit 1

# 启动脚本
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
