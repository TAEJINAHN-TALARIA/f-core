# Time-Series Stability Report

_Stub — not yet generated. See instructions below._

This report measures how stable each `(company, concept)` series is over
time — the key quality metric for an intra-company-trend dashboard.

## Why it matters

If AAPL's 10-year revenue chart shows a phantom jump because the
underlying XBRL tag changed (e.g. `Revenues` → `RevenueFromContract...`
after ASC 606 in 2018), a dashboard user could draw the wrong investment
conclusion. This report quantifies how often that happens across the
6,895 companies in our dataset.

## How to generate

```bash
# Requires SUPABASE_URL and SUPABASE_KEY in environment (or .env)
python -m etl.timeseries_stability

# Or preview without writing:
python -m etl.timeseries_stability --dry-run
```

Runtime: ~10–30 min over the full 6,895 companies on a typical
connection (paginated reads from Supabase, ~30 concepts × N pages each).

The script reads only `status=active` tags from `concept_map.json`, so
the deprecation work done in PRs #3 / #5 is reflected automatically.

## What gets measured

For each `(cik, concept)` pair, annual facts only:

1. **Tag identity over time** — same tag throughout, or did it switch?
2. **Discontinuity at switch points** — when a tag changes, is the
   value continuous (legitimate transition like ASC 606) or
   discontinuous (likely mapping issue)?
3. **Simultaneous-tag periods** — multiple tags reported for the same
   `end_date` (a canonical-selection policy will need to handle these).
4. **Phantom YoY jumps** — any year-over-year change > 80%, regardless
   of tag. Includes legitimate M&A / divestitures, but useful for
   spotting outliers worth investigating.

## Thresholds

| Signal | Threshold |
|---|--:|
| Switch discontinuity | `|Δ%| > 30%` |
| Phantom YoY jump | `|Δ%| > 80%` |

Both tunable at the top of `etl/timeseries_stability.py`.
