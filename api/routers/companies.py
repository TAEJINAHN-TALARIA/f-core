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

            # Criteria: ROE >= 15% and Debt-to-Equity <= 100% (1.0)
            if roe_val >= 0.15 and debt_val <= 1.0:
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
