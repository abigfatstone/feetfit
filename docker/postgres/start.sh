#!/bin/bash

# 启动SSH服务
service ssh start

# 后台启动PostgreSQL
docker-entrypoint.sh postgres &

# 等待PostgreSQL就绪
until pg_isready -U holistic_user -d holistic_db; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 1
done

# 执行SQL文件
echo "Executing SQL files..."

# 检查执行顺序文件是否存在
ORDER_FILE="/app/backend_db/sql_execution_order.txt"
echo "Checking for execution order file: $ORDER_FILE"
if [ -f "$ORDER_FILE" ]; then
  echo "Using execution order from: $ORDER_FILE"
  # 按照配置文件中指定的顺序执行文件
  while IFS= read -r line; do
    # 跳过空行和注释
    if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
      sql_file="/app/backend_db/$line"
      if [ -f "$sql_file" ]; then
        echo "Executing: $line"
        psql -U holistic_user -d holistic_db -f "$sql_file" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
          echo "Successfully executed: $line"
        else
          echo "Error executing: $line"
        fi
      else
        echo "Warning: File not found: $line"
      fi
    fi
  done < "$ORDER_FILE"
else
  echo "No execution order file found. Executing all SQL files in alphabetical order..."
  # 按字母顺序执行所有SQL文件
  for sql_file in /app/backend_db/resource/*.sql; do
    if [ -f "$sql_file" ]; then
      echo "Executing: $(basename "$sql_file")"
      psql -U holistic_user -d holistic_db -f "$sql_file" > /dev/null 2>&1
      if [ $? -eq 0 ]; then
        echo "Successfully executed: $(basename "$sql_file")"
      else
        echo "Error executing: $(basename "$sql_file")"
      fi
    fi
  done
fi

echo "All SQL files executed."

# 保持容器运行
wait
