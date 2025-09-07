#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FeetFit 主应用入口
跑步步态分析系统的FastAPI应用
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
import os

# 导入自定义模块
from running_gait_analyzer import RunningGaitAnalyzer

# 创建FastAPI应用
app = FastAPI(
    title="FeetFit - 跑步步态分析系统",
    description="基于传感器数据的智能跑步步态分析平台",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
analyzer = None

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    global analyzer
    analyzer = RunningGaitAnalyzer()
    print("🚀 FeetFit 跑步步态分析系统启动成功!")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    print("👋 FeetFit 系统正在关闭...")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用 FeetFit 跑步步态分析系统",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "FeetFit Gait Analysis"
    }

@app.get("/api/data/stats")
async def get_data_stats():
    """获取数据统计信息"""
    try:
        global analyzer
        if not analyzer:
            analyzer = RunningGaitAnalyzer()
        
        # 加载数据
        data = analyzer.load_data_from_db()
        
        if data.empty:
            return {"message": "暂无数据", "stats": {}}
        
        # 统计信息
        stats = {
            "total_records": len(data),
            "devices": data['device_mac'].nunique(),
            "device_list": data['device_mac'].unique().tolist(),
            "time_range": {
                "start": data['timestamp'].min().isoformat(),
                "end": data['timestamp'].max().isoformat(),
                "duration_seconds": (data['timestamp'].max() - data['timestamp'].min()).total_seconds()
            },
            "device_stats": []
        }
        
        # 按设备统计
        for device_mac in data['device_mac'].unique():
            device_data = data[data['device_mac'] == device_mac]
            device_stat = {
                "device_mac": device_mac,
                "device_name": device_data['device_name'].iloc[0],
                "record_count": len(device_data),
                "avg_temperature": float(device_data['temperature'].mean()),
                "avg_battery": float(device_data['battery_level'].mean()),
                "firmware_version": device_data['firmware_version'].iloc[0]
            }
            stats["device_stats"].append(device_stat)
        
        return {"success": True, "stats": stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据统计失败: {str(e)}")

@app.post("/api/analysis/gait")
async def analyze_gait(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """执行步态分析"""
    try:
        global analyzer
        if not analyzer:
            analyzer = RunningGaitAnalyzer()
        
        # 加载数据
        data = analyzer.load_data_from_db(start_time, end_time)
        
        if data.empty:
            raise HTTPException(status_code=404, detail="指定时间范围内没有数据")
        
        # 分离左右脚数据
        analyzer.separate_foot_data()
        
        # 执行步态分析
        metrics = analyzer.calculate_gait_metrics()
        
        if not metrics:
            raise HTTPException(status_code=400, detail="步态分析失败，数据不足")
        
        # 生成报告
        report = analyzer.generate_report()
        
        return {
            "success": True,
            "analysis_time": datetime.now().isoformat(),
            "data_range": {
                "start": start_time,
                "end": end_time,
                "records_analyzed": len(data)
            },
            "metrics": metrics,
            "report": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"步态分析失败: {str(e)}")

@app.get("/api/analysis/history")
async def get_analysis_history(limit: int = 10):
    """获取历史分析记录"""
    try:
        # 这里应该从数据库查询历史记录
        # 暂时返回模拟数据
        history = [
            {
                "id": 1,
                "analysis_time": "2025-09-07T09:49:08",
                "data_records": 7892,
                "cadence": 15.2,
                "contact_flight_ratio": 0.67,
                "dominant_strike_pattern": "heel"
            }
        ]
        
        return {
            "success": True,
            "history": history[:limit]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")

@app.get("/api/devices")
async def get_devices():
    """获取设备列表"""
    try:
        global analyzer
        if not analyzer:
            analyzer = RunningGaitAnalyzer()
        
        data = analyzer.load_data_from_db()
        
        if data.empty:
            return {"success": True, "devices": []}
        
        devices = []
        for device_mac in data['device_mac'].unique():
            device_data = data[data['device_mac'] == device_mac]
            device_info = {
                "device_mac": device_mac,
                "device_name": device_data['device_name'].iloc[0],
                "firmware_version": device_data['firmware_version'].iloc[0],
                "last_seen": device_data['timestamp'].max().isoformat(),
                "total_records": len(device_data),
                "status": "active" if (datetime.now() - device_data['timestamp'].max()).total_seconds() < 3600 else "inactive"
            }
            devices.append(device_info)
        
        return {"success": True, "devices": devices}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")

@app.get("/api/metrics/realtime")
async def get_realtime_metrics():
    """获取实时指标（最近的数据）"""
    try:
        global analyzer
        if not analyzer:
            analyzer = RunningGaitAnalyzer()
        
        # 获取最近5分钟的数据
        from datetime import timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        
        data = analyzer.load_data_from_db(
            start_time.isoformat(),
            end_time.isoformat()
        )
        
        if data.empty:
            return {"success": True, "metrics": {}, "message": "最近5分钟无数据"}
        
        # 计算实时指标
        metrics = {
            "current_time": datetime.now().isoformat(),
            "data_points": len(data),
            "devices_active": data['device_mac'].nunique(),
            "avg_accel_magnitude": float(data['accel_magnitude'].mean()),
            "avg_gyro_magnitude": float(data['gyro_magnitude'].mean()),
            "temperature_range": {
                "min": float(data['temperature'].min()),
                "max": float(data['temperature'].max()),
                "avg": float(data['temperature'].mean())
            },
            "battery_levels": {
                device_mac: float(device_data['battery_level'].mean())
                for device_mac, device_data in data.groupby('device_mac')
            }
        }
        
        return {"success": True, "metrics": metrics}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时指标失败: {str(e)}")

if __name__ == "__main__":
    # 开发环境运行
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
