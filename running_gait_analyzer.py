#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跑步步态分析系统
基于传感器数据分析跑步姿态、触地时间、腾空时间等关键指标
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import psycopg2
from scipy import signal
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "holistic_user", 
    "password": "holistic_password",
    "database": "holistic_db"
}

class RunningGaitAnalyzer:
    """跑步步态分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.data = None
        self.left_foot_data = None
        self.right_foot_data = None
        self.analysis_results = {}
        
        # 分析参数配置
        self.config = {
            # 触地检测阈值
            'ground_contact_threshold': {
                'accel_z_min': 0.5,  # Z轴加速度最小阈值（g）
                'accel_magnitude_min': 1.2,  # 加速度幅值最小阈值（g）
                'gyro_magnitude_max': 50.0,  # 角速度幅值最大阈值（°/s）
            },
            
            # 步态检测参数
            'gait_detection': {
                'min_contact_duration': 0.1,  # 最小触地时间（秒）
                'max_contact_duration': 0.5,  # 最大触地时间（秒）
                'min_flight_duration': 0.05,  # 最小腾空时间（秒）
                'max_flight_duration': 0.3,   # 最大腾空时间（秒）
            },
            
            # 压力区域阈值
            'pressure_zones': {
                'heel_angle_range': (-30, 10),      # 后跟角度范围
                'midfoot_angle_range': (-10, 30),   # 中足角度范围  
                'forefoot_angle_range': (20, 60),   # 前掌角度范围
            },
            
            # 采样频率
            'sampling_rate': 30,  # Hz
        }
    
    def load_data_from_db(self, start_time: Optional[str] = None, end_time: Optional[str] = None) -> pd.DataFrame:
        """从数据库加载传感器数据"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            
            # 构建查询条件
            where_clause = "1=1"
            if start_time:
                where_clause += f" AND timestamp >= '{start_time}'"
            if end_time:
                where_clause += f" AND timestamp <= '{end_time}'"
            
            query = f"""
            SELECT 
                timestamp, device_name, device_mac,
                accel_x, accel_y, accel_z,
                gyro_x, gyro_y, gyro_z,
                angle_x, angle_y, angle_z,
                mag_x, mag_y, mag_z,
                quaternion_0, quaternion_1, quaternion_2, quaternion_3,
                temperature, battery_level
            FROM theta_ai.sensor_data
            WHERE {where_clause}
            ORDER BY timestamp, device_mac
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # 数据预处理
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(['timestamp', 'device_mac'])
            
            # 计算加速度和角速度的幅值
            df['accel_magnitude'] = np.sqrt(df['accel_x']**2 + df['accel_y']**2 + df['accel_z']**2)
            df['gyro_magnitude'] = np.sqrt(df['gyro_x']**2 + df['gyro_y']**2 + df['gyro_z']**2)
            
            # 计算时间差（用于频率分析）
            df['time_diff'] = df.groupby('device_mac')['timestamp'].diff().dt.total_seconds()
            
            self.data = df
            print(f"✅ 成功加载 {len(df)} 条传感器数据")
            return df
            
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return pd.DataFrame()
    
    def separate_foot_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """分离左右脚数据（基于设备MAC地址）"""
        if self.data is None or self.data.empty:
            print("❌ 请先加载数据")
            return pd.DataFrame(), pd.DataFrame()
        
        # 获取所有设备MAC地址
        devices = self.data['device_mac'].unique()
        print(f"检测到设备: {devices}")
        
        if len(devices) >= 2:
            # 假设第一个设备是左脚，第二个设备是右脚
            left_foot_mac = devices[0]
            right_foot_mac = devices[1]
            
            self.left_foot_data = self.data[self.data['device_mac'] == left_foot_mac].copy()
            self.right_foot_data = self.data[self.data['device_mac'] == right_foot_mac].copy()
            
            print(f"左脚设备 ({left_foot_mac}): {len(self.left_foot_data)} 条数据")
            print(f"右脚设备 ({right_foot_mac}): {len(self.right_foot_data)} 条数据")
            
        else:
            print("⚠️ 设备数量不足，无法分离左右脚数据")
            self.left_foot_data = self.data.copy()
            self.right_foot_data = pd.DataFrame()
        
        return self.left_foot_data, self.right_foot_data
    
    def detect_ground_contact_events(self, foot_data: pd.DataFrame, foot_name: str) -> List[Dict]:
        """检测触地事件"""
        if foot_data.empty:
            return []
        
        events = []
        config = self.config['ground_contact_threshold']
        
        # 基于加速度Z轴和加速度幅值检测触地
        contact_mask = (
            (foot_data['accel_z'] > config['accel_z_min']) |
            (foot_data['accel_magnitude'] > config['accel_magnitude_min'])
        ) & (foot_data['gyro_magnitude'] < config['gyro_magnitude_max'])
        
        # 查找触地和离地的转换点
        contact_changes = contact_mask.astype(int).diff()
        contact_starts = foot_data[contact_changes == 1].index.tolist()
        contact_ends = foot_data[contact_changes == -1].index.tolist()
        
        # 确保开始和结束配对
        if len(contact_starts) > 0 and len(contact_ends) > 0:
            if contact_starts[0] > contact_ends[0]:
                contact_ends = contact_ends[1:]
            if len(contact_starts) > len(contact_ends):
                contact_starts = contact_starts[:-1]
        
        # 生成触地事件
        for start_idx, end_idx in zip(contact_starts, contact_ends):
            start_time = foot_data.loc[start_idx, 'timestamp']
            end_time = foot_data.loc[end_idx, 'timestamp']
            duration = (end_time - start_time).total_seconds()
            
            # 过滤掉过短或过长的触地事件
            min_duration = self.config['gait_detection']['min_contact_duration']
            max_duration = self.config['gait_detection']['max_contact_duration']
            
            if min_duration <= duration <= max_duration:
                # 分析触地区域
                contact_data = foot_data.loc[start_idx:end_idx]
                contact_zones = self.analyze_contact_zones(contact_data)
                
                events.append({
                    'foot': foot_name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'contact_zones': contact_zones,
                    'peak_accel': contact_data['accel_magnitude'].max(),
                    'avg_angle_x': contact_data['angle_x'].mean(),
                    'avg_angle_y': contact_data['angle_y'].mean(),
                })
        
        print(f"{foot_name}检测到 {len(events)} 个触地事件")
        return events
    
    def analyze_contact_zones(self, contact_data: pd.DataFrame) -> Dict[str, float]:
        """分析触地区域时间分布"""
        if contact_data.empty:
            return {'heel': 0, 'midfoot': 0, 'forefoot': 0}
        
        total_duration = len(contact_data) / self.config['sampling_rate']
        zones = self.config['pressure_zones']
        
        # 基于角度判断触地区域
        heel_mask = (
            (contact_data['angle_x'] >= zones['heel_angle_range'][0]) &
            (contact_data['angle_x'] <= zones['heel_angle_range'][1])
        )
        midfoot_mask = (
            (contact_data['angle_x'] >= zones['midfoot_angle_range'][0]) &
            (contact_data['angle_x'] <= zones['midfoot_angle_range'][1])
        )
        forefoot_mask = (
            (contact_data['angle_x'] >= zones['forefoot_angle_range'][0]) &
            (contact_data['angle_x'] <= zones['forefoot_angle_range'][1])
        )
        
        heel_time = heel_mask.sum() / self.config['sampling_rate']
        midfoot_time = midfoot_mask.sum() / self.config['sampling_rate']
        forefoot_time = forefoot_mask.sum() / self.config['sampling_rate']
        
        return {
            'heel': heel_time,
            'midfoot': midfoot_time,
            'forefoot': forefoot_time,
            'total': total_duration
        }
    
    def calculate_gait_metrics(self) -> Dict:
        """计算步态指标"""
        if self.left_foot_data is None or self.right_foot_data is None:
            self.separate_foot_data()
        
        # 检测左右脚触地事件
        left_events = self.detect_ground_contact_events(self.left_foot_data, '左脚')
        right_events = self.detect_ground_contact_events(self.right_foot_data, '右脚')
        
        # 合并所有事件并按时间排序
        all_events = left_events + right_events
        all_events.sort(key=lambda x: x['start_time'])
        
        if len(all_events) < 2:
            print("❌ 触地事件不足，无法计算步态指标")
            return {}
        
        # 计算腾空时间
        flight_times = []
        for i in range(len(all_events) - 1):
            current_end = all_events[i]['end_time']
            next_start = all_events[i + 1]['start_time']
            flight_time = (next_start - current_end).total_seconds()
            
            # 过滤合理的腾空时间
            min_flight = self.config['gait_detection']['min_flight_duration']
            max_flight = self.config['gait_detection']['max_flight_duration']
            
            if min_flight <= flight_time <= max_flight:
                flight_times.append(flight_time)
        
        # 计算步态指标
        contact_times = [event['duration'] for event in all_events]
        left_contact_times = [event['duration'] for event in left_events]
        right_contact_times = [event['duration'] for event in right_events]
        
        metrics = {
            # 基础时间指标
            'avg_contact_time': np.mean(contact_times) if contact_times else 0,
            'avg_flight_time': np.mean(flight_times) if flight_times else 0,
            'contact_time_std': np.std(contact_times) if contact_times else 0,
            'flight_time_std': np.std(flight_times) if flight_times else 0,
            
            # 左右脚对比
            'left_avg_contact_time': np.mean(left_contact_times) if left_contact_times else 0,
            'right_avg_contact_time': np.mean(right_contact_times) if right_contact_times else 0,
            'lr_contact_time_diff': abs(np.mean(left_contact_times) - np.mean(right_contact_times)) if left_contact_times and right_contact_times else 0,
            
            # 触地腾空比
            'contact_flight_ratio': np.mean(contact_times) / np.mean(flight_times) if contact_times and flight_times else 0,
            
            # 步频相关
            'step_count': len(all_events),
            'left_step_count': len(left_events),
            'right_step_count': len(right_events),
        }
        
        # 计算步频（每分钟步数）
        if len(all_events) >= 2:
            total_time = (all_events[-1]['end_time'] - all_events[0]['start_time']).total_seconds()
            metrics['cadence'] = (len(all_events) / total_time) * 60 if total_time > 0 else 0
        else:
            metrics['cadence'] = 0
        
        # 分析触地方式
        contact_patterns = self.analyze_contact_patterns(all_events)
        metrics.update(contact_patterns)
        
        # 分析压力中心
        cop_analysis = self.analyze_center_of_pressure(left_events, right_events)
        metrics.update(cop_analysis)
        
        self.analysis_results = metrics
        return metrics
    
    def analyze_contact_patterns(self, events: List[Dict]) -> Dict:
        """分析触地方式"""
        if not events:
            return {}
        
        heel_strikes = 0
        midfoot_strikes = 0
        forefoot_strikes = 0
        
        for event in events:
            zones = event['contact_zones']
            
            # 判断主要触地方式（基于最长时间的区域）
            max_zone = max(zones, key=lambda k: zones[k] if k != 'total' else 0)
            
            if max_zone == 'heel':
                heel_strikes += 1
            elif max_zone == 'midfoot':
                midfoot_strikes += 1
            elif max_zone == 'forefoot':
                forefoot_strikes += 1
        
        total_strikes = len(events)
        
        return {
            'heel_strike_ratio': heel_strikes / total_strikes if total_strikes > 0 else 0,
            'midfoot_strike_ratio': midfoot_strikes / total_strikes if total_strikes > 0 else 0,
            'forefoot_strike_ratio': forefoot_strikes / total_strikes if total_strikes > 0 else 0,
            'dominant_strike_pattern': max(['heel', 'midfoot', 'forefoot'], 
                                         key=lambda x: [heel_strikes, midfoot_strikes, forefoot_strikes][['heel', 'midfoot', 'forefoot'].index(x)])
        }
    
    def analyze_center_of_pressure(self, left_events: List[Dict], right_events: List[Dict]) -> Dict:
        """分析压力中心轨迹"""
        cop_metrics = {}
        
        # 分析左脚压力中心
        if left_events:
            left_cop = self.calculate_cop_trajectory(left_events, 'left')
            cop_metrics.update({f'left_{k}': v for k, v in left_cop.items()})
        
        # 分析右脚压力中心
        if right_events:
            right_cop = self.calculate_cop_trajectory(right_events, 'right')
            cop_metrics.update({f'right_{k}': v for k, v in right_cop.items()})
        
        # 计算双脚压力差异
        if left_events and right_events:
            left_peak_forces = [event['peak_accel'] for event in left_events]
            right_peak_forces = [event['peak_accel'] for event in right_events]
            
            cop_metrics.update({
                'force_asymmetry': abs(np.mean(left_peak_forces) - np.mean(right_peak_forces)),
                'left_avg_peak_force': np.mean(left_peak_forces),
                'right_avg_peak_force': np.mean(right_peak_forces),
            })
        
        return cop_metrics
    
    def calculate_cop_trajectory(self, events: List[Dict], foot_name: str) -> Dict:
        """计算单脚压力中心轨迹"""
        if not events:
            return {}
        
        # 分析角度变化模式
        angle_x_changes = []
        angle_y_changes = []
        
        for event in events:
            angle_x_changes.append(event['avg_angle_x'])
            angle_y_changes.append(event['avg_angle_y'])
        
        # 检测过度内旋（基于角度变化的标准差）
        angle_x_std = np.std(angle_x_changes) if angle_x_changes else 0
        angle_y_std = np.std(angle_y_changes) if angle_y_changes else 0
        
        # 判断内旋程度
        overpronation_risk = 'low'
        if angle_x_std > 15 or angle_y_std > 15:  # 阈值可调整
            overpronation_risk = 'high'
        elif angle_x_std > 10 or angle_y_std > 10:
            overpronation_risk = 'medium'
        
        return {
            'cop_angle_x_std': angle_x_std,
            'cop_angle_y_std': angle_y_std,
            'overpronation_risk': overpronation_risk,
            'avg_angle_x': np.mean(angle_x_changes) if angle_x_changes else 0,
            'avg_angle_y': np.mean(angle_y_changes) if angle_y_changes else 0,
        }
    
    def generate_report(self) -> str:
        """生成分析报告"""
        if not self.analysis_results:
            return "❌ 请先运行步态分析"
        
        metrics = self.analysis_results
        
        report = f"""
