import logging
import time
import requests
from typing import Generator

from .config import EDGAR_USER_AGENT

logger = logging.getLogger(__name__)

TICKERS_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# SEC EDGAR rate limit: max 10 req/s. We target 8 to be safe.
_MIN_INTERVAL = 1 / 8


def _headers() -> dict:
    return {"User-Agent": EDGAR_USER_AGENT, "Accept-Encoding": "gzip, deflate"}


def get_ticker_map() -> dict[str, dict]:
    """Download company_tickers_exchange.json and return {padded_cik: {name, ticker, exchange}}."""
    logger.info(f"Fetching company metadata from {TICKERS_EXCHANGE_URL}")
    r = requests.get(TICKERS_EXCHANGE_URL, headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    fields = data["fields"]  # ['cik', 'name', 'ticker', 'exchange']
    result = {}
    for row in data["data"]:
        entry = dict(zip(fields, row))
        cik = str(entry["cik"]).zfill(10)
        result[cik] = {
            "name": entry.get("name", ""),
            "ticker": entry.get("ticker"),
            "exchange": entry.get("exchange"),
        }
    logger.info(f"Total companies: {len(result)}")
    return result


def get_sic_map(ciks: list[str]) -> dict[str, dict]:
    """submissions 엔드포인트에서 SIC 코드와 설명을 수집한다."""
    result: dict[str, dict] = {}
    session = requests.Session()
    session.headers.update(_headers())
    total = len(ciks)
    last_request = 0.0

    for i, cik in enumerate(ciks):
        elapsed = time.monotonic() - last_request
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)

        try:
            r = session.get(SUBMISSIONS_URL.format(cik=cik), timeout=30)
            last_request = time.monotonic()
            if r.status_code == 404:
                continue
            r.raise_for_status()
            data = r.json()
            sic = data.get("sic")
            if sic:
                result[cik] = {
                    "sic": str(sic),
                    "sic_description": data.get("sicDescription", ""),
                }
        except requests.RequestException as e:
            logger.warning(f"[{i+1}/{total}] SIC fetch failed CIK {cik}: {e}")
            last_request = time.monotonic()

        if (i + 1) % 1000 == 0:
            logger.info(f"SIC fetch progress: {i+1}/{total}")

    logger.info(f"SIC map built: {len(result)}/{total} companies")
    return result


def iter_companyfacts(ciks: list[str], ticker_map: dict | None = None) -> Generator[dict, None, None]:
    """Fetch companyfacts JSON for each CIK with SEC rate limiting."""
    total = len(ciks)
    session = requests.Session()
    session.headers.update(_headers())

    last_request = 0.0
    for i, cik in enumerate(ciks):
        # Rate limiting
        elapsed = time.monotonic() - last_request
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)

        url = COMPANYFACTS_URL.format(cik=cik)
        try:
            r = session.get(url, timeout=30)
            last_request = time.monotonic()

            if r.status_code == 404:
                continue  # Company has no XBRL data
            r.raise_for_status()
            data = r.json()
            if ticker_map and cik in ticker_map:
                data["_meta"] = ticker_map[cik]
            yield data

        except requests.RequestException as e:
            logger.warning(f"[{i+1}/{total}] Failed CIK {cik}: {e}")
            last_request = time.monotonic()
            continue

        if (i + 1) % 500 == 0:
            logger.info(f"Progress: {i+1}/{total} companies fetched")
