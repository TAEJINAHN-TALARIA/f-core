"""
facts=0 + (non-common ticker pattern OR fund name pattern) companies removal.

Usage:
  python -m etl.purge_nonfacts          # dry-run
  python -m etl.purge_nonfacts --apply  # delete from DB
"""
import os
import re
import sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from .loader import get_client

APPLY = "--apply" in sys.argv

_NONCOMMON_TICKER = re.compile(
    r'.+W[ST]?$'
    r'|.+U[U]?$'
    r'|-UN$'
    r'|.+R[T]?$'
    r'|-P[A-Z]{0,2}$'
    r'|-W[ST]?$'
)

_FUND_NAME = re.compile(
    r'\b(fund|trust|etf|note|bond|preferred|warrant|unit|'
    r'depositary|receipt|index|commodity|income|yield|'
    r'dividend|series|municipal|muni|closed.end|interval)\b',
    re.IGNORECASE,
)

def is_noncommon_ticker(t):
    return bool(_NONCOMMON_TICKER.match(t.upper()))

def is_fund_name(name):
    return bool(_FUND_NAME.search(name))


def run():
    client = get_client()

    print("Collecting CIKs with facts...")
    facts_ciks = set()
    offset, page = 0, 1000
    while True:
        res = (client.table("facts")
               .select("cik")
               .range(offset, offset + page - 1)
               .execute())
        for r in res.data:
            facts_ciks.add(r["cik"])
        if len(res.data) < page:
            break
        offset += page
    print(f"  CIKs with facts: {len(facts_ciks)}")

    print("Loading companies...")
    companies = []
    offset = 0
    while True:
        res = (client.table("companies")
               .select("cik, ticker, name")
               .range(offset, offset + page - 1)
               .execute())
        companies.extend(res.data)
        if len(res.data) < page:
            break
        offset += page
    print(f"  Total companies: {len(companies)}")

    no_facts = [c for c in companies if c["cik"] not in facts_ciks]
    to_delete = []
    keep_inspect = []

    for c in no_facts:
        ticker = c.get("ticker") or ""
        name   = c.get("name")   or ""
        if is_noncommon_ticker(ticker) or is_fund_name(name):
            to_delete.append(c)
        else:
            keep_inspect.append(c)

    print(f"\n{'='*65}")
    print(f"PURGE REPORT")
    print(f"  Companies with no facts : {len(no_facts)}")
    print(f"  To delete (bad pattern) : {len(to_delete)}")
    print(f"  To keep   (foreign etc) : {len(keep_inspect)}")
    print(f"{'='*65}")

    print(f"\n[DELETE CANDIDATES — first 40]")
    for c in to_delete[:40]:
        reason = "ticker" if is_noncommon_ticker(c.get("ticker","")) else "name"
        print(f"  [{reason}]  {c['ticker']:<10s}  {c['name']}")
    if len(to_delete) > 40:
        print(f"  ... and {len(to_delete)-40} more")

    print(f"\n[KEEP — foreign/micro-cap, first 20]")
    for c in keep_inspect[:20]:
        print(f"  {c['ticker']:<10s}  {c['name']}")
    if len(keep_inspect) > 20:
        print(f"  ... and {len(keep_inspect)-20} more")

    if not APPLY:
        print(f"\nDry-run done. Run with --apply to delete {len(to_delete)} rows.")
        return

    print(f"\nDeleting {len(to_delete)} rows...")
    deleted = 0
    for c in to_delete:
        try:
            client.table("companies").delete().eq("cik", c["cik"]).execute()
            deleted += 1
        except Exception as e:
            print(f"  FAIL cik={c['cik']}: {e}")
    print(f"Done. {deleted}/{len(to_delete)} deleted. Remaining: {len(companies)-deleted}")


if __name__ == "__main__":
    run()
