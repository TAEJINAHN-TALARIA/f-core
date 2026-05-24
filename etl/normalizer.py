import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


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
            # 더 최근에 제출된 것 우선
            if (fact["filed_date"] or "") > (existing["filed_date"] or ""):
                best[key] = fact

    return list(best.values())


def compute_metrics(facts: list[dict], cik: str) -> list[dict]:
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
        # 같은 end_date의 재무상태표 스냅샷을 병합
        merged = {**instant_by_date.get(end_date, {}), **tags}
        computed = _derive(merged)
        for metric, value in computed.items():
            if value is None:
                continue
            metrics.append({
                "cik": cik,
                "end_date": end_date,
                "period_type": period_type,
                "metric": metric,
                "value": value,
            })

    return metrics


def _derive(t: dict) -> dict:
    revenue = _first(t, "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax")
    net_income = t.get("NetIncomeLoss")
    assets = t.get("Assets")
    equity = t.get("StockholdersEquity")
    liabilities = t.get("Liabilities")
    op_cf = t.get("NetCashProvidedByUsedInOperatingActivities")
    capex = t.get("PaymentsToAcquirePropertyPlantAndEquipment")
    gross_profit = t.get("GrossProfit")
    operating_income = t.get("OperatingIncomeLoss")
    interest_expense = t.get("InterestExpense")
    buybacks = _first(t, "PaymentsForRepurchaseOfCommonStock", "PaymentsForRepurchaseOfEquity")
    dividends = _first(t, "PaymentsOfDividendsCommonStock", "PaymentsOfDividends")
    fcf_val = _safe_sub(op_cf, capex)

    return {
        # 마진
        "gross_margin": _safe_div(gross_profit, revenue),
        "operating_margin": _safe_div(operating_income, revenue),
        "net_margin": _safe_div(net_income, revenue),
        # 수익성
        "roe": _safe_div(net_income, equity),
        "roa": _safe_div(net_income, assets),
        # 안정성
        "debt_ratio": _safe_div(liabilities, assets),
        "debt_to_equity": _safe_div(liabilities, equity),
        "interest_coverage": _safe_div(operating_income, interest_expense),
        # 현금흐름
        "fcf": fcf_val,
        # 주주환원
        "buyback_to_fcf": _safe_div(buybacks, fcf_val) if fcf_val is not None and fcf_val > 0 else None,
        "dividend_payout": _safe_div(dividends, net_income) if net_income is not None and net_income > 0 else None,
    }


def _first(d: dict, *keys: str):
    for k in keys:
        if k in d:
            return d[k]
    return None


def _safe_div(a, b) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 6)


def _safe_sub(a, b) -> float | None:
    if a is None or b is None:
        return None
    return a - b