🏃‍♂️ 跑步步态分析报告
{'='*50}

📊 基础步态指标:
• 平均触地时间: {metrics.get('avg_contact_time', 0):.3f} 秒
• 平均腾空时间: {metrics.get('avg_flight_time', 0):.3f} 秒
• 触地腾空比: {metrics.get('contact_flight_ratio', 0):.2f}
• 步频: {metrics.get('cadence', 0):.1f} 步/分钟

👣 双脚对比分析:
• 左脚平均触地时间: {metrics.get('left_avg_contact_time', 0):.3f} 秒
• 右脚平均触地时间: {metrics.get('right_avg_contact_time', 0):.3f} 秒
• 左右脚时间差异: {metrics.get('lr_contact_time_diff', 0):.3f} 秒

🦶 触地方式分析:
• 后跟触地比例: {metrics.get('heel_strike_ratio', 0)*100:.1f}%
• 中足触地比例: {metrics.get('midfoot_strike_ratio', 0)*100:.1f}%
• 前掌触地比例: {metrics.get('forefoot_strike_ratio', 0)*100:.1f}%
• 主要触地方式: {metrics.get('dominant_strike_pattern', 'unknown')}

💪 压力分析:
• 左脚平均峰值力量: {metrics.get('left_avg_peak_force', 0):.2f} g
• 右脚平均峰值力量: {metrics.get('right_avg_peak_force', 0):.2f} g
• 力量不对称性: {metrics.get('force_asymmetry', 0):.2f} g

