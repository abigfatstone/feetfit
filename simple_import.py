#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的传感器数据导入脚本
直接使用明文密码连接数据库
"""

import asyncio
import pandas as pd
import psycopg2
from datetime import datetime
from typing import List, Dict, Any

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "holistic_user", 
    "password": "holistic_password",
    "database": "holistic_db"
}

def parse_device_info(device_name: str) -> tuple:
    """解析设备名称，提取设备类型和MAC地址"""
    if '(' in device_name and ')' in device_name:
        device_type = device_name.split('(')[0]
        mac_address = device_name.split('(')[1].replace(')', '')
        return device_type, mac_address
    return device_name, None

def parse_timestamp(timestamp_str: str) -> datetime:
    """解析时间戳字符串"""
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

def create_sensor_table():
    """创建传感器数据表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS theta_ai.sensor_data (
        id BIGSERIAL PRIMARY KEY,
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
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- 创建索引
    CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON theta_ai.sensor_data (timestamp);
    CREATE INDEX IF NOT EXISTS idx_sensor_data_device_name ON theta_ai.sensor_data (device_name);
    CREATE INDEX IF NOT EXISTS idx_sensor_data_device_timestamp ON theta_ai.sensor_data (device_name, timestamp);
    """
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ 传感器数据表创建成功")
        return True
    except Exception as e:
        print(f"❌ 创建传感器数据表失败: {e}")
        return False

def parse_sensor_data_from_file(file_path: str) -> List[Dict[str, Any]]:
    """从文本文件解析传感器数据"""
    try:
        # 读取文件
        df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
        
        data_list = []
        for _, row in df.iterrows():
            try:
                # 解析设备信息
                device_type, mac_address = parse_device_info(row['设备名称'])
                
                # 解析时间戳
                timestamp = parse_timestamp(row['时间'])
                
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
                print(f"解析数据行失败: {e}")
                continue
        
        print(f"✅ 成功解析 {len(data_list)} 条传感器数据")
        return data_list
        
    except Exception as e:
        print(f"❌ 解析传感器数据文件失败: {e}")
        return []

def insert_sensor_data_batch(data_list: List[Dict[str, Any]]) -> bool:
    """批量插入传感器数据"""
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
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 批量插入
        cursor.executemany(insert_sql, data_list)
        conn.commit()
        
        cursor.close()
        conn.close()
        print(f"✅ 成功插入 {len(data_list)} 条传感器数据")
        return True
    except Exception as e:
        print(f"❌ 批量插入传感器数据失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始导入传感器数据")
    
    # 1. 创建表
    if not create_sensor_table():
        return
    
    # 2. 解析数据
    data_file = "data/20250605181211_181636.txt"
    data_list = parse_sensor_data_from_file(data_file)
    
    if not data_list:
        print("❌ 没有可导入的数据")
        return
    
    # 3. 批量插入数据
    if insert_sensor_data_batch(data_list):
        print(f"🎉 成功导入 {len(data_list)} 条传感器数据到数据库！")
    else:
        print("❌ 数据导入失败")

if __name__ == "__main__":
    main()
