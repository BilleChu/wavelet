-- Optimized Stock Data Tables
-- Removes redundancy and improves query performance
-- Ensure UTF-8 encoding
SET client_encoding = 'UTF8';

-- ============================================
-- Stock Master Table (股票主表 - 唯一数据源)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.stock_master (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    name_abbr VARCHAR(20),
    industry_code VARCHAR(20),
    industry_name VARCHAR(50),
    sector_code VARCHAR(20),
    sector_name VARCHAR(50),
    market VARCHAR(20) NOT NULL,
    market_code VARCHAR(10),
    list_date DATE,
    delist_date DATE,
    status VARCHAR(10) DEFAULT 'L',
    is_hs300 BOOLEAN DEFAULT FALSE,
    is_zz500 BOOLEAN DEFAULT FALSE,
    is_sz50 BOOLEAN DEFAULT FALSE,
    total_shares DECIMAL(20,4),
    circulating_shares DECIMAL(20,4),
    total_assets DECIMAL(20,4),
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_stock_status CHECK (status IN ('L', 'D', 'P', 'S'))
);

CREATE INDEX IF NOT EXISTS ix_stock_master_industry ON openfinance.stock_master(industry_code);
CREATE INDEX IF NOT EXISTS ix_stock_master_sector ON openfinance.stock_master(sector_code);
CREATE INDEX IF NOT EXISTS ix_stock_master_market ON openfinance.stock_master(market);
CREATE INDEX IF NOT EXISTS ix_stock_master_status ON openfinance.stock_master(status);
CREATE INDEX IF NOT EXISTS ix_stock_master_name ON openfinance.stock_master USING gin(to_tsvector('simple', name));

COMMENT ON TABLE openfinance.stock_master IS 'Master table for stock basic info - single source of truth';

-- ============================================
-- Stock Quote Table (优化行情表 - 移除冗余字段)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.stock_quote (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    pre_close DECIMAL(12,4),
    change_amt DECIMAL(12,4),
    change_pct DECIMAL(8,4),
    volume BIGINT,
    amount DECIMAL(20,4),
    turnover_rate DECIMAL(8,4),
    amplitude DECIMAL(8,4),
    total_market_cap DECIMAL(20,4),
    circulating_market_cap DECIMAL(20,4),
    pe_ttm DECIMAL(12,4),
    pb DECIMAL(12,4),
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_stock_quote UNIQUE (code, trade_date),
    CONSTRAINT fk_stock_quote_code FOREIGN KEY (code) REFERENCES openfinance.stock_master(code) ON DELETE CASCADE
);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS ix_stock_quote_date ON openfinance.stock_quote(trade_date DESC);
CREATE INDEX IF NOT EXISTS ix_stock_quote_code_date ON openfinance.stock_quote(code, trade_date DESC);
CREATE INDEX IF NOT EXISTS ix_stock_quote_date_code ON openfinance.stock_quote(trade_date DESC, code);

-- Partial index for active stocks
CREATE INDEX IF NOT EXISTS ix_stock_quote_active ON openfinance.stock_quote(code, trade_date DESC) 
WHERE volume > 0;

COMMENT ON TABLE openfinance.stock_quote IS 'Optimized stock quote table - references stock_master for name';

