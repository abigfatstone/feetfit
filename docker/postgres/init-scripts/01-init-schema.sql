-- 足底压力传感器数据表结构
-- 创建时间: 2025-01-14

-- 创建传感器数据表
CREATE TABLE IF NOT EXISTS sensor_data (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    device_name VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL DEFAULT 'SOLESENSE',
    date_recorded DATE,
    subject VARCHAR(50),
    activity VARCHAR(100),
    trial_number INTEGER DEFAULT 1,
    
    -- 108个传感器数据点
    data_point_1 DECIMAL(10,3),
    data_point_2 DECIMAL(10,3),
    data_point_3 DECIMAL(10,3),
    data_point_4 DECIMAL(10,3),
    data_point_5 DECIMAL(10,3),
    data_point_6 DECIMAL(10,3),
    data_point_7 DECIMAL(10,3),
    data_point_8 DECIMAL(10,3),
    data_point_9 DECIMAL(10,3),
    data_point_10 DECIMAL(10,3),
    data_point_11 DECIMAL(10,3),
    data_point_12 DECIMAL(10,3),
    data_point_13 DECIMAL(10,3),
    data_point_14 DECIMAL(10,3),
    data_point_15 DECIMAL(10,3),
    data_point_16 DECIMAL(10,3),
    data_point_17 DECIMAL(10,3),
    data_point_18 DECIMAL(10,3),
    data_point_19 DECIMAL(10,3),
    data_point_20 DECIMAL(10,3),
    data_point_21 DECIMAL(10,3),
    data_point_22 DECIMAL(10,3),
    data_point_23 DECIMAL(10,3),
    data_point_24 DECIMAL(10,3),
    data_point_25 DECIMAL(10,3),
    data_point_26 DECIMAL(10,3),
    data_point_27 DECIMAL(10,3),
    data_point_28 DECIMAL(10,3),
    data_point_29 DECIMAL(10,3),
    data_point_30 DECIMAL(10,3),
    data_point_31 DECIMAL(10,3),
    data_point_32 DECIMAL(10,3),
    data_point_33 DECIMAL(10,3),
    data_point_34 DECIMAL(10,3),
    data_point_35 DECIMAL(10,3),
    data_point_36 DECIMAL(10,3),
    data_point_37 DECIMAL(10,3),
    data_point_38 DECIMAL(10,3),
    data_point_39 DECIMAL(10,3),
    data_point_40 DECIMAL(10,3),
    data_point_41 DECIMAL(10,3),
    data_point_42 DECIMAL(10,3),
    data_point_43 DECIMAL(10,3),
    data_point_44 DECIMAL(10,3),
    data_point_45 DECIMAL(10,3),
    data_point_46 DECIMAL(10,3),
    data_point_47 DECIMAL(10,3),
    data_point_48 DECIMAL(10,3),
    data_point_49 DECIMAL(10,3),
    data_point_50 DECIMAL(10,3),
    data_point_51 DECIMAL(10,3),
    data_point_52 DECIMAL(10,3),
    data_point_53 DECIMAL(10,3),
    data_point_54 DECIMAL(10,3),
    data_point_55 DECIMAL(10,3),
    data_point_56 DECIMAL(10,3),
    data_point_57 DECIMAL(10,3),
    data_point_58 DECIMAL(10,3),
    data_point_59 DECIMAL(10,3),
    data_point_60 DECIMAL(10,3),
    data_point_61 DECIMAL(10,3),
    data_point_62 DECIMAL(10,3),
    data_point_63 DECIMAL(10,3),
    data_point_64 DECIMAL(10,3),
    data_point_65 DECIMAL(10,3),
    data_point_66 DECIMAL(10,3),
    data_point_67 DECIMAL(10,3),
    data_point_68 DECIMAL(10,3),
    data_point_69 DECIMAL(10,3),
    data_point_70 DECIMAL(10,3),
    data_point_71 DECIMAL(10,3),
    data_point_72 DECIMAL(10,3),
    data_point_73 DECIMAL(10,3),
    data_point_74 DECIMAL(10,3),
    data_point_75 DECIMAL(10,3),
    data_point_76 DECIMAL(10,3),
    data_point_77 DECIMAL(10,3),
    data_point_78 DECIMAL(10,3),
    data_point_79 DECIMAL(10,3),
    data_point_80 DECIMAL(10,3),
    data_point_81 DECIMAL(10,3),
    data_point_82 DECIMAL(10,3),
    data_point_83 DECIMAL(10,3),
    data_point_84 DECIMAL(10,3),
    data_point_85 DECIMAL(10,3),
    data_point_86 DECIMAL(10,3),
    data_point_87 DECIMAL(10,3),
    data_point_88 DECIMAL(10,3),
    data_point_89 DECIMAL(10,3),
    data_point_90 DECIMAL(10,3),
    data_point_91 DECIMAL(10,3),
    data_point_92 DECIMAL(10,3),
    data_point_93 DECIMAL(10,3),
    data_point_94 DECIMAL(10,3),
    data_point_95 DECIMAL(10,3),
    data_point_96 DECIMAL(10,3),
    data_point_97 DECIMAL(10,3),
    data_point_98 DECIMAL(10,3),
    data_point_99 DECIMAL(10,3),
    data_point_100 DECIMAL(10,3),
    data_point_101 DECIMAL(10,3),
    data_point_102 DECIMAL(10,3),
    data_point_103 DECIMAL(10,3),
    data_point_104 DECIMAL(10,3),
    data_point_105 DECIMAL(10,3),
    data_point_106 DECIMAL(10,3),
    data_point_107 DECIMAL(10,3),
    data_point_108 DECIMAL(10,3),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_data_device ON sensor_data(device_name);
CREATE INDEX IF NOT EXISTS idx_sensor_data_subject_activity ON sensor_data(subject, activity, trial_number);
CREATE INDEX IF NOT EXISTS idx_sensor_data_sensor_type ON sensor_data(sensor_type);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sensor_data_updated_at 
    BEFORE UPDATE ON sensor_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入一些示例数据用于测试
INSERT INTO sensor_data (
    filename, timestamp, device_name, sensor_type, 
    date_recorded, subject, activity, trial_number,
    data_point_1, data_point_50, data_point_108
) VALUES 
(
    'test_data.csv', 
    CURRENT_TIMESTAMP, 
    'solesenseL', 
    'SOLESENSE',
    CURRENT_DATE,
    'test_user',
    'walk',
    1,
    10.5, 15.2, 8.7
),
(
    'test_data.csv', 
    CURRENT_TIMESTAMP, 
    'solesenseR', 
    'SOLESENSE',
    CURRENT_DATE,
    'test_user',
    'walk',
    1,
    12.3, 18.1, 9.4
);

COMMENT ON TABLE sensor_data IS '足底压力传感器数据表，存储108个传感器点的压力数据';
COMMENT ON COLUMN sensor_data.device_name IS '设备名称，如solesenseL（左脚）或solesenseR（右脚）';
COMMENT ON COLUMN sensor_data.sensor_type IS '传感器类型，默认为SOLESENSE';
COMMENT ON COLUMN sensor_data.subject IS '受试者标识';
COMMENT ON COLUMN sensor_data.activity IS '活动类型，如walk、run、jump等';
COMMENT ON COLUMN sensor_data.trial_number IS '试次编号';