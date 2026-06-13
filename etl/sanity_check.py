"""
Quick data quality sanity check.
Usage: python -m etl.sanity_check
"""
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from .loader import get_client
from .config import CONCEPT_MAP

client = get_client()

SAMPLE_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "XOM"]

# ── concept → canonical tag (highest-priority per concept_map ordering)
CONCEPT_TOP_TAG = {c: info["tags"][-1] for c, info in CONCEPT_MAP.items() if info.get("tags")}
ALL_CONCEPT_TAGS = {tag: c for c, info in CONCEPT_MAP.items() for tag in info.get("tags", [])}

def get_cik(ticker):
    res = client.table("companies").select("cik, name").eq("ticker", ticker).single().execute()
    return res.data["cik"], res.data["name"]

def get_recent_facts(cik, tags, period_type="annual"):
    res = (client.table("facts")
           .select("tag, end_date, value, period_type")
           .eq("cik", cik)
           .in_("tag", tags)
           .eq("period_type", period_type)
           .lte("end_date", "2026-01-01")
           .order("end_date", desc=True)
           .limit(20)
           .execute())
    return res.data

def get_recent_metrics(cik, period_type="annual"):
    res = (client.table("metrics")
           .select("metric, end_date, value")
           .eq("cik", cik)
           .eq("period_type", period_type)
           .lte("end_date", "2026-01-01")
           .order("end_date", desc=True)
           .limit(30)
           .execute())
    return res.data

def fmt(v):
    if v is None:
        return "N/A"
    if abs(v) >= 1e9:
        return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"{v:.4f}"

print("=" * 70)
print("SANITY CHECK - major companies, most recent annual period")
print("=" * 70)

revenue_tags = CONCEPT_MAP["revenue"]["tags"]
gp_tags = CONCEPT_MAP["gross_profit"]["tags"]
ni_tags = CONCEPT_MAP["net_income"]["tags"]
key_facts_tags = revenue_tags + gp_tags + ni_tags

for ticker in SAMPLE_TICKERS:
    try:
        cik, name = get_cik(ticker)
    except Exception:
        print(f"\n{ticker}: NOT FOUND in companies table")
        continue

    facts = get_recent_facts(cik, key_facts_tags)
    metrics = get_recent_metrics(cik)

    # Group facts by (end_date, tag) - take latest if dupes
    best_fact = {}
    for f in facts:
        k = (f["end_date"], f["tag"])
        if k not in best_fact:
            best_fact[k] = f

    # Pick most recent year
    dates = sorted({k[0] for k in best_fact}, reverse=True)
    latest_date = dates[0] if dates else None

    if not latest_date:
        print(f"\n{ticker} ({name}): NO FACTS FOUND")
        continue

    # Revenue: pick first matching tag
    rev = next((best_fact[(latest_date, t)]["value"]
                for t in revenue_tags if (latest_date, t) in best_fact), None)
    gp  = next((best_fact[(latest_date, t)]["value"]
                for t in gp_tags    if (latest_date, t) in best_fact), None)
    ni  = next((best_fact[(latest_date, t)]["value"]
                for t in ni_tags    if (latest_date, t) in best_fact), None)

    # How many revenue tags matched this company/date?
    rev_hits = [t for t in revenue_tags if (latest_date, t) in best_fact]

    # Metrics
    m = {r["metric"]: r["value"] for r in metrics if r["end_date"] == latest_date}

    gross_margin = m.get("gross_margin")
    net_margin   = m.get("net_margin")

    # Flag anomalies
    flags = []
    if gross_margin is not None and (gross_margin > 1.5 or gross_margin < -1.0):
        flags.append(f"GROSS_MARGIN ANOMALY={gross_margin:.3f}")
    if net_margin is not None and (net_margin > 1.0 or net_margin < -2.0):
        flags.append(f"NET_MARGIN ANOMALY={net_margin:.3f}")
    if len(rev_hits) > 1:
        flags.append(f"MULTI-REV-TAG ({len(rev_hits)}): {rev_hits}")

    flag_str = "  ⚠ " + " | ".join(flags) if flags else ""

    print(f"\n{ticker} ({name}) - {latest_date}")
    print(f"  Revenue:      {fmt(rev)}")
    print(f"  Gross Profit: {fmt(gp)}")
    print(f"  Net Income:   {fmt(ni)}")
    print(f"  Gross Margin: {gross_margin:.3f}" if gross_margin is not None else "  Gross Margin: N/A")
    print(f"  Net Margin:   {net_margin:.3f}"   if net_margin   is not None else "  Net Margin:   N/A")
    if flag_str:
        print(flag_str)

print("\n" + "=" * 70)
print("METRICS DISTRIBUTION CHECK (all companies, annual)")
print("=" * 70)

for metric, lo, hi in [("gross_margin", -1.0, 1.5), ("net_margin", -2.0, 1.0)]:
    # Count outliers
    res = (client.table("metrics")
           .select("cik, end_date, value")
           .eq("metric", metric)
           .eq("period_type", "annual")
           .lte("end_date", "2026-01-01")
           .execute())
    rows = res.data
    total = len(rows)
    outliers = [r for r in rows if r["value"] < lo or r["value"] > hi]
    extremes = sorted(outliers, key=lambda r: abs(r["value"]), reverse=True)[:5]
    print(f"\n{metric}: {total} rows, {len(outliers)} outliers (outside [{lo}, {hi}])")
    for e in extremes:
        print(f"  cik={e['cik']} date={e['end_date']} value={e['value']:.4f}")
