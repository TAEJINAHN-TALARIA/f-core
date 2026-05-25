import logging
import time

from .config import HISTORY_CUTOFF
from .downloader import get_ticker_map, get_sic_map, iter_companyfacts
from .loader import (
    get_client,
    upsert_companies, upsert_facts, upsert_metrics,
    delete_expired,
    record_etl_start, record_etl_success, record_etl_failed,
)
from .normalizer import compute_metrics, deduplicate_facts
from .parser import extract_company_info, extract_facts
from .stats import ParseStats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run() -> None:
    start = time.time()
    logger.info("=== SEC EDGAR ETL Pipeline Start ===")

    ticker_map = get_ticker_map()
    ciks = list(ticker_map.keys())

    sic_map = get_sic_map(ciks)
    for cik, sic_data in sic_map.items():
        ticker_map.setdefault(cik, {}).update(sic_data)
    client = get_client()
    stats = ParseStats()

    run_id = record_etl_start(client)

    company_buffer: list[dict] = []
    facts_buffer: list[dict] = []
    metrics_buffer: list[dict] = []
    total_companies = 0
    total_facts = 0
    total_metrics = 0

    try:
        for data in iter_companyfacts(ciks, ticker_map=ticker_map):
            stats.mark_fetched()

            company = extract_company_info(data)
            if not company:
                continue

            cik = company["cik"]
            raw_facts = extract_facts(data, stats=stats)
            deduped_facts = deduplicate_facts(raw_facts)
            stats.record_dedup(len(deduped_facts))
            metrics = compute_metrics(deduped_facts, cik, stats=stats)

            company_buffer.append(company)
            facts_buffer.extend(deduped_facts)
            metrics_buffer.extend(metrics)
            total_companies += 1
            total_facts += len(deduped_facts)
            total_metrics += len(metrics)

            if len(facts_buffer) >= 10_000:
                _flush(client, company_buffer, facts_buffer, metrics_buffer)
                company_buffer, facts_buffer, metrics_buffer = [], [], []

        if company_buffer:
            _flush(client, company_buffer, facts_buffer, metrics_buffer)

        # HISTORY_CUTOFF 이전 만료 데이터 정리
        deleted = delete_expired(client, HISTORY_CUTOFF)
        logger.info(f"[cleanup] deleted: {deleted}")

        record_etl_success(client, run_id, total_companies, total_facts, total_metrics)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        record_etl_failed(client, run_id, str(e))
        raise

    finally:
        stats.save()

    elapsed = time.time() - start
    logger.info(f"=== Pipeline Complete: {total_companies} companies in {elapsed:.1f}s ===")


def _flush(client, companies, facts, metrics) -> None:
    upsert_companies(client, companies)
    upsert_facts(client, facts)
    upsert_metrics(client, metrics)


if __name__ == "__main__":
    run()
