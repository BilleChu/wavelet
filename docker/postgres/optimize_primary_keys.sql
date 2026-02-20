-- Primary Key Optimization Script
-- Strategy: Use natural/business keys as primary keys where appropriate
-- Benefits: Better query performance, reduced storage, simpler data model

SET client_encoding = 'UTF8';

-- ============================================================================
-- 1. stock_daily_quote: Use composite primary key (code, trade_date)
-- ============================================================================
-- This is a time-series table where queries always filter by code and date
-- Composite PK eliminates the redundant id column and unique constraint

BEGIN;

-- Create new table with optimized structure
CREATE TABLE IF NOT EXISTS openfinance.stock_daily_quote_new (
    code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    name VARCHAR(50),
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    pre_close DECIMAL(12,4),
    change DECIMAL(12,4),
    change_pct DECIMAL(8,4),
    volume BIGINT,
    amount DECIMAL(20,4),
    turnover_rate DECIMAL(8,4),
    amplitude DECIMAL(8,4),
    market_cap DECIMAL(20,4),
    circulating_market_cap DECIMAL(20,4),
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (code, trade_date)
);

-- Migrate data
INSERT INTO openfinance.stock_daily_quote_new 
SELECT code, trade_date, name, open, high, low, close, pre_close, 
       change, change_pct, volume, amount, turnover_rate, amplitude, 
       market_cap, circulating_market_cap, collected_at
FROM openfinance.stock_daily_quote
ON CONFLICT (code, trade_date) DO NOTHING;

-- Drop old table and rename
DROP TABLE IF EXISTS openfinance.stock_daily_quote CASCADE;
ALTER TABLE openfinance.stock_daily_quote_new RENAME TO stock_daily_quote;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS ix_stock_quote_date ON openfinance.stock_daily_quote(trade_date DESC);
CREATE INDEX IF NOT EXISTS ix_stock_quote_code_date ON openfinance.stock_daily_quote(code, trade_date DESC);

COMMIT;

-- ============================================================================
-- 2. stock_basic: Use code as primary key (natural key)
-- ============================================================================
-- Stock code is the natural identifier, no need for surrogate key

BEGIN;

CREATE TABLE IF NOT EXISTS openfinance.stock_basic_new (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50),
    industry VARCHAR(100),
    market VARCHAR(50),
    list_date DATE,
    total_shares DECIMAL(20,4),
    circulating_shares DECIMAL(20,4),
    market_cap DECIMAL(20,4),
    pe_ratio DECIMAL(12,4),
    pb_ratio DECIMAL(12,4),
    properties JSONB DEFAULT '{}',
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO openfinance.stock_basic_new 
SELECT code, name, industry, market, list_date, total_shares, 
       circulating_shares, market_cap, pe_ratio, pb_ratio, 
       properties, collected_at, updated_at
FROM openfinance.stock_basic
ON CONFLICT (code) DO NOTHING;

DROP TABLE IF EXISTS openfinance.stock_basic CASCADE;
ALTER TABLE openfinance.stock_basic_new RENAME TO stock_basic;

CREATE INDEX IF NOT EXISTS ix_stock_basic_industry ON openfinance.stock_basic(industry);
CREATE INDEX IF NOT EXISTS ix_stock_basic_market ON openfinance.stock_basic(market);

COMMIT;

-- ============================================================================
-- 3. stock_financial_indicator: Use composite primary key (code, report_date)
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS openfinance.stock_financial_indicator_new (
    code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    name VARCHAR(50),
    eps DECIMAL(12,4),
    bps DECIMAL(12,4),
    roe DECIMAL(8,4),
    roa DECIMAL(8,4),
    gross_margin DECIMAL(8,4),
    net_margin DECIMAL(8,4),
    debt_ratio DECIMAL(8,4),
    current_ratio DECIMAL(8,4),
    quick_ratio DECIMAL(8,4),
    revenue DECIMAL(20,4),
    net_profit DECIMAL(20,4),
    revenue_yoy DECIMAL(8,4),
    net_profit_yoy DECIMAL(8,4),
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (code, report_date)
);

INSERT INTO openfinance.stock_financial_indicator_new 
SELECT code, report_date, name, eps, bps, roe, roa, gross_margin, net_margin,
       debt_ratio, current_ratio, quick_ratio, revenue, net_profit,
       revenue_yoy, net_profit_yoy, collected_at
FROM openfinance.stock_financial_indicator
ON CONFLICT (code, report_date) DO NOTHING;

DROP TABLE IF EXISTS openfinance.stock_financial_indicator CASCADE;
ALTER TABLE openfinance.stock_financial_indicator_new RENAME TO stock_financial_indicator;

CREATE INDEX IF NOT EXISTS ix_fin_indicator_date ON openfinance.stock_financial_indicator(report_date DESC);

COMMIT;

-- ============================================================================
-- 4. stock_money_flow: Use composite primary key (code, trade_date)
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS openfinance.stock_money_flow_new (
    code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    name VARCHAR(50),
    main_net_inflow DECIMAL(20,4),
    main_net_inflow_pct DECIMAL(8,4),
    super_large_net_inflow DECIMAL(20,4),
    large_net_inflow DECIMAL(20,4),
    medium_net_inflow DECIMAL(20,4),
    small_net_inflow DECIMAL(20,4),
    north_net_inflow DECIMAL(20,4),
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (code, trade_date)
);

INSERT INTO openfinance.stock_money_flow_new 
SELECT code, trade_date, name, main_net_inflow, main_net_inflow_pct,
       super_large_net_inflow, large_net_inflow, medium_net_inflow,
       small_net_inflow, north_net_inflow, collected_at
