from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from ..dependencies import get_supabase
from ..schemas import Company, ThemeCompany

router = APIRouter()

# Simple In-memory Cache to avoid repeated DB scans
_THEME_CACHE: dict[str, list[ThemeCompany]] = {}


def _get_companies_map(db: Client) -> dict[str, dict]:
    res = (
        db.table("companies")
        .select("cik,name,ticker,exchange,sic,sic_description")
        .execute()
    )
    # CIK is stored as padded 10-char strings in DB (e.g. '0000320193')
    return {row["cik"]: row for row in (res.data or [])}


@router.get("", response_model=list[Company])
def list_companies(limit: int = 500, offset: int = 0, db: Client = Depends(get_supabase)):
    res = (
        db.table("companies")
        .select("cik,name,ticker,exchange,sic,sic_description")
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data


@router.get("/themes/{theme_type}", response_model=list[ThemeCompany])
def get_theme_companies(
    theme_type: str,
    limit: int = Query(10, ge=1, le=50),
    db: Client = Depends(get_supabase),
):
    global _THEME_CACHE
    cache_key = f"{theme_type}_{limit}"
    if cache_key in _THEME_CACHE:
        return _THEME_CACHE[cache_key]

    companies_map = _get_companies_map(db)
    result = []

    if theme_type == "operating-margin-growth":
        # 1. 5-Year Consecutive Operating Margin Growth
        res = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "operating_margin")
            .eq("period_type", "annual")
            .execute()
        )
        data = res.data or []

        by_cik = {}
        for row in data:
            cik = row["cik"]
            by_cik.setdefault(cik, []).append((row["end_date"], row["value"]))

        for cik, points in by_cik.items():
            sorted_points = sorted(points, key=lambda p: p[0])
            recent = sorted_points[-5:]
            if len(recent) < 5:
                continue
            vals = [p[1] for p in recent]
            # Margin must grow year-over-year: v0 < v1 < v2 < v3 < v4
            if all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(vals[-1] * 100, 2),  # Convert to percentage
                            history=[round(v * 100, 2) for v in vals],
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "dividend-growth":
        # 2. 5-Year Consecutive Dividend Growth
        res = (
            db.table("facts")
            .select("cik,end_date,value")
            .in_("tag", ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"])
            .eq("period_type", "annual")
            .execute()
        )
        data = res.data or []

        # Sum dividends per CIK and year (absolute values since they are outflows)
        by_cik_date = {}
        for row in data:
            cik = row["cik"]
            date = row["end_date"]
            val = abs(row["value"])
            key = (cik, date)
            by_cik_date[key] = by_cik_date.get(key, 0) + val

        by_cik = {}
        for (cik, date), val in by_cik_date.items():
            by_cik.setdefault(cik, []).append((date, val))

        for cik, points in by_cik.items():
            sorted_points = sorted(points, key=lambda p: p[0])
            recent = sorted_points[-5:]
            if len(recent) < 5:
                continue
            vals = [p[1] for p in recent]
            # Dividends must be positive and growing year-over-year
            if all(v > 0 for v in vals) and all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=vals[-1],
                            history=vals,
                        )
                    )
        # Sort by largest absolute dividend amount in latest year
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "high-roe":
        # 3. High ROE (>= 15%) & Safe Debt (<= 100%)
        res_roe = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "roe")
            .eq("period_type", "annual")
            .execute()
        )
        res_debt = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "debt_to_equity")
            .eq("period_type", "annual")
            .execute()
        )

        roe_map = {}
        for row in (res_roe.data or []):
            cik = row["cik"]
            date = row["end_date"]
            val = row["value"]
            if cik not in roe_map or date > roe_map[cik][0]:
                roe_map[cik] = (date, val)

        debt_map = {}
        for row in (res_debt.data or []):
            cik = row["cik"]
            date = row["end_date"]
            val = row["value"]
            if cik not in debt_map or date > debt_map[cik][0]:
                debt_map[cik] = (date, val)

        for cik, (date, roe_val) in roe_map.items():
            debt_info = debt_map.get(cik)
            if not debt_info:
                continue
            debt_val = debt_info[1]

            # Criteria: ROE >= 15% and Debt-to-Equity <= 100% (1.0) and >= 0 (no negative equity)
            if roe_val >= 0.15 and 0 <= debt_val <= 1.0:
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(roe_val * 100, 2),
                            history=[round(roe_val * 100, 2), round(debt_val * 100, 2)],
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "fcf-positive-10yr":
        # 4. 10-Year Consecutive Positive Free Cash Flow
        res = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "fcf")
            .eq("period_type", "annual")
            .execute()
        )
        data = res.data or []

        by_cik = {}
        for row in data:
            cik = row["cik"]
            by_cik.setdefault(cik, []).append((row["end_date"], row["value"]))

        for cik, points in by_cik.items():
            sorted_points = sorted(points, key=lambda p: p[0])
            recent = sorted_points[-10:]
            if len(recent) < 10:
                continue
            vals = [p[1] for p in recent]
            # Must not have negative FCF (FCF >= 0)
            if all(v >= 0 for v in vals):
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=vals[-1],
                            history=vals,
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "buyback-growth-5yr":
        # 5. 5-Year Consecutive Buyback Growth
        res = (
            db.table("facts")
            .select("cik,end_date,value")
            .in_("tag", ["PaymentsForRepurchaseOfCommonStock", "PaymentsForRepurchaseOfEquity"])
            .eq("period_type", "annual")
            .execute()
        )
        data = res.data or []

        by_cik_date = {}
        for row in data:
            cik = row["cik"]
            date = row["end_date"]
            val = abs(row["value"])
            key = (cik, date)
            by_cik_date[key] = by_cik_date.get(key, 0) + val

        by_cik = {}
        for (cik, date), val in by_cik_date.items():
            by_cik.setdefault(cik, []).append((date, val))

        for cik, points in by_cik.items():
            sorted_points = sorted(points, key=lambda p: p[0])
            recent = sorted_points[-5:]
            if len(recent) < 5:
                continue
            vals = [p[1] for p in recent]
            # Buybacks must be positive and growing year-over-year
            if all(v > 0 for v in vals) and all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=vals[-1],
                            history=vals,
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "zero-debt-safe":
        # 6. Zero Debt or Safe Debt-to-Equity (<= 30%)
        res_debt = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "debt_to_equity")
            .eq("period_type", "annual")
            .execute()
        )
        res_interest = (
            db.table("facts")
            .select("cik,end_date,value")
            .eq("tag", "InterestExpense")
            .eq("period_type", "annual")
            .execute()
        )

        debt_by_cik = {}
        for row in (res_debt.data or []):
            cik = row["cik"]
            debt_by_cik.setdefault(cik, []).append((row["end_date"], row["value"]))

        interest_by_cik = {}
        for row in (res_interest.data or []):
            cik = row["cik"]
            interest_by_cik.setdefault(cik, []).append((row["end_date"], row["value"]))

        for cik, points in debt_by_cik.items():
            sorted_points = sorted(points, key=lambda p: p[0])
            recent = sorted_points[-5:]
            if not recent:
                continue
            latest_debt = recent[-1][1]

            interest_points = interest_by_cik.get(cik, [])
            latest_interest = 0.0
            if interest_points:
                latest_interest = sorted(interest_points, key=lambda p: p[0])[-1][1]

            # Debt must be non-negative to avoid negative equity
            if (0 <= latest_debt <= 0.3) or (latest_interest <= 0 and latest_debt >= 0):
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(latest_debt * 100, 2),
                            history=[round(p[1] * 100, 2) for p in recent],
                        )
                    )
        result = sorted(result, key=lambda x: x.value)[:limit]

    elif theme_type == "roe-consistent-10yr":
        # 7. 10-Year Consecutive ROE >= 15%
        res = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "roe")
            .eq("period_type", "annual")
            .execute()
        )
        data = res.data or []

        by_cik = {}
        for row in data:
            cik = row["cik"]
            by_cik.setdefault(cik, []).append((row["end_date"], row["value"]))

        for cik, points in by_cik.items():
            sorted_points = sorted(points, key=lambda p: p[0])
            recent = sorted_points[-10:]
            if len(recent) < 10:
                continue
            vals = [p[1] for p in recent]
            if all(v >= 0.15 for v in vals):
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(vals[-1] * 100, 2),
                            history=[round(v * 100, 2) for v in vals],
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "deleveraging-5yr":
        # 8. 5-Year Consecutive Decrease in Debt to Equity
        res = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "debt_to_equity")
            .eq("period_type", "annual")
            .execute()
        )
        data = res.data or []

        by_cik = {}
        for row in data:
            cik = row["cik"]
            by_cik.setdefault(cik, []).append((row["end_date"], row["value"]))

        for cik, points in by_cik.items():
            sorted_points = sorted(points, key=lambda p: p[0])
            recent = sorted_points[-5:]
            if len(recent) < 5:
                continue
            vals = [p[1] for p in recent]
            # debt ratio must decrease: v0 > v1 > v2 > v3 > v4, all >= 0
            if all(v >= 0 for v in vals) and all(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(vals[-1] * 100, 2),
                            history=[round(v * 100, 2) for v in vals],
                        )
                    )
        result = sorted(result, key=lambda x: x.value)[:limit]

    elif theme_type == "shareholder-payout-high":
        # 9. Payout / FCF >= 70%
        res_fcf = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "fcf")
            .eq("period_type", "annual")
            .execute()
        )
        res_dividends = (
            db.table("facts")
            .select("cik,end_date,value")
            .in_("tag", ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"])
            .eq("period_type", "annual")
            .execute()
        )
        res_buybacks = (
            db.table("facts")
            .select("cik,end_date,value")
            .in_("tag", ["PaymentsForRepurchaseOfCommonStock", "PaymentsForRepurchaseOfEquity"])
            .eq("period_type", "annual")
            .execute()
        )

        fcf_by_cik = {}
        for row in (res_fcf.data or []):
            cik = row["cik"]
            fcf_by_cik.setdefault(cik, {})[row["end_date"]] = row["value"]

        div_by_cik = {}
        for row in (res_dividends.data or []):
            cik = row["cik"]
            div_by_cik.setdefault(cik, {}).setdefault(row["end_date"], 0.0)
            div_by_cik[cik][row["end_date"]] += abs(row["value"])

        buyback_by_cik = {}
        for row in (res_buybacks.data or []):
            cik = row["cik"]
            buyback_by_cik.setdefault(cik, {}).setdefault(row["end_date"], 0.0)
            buyback_by_cik[cik][row["end_date"]] += abs(row["value"])

        for cik, fcf_dates in fcf_by_cik.items():
            sorted_dates = sorted(fcf_dates.keys())
            recent_dates = sorted_dates[-5:]
            if not recent_dates:
                continue

            ratios = []
            for d in recent_dates:
                fcf = fcf_dates[d]
                div = div_by_cik.get(cik, {}).get(d, 0.0)
                buyback = buyback_by_cik.get(cik, {}).get(d, 0.0)
                payout = div + buyback
                if fcf and fcf > 0:
                    ratios.append(payout / fcf)
                else:
                    ratios.append(0.0)

            latest_ratio = ratios[-1]
            if latest_ratio >= 0.7:
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(latest_ratio * 100, 2),
                            history=[round(r * 100, 2) for r in ratios],
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "fcf-to-revenue-high":
        # 10. FCF / Revenue >= 20%
        res_fcf = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "fcf")
            .eq("period_type", "annual")
            .execute()
        )
        res_revenue = (
            db.table("facts")
            .select("cik,end_date,value")
            .in_("tag", ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"])
            .eq("period_type", "annual")
            .execute()
        )

        fcf_by_cik = {}
        for row in (res_fcf.data or []):
            cik = row["cik"]
            fcf_by_cik.setdefault(cik, {})[row["end_date"]] = row["value"]

        rev_by_cik = {}
        for row in (res_revenue.data or []):
            cik = row["cik"]
            rev_by_cik.setdefault(cik, {}).setdefault(row["end_date"], 0.0)
            rev_by_cik[cik][row["end_date"]] = max(rev_by_cik[cik][row["end_date"]], row["value"])

        for cik, fcf_dates in fcf_by_cik.items():
            sorted_dates = sorted(fcf_dates.keys())
            recent_dates = sorted_dates[-5:]
            if not recent_dates:
                continue

            ratios = []
            for d in recent_dates:
                fcf = fcf_dates[d]
                rev = rev_by_cik.get(cik, {}).get(d, 0.0)
                if rev and rev > 0:
                    ratios.append(fcf / rev)
                else:
                    ratios.append(0.0)

            latest_ratio = ratios[-1]
            if latest_ratio >= 0.2:
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(latest_ratio * 100, 2),
                            history=[round(r * 100, 2) for r in ratios],
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    else:
        raise HTTPException(status_code=400, detail="Invalid theme type")

    _THEME_CACHE[cache_key] = result
    return result


@router.get("/{cik}", response_model=Company)
def get_company(cik: str, db: Client = Depends(get_supabase)):
    cik = cik.zfill(10)
    res = (
        db.table("companies")
        .select("cik,name,ticker,exchange,sic,sic_description")
        .eq("cik", cik)
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Company not found")
    return res.data
