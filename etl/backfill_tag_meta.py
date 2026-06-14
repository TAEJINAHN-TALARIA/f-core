"""One-shot backfill for `tag_meta` in concept_map.json.

Two passes:
1. Deterministic — apply hand-curated whitelist (canonical seed tags) and
   blacklist (known-wrong tags) directly. Idempotent and LLM-free.
2. LLM — for every remaining tag without meta, ask Gemini to classify its
   scope. Resulting entries default to status=pending_review so human review
   gates promotion to status=active.

Usage:
    python -m etl.backfill_tag_meta --seed-only   # pass 1 only (no API key needed)
    python -m etl.backfill_tag_meta --full        # pass 1 + 2 (requires GEMINI_API_KEY)
    python -m etl.backfill_tag_meta --dry-run     # print diff, don't write
"""
import argparse
import copy
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from .concept_map_schema import VALID_SCOPES, validate_concept_map

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONCEPT_MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "web", "lib", "concept_map.json")
GEMINI_MODEL = "gemini-2.5-flash"

# Canonical seed tags — verified standard US-GAAP totals.
# (concept, tag) → scope. priority=0, status=active, source=seed.
SEED_CANONICAL: dict[tuple[str, str], str] = {
    ("revenue", "Revenues"): "total",
    ("revenue", "RevenueFromContractWithCustomerExcludingAssessedTax"): "total",
    ("revenue", "SalesRevenueNet"): "total",
    ("revenue", "OperatingRevenues"): "total",
    ("revenue", "RegulatedAndUnregulatedOperatingRevenue"): "industry_specific",
    ("revenue", "FinancialServicesRevenue"): "industry_specific",
    ("revenue", "RealEstateRevenueNet"): "industry_specific",
    ("gross_profit", "GrossProfit"): "total",
    ("operating_income", "OperatingIncomeLoss"): "total",
    ("net_income", "NetIncomeLoss"): "total",
    ("net_income", "ProfitLoss"): "total",
    ("eps_basic", "EarningsPerShareBasic"): "total",
    ("eps_diluted", "EarningsPerShareDiluted"): "total",
    ("diluted_shares", "WeightedAverageNumberOfDilutedSharesOutstanding"): "total",
    ("sbc", "ShareBasedCompensation"): "total",
    ("sbc", "AllocatedShareBasedCompensationExpense"): "total",
    ("rnd", "ResearchAndDevelopmentExpense"): "total",
    ("interest_expense", "InterestExpense"): "total",
    ("income_tax", "IncomeTaxExpenseBenefit"): "total",
    ("depreciation", "DepreciationDepletionAndAmortization"): "total",
    ("depreciation", "DepreciationAndAmortization"): "total",
    ("depreciation", "DepreciationAmortizationAndAccretionNet"): "total",
    ("depreciation", "Depreciation"): "total",
    ("assets", "Assets"): "total",
    ("assets_current", "AssetsCurrent"): "total",
    ("liabilities", "Liabilities"): "total",
    ("liabilities_current", "LiabilitiesCurrent"): "total",
    ("equity", "StockholdersEquity"): "total",
    ("equity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"): "total",
    ("long_term_debt", "LongTermDebt"): "total",
    ("cash_equivalents", "CashAndCashEquivalentsAtCarryingValue"): "total",
    ("cash_equivalents", "CashEquivalentsAtCarryingValue"): "total",
    ("retained_earnings", "RetainedEarningsAccumulatedDeficit"): "total",
    ("shares_outstanding", "CommonStockSharesOutstanding"): "total",
    ("shares_outstanding", "SharesOutstanding"): "total",
    ("shares_issued", "CommonStockSharesIssued"): "total",
    ("shares_issued", "SharesIssued"): "total",
    ("shares_issued", "PreferredStockSharesIssued"): "industry_specific",
    ("ppne_net", "PropertyPlantAndEquipmentNet"): "total",
    ("ppne_net", "PublicUtilitiesPropertyPlantAndEquipmentNet"): "industry_specific",
    ("operating_cash_flow", "NetCashProvidedByUsedInOperatingActivities"): "total",
    ("operating_cash_flow", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"): "total",
    ("investing_cash_flow", "NetCashProvidedByUsedInInvestingActivities"): "total",
    ("investing_cash_flow", "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations"): "total",
    ("financing_cash_flow", "NetCashProvidedByUsedInFinancingActivities"): "total",
    ("financing_cash_flow", "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations"): "total",
    ("capex", "PaymentsToAcquirePropertyPlantAndEquipment"): "total",
    ("stock_repurchase", "PaymentsForRepurchaseOfCommonStock"): "total",
    ("stock_repurchase", "PaymentsForRepurchaseOfEquity"): "total",
    ("dividends_paid", "PaymentsOfDividends"): "total",
    ("dividends_paid", "PaymentsOfDividendsCommonStock"): "total",
    ("dividends_paid", "PaymentsOfDividendsPreferredStockAndPreferenceStock"): "industry_specific",
    ("dividends_paid", "PaymentsOfDividendsMinorityInterest"): "industry_specific",
}

# Known-wrong tags: same concept slot but semantically different measurement.
# Marked deprecated so future ETL/API logic can exclude them.
SEED_DEPRECATED: dict[tuple[str, str], str] = {
    ("sbc", "StockIssuedDuringPeriodValueShareBasedCompensation"):
        "share issuance VALUE, not compensation expense",
    ("sbc", "StockGrantedDuringPeriodValueSharebasedCompensation"):
        "share grant VALUE, not compensation expense",
    ("sbc", "EmployeeBenefitsAndShareBasedCompensation"):
        "bundled with other employee benefits, not pure SBC",
    ("shares_outstanding", "WeightedAverageNumberOfSharesOutstandingBasic"):
        "weighted average for EPS, not period-end outstanding",
    ("shares_issued", "ConversionOfStockSharesIssued1"):
        "period event (shares issued via conversion), not cumulative issued",
    ("dividends_paid", "OtherPreferredStockDividendsAndAdjustments"):
        "income statement adjustment, not cash flow payment",
}


def _seed_meta_entry(scope: str) -> dict:
    return {
        "scope": scope,
        "status": "active",
        "priority": 0,
        "provenance": {
            "source": "seed",
            "discovered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }


def _deprecated_meta_entry(notes: str) -> dict:
    return {
        "scope": "total",  # placeholder; status overrides usage
        "status": "deprecated",
        "priority": 999,
        "provenance": {
            "source": "manual",
            "discovered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "notes": notes,
    }


def _llm_meta_entry(scope: str, notes: str | None = None) -> dict:
    entry = {
        "scope": scope if scope in VALID_SCOPES else "total",
        "status": "pending_review",
        "priority": 500,
        "provenance": {
            "source": "auto_llm",
            "discovered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": GEMINI_MODEL,
        },
    }
    if notes:
        entry["notes"] = notes
    return entry


def apply_seed(concept_map: dict) -> dict[str, int]:
    """Apply whitelist + blacklist. Returns counters. Does NOT overwrite existing meta."""
    stats = {"added_canonical": 0, "added_deprecated": 0, "skipped_existing": 0, "skipped_missing_tag": 0}

    for (concept, tag), scope in SEED_CANONICAL.items():
        if concept not in concept_map:
            continue
        if tag not in concept_map[concept].get("tags", []):
            stats["skipped_missing_tag"] += 1
            continue
        tag_meta = concept_map[concept].setdefault("tag_meta", {})
        if tag in tag_meta:
            stats["skipped_existing"] += 1
            continue
        tag_meta[tag] = _seed_meta_entry(scope)
        stats["added_canonical"] += 1

    for (concept, tag), notes in SEED_DEPRECATED.items():
        if concept not in concept_map:
            continue
        if tag not in concept_map[concept].get("tags", []):
            stats["skipped_missing_tag"] += 1
            continue
        tag_meta = concept_map[concept].setdefault("tag_meta", {})
        if tag in tag_meta:
            stats["skipped_existing"] += 1
            continue
        tag_meta[tag] = _deprecated_meta_entry(notes)
        stats["added_deprecated"] += 1

    return stats


def _gather_unmeta_tags(concept_map: dict) -> dict[str, list[str]]:
    """Return {concept: [tags without meta]} — input for LLM pass."""
    out = {}
    for concept, info in concept_map.items():
        meta_keys = info.get("tag_meta", {}).keys()
        missing = [t for t in info.get("tags", []) if t not in meta_keys]
        if missing:
            out[concept] = missing
    return out


def _call_gemini_for_scope(unmeta: dict[str, list[str]]) -> dict[str, dict[str, dict]]:
    """Ask LLM to classify scope for tags missing meta. Returns {concept: {tag: {scope, notes}}}."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set — required for --full mode.")

    prompt = (
        "Classify the SCOPE of US-GAAP XBRL tags within each financial concept.\n"
        "Scopes:\n"
        '- "total":             aggregate value for the whole company (e.g. Revenues, Assets)\n'
        '- "industry_specific": industry-standard variant of a total (e.g. FinancialServicesRevenue for banks)\n'
        '- "component":         a narrower part of a total (e.g. InterestExpenseLongTermDebt)\n'
        '- "segment":           a business-segment breakdown (e.g. BrokerageCommissionsRevenue)\n\n'
        "Concepts and their tags to classify:\n"
    )
    for concept, tags in unmeta.items():
        prompt += f"\n{concept}:\n"
        for t in tags:
            prompt += f"  - {t}\n"

    prompt += """
Return ONLY a valid JSON object, no markdown fences. Shape:
{
  "<concept>": {
    "<tag>": {"scope": "<scope>", "notes": "<one short clause>"}
  }
}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:streamGenerateContent?alt=sse&key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"thinkingConfig": {"thinkingBudget": 1024}},
    }

    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                stream=True,
                timeout=(15, 120),
            )
            response.raise_for_status()

            full_text = ""
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    chunk = json.loads(data_str)
                    parts = chunk.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])
                    for part in parts:
                        if not part.get("thought"):
                            full_text += part.get("text", "")
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

            raw = full_text.strip()
            if raw.startswith("```json"):
                raw = raw[7:-3].strip()
            elif raw.startswith("```"):
                raw = raw[3:-3].strip()
            return json.loads(raw)

        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = 4 * (2 ** attempt)
            logger.warning(f"LLM call failed ({e}); retrying in {delay}s")
            time.sleep(delay)
    return {}


