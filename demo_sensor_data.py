#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器数据管理演示脚本
展示如何使用 SensorDataManager 来处理传感器数据
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.sensor_data_manager import SensorDataManager, import_sensor_data_from_file
from config.config import cfg


async def demo_create_table():
    """演示创建传感器数据表"""
    print("=== 创建传感器数据表 ===")
    manager = SensorDataManager()
    success = await manager.create_sensor_data_table()
    if success:
        print("✅ 传感器数据表创建成功")
    else:
        print("❌ 传感器数据表创建失败")
    print()


async def demo_import_data():
    """演示从文件导入传感器数据"""
    print("=== 导入传感器数据 ===")
    
    # 数据文件路径
    data_file = "/Users/admin/code/feetfit/data/20250605181211_181636.txt"
    
    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        return
    
    print(f"正在导入数据文件: {data_file}")
    await import_sensor_data_from_file(data_file)
    print()


async def demo_query_data():
    """演示查询传感器数据"""
    print("=== 查询传感器数据 ===")
    manager = SensorDataManager()
    
    # 1. 获取设备统计信息
    print("1. 设备统计信息:")
    stats = await manager.get_device_statistics()
    if stats:
        for stat in stats:
            print(f"   设备: {stat['device_name']} ({stat['device_mac']})")
            print(f"   记录数: {stat['record_count']}")
            print(f"   首次记录: {stat['first_record']}")
            print(f"   最后记录: {stat['last_record']}")
            print(f"   平均温度: {stat['avg_temperature']:.2f}°C")
            print(f"   平均电量: {stat['avg_battery_level']:.1f}%")
            print()
    else:
        print("   没有找到设备数据")
    
    # 2. 查询最近的数据
    print("2. 最近10条数据:")
    recent_data = await manager.query_sensor_data(limit=10)
    if recent_data:
        for i, record in enumerate(recent_data[:5], 1):  # 只显示前5条
            print(f"   记录 {i}:")
            print(f"     时间: {record['timestamp']}")
            print(f"     设备: {record['device_name']}")
            print(f"     加速度: X={record['accel_x']}, Y={record['accel_y']}, Z={record['accel_z']}")
            print(f"     温度: {record['temperature']}°C, 电量: {record['battery_level']}%")
            print()
    else:
        print("   没有找到数据")
    
    # 3. 查询特定设备数据
    print("3. 查询特定设备数据 (WTSDCL):")
    device_data = await manager.query_sensor_data(device_name="WTSDCL", limit=5)
    if device_data:
        print(f"   找到 {len(device_data)} 条 WTSDCL 设备数据")
        for i, record in enumerate(device_data, 1):
            print(f"   记录 {i}: {record['timestamp']} - 温度: {record['temperature']}°C")
    else:
        print("   没有找到 WTSDCL 设备数据")
    print()


async def demo_time_range_query():
    """演示时间范围查询"""
    print("=== 时间范围查询 ===")
    manager = SensorDataManager()
    
    # 查询最近1小时的数据
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    print(f"查询时间范围: {start_time} 到 {end_time}")
    
    data = await manager.query_sensor_data(
        start_time=start_time,
        end_time=end_time,
        limit=100
    )
    
    if data:
        print(f"找到 {len(data)} 条数据")
        
        # 按设备分组统计
        device_counts = {}
        for record in data:
            device = record['device_name']
            device_counts[device] = device_counts.get(device, 0) + 1
        
        print("按设备分组:")
        for device, count in device_counts.items():
            print(f"   {device}: {count} 条记录")
    else:
        print("在指定时间范围内没有找到数据")
    print()


async def demo_data_analysis():
    """演示数据分析功能"""
    print("=== 数据分析 ===")
    manager = SensorDataManager()
    
    # 获取最近的数据进行分析
    data = await manager.query_sensor_data(limit=100)
    
    if not data:
        print("没有数据可供分析")
        return
    
    print(f"分析 {len(data)} 条数据:")
    
    # 计算加速度统计
    accel_x_values = [float(record['accel_x']) for record in data if record['accel_x'] is not None]
    accel_y_values = [float(record['accel_y']) for record in data if record['accel_y'] is not None]
    accel_z_values = [float(record['accel_z']) for record in data if record['accel_z'] is not None]
    
    if accel_x_values:
        print("加速度统计 (g):")
        print(f"   X轴: 最小={min(accel_x_values):.3f}, 最大={max(accel_x_values):.3f}, 平均={sum(accel_x_values)/len(accel_x_values):.3f}")
        print(f"   Y轴: 最小={min(accel_y_values):.3f}, 最大={max(accel_y_values):.3f}, 平均={sum(accel_y_values)/len(accel_y_values):.3f}")
        print(f"   Z轴: 最小={min(accel_z_values):.3f}, 最大={max(accel_z_values):.3f}, 平均={sum(accel_z_values)/len(accel_z_values):.3f}")
    
    # 温度统计
    temp_values = [float(record['temperature']) for record in data if record['temperature'] is not None]
    if temp_values:
        print(f"温度统计: 最小={min(temp_values):.1f}°C, 最大={max(temp_values):.1f}°C, 平均={sum(temp_values)/len(temp_values):.1f}°C")
    
    # 电量统计
    battery_values = [int(record['battery_level']) for record in data if record['battery_level'] is not None]
    if battery_values:
        print(f"电量统计: 最小={min(battery_values)}%, 最大={max(battery_values)}%, 平均={sum(battery_values)/len(battery_values):.1f}%")
    
    print()


async def main():
    """主演示函数"""
    print("🚀 传感器数据管理系统演示")
    print("=" * 50)
    
    try:
        # 1. 创建表
        await demo_create_table()
        
        # 2. 导入数据
        await demo_import_data()
        
        # 3. 查询数据
        await demo_query_data()
        
        # 4. 时间范围查询
        await demo_time_range_query()
        
        # 5. 数据分析
        await demo_data_analysis()
        
        print("✅ 演示完成!")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


def show_usage():
    """显示使用说明"""
    print("""
传感器数据管理系统使用说明:

1. 创建表:
   python demo_sensor_data.py create_table

2. 导入数据:
   python demo_sensor_data.py import_data <文件路径>

3. 查询数据:
   python demo_sensor_data.py query_data

4. 运行完整演示:
   python demo_sensor_data.py

数据库配置:
   请确保 config/config.yaml 中的数据库配置正确
   """)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create_table":
            asyncio.run(demo_create_table())
        elif command == "import_data":
            if len(sys.argv) > 2:
                file_path = sys.argv[2]
                asyncio.run(import_sensor_data_from_file(file_path))
            else:
                print("请提供数据文件路径")
        elif command == "query_data":
            asyncio.run(demo_query_data())
        elif command == "help":
            show_usage()
        else:
            print(f"未知命令: {command}")
            show_usage()
    else:
        # 运行完整演示
        asyncio.run(main())

