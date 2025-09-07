'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { 
  PlayIcon, 
  PauseIcon, 
  BackwardIcon, 
  ForwardIcon,
  ArrowPathIcon,
  ChartBarIcon,
  EyeIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/solid';

// 类型定义
interface PressureData {
  [sensorId: number]: number;
}

interface StreamData {
  timestamp: string;
  left: PressureData;
  right: PressureData;
}

interface DataOption {
  subject: string;
  activity: string;
  trial_number: number;
  data_count: number;
}

interface SensorLayouts {
  left: number[][];
  right: number[][];
}

// 动态获取API基础地址 - 优先使用环境变量中的HOST_IP
const getApiBase = () => {
  if (typeof window !== 'undefined') {
    // 浏览器端：优先使用环境变量中的HOST_IP，否则使用当前主机
    const hostIp = process.env.NEXT_PUBLIC_HOST_IP;
    const protocol = window.location.protocol;
    
    let hostname;
    if (hostIp && hostIp !== 'localhost') {
      hostname = hostIp;
      console.log('🌐 使用启动脚本设置的HOST_IP:', hostIp);
    } else {
      hostname = window.location.hostname;
      console.log('🌐 使用当前页面hostname:', hostname);
    }
    
    const apiBase = `${protocol}//${hostname}:3080`;
    console.log('🚀 最终API地址:', apiBase);
    return apiBase;
  }
  // 服务端：使用环境变量
  const serverApiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3080';
  console.log('🖥️ 服务端API地址:', serverApiBase);
  return serverApiBase;
};

