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

    # Curated after first pending_review round (LLM-suggested, human-verified).
    ("revenue", "ManagementFeesRevenue"): "component",
    ("revenue", "AdvertisingRevenue"): "component",
    ("revenue", "SalesRevenueGoodsNet"): "component",
    ("revenue", "SalesRevenueServicesNet"): "component",
    ("revenue", "LicenseAndServicesRevenue"): "component",
    ("revenue", "ReimbursementRevenue"): "component",
    ("revenue", "RevenueFromGrants"): "component",
    ("revenue", "BrokerageCommissionsRevenue"): "segment",
    ("revenue", "GoldProductsAndServicesRevenue"): "industry_specific",
    ("revenue", "RefiningAndMarketingRevenue"): "industry_specific",
    ("revenue", "HealthCareOrganizationRevenue"): "industry_specific",
    ("sbc", "AllocatedShareBasedCompensationExpenseNetOfTax"): "component",
    ("rnd", "OtherResearchAndDevelopmentExpense"): "component",
    ("interest_expense", "InterestExpenseDebt"): "component",
    ("interest_expense", "InterestExpenseLongTermDebt"): "component",
    ("interest_expense", "InterestExpenseBorrowings"): "component",
    ("interest_expense", "InterestExpenseDebtExcludingAmortization"): "component",
    ("interest_expense", "FinanceLeaseInterestExpense"): "component",
    ("interest_expense", "InterestExpenseLesseeAssetsUnderCapitalLease"): "component",
    ("interest_expense", "InterestExpenseOperating"): "component",
    ("interest_expense", "InterestExpenseNonoperating"): "component",
    ("interest_expense", "InterestExpenseOther"): "component",
    ("interest_expense", "InterestExpenseRelatedParty"): "component",
    ("interest_expense", "FinancingInterestExpense"): "component",
    ("income_tax", "CurrentIncomeTaxExpenseBenefit"): "component",
    ("depreciation", "CostOfServicesDepreciationAndAmortization"): "component",
    ("depreciation", "CostOfGoodsAndServicesSoldDepreciationAndAmortization"): "component",
    ("depreciation", "OtherDepreciationAndAmortization"): "component",
    ("assets_current", "DepositsAssetsCurrent"): "component",
    ("assets_current", "DerivativeAssetsCurrent"): "component",
    ("liabilities_current", "DeferredTaxLiabilitiesCurrent"): "component",
    ("long_term_debt", "SubordinatedLongTermDebt"): "component",
    ("long_term_debt", "UnsecuredLongTermDebt"): "component",
    ("long_term_debt", "SecuredLongTermDebt"): "component",
    ("long_term_debt", "OtherLongTermDebt"): "component",
    ("cash_equivalents", "CashCashEquivalentsAndFederalFundsSold"): "industry_specific",
    ("capex", "PaymentsForConstructionAndAcquisitionOfPropertyPlantAndEquipment"): "total",
    ("financing_cash_flow", "ProceedsFromPaymentsForOtherFinancingActivities"): "component",
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

    # Curated after first pending_review round.
    ("revenue", "ResultsOfOperationsRevenueFromOilAndGasProducingActivities"):
        "ASC 932 oil & gas supplementary disclosure, not income-statement revenue",
    ("gross_profit", "EquityMethodInvestmentSummarizedFinancialInformationGrossProfitLoss"):
        "equity-method investee's gross profit, not the reporter's own",
    ("gross_profit", "RetailLandSalesInstallmentMethodGrossProfitDeferred"):
        "deferred gross profit from installment sales, not current-period gross profit",
    ("net_income", "ResultsOfOperationsOilAndGasProducingActivitiesNetIncomeExcludingCorporateOverheadAndInterestCosts"):
        "oil & gas segment NI excluding corporate overhead, not company-wide NI",
    ("eps_basic", "EarningsPerShareBasicUndistributed"):
        "undistributed earnings per share variant, not standard basic EPS",
    ("sbc", "IncomeTaxReconciliationNondeductibleExpenseShareBasedCompensationCost"):
        "nondeductible-for-tax SBC portion in rate reconciliation, not SBC expense itself",
    ("sbc", "EmployeeServiceShareBasedCompensationAllocationOfRecognizedPeriodCostsCapitalizedAmount"):
        "capitalized portion of SBC (added to assets), not P&L expense",
    ("sbc", "AdjustmentsRelatedToTaxWithholdingForShareBasedCompensation"):
        "RSU tax-withholding adjustment, not SBC expense",
    ("sbc", "PaymentsRelatedToTaxWithholdingForShareBasedCompensation"):
        "RSU tax-withholding cash outflow, not SBC expense",
    ("depreciation", "SegmentReportingInformationDepreciationDepletionAndAmortizationExpense"):
        "segment-reporting footnote item, not company-wide D&A",
    ("depreciation", "ResultsOfOperationsDepreciationDepletionAndAmortizationAndValuationProvisions"):
        "ASC 932 oil & gas supplementary disclosure, not income-statement D&A",
    ("long_term_debt", "DebtDefaultLongtermDebtAmount"):
        "amount of long-term debt in default, not total long-term debt balance",
    ("long_term_debt", "LongTermDebtAndCapitalLeaseObligations"):
        "includes capital lease obligations — broader than pure long-term debt",
    ("long_term_debt", "BusinessAcquisitionPurchasePriceAllocationNotesPayableAndLongTermDebt"):
        "M&A purchase price allocation entry, not standing debt balance",
    ("cash_equivalents", "CashCashEquivalentsAndShortTermInvestments"):
        "includes short-term investments — broader than cash equivalents",
    ("shares_outstanding", "TemporaryEquitySharesOutstanding"):
        "mezzanine/temporary equity shares, not common stock outstanding",
    ("ppne_net", "DisposalGroupIncludingDiscontinuedOperationPropertyPlantAndEquipmentNet"):
        "PP&E held for disposal / discontinued ops, not in-service PP&E",
    ("stock_repurchase", "PaymentsForRepurchaseOfCommonStockForEmployeeTaxWithholdingObligations"):
        "RSU net-settlement tax remittance, not a buyback program payment",
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
    """Apply whitelist + blacklist. Returns counters.

    For each (concept, tag) in the seed lists:
    - If no meta exists → add the seed entry.
    - If meta exists with status=pending_review → OVERWRITE. The seed lists
      are the human-curated source of truth; this is the promotion path
      from LLM-suggested to verified.
    - If meta exists with status in {active, deprecated} → skip (already
      curated; the seed entry is redundant or a conflict).
    """
    stats = {
        "added_canonical": 0, "added_deprecated": 0,
        "promoted_to_active": 0, "promoted_to_deprecated": 0,
        "skipped_existing": 0, "skipped_missing_tag": 0,
    }

    for (concept, tag), scope in SEED_CANONICAL.items():
        if concept not in concept_map:
            continue
        if tag not in concept_map[concept].get("tags", []):
            stats["skipped_missing_tag"] += 1
            continue
        tag_meta = concept_map[concept].setdefault("tag_meta", {})
        existing = tag_meta.get(tag)
        if existing is None:
            tag_meta[tag] = _seed_meta_entry(scope)
            stats["added_canonical"] += 1
        elif existing.get("status") == "pending_review":
            tag_meta[tag] = _seed_meta_entry(scope)
            stats["promoted_to_active"] += 1
        else:
            stats["skipped_existing"] += 1

    for (concept, tag), notes in SEED_DEPRECATED.items():
        if concept not in concept_map:
            continue
        if tag not in concept_map[concept].get("tags", []):
            stats["skipped_missing_tag"] += 1
            continue
        tag_meta = concept_map[concept].setdefault("tag_meta", {})
        existing = tag_meta.get(tag)
        if existing is None:
            tag_meta[tag] = _deprecated_meta_entry(notes)
            stats["added_deprecated"] += 1
        elif existing.get("status") == "pending_review":
            tag_meta[tag] = _deprecated_meta_entry(notes)
            stats["promoted_to_deprecated"] += 1
        else:
            stats["skipped_existing"] += 1

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
