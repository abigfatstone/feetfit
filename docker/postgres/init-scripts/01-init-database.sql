-- 初始化数据库脚本

-- 创建schema
CREATE SCHEMA IF NOT EXISTS theta_ai;

-- 设置默认schema
SET search_path TO theta_ai, public;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 创建传感器数据表
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
CREATE INDEX IF NOT EXISTS idx_sensor_data_device_mac ON theta_ai.sensor_data (device_mac);
CREATE INDEX IF NOT EXISTS idx_sensor_data_device_timestamp ON theta_ai.sensor_data (device_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_data_created_at ON theta_ai.sensor_data (created_at);

-- 创建步态分析结果表
CREATE TABLE IF NOT EXISTS theta_ai.gait_analysis_results (
    id BIGSERIAL PRIMARY KEY,
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(100),
    session_id UUID DEFAULT uuid_generate_v4(),
    
    -- 基础指标
    avg_contact_time DECIMAL(8, 4),
    avg_flight_time DECIMAL(8, 4),
    contact_flight_ratio DECIMAL(8, 4),
    cadence DECIMAL(8, 2),
    
    -- 左右脚对比
    left_avg_contact_time DECIMAL(8, 4),
    right_avg_contact_time DECIMAL(8, 4),
    lr_contact_time_diff DECIMAL(8, 4),
    
    -- 触地方式
    heel_strike_ratio DECIMAL(5, 4),
    midfoot_strike_ratio DECIMAL(5, 4),
    forefoot_strike_ratio DECIMAL(5, 4),
    dominant_strike_pattern VARCHAR(20),
    
    -- 压力分析
    left_avg_peak_force DECIMAL(8, 4),
    right_avg_peak_force DECIMAL(8, 4),
    force_asymmetry DECIMAL(8, 4),
    
    -- 内旋风险
    left_overpronation_risk VARCHAR(10),
    right_overpronation_risk VARCHAR(10),
    
    -- 步数统计
    step_count INTEGER,
    left_step_count INTEGER,
    right_step_count INTEGER,
    
    -- 分析参数
    data_start_time TIMESTAMP WITH TIME ZONE,
    data_end_time TIMESTAMP WITH TIME ZONE,
    total_analysis_duration DECIMAL(8, 2),
    
    -- JSON格式的详细数据
    detailed_metrics JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建步态分析结果索引
CREATE INDEX IF NOT EXISTS idx_gait_analysis_date ON theta_ai.gait_analysis_results (analysis_date);
CREATE INDEX IF NOT EXISTS idx_gait_analysis_user ON theta_ai.gait_analysis_results (user_id);
CREATE INDEX IF NOT EXISTS idx_gait_analysis_session ON theta_ai.gait_analysis_results (session_id);

-- 创建用户表
CREATE TABLE IF NOT EXISTS theta_ai.users (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(100),
    email VARCHAR(255),
    
    -- 用户基本信息
    height DECIMAL(5, 2), -- cm
    weight DECIMAL(5, 2), -- kg
    age INTEGER,
    gender VARCHAR(10),
    
    -- 跑步经验
    running_experience VARCHAR(20), -- beginner, intermediate, advanced
    weekly_mileage DECIMAL(6, 2), -- km per week
    preferred_pace VARCHAR(20), -- easy, moderate, fast
    
    -- 设备信息
    device_info JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建用户索引
CREATE INDEX IF NOT EXISTS idx_users_user_id ON theta_ai.users (user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON theta_ai.users (email);

-- 插入示例用户
INSERT INTO theta_ai.users (user_id, username, email, height, weight, age, gender, running_experience, weekly_mileage, preferred_pace)
VALUES 
    ('demo_user_001', 'Demo Runner', 'demo@example.com', 175.0, 70.0, 28, 'male', 'intermediate', 25.0, 'moderate')
ON CONFLICT (user_id) DO NOTHING;

-- 创建触发器更新updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON theta_ai.users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 授权
GRANT ALL PRIVILEGES ON SCHEMA theta_ai TO holistic_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA theta_ai TO holistic_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA theta_ai TO holistic_user;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE '数据库初始化完成！';
    RAISE NOTICE 'Schema: theta_ai';
    RAISE NOTICE '表: sensor_data, gait_analysis_results, users';
END $$;
