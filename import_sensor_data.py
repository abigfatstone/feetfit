#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器数据批量导入脚本
从testData文件夹中导入所有CSV文件到数据库
"""

import os
import re
import csv
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.utils_db import execute_query_sync, DB_CONFIG


def extract_metadata_from_filename(filename: str) -> Dict[str, Optional[str]]:
    """
    从文件名中提取元数据
    
    文件名格式: mixed_sensor_data_2025-09-05 [人员] [动作] [试次].csv
    例如: mixed_sensor_data_2025-09-05 h jump 2.csv
    
    Args:
        filename: CSV文件名
        
    Returns:
        包含元数据的字典
    """
    # 移除文件扩展名
    base_name = filename.replace('.csv', '')
    
    # 正则表达式匹配文件名模式
    pattern = r'mixed_sensor_data_(\d{4}-\d{2}-\d{2})\s+(.+)'
    match = re.match(pattern, base_name)
    
    if not match:
        return {
            'date_recorded': None,
            'subject': None,
            'activity': None,
            'trial_number': 1
        }
    
    date_str = match.group(1)
    remaining = match.group(2).strip()
    
    # 解析日期
    try:
        date_recorded = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        date_recorded = None
    
    # 分割剩余部分
    parts = remaining.split()
    
    if len(parts) == 0:
        return {
            'date_recorded': date_recorded,
            'subject': None,
            'activity': None,
            'trial_number': 1
        }
    
    # 确定试次编号（最后一个部分如果是数字）
    trial_number = 1
    if len(parts) > 1 and parts[-1].isdigit():
        trial_number = int(parts[-1])
        parts = parts[:-1]  # 移除试次编号
    
    # 剩余部分分为人员和动作
    if len(parts) >= 2:
        subject = parts[0]
        activity = ' '.join(parts[1:])
    elif len(parts) == 1:
        # 如果只有一个部分，需要判断是人员还是动作
        part = parts[0]
        if part in ['h', 'l', 'wanley', 'marvel']:
            subject = part
            activity = None
        else:
            subject = None
            activity = part
    else:
        subject = None
        activity = None
    
    return {
        'date_recorded': date_recorded,
        'subject': subject,
        'activity': activity,
        'trial_number': trial_number
    }


def process_csv_file(file_path: str) -> List[Dict]:
    """
    处理单个CSV文件，返回数据行列表
    
    Args:
        file_path: CSV文件路径
        
    Returns:
        数据行列表
    """
    filename = os.path.basename(file_path)
    metadata = extract_metadata_from_filename(filename)
    
    data_rows = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 跳过标题行
            
            for row in reader:
                if len(row) < 3:  # 至少需要时间戳、设备名称、传感器类型
                    continue
                
                # 解析基本字段
                timestamp_str = row[0]
                device_name = row[1]
                sensor_type = row[2]
                
                # 解析时间戳
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('T', ' ').replace('Z', ''))
                except ValueError:
                    print(f"警告: 无法解析时间戳 {timestamp_str} 在文件 {filename}")
                    continue
                
                # 准备数据点（最多108个）
                data_points = {}
                for i in range(1, 109):  # data_point_1 到 data_point_108
                    col_index = i + 2  # 前3列是时间戳、设备名称、传感器类型
                    if col_index < len(row) and row[col_index].strip():
                        try:
                            data_points[f'data_point_{i}'] = float(row[col_index])
                        except (ValueError, TypeError):
                            data_points[f'data_point_{i}'] = None
                    else:
                        data_points[f'data_point_{i}'] = None
                
                # 构建数据行
                data_row = {
                    'filename': filename,
                    'timestamp': timestamp,
                    'device_name': device_name,
                    'sensor_type': sensor_type,
                    'date_recorded': metadata['date_recorded'],
                    'subject': metadata['subject'],
                    'activity': metadata['activity'],
                    'trial_number': metadata['trial_number'],
                    **data_points
                }
                
                data_rows.append(data_row)
                
    except Exception as e:
        print(f"处理文件 {filename} 时出错: {str(e)}")
        return []
    
    return data_rows


def insert_data_batch(data_rows: List[Dict]) -> bool:
    """
    批量插入数据到数据库
    
    Args:
        data_rows: 数据行列表
        
    Returns:
        是否成功
    """
    if not data_rows:
        return True
    
    # 构建插入SQL
    columns = list(data_rows[0].keys())
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    
    insert_sql = f"""
    INSERT INTO sensor_data ({columns_str})
    VALUES ({placeholders})
    """
    
    # 准备数据
    values_list = []
    for row in data_rows:
        values = [row[col] for col in columns]
        values_list.append(values)
    
    try:
        result = execute_query_sync(
            insert_sql, 
            query_type='insert_many',
            db_config=DB_CONFIG,
            fieldList=values_list
        )
        return True
    except Exception as e:
        print(f"批量插入数据失败: {str(e)}")
        return False


def main():
    """主函数"""
    # 数据文件夹路径
    data_dir = Path(__file__).parent / 'data' / 'testData'
    
    if not data_dir.exists():
        print(f"数据文件夹不存在: {data_dir}")
        return
    
    # 获取所有CSV文件
    csv_files = list(data_dir.glob('*.csv'))
    
    if not csv_files:
        print(f"在 {data_dir} 中没有找到CSV文件")
        return
    
    print(f"找到 {len(csv_files)} 个CSV文件")
    
    # 处理每个文件
    total_rows = 0
    successful_files = 0
    
    for csv_file in csv_files:
        print(f"\n处理文件: {csv_file.name}")
        
        # 处理CSV文件
        data_rows = process_csv_file(str(csv_file))
        
        if not data_rows:
            print(f"文件 {csv_file.name} 没有有效数据")
            continue
        
        print(f"从文件 {csv_file.name} 中读取了 {len(data_rows)} 行数据")
        
        # 批量插入数据
        if insert_data_batch(data_rows):
            print(f"成功导入 {len(data_rows)} 行数据")
            total_rows += len(data_rows)
            successful_files += 1
        else:
            print(f"导入文件 {csv_file.name} 失败")
    
    print(f"\n导入完成!")
    print(f"成功处理文件: {successful_files}/{len(csv_files)}")
    print(f"总共导入数据行: {total_rows}")


if __name__ == '__main__':
    main()