FROM openfinance.stock_money_flow
ON CONFLICT (code, trade_date) DO NOTHING;

DROP TABLE IF EXISTS openfinance.stock_money_flow CASCADE;
ALTER TABLE openfinance.stock_money_flow_new RENAME TO stock_money_flow;

CREATE INDEX IF NOT EXISTS ix_money_flow_date ON openfinance.stock_money_flow(trade_date DESC);

COMMIT;

-- ============================================================================
-- 5. macro_economic: Use composite primary key (indicator_code, period)
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS openfinance.macro_economic_new (
    indicator_code VARCHAR(50) NOT NULL,
    period VARCHAR(20) NOT NULL,
    indicator_name VARCHAR(100) NOT NULL,
    value DECIMAL(20,4) NOT NULL,
    unit VARCHAR(20),
    country VARCHAR(10) DEFAULT 'CN',
    source VARCHAR(50),
    published_at TIMESTAMP WITH TIME ZONE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (indicator_code, period)
);

INSERT INTO openfinance.macro_economic_new 
SELECT indicator_code, period, indicator_name, value, unit, country,
       source, published_at, collected_at
FROM openfinance.macro_economic
ON CONFLICT (indicator_code, period) DO NOTHING;

DROP TABLE IF EXISTS openfinance.macro_economic CASCADE;
ALTER TABLE openfinance.macro_economic_new RENAME TO macro_economic;

CREATE INDEX IF NOT EXISTS ix_macro_period ON openfinance.macro_economic(period);

COMMIT;

-- ============================================================================
-- 6. news: Use news_id as primary key (natural key)
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS openfinance.news_new (
    news_id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    source VARCHAR(50) NOT NULL,
    category VARCHAR(50),
    keywords TEXT[],
    sentiment DECIMAL(4,3),
    related_stocks VARCHAR(10)[],
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO openfinance.news_new 
SELECT news_id, title, content, source, category, keywords, sentiment,
       related_stocks, published_at, collected_at
FROM openfinance.news
ON CONFLICT (news_id) DO NOTHING;

DROP TABLE IF EXISTS openfinance.news CASCADE;
ALTER TABLE openfinance.news_new RENAME TO news;

CREATE INDEX IF NOT EXISTS ix_news_source ON openfinance.news(source);
CREATE INDEX IF NOT EXISTS ix_news_published ON openfinance.news(published_at DESC);
CREATE INDEX IF NOT EXISTS ix_news_category ON openfinance.news(category);

COMMIT;

-- ============================================================================
-- 7. factor_data: Use composite primary key (factor_id, code, trade_date)
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS openfinance.factor_data_new (
    factor_id VARCHAR(50) NOT NULL,
    code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    factor_name VARCHAR(100),
    factor_category VARCHAR(50),
    factor_value DECIMAL(20,8) NOT NULL,
    factor_rank INTEGER,
    factor_percentile DECIMAL(8,4),
    neutralized BOOLEAN DEFAULT FALSE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (factor_id, code, trade_date)
);

INSERT INTO openfinance.factor_data_new 
SELECT factor_id, code, trade_date, factor_name, factor_category,
       factor_value, factor_rank, factor_percentile, neutralized, collected_at
FROM openfinance.factor_data
ON CONFLICT (factor_id, code, trade_date) DO NOTHING;

DROP TABLE IF EXISTS openfinance.factor_data CASCADE;
ALTER TABLE openfinance.factor_data_new RENAME TO factor_data;

CREATE INDEX IF NOT EXISTS ix_factor_code ON openfinance.factor_data(code);
CREATE INDEX IF NOT EXISTS ix_factor_date ON openfinance.factor_data(trade_date DESC);
CREATE INDEX IF NOT EXISTS ix_factor_category ON openfinance.factor_data(factor_category);

COMMIT;

-- ============================================================================
-- 8. entities: Keep UUID primary key (good for distributed systems)
-- ============================================================================

-- entities table already uses UUID which is appropriate for knowledge graph
-- No changes needed, but add additional indexes for performance

CREATE INDEX IF NOT EXISTS ix_entity_name ON openfinance.entities(name);
CREATE INDEX IF NOT EXISTS ix_entity_name_gin ON openfinance.entities USING gin(to_tsvector('simple', name));
CREATE INDEX IF NOT EXISTS ix_entity_properties ON openfinance.entities USING gin(properties);

-- ============================================================================
-- 9. relations: Keep UUID primary key
-- ============================================================================

-- relations table already uses UUID which is appropriate
-- Add composite index for common query patterns

CREATE INDEX IF NOT EXISTS ix_relation_source_type ON openfinance.relations(source_entity_id, relation_type);
CREATE INDEX IF NOT EXISTS ix_relation_target_type ON openfinance.relations(target_entity_id, relation_type);

-- ============================================================================
-- Grant permissions
-- ============================================================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA openfinance TO openfinance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA openfinance TO openfinance;

-- ============================================================================
-- Summary of changes:
-- ============================================================================
-- Table                    | Old PK           | New PK
-- -------------------------|------------------|---------------------------
-- stock_daily_quote        | BIGSERIAL id     | (code, trade_date)
-- stock_basic              | BIGSERIAL id     | code
-- stock_financial_indicator| BIGSERIAL id     | (code, report_date)
-- stock_money_flow         | BIGSERIAL id     | (code, trade_date)
-- macro_economic           | BIGSERIAL id     | (indicator_code, period)
-- news                     | BIGSERIAL id     | news_id
-- factor_data              | BIGSERIAL id     | (factor_id, code, trade_date)
-- entities                 | UUID             | UUID (no change)
-- relations                | UUID             | UUID (no change)
-- ============================================================================