-- ============================================
-- Stock Quote Aggregate Table (行情聚合表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.stock_quote_daily_agg (
    trade_date DATE PRIMARY KEY,
    total_stocks INTEGER,
    advancing INTEGER,
    declining INTEGER,
    unchanged INTEGER,
    limit_up INTEGER,
    limit_down INTEGER,
    total_volume BIGINT,
    total_amount DECIMAL(24,4),
    avg_change_pct DECIMAL(8,4),
    market_breadth DECIMAL(8,4),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE openfinance.stock_quote_daily_agg IS 'Pre-calculated daily market aggregates';

-- ============================================
-- Stock Intraday Quote Table (日内行情表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.stock_intraday_quote (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    trade_time TIME NOT NULL,
    price DECIMAL(12,4),
    volume BIGINT,
    amount DECIMAL(20,4),
    bid_price1 DECIMAL(12,4),
    bid_volume1 BIGINT,
    ask_price1 DECIMAL(12,4),
    ask_volume1 BIGINT,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_intraday_quote UNIQUE (code, trade_date, trade_time)
);

CREATE INDEX IF NOT EXISTS ix_intraday_quote_code_date ON openfinance.stock_intraday_quote(code, trade_date);
CREATE INDEX IF NOT EXISTS ix_intraday_quote_time ON openfinance.stock_intraday_quote(trade_date, trade_time);

-- ============================================
-- Industry Classification Table (行业分类表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.industry_classification (
    industry_code VARCHAR(20) PRIMARY KEY,
    industry_name VARCHAR(50) NOT NULL,
    parent_code VARCHAR(20),
    level INTEGER DEFAULT 1,
    classification_type VARCHAR(20) DEFAULT 'sw',
    stock_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_industry_parent FOREIGN KEY (parent_code) REFERENCES openfinance.industry_classification(industry_code)
);

CREATE INDEX IF NOT EXISTS ix_industry_parent ON openfinance.industry_classification(parent_code);
CREATE INDEX IF NOT EXISTS ix_industry_type ON openfinance.industry_classification(classification_type);

-- ============================================
-- Sector Classification Table (板块分类表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.sector_classification (
    sector_code VARCHAR(20) PRIMARY KEY,
    sector_name VARCHAR(50) NOT NULL,
    sector_type VARCHAR(20) DEFAULT 'concept',
    stock_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Stock Industry Mapping (股票行业映射)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.stock_industry_map (
    code VARCHAR(10) NOT NULL REFERENCES openfinance.stock_master(code) ON DELETE CASCADE,
    industry_code VARCHAR(20) NOT NULL REFERENCES openfinance.industry_classification(industry_code),
    is_primary BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (code, industry_code)
);

-- ============================================
-- Stock Sector Mapping (股票板块映射)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.stock_sector_map (
    code VARCHAR(10) NOT NULL REFERENCES openfinance.stock_master(code) ON DELETE CASCADE,
    sector_code VARCHAR(20) NOT NULL REFERENCES openfinance.sector_classification(sector_code),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (code, sector_code)
);

-- ============================================
-- Migration: Copy data from stock_basic to stock_master
-- ============================================
INSERT INTO openfinance.stock_master (code, name, industry_code, industry_name, market, list_date, status, total_shares, circulating_shares)
SELECT 
    code,
    name,
    NULL as industry_code,
    industry as industry_name,
    COALESCE(market, 
        CASE 
            WHEN code LIKE '6%' THEN '上海证券交易所'
            WHEN code LIKE '0%' OR code LIKE '3%' THEN '深圳证券交易所'
            WHEN code LIKE '68%' THEN '上海证券交易所科创板'
            ELSE '未知'
        END
    ) as market,
    listing_date as list_date,
    COALESCE(status, 'L') as status,
    NULL as total_shares,
    NULL as circulating_shares
FROM openfinance.stock_basic
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    industry_name = EXCLUDED.industry_name,
    market = EXCLUDED.market,
    updated_at = NOW();

-- ============================================
-- Create Update Trigger
-- ============================================
CREATE OR REPLACE FUNCTION update_stock_master_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_stock_master ON openfinance.stock_master;
CREATE TRIGGER trigger_update_stock_master
    BEFORE UPDATE ON openfinance.stock_master
    FOR EACH ROW
    EXECUTE FUNCTION update_stock_master_timestamp();

-- ============================================
-- Create Views for Backward Compatibility
-- ============================================
CREATE OR REPLACE VIEW openfinance.stock_basic_v AS
SELECT 
    sm.code,
    sm.name,
    sm.industry_name as industry,
    sm.sector_name as sector,
    sm.market,
    sm.list_date as listing_date,
    sm.status,
    sm.total_shares,
    sm.circulating_shares,
    sm.updated_at
FROM openfinance.stock_master sm;

CREATE OR REPLACE VIEW openfinance.stock_daily_quote_v AS
SELECT 
    sq.code,
    sm.name,
    sq.trade_date,
    sq.open,
    sq.high,
    sq.low,
    sq.close,
    sq.pre_close,
    sq.change_amt as change,
    sq.change_pct,
    sq.volume,
    sq.amount,
    sq.turnover_rate,
    sq.amplitude,
    sq.total_market_cap as market_cap,
    sq.circulating_market_cap,
    sq.collected_at
FROM openfinance.stock_quote sq
LEFT JOIN openfinance.stock_master sm ON sq.code = sm.code;

-- ============================================
-- Grant Permissions
-- ============================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA openfinance TO openfinance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA openfinance TO openfinance;
