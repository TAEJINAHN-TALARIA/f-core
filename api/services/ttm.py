from supabase import Client

# Tags that are summed over the last 4 quarters (flow items)
FLOW_TAGS = {
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "GrossProfit",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "ResearchAndDevelopmentExpense",
    "InterestExpense",
    "IncomeTaxExpenseBenefit",
    "DepreciationDepletionAndAmortization",
    "PaymentsForRepurchaseOfCommonStock",
    "PaymentsForRepurchaseOfEquity",
    "PaymentsOfDividendsCommonStock",
    "PaymentsOfDividends",
}

# Tags that use the most recent snapshot value (stock items)
STOCK_TAGS = {
    "Assets",
    "AssetsCurrent",
    "Liabilities",
    "LiabilitiesCurrent",
    "LongTermDebt",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "RetainedEarningsAccumulatedDeficit",
    "CommonStockSharesOutstanding",
}


def compute_ttm(cik: str, db: Client) -> dict:
    """
    Returns {tag: value, ...} for TTM aggregation (using most recent Annual data).
    """
    cik = cik.zfill(10)

    # Fetch last 3 annual facts per tag for safety
    res = (
        db.table("facts")
        .select("tag,end_date,period_type,value,unit")
        .eq("cik", cik)
        .eq("period_type", "annual")
        .in_("unit", ["USD", "shares", "USD/shares"])
        .order("end_date", desc=True)
        .limit(200)
        .execute()
    )

    rows = res.data or []

    # Group by tag → sorted list of (end_date, value)
    by_tag: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        tag = row["tag"]
        by_tag.setdefault(tag, []).append((row["end_date"], row["value"]))

    result: dict[str, float] = {}
    latest_date: str = ""

    for tag, points in by_tag.items():
        seen_dates: dict[str, float] = {}
        for date, val in points:
            if date not in seen_dates:
                seen_dates[date] = val
        sorted_dates = sorted(seen_dates.keys(), reverse=True)

        if not sorted_dates:
            continue

        if not latest_date or sorted_dates[0] > latest_date:
            latest_date = sorted_dates[0]

        # Both FLOW_TAGS and STOCK_TAGS use the latest annual value
        result[tag] = seen_dates[sorted_dates[0]]

    # Also try instant facts for stock tags that had no annual entries
    missing_stock = STOCK_TAGS - set(result.keys())
    if missing_stock:
        instant_res = (
            db.table("facts")
            .select("tag,end_date,value")
            .eq("cik", cik)
            .eq("period_type", "instant")
            .in_("tag", list(missing_stock))
            .order("end_date", desc=True)
            .limit(len(missing_stock) * 4)
            .execute()
        )
        for row in (instant_res.data or []):
            tag = row["tag"]
            if tag not in result:
                result[tag] = row["value"]
                if not latest_date or row["end_date"] > latest_date:
                    latest_date = row["end_date"]

    return {"items": result, "as_of": latest_date}
