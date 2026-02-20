-- Entity and Knowledge Graph Tables for OpenFinance
-- Ensure UTF-8 encoding
SET client_encoding = 'UTF8';

-- Create entities table
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
    market_cap DECIMAL(20, 2),
    properties JSONB DEFAULT '{}',
    source VARCHAR(100),
    confidence DECIMAL(3, 2) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create relations table
CREATE TABLE IF NOT EXISTS openfinance.relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relation_id VARCHAR(255) UNIQUE NOT NULL,
    source_entity_id VARCHAR(255) NOT NULL REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE,
    target_entity_id VARCHAR(255) NOT NULL REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE,
    relation_type VARCHAR(100) NOT NULL,
    weight DECIMAL(3, 2) DEFAULT 1.0,
    confidence DECIMAL(3, 2) DEFAULT 1.0,
    evidence TEXT,
    properties JSONB DEFAULT '{}',
    source VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_entity_id, target_entity_id, relation_type)
);

-- Create entity mentions table (for tracking where entities appear)
CREATE TABLE IF NOT EXISTS openfinance.entity_mentions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id VARCHAR(255) NOT NULL REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_entities_type ON openfinance.entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON openfinance.entities USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_entities_code ON openfinance.entities(code);
CREATE INDEX IF NOT EXISTS idx_entities_industry ON openfinance.entities(industry);
CREATE INDEX IF NOT EXISTS idx_relations_source ON openfinance.relations(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON openfinance.relations(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON openfinance.relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_entity_mentions_entity ON openfinance.entity_mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_mentions_source ON openfinance.entity_mentions(source_type, source_id);

-- Create triggers for updated_at
CREATE TRIGGER update_entities_updated_at
    BEFORE UPDATE ON openfinance.entities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_relations_updated_at
    BEFORE UPDATE ON openfinance.relations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing
INSERT INTO openfinance.entities (entity_id, entity_type, name, code, industry, market, properties, source, confidence) VALUES
('company_600000', 'company', '浦发银行', '600000', '银行', '上海证券交易所', '{"market_cap": 250000000000, "pe_ratio": 5.2, "pb_ratio": 0.5}', 'akshare', 1.0),
('company_000001', 'company', '平安银行', '000001', '银行', '深圳证券交易所', '{"market_cap": 180000000000, "pe_ratio": 6.1, "pb_ratio": 0.6}', 'akshare', 1.0),
('company_601398', 'company', '工商银行', '601398', '银行', '上海证券交易所', '{"market_cap": 1500000000000, "pe_ratio": 4.8, "pb_ratio": 0.5}', 'akshare', 1.0),
('company_601288', 'company', '农业银行', '601288', '银行', '上海证券交易所', '{"market_cap": 1200000000000, "pe_ratio": 4.5, "pb_ratio": 0.5}', 'akshare', 1.0),
('company_000002', 'company', '万科A', '000002', '房地产', '深圳证券交易所', '{"market_cap": 200000000000, "pe_ratio": 8.5}', 'akshare', 1.0),
('company_600519', 'company', '贵州茅台', '600519', '白酒', '上海证券交易所', '{"market_cap": 2200000000000, "pe_ratio": 35.2}', 'akshare', 1.0),
('company_000858', 'company', '五粮液', '000858', '白酒', '深圳证券交易所', '{"market_cap": 600000000000, "pe_ratio": 28.5}', 'akshare', 1.0),
('company_002594', 'company', '比亚迪', '002594', '汽车', '深圳证券交易所', '{"market_cap": 700000000000, "pe_ratio": 45.2}', 'akshare', 1.0),
('company_300750', 'company', '宁德时代', '300750', '新能源', '深圳证券交易所', '{"market_cap": 900000000000, "pe_ratio": 25.8}', 'akshare', 1.0),
('company_002475', 'company', '立讯精密', '002475', '电子', '深圳证券交易所', '{"market_cap": 300000000000, "pe_ratio": 22.5}', 'akshare', 1.0),
('company_002024', 'company', '万象生活', '002024', '零售', '深圳证券交易所', '{"market_cap": 50000000000, "pe_ratio": 15.2}', 'akshare', 1.0),
('company_601318', 'company', '中国平安', '601318', '保险', '上海证券交易所', '{"market_cap": 800000000000, "pe_ratio": 8.5}', 'akshare', 1.0),
('company_600036', 'company', '招商银行', '600036', '银行', '上海证券交易所', '{"market_cap": 900000000000, "pe_ratio": 6.2, "pb_ratio": 0.8}', 'akshare', 1.0),
('industry_bank', 'industry', '银行', NULL, NULL, NULL, '{"level": 1, "companies_count": 42}', 'system', 1.0),
('industry_baijiu', 'industry', '白酒', NULL, NULL, NULL, '{"level": 1, "companies_count": 20}', 'system', 1.0),
('industry_xinnengyuan', 'industry', '新能源', NULL, NULL, NULL, '{"level": 1, "companies_count": 85}', 'system', 1.0),
('concept_rengongzhineng', 'concept', '人工智能', NULL, NULL, NULL, '{"related_stocks": ["002475", "300750"]}', 'system', 1.0),
('concept_tan zhonghe', 'concept', '碳中和', NULL, NULL, NULL, '{"related_stocks": ["002594", "300750"]}', 'system', 1.0),
('person_buffett', 'person', '巴菲特', NULL, NULL, NULL, '{"title": "CEO", "organization": "伯克希尔哈撒韦"}', 'system', 1.0),
('person_dalio', 'person', '达里奥', NULL, NULL, NULL, '{"title": "创始人", "organization": "桥水基金"}', 'system', 1.0)
ON CONFLICT (entity_id) DO NOTHING;

-- Insert sample relations
INSERT INTO openfinance.relations (relation_id, source_entity_id, target_entity_id, relation_type, weight, confidence, source) VALUES
('rel_001', 'company_600000', 'industry_bank', 'belongs_to', 1.0, 1.0, 'system'),
('rel_002', 'company_000001', 'industry_bank', 'belongs_to', 1.0, 1.0, 'system'),
('rel_003', 'company_601398', 'industry_bank', 'belongs_to', 1.0, 1.0, 'system'),
('rel_004', 'company_601288', 'industry_bank', 'belongs_to', 1.0, 1.0, 'system'),
('rel_005', 'company_600036', 'industry_bank', 'belongs_to', 1.0, 1.0, 'system'),
('rel_006', 'company_600519', 'industry_baijiu', 'belongs_to', 1.0, 1.0, 'system'),
('rel_007', 'company_000858', 'industry_baijiu', 'belongs_to', 1.0, 1.0, 'system'),
('rel_008', 'company_002594', 'industry_xinnengyuan', 'belongs_to', 1.0, 1.0, 'system'),
('rel_009', 'company_300750', 'industry_xinnengyuan', 'belongs_to', 1.0, 1.0, 'system'),
('rel_010', 'company_002594', 'concept_tan zhonghe', 'has_concept', 0.8, 0.9, 'system'),
('rel_011', 'company_300750', 'concept_tan zhonghe', 'has_concept', 0.9, 0.95, 'system'),
('rel_012', 'company_002594', 'concept_rengongzhineng', 'has_concept', 0.6, 0.8, 'system'),
('rel_013', 'company_600000', 'company_000001', 'competes_with', 0.8, 0.9, 'system'),
('rel_014', 'company_600000', 'company_601398', 'competes_with', 0.7, 0.85, 'system'),
('rel_015', 'company_600519', 'company_000858', 'competes_with', 0.9, 0.95, 'system'),
('rel_016', 'person_buffett', 'company_002594', 'invests_in', 0.7, 0.8, 'news'),
('rel_017', 'company_002024', 'industry_xinnengyuan', 'has_concept', 0.5, 0.7, 'system')
ON CONFLICT (source_entity_id, target_entity_id, relation_type) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA openfinance TO openfinance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA openfinance TO openfinance;
