-- Enable pg_trgm for full-text company name search
-- (Also available via Supabase Dashboard > Database > Extensions)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Composite index for common facts query pattern: CIK + tag + period, sorted by date
CREATE INDEX IF NOT EXISTS idx_facts_cik_tag_period
    ON facts (cik, tag, period_type, end_date DESC);

-- Composite index for metrics queries
CREATE INDEX IF NOT EXISTS idx_metrics_cik_period
    ON metrics (cik, period_type, end_date DESC);

-- Trigram index for fuzzy company name search
CREATE INDEX IF NOT EXISTS idx_companies_name_trgm
    ON companies USING gin (name gin_trgm_ops);

-- Case-insensitive ticker lookup
CREATE INDEX IF NOT EXISTS idx_companies_ticker_lower
    ON companies (lower(ticker));