def apply_llm(concept_map: dict) -> dict[str, int]:
    """LLM-classify all tags missing meta. Returns counters."""
    stats = {"llm_added": 0, "llm_skipped_unknown_tag": 0}
    unmeta = _gather_unmeta_tags(concept_map)
    if not unmeta:
        logger.info("Nothing for LLM pass — all tags already have meta.")
        return stats

    total = sum(len(v) for v in unmeta.values())
    logger.info(f"LLM pass: {total} tags across {len(unmeta)} concepts.")
    result = _call_gemini_for_scope(unmeta)

    for concept, tag_to_meta in result.items():
        if concept not in concept_map:
            continue
        existing_tags = set(concept_map[concept].get("tags", []))
        tag_meta = concept_map[concept].setdefault("tag_meta", {})
        for tag, meta in tag_to_meta.items():
            if tag not in existing_tags:
                stats["llm_skipped_unknown_tag"] += 1
                continue
            if tag in tag_meta:
                continue
            tag_meta[tag] = _llm_meta_entry(meta.get("scope"), meta.get("notes"))
            stats["llm_added"] += 1

    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seed-only", action="store_true", help="Apply whitelist+blacklist only (no LLM).")
    mode.add_argument("--full", action="store_true", help="Apply seed pass, then LLM-fill the rest.")
    ap.add_argument("--dry-run", action="store_true", help="Print result, do not write.")
    args = ap.parse_args()

    with open(CONCEPT_MAP_PATH, "r", encoding="utf-8") as f:
        original = json.load(f)
    working = copy.deepcopy(original)

    seed_stats = apply_seed(working)
    logger.info(f"Seed pass: {seed_stats}")

    if args.full:
        llm_stats = apply_llm(working)
        logger.info(f"LLM pass: {llm_stats}")

    errors = validate_concept_map(working)
    if errors:
        logger.error(f"Validation failed after backfill ({len(errors)} errors):")
        for e in errors[:20]:
            logger.error(f"  - {e}")
        return 2

    if args.dry_run:
        print(json.dumps(working, indent=4))
        return 0

    if working == original:
        logger.info("No changes to write.")
        return 0

    with open(CONCEPT_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(working, f, indent=4)
    logger.info(f"✅ Wrote {CONCEPT_MAP_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
