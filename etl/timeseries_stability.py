"""Time-series stability analysis for company-level concept tracking.

For an investment dashboard where the primary use case is intra-company
trends (e.g. AAPL's 10-year revenue line), the worst failure mode is a
phantom jump caused by the underlying XBRL tag changing across reporting
periods. This script scans the facts table to quantify how often that
happens and surfaces the worst cases.

Usage:
    python -m etl.timeseries_stability                # write docs/timeseries_stability.md
    python -m etl.timeseries_stability --dry-run      # print to stdout only

Requires SUPABASE_URL and SUPABASE_KEY in the environment.
"""
import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

from .loader import get_client
from .config import CONCEPT_MAP_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "timeseries_stability.md")
PAGE_SIZE = 1000

# Tunable thresholds.
SWITCH_DISCONTINUITY_PCT = 30.0   # |Δ%| at a tag-switch year above this = suspicious
PHANTOM_JUMP_PCT = 80.0           # |Δ%| YoY (any cause) above this = flag for review
TOP_N_PER_CONCEPT = 20            # worst cases surfaced in the report


def _load_active_tags() -> dict[str, list[str]]:
    """{concept: [active tag names]} — deprecated tags are excluded so the
    analysis measures the system as it should look after curation."""
    with open(CONCEPT_MAP_PATH, "r", encoding="utf-8") as f:
        cmap = json.load(f)
    out = {}
    for concept, info in cmap.items():
        meta = info.get("tag_meta", {})
        active = [t for t in info.get("tags", [])
                  if meta.get(t, {}).get("status") == "active"]
        if active:
            out[concept] = active
    return out


