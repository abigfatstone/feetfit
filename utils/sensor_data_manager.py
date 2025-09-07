# -*- coding: utf-8 -*-
"""
传感器数据管理模块
用于处理多设备传感器数据的存储和查询
"""

import asyncio
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.utils_db import utils_db_manager, DB_CONFIG_CORE


class SensorDataManager:
    """传感器数据管理器"""
    
    def __init__(self, db_config=None):
        """
        初始化传感器数据管理器
        
        Args:
            db_config: 数据库配置，默认使用 DB_CONFIG_CORE
        """
        self.db_config = db_config or DB_CONFIG_CORE
        self.db_manager = utils_db_manager
        
    async def create_sensor_data_table(self):
        """
        创建传感器数据表
        
        表结构设计说明：
        - 使用时间戳和设备ID作为复合主键
        - 添加分区支持以提高查询性能
        - 包含所有传感器数据字段
        - 添加必要的索引
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS theta_ai.sensor_data (
            id BIGSERIAL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            device_name VARCHAR(100) NOT NULL,
            device_mac VARCHAR(50),
            
            -- 加速度数据 (g)
            accel_x DECIMAL(10, 6),
            accel_y DECIMAL(10, 6),
            accel_z DECIMAL(10, 6),
            
            -- 角速度数据 (°/s)
            gyro_x DECIMAL(10, 6),
            gyro_y DECIMAL(10, 6),
            gyro_z DECIMAL(10, 6),
            
            -- 角度数据 (°)
            angle_x DECIMAL(10, 6),
            angle_y DECIMAL(10, 6),
            angle_z DECIMAL(10, 6),
            
            -- 磁场数据 (uT)
            mag_x DECIMAL(10, 6),
            mag_y DECIMAL(10, 6),
            mag_z DECIMAL(10, 6),
            
            -- 四元数数据
            quaternion_0 DECIMAL(10, 6),
            quaternion_1 DECIMAL(10, 6),
            quaternion_2 DECIMAL(10, 6),
            quaternion_3 DECIMAL(10, 6),
            
            -- 设备状态数据
            temperature DECIMAL(6, 2),
            firmware_version VARCHAR(50),
            battery_level INTEGER,
            
            -- 元数据
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            
            -- 主键约束
            PRIMARY KEY (id)
        ) PARTITION BY RANGE (timestamp);
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON theta_ai.sensor_data (timestamp);
        CREATE INDEX IF NOT EXISTS idx_sensor_data_device_name ON theta_ai.sensor_data (device_name);
        CREATE INDEX IF NOT EXISTS idx_sensor_data_device_timestamp ON theta_ai.sensor_data (device_name, timestamp);
        CREATE INDEX IF NOT EXISTS idx_sensor_data_created_at ON theta_ai.sensor_data (created_at);
        
        -- 创建当前月份的分区表
        CREATE TABLE IF NOT EXISTS theta_ai.sensor_data_current PARTITION OF theta_ai.sensor_data
        FOR VALUES FROM (CURRENT_DATE - INTERVAL '1 month') TO (CURRENT_DATE + INTERVAL '2 months');
        """
        
        try:
            await self.db_manager.execute_query(
                query=create_table_sql,
                db_config=self.db_config,
                query_type="ddl"
            )
            print("传感器数据表创建成功")
            return True
        except Exception as e:
            print(f"创建传感器数据表失败: {e}")
            return False
    
    def parse_device_info(self, device_name: str) -> tuple:
        """
        解析设备名称，提取设备类型和MAC地址
        
        Args:
            device_name: 设备名称，格式如 "WTSDCL(FE:D5:86:66:1D:7C)"
            
        Returns:
            tuple: (设备类型, MAC地址)
        """
        if '(' in device_name and ')' in device_name:
            device_type = device_name.split('(')[0]
            mac_address = device_name.split('(')[1].replace(')', '')
            return device_type, mac_address
        return device_name, None
    
    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        解析时间戳字符串
        
        Args:
            timestamp_str: 时间戳字符串，格式如 "2025-6-5 18:12:11:817"
            
        Returns:
            datetime: 解析后的时间戳
        """
        try:
            # 处理毫秒部分
            if ':' in timestamp_str.split(' ')[-1]:
                # 格式: "2025-6-5 18:12:11:817"
                date_part, time_part = timestamp_str.rsplit(' ', 1)
                if ':' in time_part:
                    time_components = time_part.split(':')
                    if len(time_components) == 4:  # 包含毫秒
                        hour, minute, second, millisecond = time_components
                        formatted_time = f"{hour}:{minute}:{second}.{millisecond}"
                        formatted_timestamp = f"{date_part} {formatted_time}"
                        return datetime.strptime(formatted_timestamp, "%Y-%m-%d %H:%M:%S.%f")
            
            # 标准格式处理
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"时间戳解析失败: {timestamp_str}, 错误: {e}")
            return datetime.now()
    
    async def insert_sensor_data_batch(self, data_list: List[Dict[str, Any]]) -> bool:
        """
        批量插入传感器数据
        
        Args:
            data_list: 传感器数据列表
            
        Returns:
            bool: 插入是否成功
        """
        if not data_list:
            return True
            
        insert_sql = """
        INSERT INTO theta_ai.sensor_data (
            timestamp, device_name, device_mac,
            accel_x, accel_y, accel_z,
            gyro_x, gyro_y, gyro_z,
            angle_x, angle_y, angle_z,
            mag_x, mag_y, mag_z,
            quaternion_0, quaternion_1, quaternion_2, quaternion_3,
            temperature, firmware_version, battery_level
        ) VALUES (
            %(timestamp)s, %(device_name)s, %(device_mac)s,
            %(accel_x)s, %(accel_y)s, %(accel_z)s,
            %(gyro_x)s, %(gyro_y)s, %(gyro_z)s,
            %(angle_x)s, %(angle_y)s, %(angle_z)s,
            %(mag_x)s, %(mag_y)s, %(mag_z)s,
            %(quaternion_0)s, %(quaternion_1)s, %(quaternion_2)s, %(quaternion_3)s,
            %(temperature)s, %(firmware_version)s, %(battery_level)s
        )
        """
        
        try:
            await self.db_manager.execute_query(
                query=insert_sql,
                params=None,
                fieldList=data_list,
                query_type="insert_many",
                db_config=self.db_config
            )
            print(f"成功插入 {len(data_list)} 条传感器数据")
            return True
        except Exception as e:
            print(f"批量插入传感器数据失败: {e}")
            return False
    
    def parse_sensor_data_from_text(self, file_path: str) -> List[Dict[str, Any]]:
        """
        从文本文件解析传感器数据
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            List[Dict]: 解析后的传感器数据列表
        """
        try:
            # 读取文件
            df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
            
            data_list = []
            for _, row in df.iterrows():
                try:
                    # 解析设备信息
                    device_type, mac_address = self.parse_device_info(row['设备名称'])
                    
                    # 解析时间戳
                    timestamp = self.parse_timestamp(row['时间'])
                    
                    # 构建数据记录
                    data_record = {
                        'timestamp': timestamp,
                        'device_name': device_type,
                        'device_mac': mac_address,
                        'accel_x': float(row['加速度X(g)']),
                        'accel_y': float(row['加速度Y(g)']),
                        'accel_z': float(row['加速度Z(g)']),
                        'gyro_x': float(row['角速度X(°/s)']),
                        'gyro_y': float(row['角速度Y(°/s)']),
                        'gyro_z': float(row['角速度Z(°/s)']),
                        'angle_x': float(row['角度X(°)']),
                        'angle_y': float(row['角度Y(°)']),
                        'angle_z': float(row['角度Z(°)']),
                        'mag_x': float(row['磁场X(uT)']),
                        'mag_y': float(row['磁场Y(uT)']),
                        'mag_z': float(row['磁场Z(uT)']),
                        'quaternion_0': float(row['四元数0()']),
                        'quaternion_1': float(row['四元数1()']),
                        'quaternion_2': float(row['四元数2()']),
                        'quaternion_3': float(row['四元数3()']),
                        'temperature': float(row['温度(°C)']),
                        'firmware_version': str(row['版本号()']),
                        'battery_level': int(row['电量(%)'])
                    }
                    data_list.append(data_record)
                except Exception as e:
                    print(f"解析数据行失败: {e}, 行数据: {row}")
                    continue
            
            print(f"成功解析 {len(data_list)} 条传感器数据")
            return data_list
            
        except Exception as e:
            print(f"解析传感器数据文件失败: {e}")
            return []
    
    async def query_sensor_data(
        self,
        device_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        查询传感器数据
        
        Args:
            device_name: 设备名称过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回记录数限制
            
        Returns:
            List[Dict]: 查询结果
        """
        where_conditions = []
        params = {}
        
        if device_name:
            where_conditions.append("device_name = %(device_name)s")
            params['device_name'] = device_name
        
        if start_time:
            where_conditions.append("timestamp >= %(start_time)s")
            params['start_time'] = start_time
        
        if end_time:
            where_conditions.append("timestamp <= %(end_time)s")
            params['end_time'] = end_time
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        query_sql = f"""
        SELECT 
            id, timestamp, device_name, device_mac,
            accel_x, accel_y, accel_z,
            gyro_x, gyro_y, gyro_z,
            angle_x, angle_y, angle_z,
            mag_x, mag_y, mag_z,
            quaternion_0, quaternion_1, quaternion_2, quaternion_3,
            temperature, firmware_version, battery_level,
            created_at
        FROM theta_ai.sensor_data
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT %(limit)s
        """
        
        params['limit'] = limit
        
        try:
            result = await self.db_manager.execute_query(
                query=query_sql,
                params=params,
                db_config=self.db_config
            )
            return result
        except Exception as e:
            print(f"查询传感器数据失败: {e}")
            return []
    
    async def get_device_statistics(self) -> List[Dict[str, Any]]:
        """
        获取设备统计信息
        
        Returns:
            List[Dict]: 设备统计信息
        """
        stats_sql = """
        SELECT 
            device_name,
            device_mac,
            COUNT(*) as record_count,
            MIN(timestamp) as first_record,
            MAX(timestamp) as last_record,
            AVG(temperature) as avg_temperature,
            AVG(battery_level) as avg_battery_level
        FROM theta_ai.sensor_data
        GROUP BY device_name, device_mac
        ORDER BY record_count DESC
        """
        
        try:
            result = await self.db_manager.execute_query(
                query=stats_sql,
                db_config=self.db_config
            )
            return result
        except Exception as e:
            print(f"获取设备统计信息失败: {e}")
            return []


