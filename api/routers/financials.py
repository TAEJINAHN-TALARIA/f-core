from fastapi import APIRouter, Depends, Query
from supabase import Client

from ..dependencies import get_supabase
from ..schemas import (
    FactPoint,
    Filing,
    FilingsResponse,
    FinancialsResponse,
    MetricPoint,
    MetricsResponse,
    TTMItem,
    TTMResponse,
)
from ..services.ttm import compute_ttm

router = APIRouter()

# Canonical tag sets per financial statement
INCOME_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "GrossProfit",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "ShareBasedCompensation",
    "ResearchAndDevelopmentExpense",
    "InterestExpense",
    "IncomeTaxExpenseBenefit",
    "DepreciationDepletionAndAmortization",
    "Depreciation",
]

BALANCE_TAGS = [
    "Assets",
    "AssetsCurrent",
    "Liabilities",
    "LiabilitiesCurrent",
    "LongTermDebt",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "RetainedEarningsAccumulatedDeficit",
    "CommonStockSharesOutstanding",
    "PropertyPlantAndEquipmentNet",
    "CommonStockSharesIssued",
]

CASHFLOW_TAGS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsForRepurchaseOfCommonStock",
    "PaymentsForRepurchaseOfEquity",
    "PaymentsOfDividendsCommonStock",
    "PaymentsOfDividends",
]


def _fetch_facts(
    db: Client,
    cik: str,
    tags: list[str],
    period_types: list[str],
    limit: int = 40,
) -> list[dict]:
    cik = cik.zfill(10)
    res = (
        db.table("facts")
        .select("tag,unit,period_type,end_date,filed_date,form,value")
        .eq("cik", cik)
        .in_("tag", tags)
        .in_("period_type", period_types)
        .order("end_date", desc=True)
        .limit(limit * len(tags))
        .execute()
    )
    return res.data or []


def _rows_to_series(rows: list[dict]) -> dict[str, FinancialsResponse]:
    """Group rows by tag, deduplicate end_dates, return map of tag→FinancialsResponse."""
    by_tag: dict[str, dict] = {}
    for row in rows:
        tag = row["tag"]
        if tag not in by_tag:
            by_tag[tag] = {"unit": row["unit"], "seen": {}}
        end = row["end_date"]
        if end not in by_tag[tag]["seen"]:
            by_tag[tag]["seen"][end] = row
    return by_tag


@router.get("/{cik}/financials")
def get_financials(
    cik: str,
    period: str = Query("quarterly", pattern="^(annual|quarterly)$"),
    db: Client = Depends(get_supabase),
) -> list[FinancialsResponse]:
    period_type = "annual" if period == "annual" else "quarterly"
    rows = _fetch_facts(db, cik, INCOME_TAGS, [period_type], limit=20)
    by_tag = _rows_to_series(rows)

    result = []
    for tag, info in by_tag.items():
        points = sorted(info["seen"].values(), key=lambda r: r["end_date"])
        result.append(
            FinancialsResponse(
                cik=cik,
                tag=tag,
                unit=info["unit"],
                data=[
                    FactPoint(
                        end_date=r["end_date"],
                        period_type=r["period_type"],
                        form=r.get("form"),
                        filed_date=r.get("filed_date"),
                        value=r["value"],
                    )
                    for r in points
                ],
            )
        )
    return result


@router.get("/{cik}/balance-sheet")
def get_balance_sheet(
    cik: str,
    period: str = Query("quarterly", pattern="^(annual|quarterly|instant)$"),
    db: Client = Depends(get_supabase),
) -> list[FinancialsResponse]:
    period_types = ["instant", "quarterly"] if period in ("quarterly", "instant") else ["annual", "instant"]
    rows = _fetch_facts(db, cik, BALANCE_TAGS, period_types, limit=20)
    by_tag = _rows_to_series(rows)

    result = []
    for tag, info in by_tag.items():
        points = sorted(info["seen"].values(), key=lambda r: r["end_date"])
        result.append(
            FinancialsResponse(
                cik=cik,
                tag=tag,
                unit=info["unit"],
                data=[
                    FactPoint(
                        end_date=r["end_date"],
                        period_type=r["period_type"],
                        form=r.get("form"),
                        filed_date=r.get("filed_date"),
                        value=r["value"],
                    )
                    for r in points
                ],
            )
        )
    return result


@router.get("/{cik}/cash-flow")
def get_cash_flow(
    cik: str,
    period: str = Query("quarterly", pattern="^(annual|quarterly)$"),
    db: Client = Depends(get_supabase),
) -> list[FinancialsResponse]:
    period_type = "annual" if period == "annual" else "quarterly"
    rows = _fetch_facts(db, cik, CASHFLOW_TAGS, [period_type], limit=20)
    by_tag = _rows_to_series(rows)

    result = []
    for tag, info in by_tag.items():
        points = sorted(info["seen"].values(), key=lambda r: r["end_date"])
        result.append(
            FinancialsResponse(
                cik=cik,
                tag=tag,
                unit=info["unit"],
                data=[
                    FactPoint(
                        end_date=r["end_date"],
                        period_type=r["period_type"],
                        form=r.get("form"),
                        filed_date=r.get("filed_date"),
                        value=r["value"],
                    )
                    for r in points
                ],
            )
        )
    return result


@router.get("/{cik}/metrics")
def get_metrics(
    cik: str,
    period: str = Query("quarterly", pattern="^(annual|quarterly)$"),
    db: Client = Depends(get_supabase),
) -> MetricsResponse:
    cik_padded = cik.zfill(10)
    period_type = "annual" if period == "annual" else "quarterly"
    res = (
        db.table("metrics")
        .select("end_date,period_type,metric,value")
        .eq("cik", cik_padded)
        .eq("period_type", period_type)
        .order("end_date", desc=True)
        .limit(200)
        .execute()
    )
    return MetricsResponse(
        cik=cik,
        data=[MetricPoint(**row) for row in (res.data or [])],
    )


@router.get("/{cik}/ttm")
def get_ttm(cik: str, db: Client = Depends(get_supabase)) -> TTMResponse:
    ttm = compute_ttm(cik, db)
    items = [
        TTMItem(tag=tag, value=value)
        for tag, value in ttm["items"].items()
    ]
    return TTMResponse(cik=cik, as_of=ttm["as_of"] or "", items=items)


@router.get("/{cik}/filings")
def get_filings(
    cik: str,
    limit: int = Query(20, ge=1, le=100),
    db: Client = Depends(get_supabase),
) -> FilingsResponse:
    cik_padded = cik.zfill(10)
    res = (
        db.table("facts")
        .select("form,filed_date,end_date,cik")
        .eq("cik", cik_padded)
        .in_("form", ["10-K", "10-Q", "10-K/A", "10-Q/A"])
        .order("filed_date", desc=True)
        .limit(limit * 5)
        .execute()
    )

    # Deduplicate by (form, end_date)
    seen: set[tuple] = set()
    filings: list[Filing] = []
    for row in (res.data or []):
        key = (row["form"], row["end_date"])
        if key not in seen:
            seen.add(key)
            filings.append(Filing(**row))
        if len(filings) >= limit:
            break

    return FilingsResponse(cik=cik, data=filings)