def _fetch_annual_facts(client, tags: list[str]) -> list[dict]:
    """Paginated select: every annual fact for these tags."""
    rows = []
    offset = 0
    while True:
        res = (client.table("facts")
               .select("cik,tag,end_date,value")
               .in_("tag", tags)
               .eq("period_type", "annual")
               .lte("end_date", "today")  # exclude future-dated facts (see CLAUDE.md)
               .range(offset, offset + PAGE_SIZE - 1)
               .execute())
        if not res.data:
            break
        rows.extend(res.data)
        if len(res.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def _get_companies(client) -> dict[str, str]:
    """{cik: name} for human-readable report."""
    res = client.table("companies").select("cik,name").execute()
    return {r["cik"]: r["name"] for r in (res.data or [])}


def _analyze_concept(concept: str, tags: list[str], rows: list[dict]) -> dict:
    """Return per-concept stats + list of worst-case (cik, ...) findings."""
    # Group: cik -> end_date -> {tag: value}
    by_cik: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        by_cik[r["cik"]][r["end_date"]][r["tag"]] = float(r["value"])

    findings = []
    stats = {
        "companies_with_data": 0,
        "single_tag_throughout": 0,
        "multi_tag_clean": 0,
        "multi_tag_with_discontinuity": 0,
        "simultaneous_tag_periods": 0,
        "phantom_yoy_jumps": 0,
    }

    for cik, periods in by_cik.items():
        stats["companies_with_data"] += 1
        # Time-ordered series
        sorted_dates = sorted(periods.keys())
        tags_seen = set()
        for d in sorted_dates:
            tags_seen.update(periods[d].keys())

        # Detect simultaneous-tag periods
        simul_periods = [d for d in sorted_dates if len(periods[d]) > 1]
        if simul_periods:
            stats["simultaneous_tag_periods"] += len(simul_periods)
            findings.append({
                "type": "simultaneous",
                "cik": cik,
                "dates": simul_periods[:3],  # truncate for readability
                "tags_per_date": {d: list(periods[d].keys()) for d in simul_periods[:3]},
            })

        # Single tag throughout?
        if len(tags_seen) == 1:
            stats["single_tag_throughout"] += 1
        else:
            # Multiple tags used — check for discontinuity at switch
            # Use a canonical per-period value: max value across simultaneous tags
            # (arbitrary but consistent; real selection would be the canonical algorithm)
            series = [(d, list(periods[d].keys())[0], list(periods[d].values())[0])
                      for d in sorted_dates]
            had_discontinuity = False
            for i in range(1, len(series)):
                prev_d, prev_tag, prev_v = series[i-1]
                cur_d, cur_tag, cur_v = series[i]
                if prev_tag != cur_tag and prev_v != 0:
                    pct = abs((cur_v - prev_v) / prev_v) * 100
                    if pct > SWITCH_DISCONTINUITY_PCT:
                        had_discontinuity = True
                        findings.append({
                            "type": "switch_discontinuity",
                            "cik": cik,
                            "at": cur_d,
                            "from_tag": prev_tag, "to_tag": cur_tag,
                            "from_value": prev_v, "to_value": cur_v,
                            "pct_change": pct,
                        })
            if had_discontinuity:
                stats["multi_tag_with_discontinuity"] += 1
            else:
                stats["multi_tag_clean"] += 1

        # Phantom YoY jumps regardless of tag — flag the biggest only
        series_vals = [(d, max(periods[d].values())) for d in sorted_dates]
        biggest_jump = None
        for i in range(1, len(series_vals)):
            prev_d, prev_v = series_vals[i-1]
            cur_d, cur_v = series_vals[i]
            if prev_v == 0:
                continue
            pct = abs((cur_v - prev_v) / prev_v) * 100
            if pct > PHANTOM_JUMP_PCT and (biggest_jump is None or pct > biggest_jump["pct_change"]):
                biggest_jump = {
                    "type": "phantom_jump",
                    "cik": cik,
                    "at": cur_d,
                    "from_value": prev_v, "to_value": cur_v,
                    "pct_change": pct,
                }
        if biggest_jump:
            stats["phantom_yoy_jumps"] += 1
            findings.append(biggest_jump)

    return {"stats": stats, "findings": findings, "tag_set_size": len(tags)}


def _render_report(per_concept: dict[str, dict], companies: dict[str, str]) -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total_pairs = sum(c["stats"]["companies_with_data"] for c in per_concept.values())
    total_clean = sum(c["stats"]["single_tag_throughout"] + c["stats"]["multi_tag_clean"]
                      for c in per_concept.values())
    pct_clean = (100 * total_clean / total_pairs) if total_pairs else 0

    lines = []
    lines.append(f"# Time-Series Stability Report")
    lines.append("")
    lines.append(f"_Generated {now}_")
    lines.append("")
    lines.append(f"Scope: annual facts, `status=active` tags only.")
    lines.append(f"Thresholds: switch discontinuity > {SWITCH_DISCONTINUITY_PCT}%, "
                 f"phantom YoY jump > {PHANTOM_JUMP_PCT}%.")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(f"- Total `(company, concept)` pairs analyzed: **{total_pairs:,}**")
    lines.append(f"- Stable (single-tag throughout, or multi-tag without discontinuity): **{total_clean:,} ({pct_clean:.1f}%)**")
    lines.append("")
    lines.append("## Per-concept summary")
    lines.append("")
    lines.append("| concept | companies | single-tag | multi-tag clean | multi-tag discontinuity | simultaneous periods | phantom jumps |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|")
    for concept in sorted(per_concept):
        s = per_concept[concept]["stats"]
        lines.append(f"| `{concept}` | {s['companies_with_data']:,} | {s['single_tag_throughout']:,} | "
                     f"{s['multi_tag_clean']:,} | {s['multi_tag_with_discontinuity']:,} | "
                     f"{s['simultaneous_tag_periods']:,} | {s['phantom_yoy_jumps']:,} |")
    lines.append("")
    lines.append(f"## Worst cases (top {TOP_N_PER_CONCEPT} per concept)")
    lines.append("")
    for concept in sorted(per_concept):
        findings = per_concept[concept]["findings"]
        if not findings:
            continue
        # Sort: discontinuity by pct, simultaneous by date count, phantom by pct
        discont = sorted([f for f in findings if f["type"] == "switch_discontinuity"],
                         key=lambda f: -f["pct_change"])[:TOP_N_PER_CONCEPT]
        simul = [f for f in findings if f["type"] == "simultaneous"][:5]
        phantom = sorted([f for f in findings if f["type"] == "phantom_jump"],
                         key=lambda f: -f["pct_change"])[:10]
        if not (discont or simul or phantom):
            continue
        lines.append(f"### `{concept}`")
        lines.append("")
        if discont:
            lines.append("**Tag-switch discontinuities**")
            lines.append("")
            lines.append("| company | year | from | to | Δ% |")
            lines.append("|---|---|---|---|--:|")
            for f in discont:
                name = companies.get(f["cik"], f["cik"])
                lines.append(f"| {name} | {f['at'][:4]} | `{f['from_tag']}` | `{f['to_tag']}` | "
                             f"{f['pct_change']:.1f}% |")
            lines.append("")
        if simul:
            lines.append("**Simultaneous-tag periods (multiple tags reported for same date)**")
            lines.append("")
            for f in simul:
                name = companies.get(f["cik"], f["cik"])
                lines.append(f"- {name}: {list(f['tags_per_date'].items())[:2]}")
            lines.append("")
        if phantom:
            lines.append("**Largest YoY jumps (any cause — may include real M&A / divestitures)**")
            lines.append("")
            lines.append("| company | year | Δ% |")
            lines.append("|---|---|--:|")
            for f in phantom:
                name = companies.get(f["cik"], f["cik"])
                lines.append(f"| {name} | {f['at'][:4]} | {f['pct_change']:.1f}% |")
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print report to stdout, do not write.")
    args = ap.parse_args()

    client = get_client()
    active_tags = _load_active_tags()
    logger.info(f"Analyzing {len(active_tags)} concepts.")

    companies = _get_companies(client)
    logger.info(f"Loaded {len(companies)} companies.")

    per_concept = {}
    for concept, tags in active_tags.items():
        logger.info(f"  Fetching '{concept}' ({len(tags)} active tags)...")
        rows = _fetch_annual_facts(client, tags)
        logger.info(f"    {len(rows):,} annual facts")
        per_concept[concept] = _analyze_concept(concept, tags, rows)

    report = _render_report(per_concept, companies)

    if args.dry_run:
        print(report)
        return 0

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"✅ Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