const PressureVisualization: React.FC = () => {
  // 状态管理
  const [sensorLayouts, setSensorLayouts] = useState<SensorLayouts | null>(null);
  const [dataOptions, setDataOptions] = useState<DataOption[]>([]);
  const [apiBase, setApiBase] = useState<string>('');
  const [selectedOption, setSelectedOption] = useState({
    subject: 'h',
    activity: 'walk',
    trial: 1
  });
  const [streamData, setStreamData] = useState<StreamData[]>([]);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(500);
  const [maxPressure, setMaxPressure] = useState(100);
  const [viewMode, setViewMode] = useState<'2d' | '3d'>('2d');
  const [showStats, setShowStats] = useState(false);
  const [loading, setLoading] = useState(true);

  // 初始化API地址
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // 优先使用环境变量中的HOST_IP
      const hostIp = process.env.NEXT_PUBLIC_HOST_IP;
      const protocol = window.location.protocol;
      
      let hostname;
      if (hostIp && hostIp !== 'localhost') {
        hostname = hostIp;
        console.log('🌐 使用启动脚本设置的HOST_IP:', hostIp);
      } else {
        hostname = window.location.hostname;
        console.log('🌐 使用当前页面hostname:', hostname);
      }
      
      const dynamicApiBase = `${protocol}//${hostname}:3080`;
      console.log('🚀 设置API地址:', dynamicApiBase);
      setApiBase(dynamicApiBase);
    }
  }, []);

  // 获取传感器布局
  useEffect(() => {
    if (!apiBase) return;
    
    const fetchLayout = async () => {
      try {
        console.log('📡 请求传感器布局:', `${apiBase}/api/sensor-layout`);
        const response = await axios.get(`${apiBase}/api/sensor-layout`);
        setSensorLayouts(response.data);
        console.log('✅ 传感器布局获取成功');
      } catch (error) {
        console.error('❌ 获取传感器布局失败:', error);
        // 设置默认布局以防止卡在加载状态
        setSensorLayouts({
          left: [[1,2,3,4,5,6,7,8]],
          right: [[1,2,3,4,5,6,7,8]]
        });
      }
    };
    fetchLayout();
  }, [apiBase]);

  // 获取数据选项
  useEffect(() => {
    if (!apiBase) return;
    
    const fetchDataOptions = async () => {
      try {
        console.log('📡 请求数据选项:', `${apiBase}/api/data-options`);
        const response = await axios.get(`${apiBase}/api/data-options`);
        setDataOptions(response.data);
        console.log('✅ 数据选项获取成功，共', response.data.length, '个选项');
      } catch (error) {
        console.error('❌ 获取数据选项失败:', error);
        // 设置默认选项以防止卡在加载状态
        setDataOptions([{
          subject: 'h',
          activity: 'walk', 
          trial_number: 1,
          data_count: 100
        }]);
      }
    };
    fetchDataOptions();
  }, [apiBase]);

  // 获取压力数据流
  const fetchPressureStream = useCallback(async () => {
    if (!apiBase) return;
    
    setLoading(true);
    try {
      console.log('请求压力数据:', `${apiBase}/api/pressure-stream`);
      const response = await axios.get(`${apiBase}/api/pressure-stream`, {
        params: {
          subject: selectedOption.subject,
          activity: selectedOption.activity,
          trial: selectedOption.trial,
          start_index: 0,
          count: 50
        }
      });
      
      const data = response.data;
      console.log('✅ 压力数据获取成功，共', data.length, '帧数据');
      setStreamData(data);
      setCurrentFrame(0);
      
      // 计算最大压力值
      let maxVal = 0;
      data.forEach((frame: StreamData) => {
        Object.values(frame.left).forEach(val => maxVal = Math.max(maxVal, val));
        Object.values(frame.right).forEach(val => maxVal = Math.max(maxVal, val));
      });
      setMaxPressure(maxVal || 100);
      console.log('📊 最大压力值:', maxVal);
      
    } catch (error) {
      console.error('获取压力数据失败:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedOption, apiBase]);

  // 当选项改变时重新获取数据
  useEffect(() => {
    if (selectedOption.subject && selectedOption.activity) {
      fetchPressureStream();
    }
  }, [selectedOption, fetchPressureStream]);

  // 播放控制
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isPlaying && streamData.length > 0) {
      interval = setInterval(() => {
        setCurrentFrame(prev => (prev + 1) % streamData.length);
      }, playSpeed);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlaying, streamData.length, playSpeed]);

  // 获取压力值对应的颜色 - 高端蓝色主题
  const getPressureColor = (pressure: number): string => {
    if (pressure === 0) return 'rgba(248, 250, 252, 0.6)'; // 极淡灰蓝色
    
    const intensity = Math.min(pressure / maxPressure, 1);
    
    // 现代高端蓝色渐变色彩映射
    if (intensity < 0.2) {
      return `rgba(59, 130, 246, ${0.3 + intensity * 0.3})`; // 浅蓝色
    } else if (intensity < 0.4) {
      return `rgba(37, 99, 235, ${0.4 + intensity * 0.3})`; // 蓝色
    } else if (intensity < 0.6) {
      return `rgba(147, 51, 234, ${0.5 + intensity * 0.3})`; // 紫色
    } else if (intensity < 0.8) {
      return `rgba(236, 72, 153, ${0.6 + intensity * 0.3})`; // 粉紫色
    } else {
      return `rgba(239, 68, 68, ${0.7 + intensity * 0.3})`; // 红色
    }
  };

  // 获取压力强度等级
  const getPressureLevel = (pressure: number): string => {
    const intensity = pressure / maxPressure;
    if (intensity < 0.2) return 'low';
    if (intensity < 0.5) return 'medium';
    if (intensity < 0.8) return 'high';
    return 'critical';
  };

  // 渲染单个脚的传感器 - 完全重新设计，优化间距和视觉效果
  const renderFoot = (layout: number[][], pressureData: PressureData, side: 'left' | 'right') => {
    return (
      <motion.div 
        className={`relative p-6 lg:p-10 rounded-[2rem] bg-gradient-to-br from-white/95 via-slate-50/90 to-blue-50/80 backdrop-blur-2xl border border-slate-200/50 shadow-[0_32px_64px_-12px_rgba(0,0,0,0.12)] w-full max-w-2xl`}
        initial={{ opacity: 0, scale: 0.95, y: 30 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.6, delay: side === 'left' ? 0 : 0.15, ease: "easeOut" }}
        style={{
          boxShadow: '0 32px 64px -12px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(148, 163, 184, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
        }}
      >
        {/* 脚部标题 */}
        <div className="text-center mb-10">
          <motion.h3 
            className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-slate-800 via-blue-600 to-indigo-600 mb-4"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: side === 'left' ? 0.3 : 0.45 }}
          >
            {side === 'left' ? '🦶 LEFT FOOT' : 'RIGHT FOOT 🦶'}
          </motion.h3>
          <div className="h-[3px] w-24 bg-gradient-to-r from-blue-500 to-indigo-500 mx-auto rounded-full shadow-sm"></div>
          <p className="text-slate-600 mt-3 font-medium tracking-wide">压力传感器阵列</p>
        </div>
        
        {/* 传感器网格 - 大幅增加间距 */}
        <div className="sensor-grid space-y-4 lg:space-y-6">
          {layout.map((row, rowIndex) => (
            <motion.div 
              key={rowIndex} 
              className="flex justify-center gap-4 lg:gap-6"
              initial={{ opacity: 0, x: side === 'left' ? -20 : 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + rowIndex * 0.05 }}
            >
              {row.map((sensorId) => {
                const pressure = pressureData[sensorId] || 0;
                const color = getPressureColor(pressure);
                const level = getPressureLevel(pressure);
                
                return (
                  <motion.div
                    key={`${sensorId}-${currentFrame}`}
                    className={`
                      group relative w-12 h-12 lg:w-16 lg:h-16 rounded-2xl border-2 cursor-pointer
                      transition-all duration-300 hover:scale-125 hover:z-20 hover:rotate-3
                      ${level === 'critical' ? 'border-red-400 shadow-2xl shadow-red-300/50' : 
                        level === 'high' ? 'border-orange-400 shadow-2xl shadow-orange-300/50' :
                        level === 'medium' ? 'border-blue-400 shadow-2xl shadow-blue-300/50' : 'border-slate-300 shadow-xl shadow-slate-300/30'}
                    `}
                    style={{
                      backgroundColor: color,
                      boxShadow: pressure > 0 ? 
                        `0 20px 40px -8px ${color}, 0 0 0 1px rgba(148, 163, 184, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.2)` : 
                        '0 12px 24px -6px rgba(148, 163, 184, 0.15), 0 0 0 1px rgba(148, 163, 184, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
                    }}
                    initial={{ scale: 0.3, opacity: 0 }}
                    animate={{ 
                      scale: 1 + (pressure / maxPressure) * 0.15,
                      opacity: 0.95 + (pressure / maxPressure) * 0.05
                    }}
                    transition={{ 
                      duration: 0.4,
                      type: "spring",
                      stiffness: 200,
                      damping: 15
                    }}
                    whileHover={{ 
                      scale: 1.3,
                      rotate: 8,
                      zIndex: 100,
                      transition: { duration: 0.2 }
                    }}
                  >
                    {/* 传感器编号 */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-sm lg:text-base font-black text-slate-700 drop-shadow-sm group-hover:text-slate-800 transition-colors">
                        {sensorId}
                      </span>
                    </div>
                    
                    {/* 悬浮信息卡片 */}
                    <motion.div 
                      className="absolute -top-16 left-1/2 transform -translate-x-1/2 bg-slate-900/95 text-white px-3 py-2 rounded-xl text-sm font-mono backdrop-blur-sm border border-slate-700/50 opacity-0 pointer-events-none shadow-2xl"
                      whileHover={{ 
                        opacity: 1,
                        y: -4,
                        transition: { duration: 0.2 }
                      }}
                    >
                      <div className="text-center">
                        <div className="text-xs text-slate-300 mb-1">传感器 {sensorId}</div>
                        <div className="font-bold">{pressure.toFixed(1)}</div>
                        <div className="text-xs text-slate-400 mt-1">{level.toUpperCase()}</div>
                      </div>
                      {/* 箭头 */}
                      <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-900/95"></div>
                    </motion.div>
                    
                    {/* 极高压力的脉冲动画 */}
                    {pressure > maxPressure * 0.8 && (
                      <motion.div
                        className="absolute inset-0 rounded-2xl border-3 border-red-400"
                        animate={{
                          scale: [1, 1.4, 1],
                          opacity: [0.8, 0, 0.8],
                          rotate: [0, 180, 360]
                        }}
                        transition={{
                          duration: 2,
                          repeat: Infinity,
                          ease: "easeInOut"
                        }}
                      />
                    )}
                    
                    {/* 内发光效果 */}
                    {pressure > maxPressure * 0.5 && (
                      <div 
                        className="absolute inset-1 rounded-xl opacity-40"
                        style={{
                          background: `radial-gradient(circle, ${color} 0%, transparent 70%)`
                        }}
                      />
                    )}
                  </motion.div>
                );
              })}
            </motion.div>
          ))}
        </div>
        
        {/* 脚部统计信息 */}
        <motion.div 
          className="mt-10 p-4 bg-white/40 backdrop-blur-sm rounded-xl border border-white/50"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1 }}
        >
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-slate-700">{Object.values(pressureData).filter(p => p > 0).length}</div>
              <div className="text-xs text-slate-500 font-medium">激活传感器</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-700">{Math.max(...Object.values(pressureData)).toFixed(1)}</div>
              <div className="text-xs text-slate-500 font-medium">峰值压力</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-700">{(Object.values(pressureData).reduce((sum, p) => sum + p, 0) / Object.values(pressureData).length).toFixed(1)}</div>
              <div className="text-xs text-slate-500 font-medium">平均压力</div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    );
  };

  // 控制面板 - 高端现代设计
  const renderControls = () => (
    <motion.div 
      className="bg-gradient-to-br from-white/95 via-slate-50/90 to-blue-50/80 backdrop-blur-2xl rounded-3xl p-10 border border-slate-200/50 shadow-[0_32px_64px_-12px_rgba(0,0,0,0.1)]"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      style={{
        boxShadow: '0 32px 64px -12px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(148, 163, 184, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
      }}
    >
      {/* 数据选择器 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
        <div className="space-y-4">
          <label className="block text-base font-bold text-slate-700 tracking-wide">👤 受试者</label>
          <select 
            value={selectedOption.subject}
            onChange={(e) => setSelectedOption(prev => ({ ...prev, subject: e.target.value }))}
            className="w-full px-5 py-4 bg-white/80 backdrop-blur-sm border-2 border-slate-200 rounded-2xl text-slate-700 font-medium focus:ring-4 focus:ring-blue-500/20 focus:border-blue-400 transition-all shadow-lg hover:shadow-xl"
          >
            {[...new Set(dataOptions.map(opt => opt.subject))].map(subject => (
              <option key={subject} value={subject} className="bg-white font-medium">
                {subject.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
        
        <div className="space-y-4">
          <label className="block text-base font-bold text-slate-700 tracking-wide">🏃 活动</label>
          <select 
            value={selectedOption.activity}
            onChange={(e) => setSelectedOption(prev => ({ ...prev, activity: e.target.value }))}
            className="w-full px-5 py-4 bg-white/80 backdrop-blur-sm border-2 border-slate-200 rounded-2xl text-slate-700 font-medium focus:ring-4 focus:ring-blue-500/20 focus:border-blue-400 transition-all shadow-lg hover:shadow-xl"
          >
            {[...new Set(dataOptions
              .filter(opt => opt.subject === selectedOption.subject)
              .map(opt => opt.activity)
            )].map(activity => (
              <option key={activity} value={activity} className="bg-white font-medium">
                {activity.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
        
        <div className="space-y-4">
          <label className="block text-base font-bold text-slate-700 tracking-wide">📊 试次</label>
          <select 
            value={selectedOption.trial}
            onChange={(e) => setSelectedOption(prev => ({ ...prev, trial: parseInt(e.target.value) }))}
            className="w-full px-5 py-4 bg-white/80 backdrop-blur-sm border-2 border-slate-200 rounded-2xl text-slate-700 font-medium focus:ring-4 focus:ring-blue-500/20 focus:border-blue-400 transition-all shadow-lg hover:shadow-xl"
          >
            {[...new Set(dataOptions
              .filter(opt => opt.subject === selectedOption.subject && opt.activity === selectedOption.activity)
              .map(opt => opt.trial_number)
            )].map(trial => (
              <option key={trial} value={trial} className="bg-white font-medium">
                TRIAL {trial}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      {/* 播放控制 */}
      <div className="flex items-center justify-center gap-8 mb-10">
        <motion.button 
          onClick={() => setCurrentFrame(0)}
          className="group p-5 bg-gradient-to-br from-slate-600 to-slate-700 rounded-2xl hover:from-slate-500 hover:to-slate-600 transition-all shadow-2xl text-white border border-slate-500/50"
          whileHover={{ scale: 1.05, rotate: -5 }}
          whileTap={{ scale: 0.95 }}
        >
          <BackwardIcon className="w-7 h-7 group-hover:scale-110 transition-transform" />
        </motion.button>
        
        <motion.button 
          onClick={() => setIsPlaying(!isPlaying)}
          className={`group p-6 rounded-3xl transition-all shadow-2xl text-white border-2 ${
            isPlaying 
              ? 'bg-gradient-to-br from-red-500 to-red-600 hover:from-red-400 hover:to-red-500 border-red-400/50' 
              : 'bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-400 hover:to-indigo-500 border-blue-400/50'
          }`}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          {isPlaying ? (
            <PauseIcon className="w-10 h-10 group-hover:scale-110 transition-transform" />
          ) : (
            <PlayIcon className="w-10 h-10 group-hover:scale-110 transition-transform" />
          )}
        </motion.button>
        
        <motion.button 
          onClick={() => setCurrentFrame((prev) => (prev + 1) % streamData.length)}
          className="group p-5 bg-gradient-to-br from-slate-600 to-slate-700 rounded-2xl hover:from-slate-500 hover:to-slate-600 transition-all shadow-2xl text-white border border-slate-500/50"
          whileHover={{ scale: 1.05, rotate: 5 }}
          whileTap={{ scale: 0.95 }}
        >
          <ForwardIcon className="w-7 h-7 group-hover:scale-110 transition-transform" />
        </motion.button>
      </div>
      
      {/* 状态信息 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <motion.div 
          className="bg-white/60 backdrop-blur-sm rounded-2xl p-5 text-center border border-slate-200/50 shadow-lg"
          whileHover={{ scale: 1.02, y: -2 }}
        >
          <div className="text-3xl font-black text-blue-600 mb-2">{currentFrame + 1}</div>
          <div className="text-sm text-slate-600 font-medium">当前帧</div>
        </motion.div>
        
        <motion.div 
          className="bg-white/60 backdrop-blur-sm rounded-2xl p-5 text-center border border-slate-200/50 shadow-lg"
          whileHover={{ scale: 1.02, y: -2 }}
        >
          <div className="text-3xl font-black text-indigo-600 mb-2">{streamData.length}</div>
          <div className="text-sm text-slate-600 font-medium">总帧数</div>
        </motion.div>
        
        <motion.div 
          className="bg-white/60 backdrop-blur-sm rounded-2xl p-5 text-center border border-slate-200/50 shadow-lg"
          whileHover={{ scale: 1.02, y: -2 }}
        >
          <div className="text-3xl font-black text-purple-600 mb-2">{maxPressure.toFixed(0)}</div>
          <div className="text-sm text-slate-600 font-medium">最大压力</div>
        </motion.div>
        
        <motion.div 
          className="bg-white/60 backdrop-blur-sm rounded-2xl p-5 text-center border border-slate-200/50 shadow-lg"
          whileHover={{ scale: 1.02, y: -2 }}
        >
          <div className="text-3xl font-black text-pink-600 mb-2">{playSpeed}</div>
          <div className="text-sm text-slate-600 font-medium">间隔(ms)</div>
        </motion.div>
      </div>
      
      {/* 进度条 */}
      <div className="space-y-5 mb-8">
        <label className="block text-base font-bold text-slate-700">📈 播放进度</label>
        <div className="relative">
          <input
            type="range"
            min={0}
            max={streamData.length - 1}
            value={currentFrame}
            onChange={(e) => setCurrentFrame(parseInt(e.target.value))}
            className="w-full h-4 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-full appearance-none cursor-pointer shadow-inner"
            style={{
              background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${(currentFrame / (streamData.length - 1)) * 100}%, #e2e8f0 ${(currentFrame / (streamData.length - 1)) * 100}%, #e2e8f0 100%)`
            }}
          />
        </div>
      </div>
      
      {/* 速度控制 */}
      <div className="space-y-5">
        <label className="block text-base font-bold text-slate-700">⏱️ 播放速度</label>
        <div className="relative">
          <input
            type="range"
            min={100}
            max={2000}
            value={playSpeed}
            onChange={(e) => setPlaySpeed(parseInt(e.target.value))}
            className="w-full h-4 bg-gradient-to-r from-purple-100 to-pink-100 rounded-full appearance-none cursor-pointer shadow-inner"
            style={{
              background: `linear-gradient(to right, #8b5cf6 0%, #8b5cf6 ${((2000 - playSpeed) / 1900) * 100}%, #e2e8f0 ${((2000 - playSpeed) / 1900) * 100}%, #e2e8f0 100%)`
            }}
          />
        </div>
        <div className="flex justify-between text-sm text-slate-500 font-medium">
          <span>快速 (100ms)</span>
          <span>慢速 (2000ms)</span>
        </div>
      </div>
    </motion.div>
  );

  // 加载状态 - 高端设计
  if (loading || !sensorLayouts || streamData.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/50 to-indigo-50/80 flex items-center justify-center">
        <motion.div
          className="text-center p-12 bg-white/90 backdrop-blur-2xl rounded-3xl border border-slate-200/50 shadow-[0_32px_64px_-12px_rgba(0,0,0,0.15)]"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          style={{
            boxShadow: '0 32px 64px -12px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(148, 163, 184, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
          }}
        >
          <motion.div
            className="relative mx-auto mb-8"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            <div className="w-24 h-24 border-4 border-gradient-to-r from-blue-500 to-indigo-500 border-t-transparent rounded-full"></div>
            <div className="absolute inset-3 w-16 h-16 border-4 border-purple-400 border-b-transparent rounded-full animate-spin-reverse"></div>
          </motion.div>
          
          <motion.h2 
            className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-slate-800 to-blue-600 mb-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            加载中...
          </motion.h2>
          
          <motion.p 
            className="text-xl text-slate-600 font-medium mb-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            正在准备足底压力数据
          </motion.p>
          
          <motion.p 
            className="text-slate-500"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
          >
            请耐心等待，我们正在为您构建高端可视化体验
          </motion.p>
        </motion.div>
      </div>
    );
  }

  const currentData = streamData[currentFrame];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/50 to-indigo-50/80">
      {/* 头部 */}
      <motion.header 
        className="text-center py-16 px-4"
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <motion.h1 
          className="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-r from-slate-900 via-blue-600 to-indigo-600 mb-8 tracking-tight"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.8 }}
        >
          👣 FeetFit Analytics
        </motion.h1>
        
        <motion.div 
          className="text-3xl text-slate-700 font-bold mb-4 tracking-wide"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.6 }}
        >
          {selectedOption.subject.toUpperCase()} · {selectedOption.activity.toUpperCase()} · TRIAL {selectedOption.trial}
        </motion.div>
        
        {streamData[currentFrame] && (
          <motion.div 
            className="text-xl text-slate-500 font-medium"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.6 }}
          >
            {new Date(streamData[currentFrame].timestamp).toLocaleTimeString()}
          </motion.div>
        )}
        
        <motion.div 
          className="mt-8 w-40 h-1.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 mx-auto rounded-full shadow-lg"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ delay: 0.8, duration: 0.8 }}
        />
      </motion.header>
      
      {/* 控制面板 */}
      <div className="max-w-7xl mx-auto px-6 mb-12">
        {renderControls()}
      </div>
      
      {/* 可视化容器 - 左右脚并排显示 */}
      <div className="w-full mx-auto px-4 lg:px-6 pb-12">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentFrame}
            className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 justify-items-center items-start max-w-none"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            {renderFoot(sensorLayouts.left, currentData.left, 'left')}
            {renderFoot(sensorLayouts.right, currentData.right, 'right')}
          </motion.div>
        </AnimatePresence>
      </div>
      
      {/* 压力图例和统计 */}
      <motion.div 
        className="max-w-6xl mx-auto px-6 pb-16"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        <div className="bg-gradient-to-br from-white/95 via-slate-50/90 to-blue-50/80 backdrop-blur-2xl rounded-3xl p-10 border border-slate-200/50 shadow-[0_32px_64px_-12px_rgba(0,0,0,0.1)]"
          style={{
            boxShadow: '0 32px 64px -12px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(148, 163, 184, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
          }}
        >
          <motion.h3 
            className="text-4xl font-black text-center text-slate-800 mb-10 tracking-tight"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.6 }}
          >
            🎨 压力强度视觉映射
          </motion.h3>
          
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 mb-10">
            <motion.div 
              className="text-center group"
              whileHover={{ scale: 1.05 }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-400 to-blue-500 shadow-2xl mx-auto mb-4 group-hover:shadow-blue-400/50 transition-all"></div>
              <div className="text-lg font-bold text-slate-700">低压力</div>
              <div className="text-sm text-slate-500">0-20%</div>
            </motion.div>
            
            <motion.div 
              className="text-center group"
              whileHover={{ scale: 1.05 }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-400 to-purple-500 shadow-2xl mx-auto mb-4 group-hover:shadow-purple-400/50 transition-all"></div>
              <div className="text-lg font-bold text-slate-700">中等压力</div>
              <div className="text-sm text-slate-500">20-60%</div>
            </motion.div>
            
            <motion.div 
              className="text-center group"
              whileHover={{ scale: 1.05 }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 }}
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-pink-400 to-pink-500 shadow-2xl mx-auto mb-4 group-hover:shadow-pink-400/50 transition-all"></div>
              <div className="text-lg font-bold text-slate-700">高压力</div>
              <div className="text-sm text-slate-500">60-80%</div>
            </motion.div>
            
            <motion.div 
              className="text-center group"
              whileHover={{ scale: 1.05 }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.0 }}
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-400 to-red-500 shadow-2xl mx-auto mb-4 animate-pulse group-hover:shadow-red-400/50 transition-all"></div>
              <div className="text-lg font-bold text-slate-700">极高压力</div>
              <div className="text-sm text-slate-500">80-100%</div>
            </motion.div>
          </div>
          
          {/* 渐变条 */}
          <motion.div 
            className="mt-8 h-6 bg-gradient-to-r from-blue-400 via-purple-500 via-pink-400 to-red-500 rounded-2xl shadow-2xl shadow-blue-500/30"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ delay: 1.1, duration: 1.2, ease: "easeOut" }}
          />
          
          <div className="flex justify-between text-base font-bold text-slate-600 mt-4">
            <span>0</span>
            <span>{(maxPressure * 0.25).toFixed(0)}</span>
            <span>{(maxPressure * 0.5).toFixed(0)}</span>
            <span>{(maxPressure * 0.75).toFixed(0)}</span>
            <span>{maxPressure.toFixed(0)}</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default PressureVisualization;