🎯 压力中心分析:
• 左脚内旋风险: {metrics.get('left_overpronation_risk', 'unknown')}
• 右脚内旋风险: {metrics.get('right_overpronation_risk', 'unknown')}

📈 跑姿评估:
"""
        
        # 添加跑姿建议
        report += self.generate_recommendations(metrics)
        
        return report
    
    def generate_recommendations(self, metrics: Dict) -> str:
        """生成跑姿建议"""
        recommendations = []
        
        # 触地腾空比建议
        ratio = metrics.get('contact_flight_ratio', 0)
        if ratio > 1.5:
            recommendations.append("• 触地腾空比较高，建议减少触地时间，提高跑步轻盈度")
        elif ratio < 0.8:
            recommendations.append("• 触地腾空比较低，跑姿较为轻盈，继续保持")
        
        # 左右脚平衡建议
        lr_diff = metrics.get('lr_contact_time_diff', 0)
        if lr_diff > 0.02:
            recommendations.append("• 左右脚触地时间差异较大，建议关注步态对称性")
        
        # 触地方式建议
        dominant_pattern = metrics.get('dominant_strike_pattern', '')
        if dominant_pattern == 'heel':
            recommendations.append("• 主要为后跟触地，建议尝试中足或前掌触地以减少冲击")
        elif dominant_pattern == 'forefoot':
            recommendations.append("• 主要为前掌触地，跑姿较为高效，注意小腿肌肉恢复")
        
        # 内旋风险建议
        left_risk = metrics.get('left_overpronation_risk', 'low')
        right_risk = metrics.get('right_overpronation_risk', 'low')
        if left_risk == 'high' or right_risk == 'high':
            recommendations.append("• 检测到较高内旋风险，建议选择支撑性跑鞋或考虑步态矫正")
        
        if not recommendations:
            recommendations.append("• 整体步态表现良好，继续保持当前跑姿")
        
        return '\n'.join(recommendations)
    
    def visualize_analysis(self, save_path: Optional[str] = None):
        """可视化分析结果"""
        if not self.analysis_results:
            print("❌ 请先运行步态分析")
            return
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('跑步步态分析可视化', fontsize=16, fontweight='bold')
        
        metrics = self.analysis_results
        
        # 1. 触地时间对比
        ax1 = axes[0, 0]
        contact_times = [
            metrics.get('left_avg_contact_time', 0),
            metrics.get('right_avg_contact_time', 0)
        ]
        bars1 = ax1.bar(['左脚', '右脚'], contact_times, color=['#FF6B6B', '#4ECDC4'])
        ax1.set_title('双脚触地时间对比')
        ax1.set_ylabel('时间 (秒)')
        for bar, value in zip(bars1, contact_times):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                    f'{value:.3f}s', ha='center', va='bottom')
        
        # 2. 触地方式分布
        ax2 = axes[0, 1]
        strike_patterns = [
            metrics.get('heel_strike_ratio', 0) * 100,
            metrics.get('midfoot_strike_ratio', 0) * 100,
            metrics.get('forefoot_strike_ratio', 0) * 100
        ]
        colors = ['#FFD93D', '#6BCF7F', '#4D96FF']
        wedges, texts, autotexts = ax2.pie(strike_patterns, labels=['后跟', '中足', '前掌'], 
                                          colors=colors, autopct='%1.1f%%', startangle=90)
        ax2.set_title('触地方式分布')
        
        # 3. 触地腾空比
        ax3 = axes[0, 2]
        ratio = metrics.get('contact_flight_ratio', 0)
        ax3.bar(['触地腾空比'], [ratio], color='#FF8C42', width=0.5)
        ax3.set_title('触地腾空比')
        ax3.set_ylabel('比值')
        ax3.text(0, ratio + 0.05, f'{ratio:.2f}', ha='center', va='bottom', fontweight='bold')
        
        # 4. 压力峰值对比
        ax4 = axes[1, 0]
        peak_forces = [
            metrics.get('left_avg_peak_force', 0),
            metrics.get('right_avg_peak_force', 0)
        ]
        bars4 = ax4.bar(['左脚', '右脚'], peak_forces, color=['#E74C3C', '#3498DB'])
        ax4.set_title('双脚压力峰值对比')
        ax4.set_ylabel('加速度 (g)')
        for bar, value in zip(bars4, peak_forces):
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                    f'{value:.2f}g', ha='center', va='bottom')
        
        # 5. 内旋风险评估
        ax5 = axes[1, 1]
        risk_levels = {'low': 1, 'medium': 2, 'high': 3}
        left_risk_level = risk_levels.get(metrics.get('left_overpronation_risk', 'low'), 1)
        right_risk_level = risk_levels.get(metrics.get('right_overpronation_risk', 'low'), 1)
        
        risk_colors = {1: '#2ECC71', 2: '#F39C12', 3: '#E74C3C'}
        bars5 = ax5.bar(['左脚', '右脚'], [left_risk_level, right_risk_level], 
                       color=[risk_colors[left_risk_level], risk_colors[right_risk_level]])
        ax5.set_title('内旋风险评估')
        ax5.set_ylabel('风险等级')
        ax5.set_ylim(0, 4)
        ax5.set_yticks([1, 2, 3])
        ax5.set_yticklabels(['低', '中', '高'])
        
        # 6. 步频指标
        ax6 = axes[1, 2]
        cadence = metrics.get('cadence', 0)
        step_count = metrics.get('step_count', 0)
        
        ax6.text(0.5, 0.7, f'步频\n{cadence:.1f} 步/分钟', ha='center', va='center', 
                fontsize=14, fontweight='bold', transform=ax6.transAxes)
        ax6.text(0.5, 0.3, f'总步数\n{step_count} 步', ha='center', va='center', 
                fontsize=12, transform=ax6.transAxes)
        ax6.set_title('步频统计')
        ax6.axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ 可视化图表已保存到: {save_path}")
        
        plt.show()

def main():
    """主函数 - 演示完整的分析流程"""
    print("🏃‍♂️ 跑步步态分析系统启动")
    print("="*50)
    
    # 创建分析器
    analyzer = RunningGaitAnalyzer()
    
    # 加载数据
    print("📊 正在加载传感器数据...")
    data = analyzer.load_data_from_db()
    
    if data.empty:
        print("❌ 数据加载失败，请检查数据库连接")
        return
    
    # 分离左右脚数据
    print("\n👣 正在分离左右脚数据...")
    analyzer.separate_foot_data()
    
    # 运行步态分析
    print("\n🔍 正在进行步态分析...")
    metrics = analyzer.calculate_gait_metrics()
    
    if not metrics:
        print("❌ 步态分析失败")
        return
    
    # 生成报告
    print("\n📋 生成分析报告...")
    report = analyzer.generate_report()
    print(report)
    
    # 保存报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"running_gait_report_{timestamp}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n✅ 报告已保存到: {report_file}")
    
    # 生成可视化
    print("\n📈 生成可视化图表...")
    chart_file = f"running_gait_analysis_{timestamp}.png"
    analyzer.visualize_analysis(save_path=chart_file)
    
    print("\n🎉 跑步步态分析完成！")

if __name__ == "__main__":
    main()
