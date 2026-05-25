import logging
import os
from datetime import datetime, timezone
from supabase import create_client, Client

from .config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── ETL 실행 이력 ────────────────────────────────────────────

def _run_id() -> str:
    gh = os.environ.get("GITHUB_RUN_ID")
    if gh:
        return f"gh-{gh}"
    return f"local-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"


def record_etl_start(client: Client) -> str:
    rid = _run_id()
    client.table("etl_runs").upsert(
        {"run_id": rid, "started_at": datetime.now(timezone.utc).isoformat(), "status": "running"},
        on_conflict="run_id",
    ).execute()
    return rid


def record_etl_success(client: Client, run_id: str, companies: int, facts: int, metrics: int) -> None:
    client.table("etl_runs").update({
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "companies": companies,
        "facts": facts,
        "metrics": metrics,
    }).eq("run_id", run_id).execute()


def record_etl_failed(client: Client, run_id: str, error: str) -> None:
    client.table("etl_runs").update({
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "error": error[:500],
    }).eq("run_id", run_id).execute()


def upsert_companies(client: Client, companies: list[dict]) -> None:
    _batch_upsert(client, "companies", companies, conflict="cik")


def upsert_facts(client: Client, facts: list[dict]) -> None:
    _batch_upsert(
        client,
        "facts",
        facts,
        conflict="cik,tag,unit,end_date,period_type",
    )


def upsert_metrics(client: Client, metrics: list[dict]) -> None:
    _batch_upsert(
        client,
        "metrics",
        metrics,
        conflict="cik,end_date,period_type,metric",
    )


def delete_expired(client: Client, cutoff: str) -> dict[str, int]:
    """HISTORY_CUTOFF 이전 facts/metrics 삭제. 매 ETL 완료 후 호출."""
    counts = {}
    for table in ("facts", "metrics"):
        res = client.table(table).delete().lt("end_date", cutoff).execute()
        counts[table] = len(res.data)
        logger.info(f"[{table}] deleted {counts[table]} rows older than {cutoff}")
    return counts


def _batch_upsert(client: Client, table: str, rows: list[dict], conflict: str) -> None:
    if not rows:
        return

    total = len(rows)
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        try:
            client.table(table).upsert(batch, on_conflict=conflict).execute()
            logger.debug(f"  [{table}] upserted {i + len(batch)}/{total}")
        except Exception as e:
            logger.error(f"  [{table}] batch upsert failed at {i}: {e}")
            raise

    logger.info(f"[{table}] total upserted: {total}")
