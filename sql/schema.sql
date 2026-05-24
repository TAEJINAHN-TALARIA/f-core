-- 기업 정보
CREATE TABLE IF NOT EXISTS companies (
    cik             TEXT PRIMARY KEY,       -- 10자리 zero-padded CIK
    name            TEXT,
    ticker          TEXT,
    exchange        TEXT,
    sic             TEXT,
    sic_description TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies (ticker);

-- 원본 재무 팩트 (핵심 XBRL 태그)
CREATE TABLE IF NOT EXISTS facts (
    id          BIGSERIAL PRIMARY KEY,
    cik         TEXT NOT NULL REFERENCES companies (cik),
    tag         TEXT NOT NULL,
    unit        TEXT NOT NULL,             -- USD, shares, USD/shares
    period_type TEXT NOT NULL,             -- instant | annual | quarterly | other
    start_date  DATE,
    end_date    DATE NOT NULL,
    filed_date  DATE,
    form        TEXT,                      -- 10-K, 10-Q, ...
    frame       TEXT,
    value       DOUBLE PRECISION NOT NULL,
    UNIQUE (cik, tag, unit, end_date, period_type)
);

CREATE INDEX IF NOT EXISTS idx_facts_cik         ON facts (cik);
CREATE INDEX IF NOT EXISTS idx_facts_tag         ON facts (tag);
CREATE INDEX IF NOT EXISTS idx_facts_end_date    ON facts (end_date);
CREATE INDEX IF NOT EXISTS idx_facts_cik_tag     ON facts (cik, tag);

-- 파생 지표 (gross_margin, roe, roa, ...)
CREATE TABLE IF NOT EXISTS metrics (
    id          BIGSERIAL PRIMARY KEY,
    cik         TEXT NOT NULL REFERENCES companies (cik),
    end_date    DATE NOT NULL,
    period_type TEXT NOT NULL,
    metric      TEXT NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    UNIQUE (cik, end_date, period_type, metric)
);

CREATE INDEX IF NOT EXISTS idx_metrics_cik      ON metrics (cik);
CREATE INDEX IF NOT EXISTS idx_metrics_metric   ON metrics (metric);
CREATE INDEX IF NOT EXISTS idx_metrics_end_date ON metrics (end_date);
