import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from .config import CONCEPT_MAP

if TYPE_CHECKING:
    from .stats import ParseStats

logger = logging.getLogger(__name__)

def _get_concept_value(d: dict, concept: str) -> float | None:
    tags = CONCEPT_MAP.get(concept, {}).get("tags", [])
    for tag in tags:
        if tag in d:
            return d[tag]
    return None


def deduplicate_facts(facts: list[dict]) -> list[dict]:
    """같은 (cik, tag, unit, end_date, period_type) 중 가장 최근 filed_date 것만 유지"""
    best: dict[tuple, dict] = {}

    for fact in facts:
        key = (
            fact["cik"],
            fact["tag"],
            fact["unit"],
            fact["end_date"],
            fact["period_type"],
        )
        existing = best.get(key)
        if existing is None:
            best[key] = fact
        else:
            if (fact["filed_date"] or "") > (existing["filed_date"] or ""):
                best[key] = fact

    return list(best.values())


def compute_metrics(
    facts: list[dict], cik: str, stats: "ParseStats | None" = None
) -> list[dict]:
    """
    facts에서 파생 지표를 계산한다.
    반환: [{"cik", "end_date", "period_type", "metric", "value"}, ...]

    재무상태표 항목(instant)과 손익/현금흐름 항목(quarterly/annual)은
    period_type이 달라 같은 그룹에 묶이지 않으므로, end_date가 같은
    instant 항목을 duration 기간에 병합한 뒤 지표를 계산한다.
    """
    instant_by_date: dict[str, dict] = defaultdict(dict)
    by_period: dict[tuple, dict] = defaultdict(dict)

    for f in facts:
        if f["cik"] != cik:
            continue
        if f["period_type"] == "instant":
            instant_by_date[f["end_date"]][f["tag"]] = f["value"]
        else:
            key = (f["end_date"], f["period_type"])
            by_period[key][f["tag"]] = f["value"]

    metrics = []
    for (end_date, period_type), tags in by_period.items():
        merged = {**instant_by_date.get(end_date, {}), **tags}
        computed, missing = _derive(merged)
        for metric, value in computed.items():
            if value is None:
                if stats and missing.get(metric):
                    stats.metric_missing(metric, missing[metric])
                continue
            metrics.append({
                "cik": cik,
                "end_date": end_date,
                "period_type": period_type,
                "metric": metric,
                "value": value,
            })

    if stats:
        stats.metric_ok(len(metrics))

    return metrics


def _derive(t: dict) -> tuple[dict, dict]:
    """
    Returns:
        computed: metric → value (None if couldn't compute)
        missing:  metric → 누락된 재료 개념 이름
    """
    revenue = _get_concept_value(t, "revenue")
    net_income = _get_concept_value(t, "net_income")
    equity = _get_concept_value(t, "equity")
    liabilities = _get_concept_value(t, "liabilities")
    op_cf = _get_concept_value(t, "operating_cash_flow")
    capex = _get_concept_value(t, "capex")
    gross_profit = _get_concept_value(t, "gross_profit")
    operating_income = _get_concept_value(t, "operating_income")
    interest_expense = _get_concept_value(t, "interest_expense")
    buybacks = _get_concept_value(t, "stock_repurchase")
    dividends = _get_concept_value(t, "dividends_paid")
    
    fcf_val = _safe_sub(op_cf, abs(capex) if capex is not None else None)

    computed = {
        "gross_margin":       _safe_div(gross_profit, revenue),
        "operating_margin":   _safe_div(operating_income, revenue),
        "net_margin":         _safe_div(net_income, revenue),
        "roe":                _safe_div(net_income, equity),
        "debt_to_equity":     _safe_div(liabilities, equity),
        "interest_coverage":  _safe_div(operating_income, interest_expense),
        "fcf":                fcf_val,
        "buyback_to_fcf":     _safe_div(buybacks, fcf_val) if fcf_val and fcf_val > 0 else None,
        "dividend_payout":    _safe_div(dividends, net_income) if net_income and net_income > 0 else None,
    }

    # 계산 실패 시 어떤 재료가 없었는지 기록
    missing: dict[str, str] = {}
    if computed["gross_margin"] is None:
        missing["gross_margin"] = "gross_profit" if revenue else "revenue"
    if computed["operating_margin"] is None:
        missing["operating_margin"] = "operating_income" if revenue else "revenue"
    if computed["net_margin"] is None:
        missing["net_margin"] = "net_income" if revenue else "revenue"
    if computed["roe"] is None:
        missing["roe"] = "equity" if net_income else "net_income"
    if computed["debt_to_equity"] is None:
        missing["debt_to_equity"] = "equity" if liabilities else "liabilities"
    if computed["interest_coverage"] is None:
        missing["interest_coverage"] = "interest_expense" if operating_income else "operating_income"
    if computed["fcf"] is None:
        missing["fcf"] = "capex" if op_cf else "operating_cash_flow"

    return computed, missing


def _safe_div(a, b) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 6)


def _safe_sub(a, b) -> float | None:
    if a is None or b is None:
        return None
    return a - b


def _safe_add(a, b) -> float | None:
    if a is None or b is None:
        return None
    return a + b
