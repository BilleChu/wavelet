-- Person Profile Tables
-- 人物档案相关数据表
-- Ensure UTF-8 encoding
SET client_encoding = 'UTF8';

-- ============================================
-- Person Profiles Table (人物档案扩展表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.person_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id VARCHAR(255) NOT NULL,
    
    -- 评分数据（快照）
    total_score DECIMAL(5,2) DEFAULT 0,
    influence_score DECIMAL(5,2) DEFAULT 0,
    activity_score DECIMAL(5,2) DEFAULT 0,
    accuracy_score DECIMAL(5,2) DEFAULT 0,
    network_score DECIMAL(5,2) DEFAULT 0,
    industry_score DECIMAL(5,2) DEFAULT 0,
    
    -- 统计数据
    followers_count INTEGER DEFAULT 0,
    news_mentions INTEGER DEFAULT 0,
    report_count INTEGER DEFAULT 0,
    managed_assets DECIMAL(20,4),
    
    -- 行业评分明细（JSON）
    industry_scores JSONB DEFAULT '{}',
    
    -- 扩展属性
    properties JSONB DEFAULT '{}',
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_synced_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT uq_person_profile_entity UNIQUE (entity_id),
    CONSTRAINT fk_person_profile_entity FOREIGN KEY (entity_id) 
        REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_person_profiles_score ON openfinance.person_profiles(total_score DESC);
CREATE INDEX IF NOT EXISTS ix_person_profiles_entity ON openfinance.person_profiles(entity_id);
CREATE INDEX IF NOT EXISTS ix_person_profiles_followers ON openfinance.person_profiles(followers_count DESC);

COMMENT ON TABLE openfinance.person_profiles IS 'Person profile extension table with scores and statistics';

-- ============================================
-- Person Activities Table (人物动态表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.person_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id VARCHAR(100) UNIQUE NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    
    activity_type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    source VARCHAR(100),
    source_url VARCHAR(500),
    
    industry VARCHAR(100),
    
    sentiment_score DECIMAL(4,3),
    impact_score DECIMAL(5,2),
    
    related_codes TEXT[],
    related_entities TEXT[],
    
    activity_date TIMESTAMP WITH TIME ZONE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_person_activity_entity FOREIGN KEY (entity_id) 
        REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_person_activities_entity ON openfinance.person_activities(entity_id);
CREATE INDEX IF NOT EXISTS ix_person_activities_date ON openfinance.person_activities(activity_date DESC);
CREATE INDEX IF NOT EXISTS ix_person_activities_type ON openfinance.person_activities(activity_type);
CREATE INDEX IF NOT EXISTS ix_person_activities_industry ON openfinance.person_activities(industry);

COMMENT ON TABLE openfinance.person_activities IS 'Person activity timeline with news, reports, and social updates';

-- ============================================
-- Person Industry Scores Table (人物行业评分历史表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.person_industry_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id VARCHAR(255) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    score_date DATE NOT NULL,
    
    total_score DECIMAL(5,2),
    expertise_score DECIMAL(5,2),
    influence_score DECIMAL(5,2),
    accuracy_score DECIMAL(5,2),
    
    metrics JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_person_industry_score UNIQUE (entity_id, industry, score_date),
    CONSTRAINT fk_person_industry_score_entity FOREIGN KEY (entity_id) 
        REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_person_industry_scores_entity ON openfinance.person_industry_scores(entity_id);
CREATE INDEX IF NOT EXISTS ix_person_industry_scores_industry ON openfinance.person_industry_scores(industry);
CREATE INDEX IF NOT EXISTS ix_person_industry_scores_date ON openfinance.person_industry_scores(score_date DESC);

COMMENT ON TABLE openfinance.person_industry_scores IS 'Historical industry-specific scores for persons';

-- ============================================
-- Person Score History Table (人物评分历史表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.person_score_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id VARCHAR(255) NOT NULL,
    score_date DATE NOT NULL,
    
    total_score DECIMAL(5,2),
    influence_score DECIMAL(5,2),
    activity_score DECIMAL(5,2),
    accuracy_score DECIMAL(5,2),
    network_score DECIMAL(5,2),
    industry_score DECIMAL(5,2),
    
    metrics JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_person_score_history UNIQUE (entity_id, score_date),
    CONSTRAINT fk_person_score_history_entity FOREIGN KEY (entity_id) 
        REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_person_score_history_entity ON openfinance.person_score_history(entity_id);
CREATE INDEX IF NOT EXISTS ix_person_score_history_date ON openfinance.person_score_history(score_date DESC);

COMMENT ON TABLE openfinance.person_score_history IS 'Historical overall scores for persons';

-- ============================================
-- Person Mentions Table (人物提及关联表)
-- ============================================
CREATE TABLE IF NOT EXISTS openfinance.person_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id VARCHAR(255) NOT NULL,
    
    mention_type VARCHAR(50) NOT NULL,
    mention_id VARCHAR(100) NOT NULL,
    
    title VARCHAR(500),
    summary TEXT,
    source_url VARCHAR(500),
    
    sentiment_score DECIMAL(4,3),
    
    related_codes TEXT[],
    related_industries TEXT[],
    
    mention_date TIMESTAMP WITH TIME ZONE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_person_mention_entity FOREIGN KEY (entity_id) 
        REFERENCES openfinance.entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_person_mentions_entity ON openfinance.person_mentions(entity_id);
CREATE INDEX IF NOT EXISTS ix_person_mentions_type ON openfinance.person_mentions(mention_type);
CREATE INDEX IF NOT EXISTS ix_person_mentions_date ON openfinance.person_mentions(mention_date DESC);

COMMENT ON TABLE openfinance.person_mentions IS 'Person mentions in news and research reports';

-- ============================================
-- Functions for score calculation
-- ============================================
CREATE OR REPLACE FUNCTION openfinance.update_person_profile_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_person_profile_timestamp
    BEFORE UPDATE ON openfinance.person_profiles
    FOR EACH ROW
    EXECUTE FUNCTION openfinance.update_person_profile_timestamp();

-- ============================================
-- Views for common queries
-- ============================================
CREATE OR REPLACE VIEW openfinance.v_person_list AS
SELECT 
    e.id,
    e.entity_id,
    e.name,
    e.code,
    e.industry,
    e.properties->>'person_type' AS person_type,
    e.properties->>'title' AS title,
    e.properties->>'company' AS company,
    e.properties->>'avatar_url' AS avatar_url,
    e.properties->>'verified' AS verified,
    COALESCE(pp.total_score, 0) AS total_score,
    COALESCE(pp.influence_score, 0) AS influence_score,
    COALESCE(pp.activity_score, 0) AS activity_score,
    COALESCE(pp.accuracy_score, 0) AS accuracy_score,
    COALESCE(pp.network_score, 0) AS network_score,
    COALESCE(pp.followers_count, 0) AS followers_count,
    COALESCE(pp.news_mentions, 0) AS news_mentions,
    COALESCE(pp.report_count, 0) AS report_count,
    pp.industry_scores,
    e.created_at,
    e.updated_at
FROM openfinance.entities e
LEFT JOIN openfinance.person_profiles pp ON e.entity_id = pp.entity_id
WHERE e.entity_type = 'person';

COMMENT ON VIEW openfinance.v_person_list IS 'View for person list with scores and statistics';

-- ============================================
-- Initial data for testing (optional)
-- ============================================
-- This can be removed in production
