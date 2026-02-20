-- Database Index Optimization Script
-- Run this script to create optimized indexes for the OpenFinance database

-- Ensure schema exists
CREATE SCHEMA IF NOT EXISTS openfinance;

-- ============================================
-- Stock Daily Quote Table Indexes
-- ============================================

-- Primary lookup: by code and date range
CREATE INDEX IF NOT EXISTS ix_stock_quote_code_date_desc 
    ON openfinance.stock_daily_quote (code, trade_date DESC);

-- Time-series queries: by date range
CREATE INDEX IF NOT EXISTS ix_stock_quote_date_desc 
    ON openfinance.stock_daily_quote (trade_date DESC);

-- Covering index for common queries
CREATE INDEX IF NOT EXISTS ix_stock_quote_covering 
    ON openfinance.stock_daily_quote (code, trade_date) 
    INCLUDE (open, high, low, close, volume, amount);

-- Partial index for active stocks (recent data only)
CREATE INDEX IF NOT EXISTS ix_stock_quote_recent 
    ON openfinance.stock_daily_quote (code, trade_date DESC) 
    WHERE trade_date > CURRENT_DATE - INTERVAL '1 year';

-- ============================================
-- Stock Basic Table Indexes
-- ============================================

-- Industry-based queries
CREATE INDEX IF NOT EXISTS ix_stock_basic_industry 
    ON openfinance.stock_basic (industry) 
    WHERE industry IS NOT NULL;

-- Market cap ranking
CREATE INDEX IF NOT EXISTS ix_stock_basic_market_cap_desc 
    ON openfinance.stock_basic (market_cap DESC) 
    WHERE market_cap IS NOT NULL;

-- ============================================
-- Financial Indicator Table Indexes
-- ============================================

-- Report date based queries
CREATE INDEX IF NOT EXISTS ix_fin_indicator_code_date_desc 
    ON openfinance.stock_financial_indicator (code, report_date DESC);

-- ROE ranking queries
CREATE INDEX IF NOT EXISTS ix_fin_indicator_roe_desc 
    ON openfinance.stock_financial_indicator (roe DESC) 
    WHERE roe IS NOT NULL;

-- ============================================
-- Money Flow Table Indexes
-- ============================================

-- Code and date lookup
CREATE INDEX IF NOT EXISTS ix_money_flow_code_date_desc 
    ON openfinance.stock_money_flow (code, trade_date DESC);

-- Main inflow ranking
CREATE INDEX IF NOT EXISTS ix_money_flow_main_inflow_desc 
    ON openfinance.stock_money_flow (main_net_inflow DESC) 
    WHERE main_net_inflow IS NOT NULL;

-- ============================================
-- News Table Indexes
-- ============================================

-- Full-text search on title
CREATE INDEX IF NOT EXISTS ix_news_title_gin 
    ON openfinance.news USING gin(to_tsvector('simple', title));

-- Source and date queries
CREATE INDEX IF NOT EXISTS ix_news_source_date 
    ON openfinance.news (source, published_at DESC);

-- ============================================
-- Macro Economic Table Indexes
-- ============================================

-- Indicator code and period lookup
CREATE INDEX IF NOT EXISTS ix_macro_indicator_period 
    ON openfinance.macro_economic (indicator_code, period DESC);

-- Country-based queries
CREATE INDEX IF NOT EXISTS ix_macro_country 
    ON openfinance.macro_economic (country) 
    WHERE country IS NOT NULL;

-- ============================================
-- Factor Data Table Indexes
-- ============================================

-- Factor and date lookup
CREATE INDEX IF NOT EXISTS ix_factor_code_date 
    ON openfinance.factor_data (factor_id, code, trade_date DESC);

-- Factor category queries
CREATE INDEX IF NOT EXISTS ix_factor_category_date 
    ON openfinance.factor_data (factor_category, trade_date DESC) 
    WHERE factor_category IS NOT NULL;

-- Factor value ranking
CREATE INDEX IF NOT EXISTS ix_factor_value_desc 
    ON openfinance.factor_data (factor_id, trade_date, factor_value DESC);

-- ============================================
-- Knowledge Graph Tables Indexes
-- ============================================

-- Entity type queries
CREATE INDEX IF NOT EXISTS ix_entity_type_name 
    ON openfinance.entities (entity_type, name);

-- Entity search by name
CREATE INDEX IF NOT EXISTS ix_entity_name_gin 
    ON openfinance.entities USING gin(to_tsvector('simple', name));

-- Entity search by code
CREATE INDEX IF NOT EXISTS ix_entity_code 
    ON openfinance.entities (code) 
    WHERE code IS NOT NULL;

-- Relation queries
CREATE INDEX IF NOT EXISTS ix_relation_source_type 
    ON openfinance.relations (source_entity_id, relation_type);

CREATE INDEX IF NOT EXISTS ix_relation_target_type 
    ON openfinance.relations (target_entity_id, relation_type);

-- ============================================
-- ESG Rating Table Indexes
-- ============================================

CREATE INDEX IF NOT EXISTS ix_esg_code_date 
    ON openfinance.esg_rating (code, rating_date DESC);

CREATE INDEX IF NOT EXISTS ix_esg_agency 
    ON openfinance.esg_rating (rating_agency, rating_date DESC);

-- ============================================
-- Event Table Indexes
-- ============================================

CREATE INDEX IF NOT EXISTS ix_event_type_date 
    ON openfinance.events (event_type, event_date DESC);

CREATE INDEX IF NOT EXISTS ix_event_date_desc 
    ON openfinance.events (event_date DESC);

-- ============================================
-- Maintenance
-- ============================================

-- Analyze tables for query planner
ANALYZE openfinance.stock_daily_quote;
ANALYZE openfinance.stock_basic;
ANALYZE openfinance.stock_financial_indicator;
ANALYZE openfinance.stock_money_flow;
ANALYZE openfinance.news;
ANALYZE openfinance.macro_economic;
ANALYZE openfinance.factor_data;
ANALYZE openfinance.entities;
ANALYZE openfinance.relations;
ANALYZE openfinance.esg_rating;
ANALYZE openfinance.events;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA openfinance TO openfinance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA openfinance TO openfinance;
