-- Research Reports Tables
-- Create tables for research reports and analysts

-- Research Reports Table
CREATE TABLE IF NOT EXISTS openfinance.research_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    content TEXT,
    
    source VARCHAR(50) NOT NULL,
    source_url VARCHAR(500),
    
    related_codes TEXT[] DEFAULT '{}',
    related_names TEXT[] DEFAULT '{}',
    industry VARCHAR(100),
    
    institution VARCHAR(100),
    analyst VARCHAR(100),
    
    rating VARCHAR(20),
    target_price DECIMAL(12, 4),
    
    sentiment_score DECIMAL(4, 3),
    sentiment_label VARCHAR(20),
    extracted_entities JSONB DEFAULT '{}',
    extracted_relations JSONB DEFAULT '{}',
    
    publish_date TIMESTAMP WITH TIME ZONE,
    report_date DATE,
    
    report_type VARCHAR(50),
    page_count INTEGER,
    
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for research_reports
CREATE INDEX IF NOT EXISTS ix_research_reports_source ON openfinance.research_reports (source);
CREATE INDEX IF NOT EXISTS ix_research_reports_publish_date ON openfinance.research_reports (publish_date DESC);
CREATE INDEX IF NOT EXISTS ix_research_reports_institution ON openfinance.research_reports (institution);
CREATE INDEX IF NOT EXISTS ix_research_reports_rating ON openfinance.research_reports (rating);
CREATE INDEX IF NOT EXISTS ix_research_reports_report_type ON openfinance.research_reports (report_type);

-- Create GIN index for related_codes array
CREATE INDEX IF NOT EXISTS ix_research_reports_related_codes ON openfinance.research_reports USING GIN (related_codes);

-- Research Analysts Table
CREATE TABLE IF NOT EXISTS openfinance.research_analysts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analyst_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    institution VARCHAR(100),
    specialty VARCHAR(200),
    accuracy_score DECIMAL(4, 3),
    report_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for research_analysts
CREATE INDEX IF NOT EXISTS ix_research_analysts_name ON openfinance.research_analysts (name);
CREATE INDEX IF NOT EXISTS ix_research_analysts_institution ON openfinance.research_analysts (institution);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_research_reports_updated_at
    BEFORE UPDATE ON openfinance.research_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_research_analysts_updated_at
    BEFORE UPDATE ON openfinance.research_analysts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE openfinance.research_reports IS 'Research reports from various sources';
COMMENT ON TABLE openfinance.research_analysts IS 'Research analysts information';
