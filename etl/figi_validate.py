"""
OpenFIGI-based ticker validation and correction.

For each company in the DB:
  1. Query OpenFIGI with the current ticker.
  2. If no "Common Stock" result → ticker is wrong.
  3. Cross-reference with a fresh SEC file to get a candidate replacement.
  4. Verify the replacement is also confirmed Common Stock by OpenFIGI.
  5. Report mismatches; with --apply write corrections to DB.

Usage:
  python -m etl.figi_validate            # dry-run
  python -m etl.figi_validate --apply    # write corrections
"""
import os
import sys
import time
import logging
import requests
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from .loader import get_client
from .downloader import _headers as _edgar_headers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

APPLY = "--apply" in sys.argv

OPENFIGI_URL  = "https://api.openfigi.com/v3/mapping"
OPENFIGI_KEY  = os.environ.get("OPENFIGI_API_KEY", "")

# With API key: 100 jobs/request, 250 req/6s
# Without key : 10  jobs/request, 25  req/min
BATCH_SIZE    = 100 if OPENFIGI_KEY else 10
REQ_PER_BURST = 25 if OPENFIGI_KEY else 25
BURST_WINDOW  = 6  if OPENFIGI_KEY else 60   # seconds

COMMON_STOCK_TYPES = {"Common Stock", "Ordinary Shares", "Equity"}


def _figi_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if OPENFIGI_KEY:
        h["X-OPENFIGI-APIKEY"] = OPENFIGI_KEY
    return h


