#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足底压力可视化后端API服务器
使用FastAPI框架，提供传感器数据接口
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import asyncpg
from typing import List, Dict, Optional, Any
import os
import sys
from datetime import datetime
import json

# 获取后端目录路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(backend_dir)
project_name = "pressure-viz-web"
log_dir = os.path.join(project_dir, "logs")

# 添加父目录到路径以导入utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from utils.utils_db import execute_query_sync, DB_CONFIG
    from utils.logger import startup_logger
    
    # 初始化日志系统
    startup_logger(True, False, project_dir, project_name, project_name, log_dir)
    
except ImportError:
    print("警告: 无法导入utils_db或logger，使用备用配置")
    # Docker环境下的数据库配置
    DB_CONFIG = {
        "pg_host": os.getenv("DB_HOST", "db"),
        "pg_port": int(os.getenv("DB_PORT", 5432)),
        "pg_user": os.getenv("DB_USER", "holistic_user"), 
        "pg_password": os.getenv("DB_PASSWORD", "holistic_password"),
        "pg_dbname": os.getenv("DB_NAME", "holistic_db"),
        "encryption_key": os.getenv("PG_ENCRYPTION_KEY", "61df425f-2e57-4798-96be-bb2ac3cebba4")
    }

# 创建FastAPI应用
app = FastAPI(
    title="足底压力可视化API",
    description="提供传感器数据和可视化接口",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3060", "http://127.0.0.1:3060"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 传感器布局定义（基于layout.m）
SENSOR_LAYOUTS = {
    "left": [
        [13, 25, 37, 49, 61, 73, 85, 97],
        [2, 14, 26, 38, 50, 62, 74, 86, 98],
        [3, 15, 27, 39, 51, 63, 75, 87, 99],
        [4, 16, 28, 40, 52, 64, 76, 88, 100],
        [5, 17, 29, 41, 53, 65, 77, 89],
        [6, 18, 30, 42, 54, 66, 78],
        [7, 19, 31, 43, 55, 67],
        [8, 20, 32, 44, 56, 68],
        [9, 21, 33, 45, 57, 69],
        [10, 22, 34, 46, 58, 70],
        [11, 23, 35, 47, 59, 71],
        [12, 24, 36, 48, 60, 72]
    ],
    "right": [
        [1, 13, 25, 37, 49, 61, 73, 85],
        [2, 14, 26, 38, 50, 62, 74, 86, 98],
        [3, 15, 27, 39, 51, 63, 75, 87, 99],
        [4, 16, 28, 40, 52, 64, 76, 88, 100],
        [17, 29, 41, 53, 65, 77, 89, 101],
        [30, 42, 54, 66, 78, 90, 102],
        [43, 55, 67, 79, 91, 103],
        [44, 56, 68, 80, 92, 104],
        [45, 57, 69, 81, 93, 105],
        [46, 58, 70, 82, 94, 106],
        [47, 59, 71, 83, 95, 107],
        [48, 60, 72, 84, 96, 108]
    ]
}

# 数据库连接池
db_pool = None

async def init_db():
    """初始化数据库连接池"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            host=DB_CONFIG["pg_host"],
            port=DB_CONFIG["pg_port"],
            user=DB_CONFIG["pg_user"],
            password=DB_CONFIG["pg_password"],
            database=DB_CONFIG["pg_dbname"],
            min_size=1,
            max_size=10
        )
        print("数据库连接池初始化成功")
    except Exception as e:
        print(f"数据库连接失败: {e}")
        db_pool = None

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    if db_pool:
        await db_pool.close()

# API路由

@app.get("/")
async def root():
    """根路径"""
    return {"message": "足底压力可视化API服务器", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return {"status": "healthy", "database": "connected", "timestamp": datetime.now().isoformat()}
        else:
            return {"status": "degraded", "database": "disconnected", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}

@app.get("/api/sensor-layout")
async def get_sensor_layout():
    """获取传感器布局"""
    return SENSOR_LAYOUTS

@app.get("/api/data-options")
async def get_data_options():
    """获取可用的数据组合"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="数据库连接不可用")
    
    try:
        async with db_pool.acquire() as conn:
            query = """
            SELECT DISTINCT subject, activity, trial_number, COUNT(*) as data_count
            FROM sensor_data 
            WHERE sensor_type = 'SOLESENSE'
            GROUP BY subject, activity, trial_number
            ORDER BY subject, activity, trial_number
            """
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询数据选项失败: {str(e)}")

@app.get("/api/pressure-data")
async def get_pressure_data(
    subject: str = Query("h", description="受试者"),
    activity: str = Query("walk", description="活动类型"),
    trial: int = Query(1, description="试次"),
    limit: int = Query(50, description="数据限制")
):
    """获取压力数据"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="数据库连接不可用")
    
    try:
        async with db_pool.acquire() as conn:
            # 构建数据点字段列表
            data_point_fields = ", ".join([f"data_point_{i}" for i in range(1, 109)])
            
            query = f"""
            SELECT 
                timestamp,
                device_name,
                {data_point_fields}
            FROM sensor_data 
            WHERE sensor_type = 'SOLESENSE' 
            AND subject = $1
            AND activity = $2
            AND trial_number = $3
            ORDER BY timestamp 
            LIMIT $4
            """
            
            rows = await conn.fetch(query, subject, activity, trial, limit)
            
            # 转换数据格式
            processed_data = []
            for row in rows:
                pressure_data = {}
                for i in range(1, 109):
                    value = row[f"data_point_{i}"]
                    pressure_data[i] = float(value) if value is not None else 0.0
                
                processed_data.append({
                    "timestamp": row["timestamp"].isoformat(),
                    "device": row["device_name"],
                    "pressureData": pressure_data
                })
            
            return processed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取压力数据失败: {str(e)}")

@app.get("/api/pressure-stream")
async def get_pressure_stream(
    subject: str = Query("h", description="受试者"),
    activity: str = Query("walk", description="活动类型"),
    trial: int = Query(1, description="试次"),
    start_index: int = Query(0, description="起始索引"),
    count: int = Query(10, description="数据数量")
):
    """获取实时压力数据流（用于动画）"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="数据库连接不可用")
    
    try:
        async with db_pool.acquire() as conn:
            data_point_fields = ", ".join([f"data_point_{i}" for i in range(1, 109)])
            
            query = f"""
            SELECT 
                timestamp,
                device_name,
                {data_point_fields}
            FROM sensor_data 
            WHERE sensor_type = 'SOLESENSE' 
            AND subject = $1
            AND activity = $2
            AND trial_number = $3
            ORDER BY timestamp 
            OFFSET $4 LIMIT $5
            """
            
            rows = await conn.fetch(query, subject, activity, trial, start_index, count)
            
            # 按时间戳分组左右脚数据
            time_groups = {}
            for row in rows:
                timestamp = row["timestamp"].isoformat()
                if timestamp not in time_groups:
                    time_groups[timestamp] = {}
                
                pressure_data = {}
                for i in range(1, 109):
                    value = row[f"data_point_{i}"]
                    pressure_data[i] = float(value) if value is not None else 0.0
                
                time_groups[timestamp][row["device_name"]] = pressure_data
            
            # 转换为数组格式
            stream_data = []
            for timestamp, devices in time_groups.items():
                stream_data.append({
                    "timestamp": timestamp,
                    "left": devices.get("solesenseL", {}),
                    "right": devices.get("solesenseR", {})
                })
            
            return stream_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取压力流数据失败: {str(e)}")

@app.get("/api/pressure-stats")
async def get_pressure_stats(
    subject: Optional[str] = Query(None, description="受试者"),
    activity: Optional[str] = Query(None, description="活动类型"),
    trial: Optional[int] = Query(None, description="试次")
):
    """获取压力统计信息"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="数据库连接不可用")
    
    try:
        async with db_pool.acquire() as conn:
            where_conditions = ["sensor_type = 'SOLESENSE'"]
            params = []
            
            if subject:
                params.append(subject)
                where_conditions.append(f"subject = ${len(params)}")
            if activity:
                params.append(activity)
                where_conditions.append(f"activity = ${len(params)}")
            if trial:
                params.append(trial)
                where_conditions.append(f"trial_number = ${len(params)}")
            
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
            SELECT 
                subject,
                activity,
                device_name,
                AVG(data_point_1 + data_point_50 + data_point_108) as avg_pressure,
                MAX(data_point_50) as max_pressure,
                COUNT(*) as sample_count
            FROM sensor_data 
            WHERE {where_clause}
            GROUP BY subject, activity, device_name
            ORDER BY subject, activity, device_name
            """
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取压力统计失败: {str(e)}")

@app.get("/api/pressure-heatmap/{subject}/{activity}/{trial}")
async def get_pressure_heatmap(
    subject: str,
    activity: str,
    trial: int,
    frame_index: int = Query(0, description="帧索引")
):
    """获取特定帧的压力热力图数据"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="数据库连接不可用")
    
    try:
        async with db_pool.acquire() as conn:
            data_point_fields = ", ".join([f"data_point_{i}" for i in range(1, 109)])
            
            query = f"""
            SELECT 
                timestamp,
                device_name,
                {data_point_fields}
            FROM sensor_data 
            WHERE sensor_type = 'SOLESENSE' 
            AND subject = $1
            AND activity = $2
            AND trial_number = $3
            ORDER BY timestamp 
            OFFSET $4 LIMIT 1
            """
            
            rows = await conn.fetch(query, subject, activity, trial, frame_index)
            
            if not rows:
                raise HTTPException(status_code=404, detail="未找到数据")
            
            # 处理左右脚数据
            heatmap_data = {"left": {}, "right": {}, "timestamp": None}
            
            for row in rows:
                if not heatmap_data["timestamp"]:
                    heatmap_data["timestamp"] = row["timestamp"].isoformat()
                
                pressure_data = {}
                for i in range(1, 109):
                    value = row[f"data_point_{i}"]
                    pressure_data[i] = float(value) if value is not None else 0.0
                
                if row["device_name"] == "solesenseL":
                    heatmap_data["left"] = pressure_data
                elif row["device_name"] == "solesenseR":
                    heatmap_data["right"] = pressure_data
            
            return heatmap_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热力图数据失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3080)
