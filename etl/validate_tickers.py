"""
Ticker validation: two-pass cross-reference.

Pass 1: Re-download SEC company_tickers_exchange.json, detect duplicate CIKs,
        prefer common-stock ticker over ETF/fund when collision occurs.

Pass 2: Cross-reference with Nasdaq FTP listed-securities files.
        Flag tickers that are ETFs or don't exist on any exchange.

Usage: python -m etl.validate_tickers [--apply]
       --apply: write corrections back to DB (default: dry-run only)
"""
import sys
import re
import io
import os
import csv
import logging
import requests
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from .loader import get_client
from .downloader import _headers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

APPLY        = "--apply"        in sys.argv
COMMON_ONLY  = "--common-only"  in sys.argv  # only fix non-common → common moves

# Ticker suffix patterns that identify non-common-stock securities
_WARRANT_RE   = re.compile(r'.+W[ST]?$')       # OABIW, ASTLW, SBXE-WT
_UNIT_RE      = re.compile(r'.+U[U]?$')         # DMAAU, ACAAU
_RIGHTS_RE    = re.compile(r'.+R[T]?$')         # rights
_FOREIGN_RE   = re.compile(r'.+F$')             # ASMLF (foreign OTC ADR)
_PREFERRED_RE = re.compile(r'.+-P[A-Z]{0,2}$')  # GS-PD, MTB-PK, HFRO-PB (NOT BRK-A, HVT-A)

def _is_noncommon_ticker(ticker: str) -> bool:
    """Return True if ticker looks like a warrant, unit, right, foreign ADR, or preferred."""
    t = ticker.upper()
    return bool(
        _WARRANT_RE.match(t)   or
        _UNIT_RE.match(t)      or
        _RIGHTS_RE.match(t)    or
        _FOREIGN_RE.match(t)   or
        _PREFERRED_RE.match(t)
    )

# Nasdaq FTP public files (used as optional Pass 2)
NASDAQ_TRADED_URL = "https://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqtraded.txt"
OTHER_LISTED_URL  = "https://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"
NASDAQ_TIMEOUT = 10  # short timeout — fall back gracefully if blocked

# Keywords that signal a security is NOT a common-stock company
_FUND_KEYWORDS = re.compile(
    r"\b(etf|fund|trust|note|notes|bond|bond|preferred|warrant|"
    r"unit|units|depositary|receipt|index|commodity|strategy|"
    r"income|yield|dividend|series|class)\b",
    re.IGNORECASE,
)

def _is_fund_name(name: str) -> bool:
    return bool(_FUND_KEYWORDS.search(name))


# ── PASS 1: SEC file ─────────────────────────────────────────────────────────

