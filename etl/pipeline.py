import logging
import time

from .downloader import get_ticker_map, iter_companyfacts
from .loader import get_client, upsert_companies, upsert_facts, upsert_metrics
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
    client = get_client()
    stats = ParseStats()

    company_buffer: list[dict] = []
    facts_buffer: list[dict] = []
    metrics_buffer: list[dict] = []
    total_companies = 0

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

        if len(facts_buffer) >= 10_000:
            _flush(client, company_buffer, facts_buffer, metrics_buffer)
            company_buffer, facts_buffer, metrics_buffer = [], [], []

    if company_buffer:
        _flush(client, company_buffer, facts_buffer, metrics_buffer)

    stats.save()

    elapsed = time.time() - start
    logger.info(f"=== Pipeline Complete: {total_companies} companies in {elapsed:.1f}s ===")


def _flush(client, companies, facts, metrics) -> None:
    upsert_companies(client, companies)
    upsert_facts(client, facts)
    upsert_metrics(client, metrics)


if __name__ == "__main__":
    run()
