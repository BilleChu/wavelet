-- OpenFinance Data Tables
-- Ensure UTF-8 encoding
SET client_encoding = 'UTF8';

-- Stock Daily Quote Table
CREATE TABLE IF NOT EXISTS openfinance.stock_daily_quote (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(50),
    trade_date DATE NOT NULL,
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
    CONSTRAINT uq_stock_quote_code_date UNIQUE (code, trade_date)
);

-- Stock Basic Info Table
CREATE TABLE IF NOT EXISTS openfinance.stock_basic (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
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

-- Financial Indicator Table
CREATE TABLE IF NOT EXISTS openfinance.stock_financial_indicator (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(50),
    report_date DATE NOT NULL,
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
    CONSTRAINT uq_fin_indicator_code_date UNIQUE (code, report_date)
);

-- Money Flow Table
CREATE TABLE IF NOT EXISTS openfinance.stock_money_flow (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(50),
    trade_date DATE NOT NULL,
    main_net_inflow DECIMAL(20,4),
    main_net_inflow_pct DECIMAL(8,4),
    super_large_net_inflow DECIMAL(20,4),
    large_net_inflow DECIMAL(20,4),
    medium_net_inflow DECIMAL(20,4),
    small_net_inflow DECIMAL(20,4),
    north_net_inflow DECIMAL(20,4),
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_money_flow_code_date UNIQUE (code, trade_date)
);

-- Macro Economic Table
CREATE TABLE IF NOT EXISTS openfinance.macro_economic (
    id BIGSERIAL PRIMARY KEY,
    indicator_code VARCHAR(50) NOT NULL,
    indicator_name VARCHAR(100) NOT NULL,
    value DECIMAL(20,4) NOT NULL,
    unit VARCHAR(20),
    period VARCHAR(20) NOT NULL,
    country VARCHAR(10) DEFAULT 'CN',
    source VARCHAR(50),
    published_at TIMESTAMP WITH TIME ZONE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_macro_indicator_period UNIQUE (indicator_code, period)
);

-- News Table
CREATE TABLE IF NOT EXISTS openfinance.news (
    id BIGSERIAL PRIMARY KEY,
    news_id VARCHAR(100) NOT NULL UNIQUE,
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

-- Factor Data Table
CREATE TABLE IF NOT EXISTS openfinance.factor_data (
    id BIGSERIAL PRIMARY KEY,
    factor_id VARCHAR(50) NOT NULL,
    factor_name VARCHAR(100),
    factor_category VARCHAR(50),
    code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    factor_value DECIMAL(20,8) NOT NULL,
    factor_rank INTEGER,
    factor_percentile DECIMAL(8,4),
    neutralized BOOLEAN DEFAULT FALSE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_factor_code_date UNIQUE (factor_id, code, trade_date)
);

-- Entities Table (Knowledge Graph)
CREATE TABLE IF NOT EXISTS openfinance.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id VARCHAR(255) UNIQUE NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    name VARCHAR(500) NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    description TEXT,
    code VARCHAR(50),
    industry VARCHAR(100),
    market VARCHAR(50),
    market_cap DECIMAL(20,2),
    properties JSONB DEFAULT '{}',
    source VARCHAR(100),
    confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Relations Table (Knowledge Graph)
CREATE TABLE IF NOT EXISTS openfinance.relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relation_id VARCHAR(255) UNIQUE NOT NULL,
    source_entity_id VARCHAR(255) NOT NULL REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE,
    target_entity_id VARCHAR(255) NOT NULL REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE,
    relation_type VARCHAR(100) NOT NULL,
    weight DECIMAL(3,2) DEFAULT 1.0,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    evidence TEXT,
    properties JSONB DEFAULT '{}',
    source VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(source_entity_id, target_entity_id, relation_type)
);

-- Create Indexes
CREATE INDEX IF NOT EXISTS ix_stock_quote_code ON openfinance.stock_daily_quote(code);
CREATE INDEX IF NOT EXISTS ix_stock_quote_date ON openfinance.stock_daily_quote(trade_date);
CREATE INDEX IF NOT EXISTS ix_stock_quote_code_date ON openfinance.stock_daily_quote(code, trade_date DESC);

CREATE INDEX IF NOT EXISTS ix_fin_indicator_code ON openfinance.stock_financial_indicator(code);
CREATE INDEX IF NOT EXISTS ix_fin_indicator_date ON openfinance.stock_financial_indicator(report_date);

CREATE INDEX IF NOT EXISTS ix_money_flow_code ON openfinance.stock_money_flow(code);
CREATE INDEX IF NOT EXISTS ix_money_flow_date ON openfinance.stock_money_flow(trade_date);

CREATE INDEX IF NOT EXISTS ix_macro_indicator ON openfinance.macro_economic(indicator_code);
CREATE INDEX IF NOT EXISTS ix_macro_period ON openfinance.macro_economic(period);

CREATE INDEX IF NOT EXISTS ix_news_source ON openfinance.news(source);
CREATE INDEX IF NOT EXISTS ix_news_published ON openfinance.news(published_at DESC);

CREATE INDEX IF NOT EXISTS ix_factor_id ON openfinance.factor_data(factor_id);
CREATE INDEX IF NOT EXISTS ix_factor_code ON openfinance.factor_data(code);
CREATE INDEX IF NOT EXISTS ix_factor_date ON openfinance.factor_data(trade_date);

CREATE INDEX IF NOT EXISTS ix_entity_type ON openfinance.entities(entity_type);
CREATE INDEX IF NOT EXISTS ix_entity_code ON openfinance.entities(code);
CREATE INDEX IF NOT EXISTS ix_entity_industry ON openfinance.entities(industry);

CREATE INDEX IF NOT EXISTS ix_relation_source ON openfinance.relations(source_entity_id);
CREATE INDEX IF NOT EXISTS ix_relation_target ON openfinance.relations(target_entity_id);
CREATE INDEX IF NOT EXISTS ix_relation_type ON openfinance.relations(relation_type);

-- Insert sample entities for knowledge graph
INSERT INTO openfinance.entities (entity_id, entity_type, name, code, industry, market, properties, source, confidence) VALUES
('company_600000', 'company', '浦发银行', '600000', '银行', '上海证券交易所', '{"market_cap": 250000000000, "pe_ratio": 5.2}', 'akshare', 1.0),
('company_000001', 'company', '平安银行', '000001', '银行', '深圳证券交易所', '{"market_cap": 180000000000, "pe_ratio": 6.1}', 'akshare', 1.0),
('company_601398', 'company', '工商银行', '601398', '银行', '上海证券交易所', '{"market_cap": 1500000000000, "pe_ratio": 4.8}', 'akshare', 1.0),
('company_600519', 'company', '贵州茅台', '600519', '白酒', '上海证券交易所', '{"market_cap": 2200000000000, "pe_ratio": 35.2}', 'akshare', 1.0),
('company_000858', 'company', '五粮液', '000858', '白酒', '深圳证券交易所', '{"market_cap": 600000000000, "pe_ratio": 28.5}', 'akshare', 1.0),
('company_002594', 'company', '比亚迪', '002594', '汽车', '深圳证券交易所', '{"market_cap": 700000000000, "pe_ratio": 45.2}', 'akshare', 1.0),
('company_300750', 'company', '宁德时代', '300750', '新能源', '深圳证券交易所', '{"market_cap": 900000000000, "pe_ratio": 25.8}', 'akshare', 1.0),
('industry_bank', 'industry', '银行', NULL, NULL, NULL, '{"level": 1}', 'system', 1.0),
('industry_baijiu', 'industry', '白酒', NULL, NULL, NULL, '{"level": 1}', 'system', 1.0),
('industry_xinnengyuan', 'industry', '新能源', NULL, NULL, NULL, '{"level": 1}', 'system', 1.0)
ON CONFLICT (entity_id) DO NOTHING;

-- Insert sample relations
INSERT INTO openfinance.relations (relation_id, source_entity_id, target_entity_id, relation_type, weight, confidence, source) VALUES
('rel_001', 'company_600000', 'industry_bank', 'belongs_to', 1.0, 1.0, 'system'),
('rel_002', 'company_000001', 'industry_bank', 'belongs_to', 1.0, 1.0, 'system'),
('rel_003', 'company_601398', 'industry_bank', 'belongs_to', 1.0, 1.0, 'system'),
('rel_004', 'company_600519', 'industry_baijiu', 'belongs_to', 1.0, 1.0, 'system'),
('rel_005', 'company_000858', 'industry_baijiu', 'belongs_to', 1.0, 1.0, 'system'),
('rel_006', 'company_002594', 'industry_xinnengyuan', 'belongs_to', 1.0, 1.0, 'system'),
('rel_007', 'company_300750', 'industry_xinnengyuan', 'belongs_to', 1.0, 1.0, 'system')
ON CONFLICT (source_entity_id, target_entity_id, relation_type) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA openfinance TO openfinance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA openfinance TO openfinance;
