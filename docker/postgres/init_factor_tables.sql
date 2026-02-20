-- Factor Registry and Optimized Factor Data Tables
-- Separates factor metadata from factor values for better data management
-- Ensure UTF-8 encoding
SET client_encoding = 'UTF8';

-- ============================================
-- Factor Registry Table (因子注册表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.factor_registry (
    factor_id VARCHAR(50) PRIMARY KEY,
    factor_code VARCHAR(50) UNIQUE NOT NULL,
    factor_name VARCHAR(100) NOT NULL,
    factor_type VARCHAR(30) NOT NULL,
    factor_category VARCHAR(50),
    description TEXT,
    formula TEXT,
    parameters JSONB DEFAULT '{}',
    dependencies TEXT[] DEFAULT '{}',
    lookback_period INTEGER DEFAULT 20,
    frequency VARCHAR(20) DEFAULT 'daily',
    data_requirements JSONB DEFAULT '{}',
    neutralization_config JSONB DEFAULT '{}',
    is_builtin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    version VARCHAR(20) DEFAULT '1.0',
    author VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_factor_type CHECK (factor_type IN ('technical', 'fundamental', 'alternative', 'custom', 'macro'))
);

COMMENT ON TABLE openfinance.factor_registry IS 'Factor metadata registry - stores factor definitions and configurations';
COMMENT ON COLUMN openfinance.factor_registry.dependencies IS 'List of data fields required for factor calculation';
COMMENT ON COLUMN openfinance.factor_registry.data_requirements IS 'JSON specifying required data tables and columns';

-- ============================================
-- Optimized Factor Data Table (优化因子数据表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.factor_data (
    id BIGSERIAL PRIMARY KEY,
    factor_id VARCHAR(50) NOT NULL REFERENCES openfinance.factor_registry(factor_id) ON DELETE CASCADE,
    code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    factor_value DECIMAL(20,8) NOT NULL,
    factor_rank INTEGER,
    factor_percentile DECIMAL(8,4),
    factor_zscore DECIMAL(12,6),
    is_neutralized BOOLEAN DEFAULT FALSE,
    neutralization_method VARCHAR(50),
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_factor_data UNIQUE (factor_id, code, trade_date)
);

-- Create indexes for factor_data
CREATE INDEX IF NOT EXISTS ix_factor_data_factor_id ON openfinance.factor_data(factor_id);
CREATE INDEX IF NOT EXISTS ix_factor_data_code ON openfinance.factor_data(code);
CREATE INDEX IF NOT EXISTS ix_factor_data_date ON openfinance.factor_data(trade_date);
CREATE INDEX IF NOT EXISTS ix_factor_data_factor_date ON openfinance.factor_data(factor_id, trade_date);
CREATE INDEX IF NOT EXISTS ix_factor_data_code_date ON openfinance.factor_data(code, trade_date);

-- Create partition for factor_data (by trade_date)
-- Note: For production, consider using TimescaleDB or native PostgreSQL partitioning

COMMENT ON TABLE openfinance.factor_data IS 'Optimized factor values table - references factor_registry for metadata';
COMMENT ON COLUMN openfinance.factor_data.factor_zscore IS 'Z-score normalized factor value';
COMMENT ON COLUMN openfinance.factor_data.data_quality_score IS 'Quality score for the factor value (0-1)';

-- ============================================
-- Factor Calculation Log Table (因子计算日志)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.factor_calculation_log (
    id BIGSERIAL PRIMARY KEY,
    factor_id VARCHAR(50) NOT NULL REFERENCES openfinance.factor_registry(factor_id),
    calculation_date DATE NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    total_stocks INTEGER,
    successful_stocks INTEGER,
    failed_stocks INTEGER,
    error_message TEXT,
    duration_ms INTEGER,
    parameters_used JSONB DEFAULT '{}',
    
    CONSTRAINT chk_calc_status CHECK (status IN ('running', 'completed', 'failed', 'partial'))
);

CREATE INDEX IF NOT EXISTS ix_factor_calc_log_factor ON openfinance.factor_calculation_log(factor_id);
CREATE INDEX IF NOT EXISTS ix_factor_calc_log_date ON openfinance.factor_calculation_log(calculation_date);
CREATE INDEX IF NOT EXISTS ix_factor_calc_log_status ON openfinance.factor_calculation_log(status);

-- ============================================
-- Factor Performance Statistics Table (因子绩效统计)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.factor_performance (
    id BIGSERIAL PRIMARY KEY,
    factor_id VARCHAR(50) NOT NULL REFERENCES openfinance.factor_registry(factor_id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    ic_mean DECIMAL(8,6),
    ic_std DECIMAL(8,6),
    ic_ir DECIMAL(8,6),
    ic_positive_ratio DECIMAL(5,4),
    rank_ic_mean DECIMAL(8,6),
    rank_ic_std DECIMAL(8,6),
    monotonicity DECIMAL(5,4),
    turnover_mean DECIMAL(8,4),
    coverage_mean DECIMAL(5,4),
    quantile_returns JSONB DEFAULT '{}',
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_factor_performance UNIQUE (factor_id, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS ix_factor_perf_factor ON openfinance.factor_performance(factor_id);

-- ============================================
-- Insert Builtin Factors (插入内置因子)
-- ============================================
INSERT INTO openfinance.factor_registry 
(factor_id, factor_code, factor_name, factor_type, factor_category, description, formula, parameters, dependencies, lookback_period, is_builtin, tags)
VALUES
('rsi_14', 'RSI', 'Relative Strength Index', 'technical', 'momentum', 
 'RSI measures the speed and magnitude of price movements', 
 'RSI = 100 - 100 / (1 + RS) where RS = Average Gain / Average Loss',
 '{"period": 14, "overbought": 70, "oversold": 30}',
 ARRAY['close'],
 14,
 TRUE,
 ARRAY['momentum', 'oscillator', 'overbought_oversold']),

('kdj_9_3_3', 'KDJ', 'KDJ Indicator', 'technical', 'momentum',
 'KDJ is a stochastic oscillator with K, D, J lines',
 'K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100; D = SMA(K, M1); J = 3*K - 2*D',
 '{"n": 9, "m1": 3, "m2": 3}',
 ARRAY['high', 'low', 'close'],
 9,
 TRUE,
 ARRAY['momentum', 'stochastic', 'oscillator']),

('macd_12_26_9', 'MACD', 'Moving Average Convergence Divergence', 'technical', 'trend',
 'MACD shows the relationship between two moving averages of price',
 'MACD = EMA(12) - EMA(26); Signal = EMA(MACD, 9); Histogram = MACD - Signal',
 '{"fast": 12, "slow": 26, "signal": 9}',
 ARRAY['close'],
 26,
 TRUE,
 ARRAY['trend', 'momentum', 'moving_average']),

('bollinger_20_2', 'BOLL', 'Bollinger Bands', 'technical', 'volatility',
 'Bollinger Bands measure market volatility and overbought/oversold conditions',
 'Middle = SMA(20); Upper = Middle + 2*StdDev; Lower = Middle - 2*StdDev',
 '{"period": 20, "std_dev": 2}',
 ARRAY['close'],
 20,
 TRUE,
 ARRAY['volatility', 'bands', 'overbought_oversold']),

('ma_5', 'MA5', '5-Day Moving Average', 'technical', 'trend',
 'Simple 5-day moving average of closing price',
 'MA5 = SMA(close, 5)',
 '{"period": 5}',
 ARRAY['close'],
 5,
 TRUE,
 ARRAY['trend', 'moving_average', 'short_term']),

('ma_20', 'MA20', '20-Day Moving Average', 'technical', 'trend',
 'Simple 20-day moving average of closing price',
 'MA20 = SMA(close, 20)',
 '{"period": 20}',
 ARRAY['close'],
 20,
 TRUE,
 ARRAY['trend', 'moving_average', 'medium_term']),

('volume_ratio', 'VOLR', 'Volume Ratio', 'technical', 'volume',
 'Ratio of current volume to average volume',
 'Volume Ratio = Current Volume / Average Volume(5)',
 '{"period": 5}',
 ARRAY['volume'],
 5,
 TRUE,
 ARRAY['volume', 'liquidity']),

('turnover_rate', 'TURN', 'Turnover Rate', 'technical', 'liquidity',
 'Percentage of shares traded in a day',
 'Turnover = Volume / Circulating Shares * 100',
 '{}',
 ARRAY['volume'],
 1,
 TRUE,
 ARRAY['liquidity', 'volume'])
ON CONFLICT (factor_id) DO UPDATE SET
    factor_name = EXCLUDED.factor_name,
    description = EXCLUDED.description,
    updated_at = NOW();

-- ============================================
-- Create Update Trigger for factor_registry
-- ============================================
CREATE OR REPLACE FUNCTION update_factor_registry_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_factor_registry ON openfinance.factor_registry;
CREATE TRIGGER trigger_update_factor_registry
    BEFORE UPDATE ON openfinance.factor_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_factor_registry_timestamp();

-- ============================================
-- Grant Permissions
-- ============================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA openfinance TO openfinance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA openfinance TO openfinance;
