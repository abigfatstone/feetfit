#!/bin/bash
set -e

# 启动PostgreSQL服务器的脚本

# 如果数据目录不存在，初始化数据库
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "初始化PostgreSQL数据库..."
    initdb -D "$PGDATA" -U "$POSTGRES_USER" --pwfile=<(echo "$POSTGRES_PASSWORD")
    
    # 创建数据库
    echo "创建数据库: $POSTGRES_DB"
    createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
fi

# 启动PostgreSQL
echo "启动PostgreSQL服务器..."
exec postgres -D "$PGDATA" -c config_file=/etc/postgresql/postgresql.conf
