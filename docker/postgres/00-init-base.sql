-- OpenFinance Database Initialization
-- Run this script first to set up the database

-- Ensure UTF-8 encoding
SET client_encoding = 'UTF8';

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS openfinance;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create update_updated_at_column function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant permissions
GRANT ALL ON SCHEMA openfinance TO openfinance;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA openfinance TO openfinance;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA openfinance TO openfinance;
