# 传感器数据管理系统

这个系统用于管理和存储多设备传感器数据，支持高频率的时间序列数据存储和查询。

## 数据库表结构

### 主表: `theta_ai.sensor_data`

| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | BIGSERIAL | 主键ID |
| timestamp | TIMESTAMP WITH TIME ZONE | 数据时间戳 |
| device_name | VARCHAR(100) | 设备名称 |
| device_mac | VARCHAR(50) | 设备MAC地址 |
| accel_x/y/z | DECIMAL(10,6) | 加速度数据 (g) |
| gyro_x/y/z | DECIMAL(10,6) | 角速度数据 (°/s) |
| angle_x/y/z | DECIMAL(10,6) | 角度数据 (°) |
| mag_x/y/z | DECIMAL(10,6) | 磁场数据 (uT) |
| quaternion_0/1/2/3 | DECIMAL(10,6) | 四元数数据 |
| temperature | DECIMAL(6,2) | 温度 (°C) |
| firmware_version | VARCHAR(50) | 固件版本 |
| battery_level | INTEGER | 电量百分比 |
| created_at | TIMESTAMP WITH TIME ZONE | 创建时间 |

### 索引设计

- 主键索引: `id`
- 时间索引: `timestamp`
- 设备索引: `device_name`
- 复合索引: `device_name + timestamp`
- 创建时间索引: `created_at`

### 分区策略

表按时间戳进行分区，提高查询性能：
- 当前分区覆盖前1个月到后2个月的数据
- 可根据需要创建更多历史分区

## 核心功能

### 1. SensorDataManager 类

主要的数据管理类，提供以下功能：

#### 初始化
```python
from utils.sensor_data_manager import SensorDataManager

manager = SensorDataManager()
```

#### 创建表
```python
await manager.create_sensor_data_table()
```

#### 数据解析和导入
```python
# 从文本文件解析数据
data_list = manager.parse_sensor_data_from_text("data_file.txt")

# 批量插入数据
await manager.insert_sensor_data_batch(data_list)
```

#### 数据查询
```python
# 查询最近的数据
recent_data = await manager.query_sensor_data(limit=100)

# 查询特定设备数据
device_data = await manager.query_sensor_data(device_name="WTSDCL", limit=50)

# 时间范围查询
from datetime import datetime, timedelta
end_time = datetime.now()
start_time = end_time - timedelta(hours=1)
time_range_data = await manager.query_sensor_data(
    start_time=start_time,
    end_time=end_time,
    limit=200
)
```

#### 设备统计
```python
stats = await manager.get_device_statistics()
```

### 2. 便捷函数

#### 文件导入
```python
from utils.sensor_data_manager import import_sensor_data_from_file

await import_sensor_data_from_file("path/to/data_file.txt")
```

## 使用示例

### 基本使用流程

1. **创建数据表**
```python
import asyncio
from utils.sensor_data_manager import SensorDataManager

async def setup_database():
    manager = SensorDataManager()
    await manager.create_sensor_data_table()

asyncio.run(setup_database())
```

2. **导入数据**
```python
from utils.sensor_data_manager import import_sensor_data_from_file

# 导入传感器数据文件
await import_sensor_data_from_file("/path/to/sensor_data.txt")
```

3. **查询数据**
```python
async def query_example():
    manager = SensorDataManager()
    
    # 获取设备统计
    stats = await manager.get_device_statistics()
    print("设备统计:", stats)
    
    # 查询最近数据
    recent = await manager.query_sensor_data(limit=10)
    print("最近数据:", recent)

asyncio.run(query_example())
```

### 演示脚本使用

系统提供了完整的演示脚本 `demo_sensor_data.py`：

```bash
# 运行完整演示
python demo_sensor_data.py

# 只创建表
python demo_sensor_data.py create_table

# 导入指定文件
python demo_sensor_data.py import_data /path/to/data_file.txt

# 查询数据
python demo_sensor_data.py query_data

# 显示帮助
python demo_sensor_data.py help
```

## 数据格式说明

### 输入数据格式

系统支持制表符分隔的文本文件，包含以下列：

```
时间	设备名称	加速度X(g)	加速度Y(g)	加速度Z(g)	角速度X(°/s)	角速度Y(°/s)	角速度Z(°/s)	角度X(°)	角度Y(°)	角度Z(°)	磁场X(uT)	磁场Y(uT)	磁场Z(uT)	四元数0()	四元数1()	四元数2()	四元数3()	温度(°C)	版本号()	电量(%)
```

### 时间戳格式

支持以下时间戳格式：
- `2025-6-5 18:12:11:817` (包含毫秒)
- `2025-6-5 18:12:11` (标准格式)

### 设备名称格式

设备名称格式: `设备类型(MAC地址)`
- 例如: `WTSDCL(FE:D5:86:66:1D:7C)`
- 系统会自动解析设备类型和MAC地址

## 性能优化

### 批量插入

系统使用批量插入来提高性能：
```python
# 一次插入多条记录
await manager.insert_sensor_data_batch(data_list)
```

### 分区表

使用时间分区来优化查询性能，特别是对于大量历史数据的查询。

### 索引优化

针对常见查询模式创建了优化的索引：
- 时间范围查询
- 设备过滤查询
- 复合查询

## 错误处理

系统包含完善的错误处理机制：
- 数据解析错误处理
- 数据库连接错误处理
- 批量插入失败回滚
- 详细的错误日志记录

## 扩展功能

### 数据分析

可以基于存储的数据进行各种分析：
- 设备运行状态分析
- 传感器数据趋势分析
- 异常检测
- 设备性能监控

### 数据导出

支持将查询结果导出为不同格式：
- JSON格式
- CSV格式
- DataFrame格式（用于数据分析）

## 配置要求

### 数据库配置

确保 `config/config.yaml` 中包含正确的数据库配置：

```yaml
pg_host_core: "your_db_host"
pg_port_core: 5432
pg_user_core: "your_username"
pg_dbname_core: "your_database"
pg_schema_core: "theta_ai"
```

### 依赖包

系统依赖以下Python包：
- `asyncio` - 异步编程支持
- `pandas` - 数据处理
- `psycopg2` - PostgreSQL连接
- `sqlalchemy` - ORM支持

## 注意事项

1. **数据量管理**: 对于大量数据，建议定期清理历史数据或使用数据归档策略
2. **并发处理**: 系统支持异步操作，可以处理高并发的数据插入和查询
3. **数据完整性**: 系统会验证数据格式，跳过无效的数据行
4. **性能监控**: 建议监控数据库性能，根据需要调整索引和分区策略

## 故障排除

### 常见问题

1. **连接失败**: 检查数据库配置和网络连接
2. **导入失败**: 检查数据文件格式和编码
3. **查询慢**: 检查索引使用情况和查询条件
4. **内存不足**: 对于大文件，考虑分批处理

### 日志查看

系统会记录详细的操作日志，包括：
- SQL执行日志
- 数据处理日志
- 错误详情日志