def load_sec_ticker_map() -> dict[str, dict]:
    """
    Download company_tickers_exchange.json.
    For duplicate CIKs, prefer the entry whose name does NOT look like a fund.
    Returns {cik: {ticker, name, exchange}}.
    """
    url = "https://www.sec.gov/files/company_tickers_exchange.json"
    logger.info(f"Downloading SEC ticker file: {url}")
    r = requests.get(url, headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    fields = data["fields"]  # ['cik', 'name', 'ticker', 'exchange']

    # Collect all entries per CIK
    by_cik: dict[str, list[dict]] = defaultdict(list)
    for row in data["data"]:
        entry = dict(zip(fields, row))
        cik = str(entry["cik"]).zfill(10)
        by_cik[cik].append({
            "ticker":   entry.get("ticker", ""),
            "name":     entry.get("name", ""),
            "exchange": entry.get("exchange", ""),
        })

    result = {}
    duplicates = 0
    for cik, entries in by_cik.items():
        if len(entries) == 1:
            result[cik] = entries[0]
            continue

        duplicates += 1
        # Prefer a non-fund entry
        non_funds = [e for e in entries if not _is_fund_name(e["name"])]
        winner = non_funds[0] if non_funds else entries[0]
        result[cik] = winner

    logger.info(f"SEC file: {len(result)} unique CIKs ({duplicates} had duplicates — resolved)")
    return result


# ── PASS 2: Nasdaq/NYSE listed files ─────────────────────────────────────────

def load_exchange_ticker_sets() -> tuple[set[str], set[str]]:
    """
    Returns (all_tickers, etf_tickers) from Nasdaq's public symbol directory.
    Falls back to empty sets if the FTP endpoint is unreachable.
    """
    all_tickers: set[str] = set()
    etf_tickers: set[str] = set()

    for url in [NASDAQ_TRADED_URL, OTHER_LISTED_URL]:
        try:
            logger.info(f"Downloading exchange file: {url}")
            r = requests.get(url, timeout=NASDAQ_TIMEOUT)
            r.raise_for_status()
            reader = csv.DictReader(io.StringIO(r.text), delimiter="|")
            for row in reader:
                sym = row.get("Symbol", "").strip()
                if not sym or sym == "Symbol":
                    continue
                if row.get("Test Issue", "").strip().upper() == "Y":
                    continue
                all_tickers.add(sym)
                if row.get("ETF", "").strip().upper() == "Y":
                    etf_tickers.add(sym)
        except Exception as e:
            logger.warning(f"Nasdaq FTP unavailable ({e}). Skipping exchange cross-reference.")

    if all_tickers:
        logger.info(f"Exchange files: {len(all_tickers)} tickers ({len(etf_tickers)} ETFs)")
    else:
        logger.info("Exchange cross-reference skipped — ETF detection via name heuristic only.")
    return all_tickers, etf_tickers


# ── DB ────────────────────────────────────────────────────────────────────────

def load_db_companies(client) -> list[dict]:
    """Load all companies from DB (paginated)."""
    rows = []
    page_size = 1000
    offset = 0
    while True:
        res = (client.table("companies")
               .select("cik, ticker, name")
               .range(offset, offset + page_size - 1)
               .execute())
        rows.extend(res.data)
        if len(res.data) < page_size:
            break
        offset += page_size
    logger.info(f"DB: {len(rows)} companies loaded")
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    client = get_client()
    sec_map        = load_sec_ticker_map()
    all_ex, etf_ex = load_exchange_ticker_sets()
    db_companies   = load_db_companies(client)

    corrections: list[dict] = []  # {cik, old_ticker, new_ticker, reason}
    warnings:    list[str]  = []

    for comp in db_companies:
        cik        = comp["cik"]
        db_ticker  = comp["ticker"] or ""
        db_name    = comp["name"] or ""
        sec_entry  = sec_map.get(cik)

        # 1) SEC-level mismatch
        if sec_entry:
            sec_ticker = sec_entry["ticker"] or ""
            if sec_ticker and sec_ticker != db_ticker:
                corrections.append({
                    "cik":        cik,
                    "old_ticker": db_ticker,
                    "new_ticker": sec_ticker,
                    "name":       db_name,
                    "reason":     "SEC_MISMATCH",
                })
                continue  # will re-evaluate corrected ticker in next pass

        # 2) ETF ticker: either confirmed by exchange file OR
        #    ticker is ETF per name heuristic while company name looks like a real company
        ticker_is_etf = (db_ticker in etf_ex) if etf_ex else False
        # Fallback: if exchange data unavailable, detect via SEC name for the TICKER
        if not ticker_is_etf and not etf_ex and sec_entry:
            # Check if the SEC entry that MATCHES this ticker is a fund
            # (the SEC entry we selected for this CIK is non-fund, but maybe the
            #  DB ticker belongs to a different SEC entry for same CIK)
            pass  # handled implicitly by SEC_MISMATCH above

        if ticker_is_etf and not _is_fund_name(db_name):
            sec_ticker = sec_entry["ticker"] if sec_entry else ""
            new_ticker = sec_ticker if (sec_ticker and sec_ticker != db_ticker) else ""
            corrections.append({
                "cik":        cik,
                "old_ticker": db_ticker,
                "new_ticker": new_ticker,
                "name":       db_name,
                "reason":     "TICKER_IS_ETF",
            })

        # 3) Ticker completely absent from any exchange (OTC is fine, just flag)
        elif db_ticker and db_ticker not in all_ex:
            warnings.append(
                f"  NOT_ON_EXCHANGE  cik={cik}  ticker={db_ticker:<8s}  name={db_name}"
            )

    # ── Filter: common-only mode ──────────────────────────────────────────────
    # Split corrections into "non-common → common" vs "common → common (class change)"
    noncommon_fixes = [
        c for c in corrections
        if c["new_ticker"] and _is_noncommon_ticker(c["old_ticker"])
    ]
    classchange_fixes = [
        c for c in corrections
        if c["new_ticker"] and not _is_noncommon_ticker(c["old_ticker"])
    ]

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"CORRECTIONS TOTAL: {len(corrections)}")
    print(f"  Non-common -> common (warrant/unit/preferred/ADR): {len(noncommon_fixes)}")
    print(f"  Common class change (BRK-A->BRK-B type):          {len(classchange_fixes)}")
    print(f"{'='*70}")

    print(f"\n[NON-COMMON -> COMMON] Warrant/unit/preferred/ADR fixes ({len(noncommon_fixes)})")
    for c in noncommon_fixes[:40]:
        arrow = f"{c['old_ticker']:<10s} -> {c['new_ticker']:<8s}"
        print(f"  cik={c['cik']}  {arrow}  {c['name']}")
    if len(noncommon_fixes) > 40:
        print(f"  ... and {len(noncommon_fixes)-40} more")

    print(f"\n[COMMON CLASS CHANGE] Both tickers are common stock ({len(classchange_fixes)})")
    for c in classchange_fixes[:20]:
        arrow = f"{c['old_ticker']:<10s} -> {c['new_ticker']:<8s}"
        print(f"  cik={c['cik']}  {arrow}  {c['name']}")
    if len(classchange_fixes) > 20:
        print(f"  ... and {len(classchange_fixes)-20} more")

    # ── Apply ─────────────────────────────────────────────────────────────────
    to_apply = noncommon_fixes if COMMON_ONLY else [c for c in corrections if c["new_ticker"]]

    if not APPLY:
        print(f"\nDry-run complete.")
        print(f"  --apply            : applies all {len([c for c in corrections if c['new_ticker']])} corrections")
        print(f"  --apply --common-only: applies {len(noncommon_fixes)} non-common->common fixes only")
        return

    mode = "common-only" if COMMON_ONLY else "all"
    print(f"\nApplying {len(to_apply)} corrections ({mode} mode)...")
    updated = 0
    for c in to_apply:
        try:
            client.table("companies").update({"ticker": c["new_ticker"]}).eq("cik", c["cik"]).execute()
            updated += 1
        except Exception as e:
            logger.warning(f"Failed to update cik={c['cik']}: {e}")
    print(f"Done. {updated}/{len(to_apply)} rows updated.")


if __name__ == "__main__":
    run()
