-- ETL 실행 이력 테이블
-- pipeline.py가 실행 시작/완료/실패 시 upsert
CREATE TABLE IF NOT EXISTS etl_runs (
    id          BIGSERIAL PRIMARY KEY,
    run_id      TEXT NOT NULL UNIQUE,           -- github run_id 또는 "local-{timestamp}"
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status      TEXT NOT NULL DEFAULT 'running', -- running | success | failed
    companies   INT,
    facts       INT,
    metrics     INT,
    error       TEXT
);

-- API가 최신 1건만 조회하므로 finished_at DESC 인덱스
CREATE INDEX IF NOT EXISTS idx_etl_runs_finished ON etl_runs (finished_at DESC NULLS LAST);
