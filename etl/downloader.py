import re
import logging
import threading
import time
import requests
from collections import defaultdict
from typing import Generator

from .config import EDGAR_USER_AGENT

# Patterns that identify non-common-stock securities in the SEC file
_NONCOMMON_TICKER_RE = re.compile(
    r'.+W[ST]?$'       # warrants: OABIW, SBXE-WT
    r'|.+U[U]?$'       # units:    DMAAU
    r'|-UN$'           # units:    JENA-UN
    r'|-P[A-Z]{0,2}$'  # preferred: GS-PD, MTB-PK
    r'|-W[ST]?$'       # hyphen warrants: VACI-WT
)
_FUND_NAME_RE = re.compile(
    r'\b(fund|trust|etf|note|bond|preferred|warrant|unit|'
    r'depositary|receipt|index|commodity|income|yield|'
    r'dividend|series|municipal|muni|interval)\b',
    re.IGNORECASE,
)

def _is_common_stock_entry(entry: dict) -> bool:
    ticker = (entry.get("ticker") or "").upper()
    name   = entry.get("name") or ""
    if _NONCOMMON_TICKER_RE.match(ticker):
        return False
    if _FUND_NAME_RE.search(name):
        return False
    return True

logger = logging.getLogger(__name__)

TICKERS_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# SEC EDGAR rate limit: max 10 req/s per IP. Target 8 to leave headroom.
# Lock + monotonic timestamp are MODULE-level so the cap holds across threads —
# auto_discover_tags fans out 10×10 concurrent downloads, and per-call limiting
# would otherwise let the actual request rate reach ~100/s and trigger 429s.
_MIN_INTERVAL = 1 / 8
_rate_lock = threading.Lock()
_last_request_at = 0.0


def _throttle() -> None:
    """Block until at least _MIN_INTERVAL has elapsed since the previous SEC hit."""
    global _last_request_at
    with _rate_lock:
        elapsed = time.monotonic() - _last_request_at
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        _last_request_at = time.monotonic()


def _get_with_retry(session: requests.Session, url: str, *, max_attempts: int = 4) -> requests.Response:
    """GET with global throttle and 429-aware backoff. Other HTTP errors propagate via raise_for_status caller."""
    for attempt in range(max_attempts):
        _throttle()
        r = session.get(url, timeout=30)
        if r.status_code != 429:
            return r
        retry_after = r.headers.get("Retry-After")
        try:
            wait = float(retry_after) if retry_after else 2 ** attempt
        except ValueError:
            wait = 2 ** attempt
        wait = min(max(wait, 1.0), 30.0)
        logger.warning(f"429 from SEC for {url}; backing off {wait:.1f}s (attempt {attempt+1}/{max_attempts})")
        time.sleep(wait)
    return r  # final 429 — let caller handle via raise_for_status


def _headers() -> dict:
    return {"User-Agent": EDGAR_USER_AGENT, "Accept-Encoding": "gzip, deflate"}


def get_ticker_map() -> dict[str, dict]:
    """
    Download company_tickers_exchange.json and return {padded_cik: {name, ticker, exchange}}.

    Duplicate CIK handling: the SEC file lists every registered security, so one CIK can
    appear multiple times (company + its ETFs, warrants, preferred shares).
    We prefer the first common-stock entry; fall back to the first entry of any kind.
    """
    logger.info(f"Fetching company metadata from {TICKERS_EXCHANGE_URL}")
    r = requests.get(TICKERS_EXCHANGE_URL, headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    fields = data["fields"]  # ['cik', 'name', 'ticker', 'exchange']

    by_cik: dict[str, list[dict]] = defaultdict(list)
    for row in data["data"]:
        entry = dict(zip(fields, row))
        cik = str(entry["cik"]).zfill(10)
        by_cik[cik].append({
            "name":     entry.get("name", ""),
            "ticker":   entry.get("ticker"),
            "exchange": entry.get("exchange"),
        })

    result = {}
    for cik, entries in by_cik.items():
        common = [e for e in entries if _is_common_stock_entry(e)]
        result[cik] = common[0] if common else entries[0]

    logger.info(f"Total companies: {len(result)}")
    return result


def get_sic_map(ciks: list[str]) -> dict[str, dict]:
    """submissions 엔드포인트에서 SIC 코드와 설명을 수집한다."""
    result: dict[str, dict] = {}
    session = requests.Session()
    session.headers.update(_headers())
    total = len(ciks)

    for i, cik in enumerate(ciks):
        try:
            r = _get_with_retry(session, SUBMISSIONS_URL.format(cik=cik))
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

        if (i + 1) % 1000 == 0:
            logger.info(f"SIC fetch progress: {i+1}/{total}")

    logger.info(f"SIC map built: {len(result)}/{total} companies")
    return result


def iter_companyfacts(ciks: list[str], ticker_map: dict | None = None) -> Generator[dict, None, None]:
    """Fetch companyfacts JSON for each CIK. Rate limiting and 429 retry are global
    (see _throttle / _get_with_retry) so multi-threaded callers stay within SEC's
    10 req/s cap."""
    total = len(ciks)
    session = requests.Session()
    session.headers.update(_headers())

    for i, cik in enumerate(ciks):
        url = COMPANYFACTS_URL.format(cik=cik)
        try:
            r = _get_with_retry(session, url)
            if r.status_code == 404:
                continue  # Company has no XBRL data
            r.raise_for_status()
            data = r.json()
            if ticker_map and cik in ticker_map:
                data["_meta"] = ticker_map[cik]
            yield data
        except requests.RequestException as e:
            logger.warning(f"[{i+1}/{total}] Failed CIK {cik}: {e}")
            continue

        if (i + 1) % 500 == 0:
            logger.info(f"Progress: {i+1}/{total} companies fetched")
