"""Quick smoke test: load 5 companies into Supabase."""
import logging
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test")

from etl.downloader import get_ticker_map, iter_companyfacts
from etl.parser import extract_company_info, extract_facts
from etl.normalizer import deduplicate_facts, compute_metrics
from etl.loader import get_client, upsert_companies, upsert_facts, upsert_metrics

ticker_map = get_ticker_map()
ciks = list(ticker_map.keys())[:5]
logger.info(f"Test CIKs: {ciks}")

client = get_client()
companies, facts_all, metrics_all = [], [], []

for data in iter_companyfacts(ciks, ticker_map=ticker_map):
    company = extract_company_info(data)
    if not company:
        continue
    raw = extract_facts(data)
    deduped = deduplicate_facts(raw)
    mets = compute_metrics(deduped, company["cik"])
    companies.append(company)
    facts_all.extend(deduped)
    metrics_all.extend(mets)
    logger.info(f"  {company['name']} ({company['ticker']}) — {len(deduped)} facts, {len(mets)} metrics")

upsert_companies(client, companies)
upsert_facts(client, facts_all)
upsert_metrics(client, metrics_all)
logger.info(f"Done. {len(companies)} companies loaded.")