async def import_sensor_data_from_file(file_path: str, db_config=None):
    """
    从文件导入传感器数据的便捷函数
    
    Args:
        file_path: 数据文件路径
        db_config: 数据库配置
    """
    manager = SensorDataManager(db_config)
    
    # 创建表
    await manager.create_sensor_data_table()
    
    # 解析数据
    data_list = manager.parse_sensor_data_from_text(file_path)
    
    if data_list:
        # 批量插入数据
        success = await manager.insert_sensor_data_batch(data_list)
        if success:
            print(f"成功导入 {len(data_list)} 条传感器数据")
        else:
            print("数据导入失败")
    else:
        print("没有可导入的数据")


if __name__ == "__main__":
    # 示例用法
    async def main():
        # 导入数据文件
        await import_sensor_data_from_file("/Users/admin/code/feetfit/data/20250605181211_181636.txt")
        
        # 查询示例
        manager = SensorDataManager()
        
        # 获取设备统计
        stats = await manager.get_device_statistics()
        print("设备统计信息:")
        for stat in stats:
            print(f"设备: {stat['device_name']}, 记录数: {stat['record_count']}")
        
        # 查询特定设备数据
        data = await manager.query_sensor_data(device_name="WTSDCL", limit=10)
        print(f"查询到 {len(data)} 条数据")
    
    asyncio.run(main())

