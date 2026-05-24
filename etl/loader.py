import logging
from supabase import create_client, Client

from .config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


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