def query_openfigi(jobs: list[dict]) -> list[dict]:
    """
    POST up to BATCH_SIZE jobs. Returns list of result objects
    (same order as input; each has 'data' list or 'error'/'warning').
    Handles 429 with backoff.
    """
    for attempt in range(4):
        r = requests.post(OPENFIGI_URL, json=jobs, headers=_figi_headers(), timeout=30)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", BURST_WINDOW * (attempt + 1)))
            logger.warning(f"Rate-limited. Waiting {wait}s...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("OpenFIGI rate limit exceeded after retries")


def is_common_stock(figi_entry: dict) -> bool:
    st  = figi_entry.get("securityType",  "") or ""
    st2 = figi_entry.get("securityType2", "") or ""
    return st in COMMON_STOCK_TYPES or st2 in COMMON_STOCK_TYPES


def validate_tickers_batch(tickers: list[str]) -> dict[str, bool]:
    """
    Returns {ticker: is_common_stock} for each ticker in the list.
    Batches calls to OpenFIGI respecting rate limits.
    """
    results: dict[str, bool] = {}
    req_count = 0

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        jobs  = [{"idType": "TICKER", "idValue": t} for t in batch]

        resp = query_openfigi(jobs)
        req_count += 1

        for ticker, item in zip(batch, resp):
            data = item.get("data", [])
            results[ticker] = any(is_common_stock(e) for e in data)

        # Rate limiting
        if req_count % REQ_PER_BURST == 0:
            logger.info(f"  Processed {i + len(batch)}/{len(tickers)} tickers — pausing {BURST_WINDOW}s")
            time.sleep(BURST_WINDOW)

    return results


def load_sec_correction_map() -> dict[str, str]:
    """
    Download SEC company_tickers_exchange.json and return
    {db_ticker: sec_suggested_ticker} for mismatches.
    Reuses the duplicate-CIK resolution logic from validate_tickers.
    """
    import re
    from collections import defaultdict

    _FUND_RE = re.compile(
        r"\b(etf|fund|trust|note|bond|preferred|warrant|unit|depositary|"
        r"receipt|index|commodity|income|yield|dividend|series)\b",
        re.IGNORECASE,
    )

    url = "https://www.sec.gov/files/company_tickers_exchange.json"
    logger.info("Downloading SEC ticker file for cross-reference...")
    r = requests.get(url, headers=_edgar_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    fields = data["fields"]

    by_cik: dict[str, list[dict]] = defaultdict(list)
    for row in data["data"]:
        e   = dict(zip(fields, row))
        cik = str(e["cik"]).zfill(10)
        by_cik[cik].append({"ticker": e.get("ticker", ""), "name": e.get("name", "")})

    # CIK → best (non-fund) ticker from SEC
    cik_to_sec_ticker: dict[str, str] = {}
    for cik, entries in by_cik.items():
        non_funds = [e for e in entries if not _FUND_RE.search(e["name"])]
        winner = non_funds[0] if non_funds else entries[0]
        cik_to_sec_ticker[cik] = winner["ticker"]

    return cik_to_sec_ticker   # {cik: sec_ticker}


def load_db_companies(client) -> list[dict]:
    rows, offset, page = [], 0, 1000
    while True:
        res = (client.table("companies")
               .select("cik, ticker, name")
               .range(offset, offset + page - 1)
               .execute())
        rows.extend(res.data)
        if len(res.data) < page:
            break
        offset += page
    logger.info(f"DB: {len(rows)} companies loaded")
    return rows


def run():
    if not OPENFIGI_KEY:
        logger.warning("OPENFIGI_API_KEY not set — using free tier (10 jobs/req, 25 req/min, ~28 min)")

    client        = get_client()
    db_companies  = load_db_companies(client)
    sec_map       = load_sec_correction_map()   # {cik: sec_ticker}

    # ── Step 1: validate all unique DB tickers ────────────────────────────────
    unique_tickers = list({c["ticker"] for c in db_companies if c.get("ticker")})
    logger.info(f"Validating {len(unique_tickers)} unique tickers via OpenFIGI...")
    ticker_is_common = validate_tickers_batch(unique_tickers)

    bad_tickers = {t for t, ok in ticker_is_common.items() if not ok}
    logger.info(f"Result: {len(unique_tickers) - len(bad_tickers)} valid, {len(bad_tickers)} not common stock")

    # ── Step 2: for bad tickers, find SEC suggestion and re-validate ──────────
    companies_to_fix = [c for c in db_companies if c.get("ticker") in bad_tickers]

    candidate_tickers: set[str] = set()
    for comp in companies_to_fix:
        sec_t = sec_map.get(comp["cik"], "")
        if sec_t and sec_t != comp["ticker"]:
            candidate_tickers.add(sec_t)

    if candidate_tickers:
        logger.info(f"Validating {len(candidate_tickers)} SEC-suggested replacement tickers...")
        extra = validate_tickers_batch(list(candidate_tickers))
        ticker_is_common.update(extra)

    # ── Step 3: build correction list ─────────────────────────────────────────
    corrections = []
    no_fix      = []

    for comp in companies_to_fix:
        cik       = comp["cik"]
        old_t     = comp["ticker"]
        sec_t     = sec_map.get(cik, "")
        can_fix   = sec_t and sec_t != old_t and ticker_is_common.get(sec_t, False)

        if can_fix:
            corrections.append({
                "cik":        cik,
                "name":       comp["name"],
                "old_ticker": old_t,
                "new_ticker": sec_t,
            })
        else:
            no_fix.append({
                "cik":         cik,
                "name":        comp["name"],
                "old_ticker":  old_t,
                "sec_suggest": sec_t or "(none)",
                "sec_is_common": ticker_is_common.get(sec_t, False) if sec_t else False,
            })

    # ── Report ─────────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"OPENFIGI VALIDATION RESULTS")
    print(f"  Total companies : {len(db_companies)}")
    print(f"  Valid (common)  : {len(db_companies) - len(companies_to_fix)}")
    print(f"  Wrong ticker    : {len(companies_to_fix)}")
    print(f"  Fixable         : {len(corrections)}")
    print(f"  No fix found    : {len(no_fix)}")
    print(f"{'='*70}")

    print(f"\n[FIXABLE] Old ticker -> Confirmed common stock replacement ({len(corrections)})")
    for c in corrections[:50]:
        print(f"  {c['old_ticker']:<10s} -> {c['new_ticker']:<8s}  {c['name']}")
    if len(corrections) > 50:
        print(f"  ... and {len(corrections)-50} more")

    print(f"\n[NO FIX] Non-common ticker with no confirmed replacement ({len(no_fix)})")
    for c in no_fix[:20]:
        sec_info = f"SEC suggests {c['sec_suggest']} (also not common)" if not c['sec_is_common'] else ""
        print(f"  {c['old_ticker']:<10s}  {c['name'][:40]}  {sec_info}")
    if len(no_fix) > 20:
        print(f"  ... and {len(no_fix)-20} more")

    # ── Apply ──────────────────────────────────────────────────────────────────
    if not APPLY:
        print(f"\nDry-run complete. Run with --apply to write {len(corrections)} corrections to DB.")
        return

    print(f"\nApplying {len(corrections)} corrections...")
    updated = 0
    for c in corrections:
        try:
            client.table("companies").update({"ticker": c["new_ticker"]}).eq("cik", c["cik"]).execute()
            updated += 1
        except Exception as e:
            logger.warning(f"Update failed cik={c['cik']}: {e}")
    print(f"Done. {updated}/{len(corrections)} rows updated.")


if __name__ == "__main__":
    run()
