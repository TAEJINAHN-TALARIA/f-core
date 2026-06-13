import statistics
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

    if theme_type == "high-roe-low-debt":
        # 1. 고ROE & 저부채 우량주
        # ROE >= 15% AND 부채비율 <= 100% (최근 연도)
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

    elif theme_type == "dividend-growth-5yr":
        # 2. 배당성장 (5년 연속)
        # 배당금 총액 YoY 5년 연속 증가
        res = (
            db.table("facts")
            .select("cik,end_date,value")
            .in_("tag", ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"])
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

    elif theme_type == "fcf-positive-10yr":
        # 3. 10년 연속 FCF 흑자
        # FCF > 0, 10년 연속
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
            if all(v > 0 for v in vals):
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

    elif theme_type == "shareholder-return-high-3yr":
        # 4. 현금흐름 주주환원 >= 70%
        # (배당금 + 자사주매입) / FCF >= 0.7 (3년 평균)
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
            if len(recent_dates) < 3:
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

            # Check latest 3 years average
            avg_3yr = sum(ratios[-3:]) / 3
            if avg_3yr >= 0.7:
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(avg_3yr * 100, 2),
                            history=[round(r * 100, 2) for r in ratios],
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "roe-consistent-7yr":
        # 5. 연속 고ROE (7년, >= 15%)
        # ROE >= 15% 7년 연속
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
            recent = sorted_points[-7:]
            if len(recent) < 7:
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

    elif theme_type == "fcf-margin-high-industry":
        # 6. FCF 마진 >= 20% (업종 조정)
        # FCF ÷ 매출액 ≥ 업종 중앙값 × 1.5
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

        # Calculate latest margin for all companies
        latest_margins = {}
        by_industry = {}
        all_margins = []

        for cik, fcf_dates in fcf_by_cik.items():
            sorted_dates = sorted(fcf_dates.keys())
            if not sorted_dates:
                continue
            latest_d = sorted_dates[-1]
            fcf = fcf_dates[latest_d]
            rev = rev_by_cik.get(cik, {}).get(latest_d, 0.0)
            if rev and rev > 0:
                margin = fcf / rev
                latest_margins[cik] = margin
                all_margins.append(margin)
                
                # Group by industry (sic)
                c_info = companies_map.get(cik)
                if c_info and c_info.get("sic"):
                    sic = c_info["sic"]
                    by_industry.setdefault(sic, []).append(margin)

        # Calculate medians
        industry_medians = {}
        for sic, margins in by_industry.items():
            industry_medians[sic] = statistics.median(margins)
        global_median = statistics.median(all_margins) if all_margins else 0.0

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

            latest_margin = ratios[-1]
            c_info = companies_map.get(cik)
            if not c_info:
                continue
            sic = c_info.get("sic")
            median = industry_medians.get(sic, global_median) if sic else global_median

            # Check condition: margin >= median * 1.5
            if latest_margin >= median * 1.5:
                result.append(
                    ThemeCompany(
                        **c_info,
                        value=round(latest_margin * 100, 2),
                        history=[round(r * 100, 2) for r in ratios],
                    )
                )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "fcf-margin-growth-3yr":
        # 7. FCF 마진 확장 추세
        # FCF 마진이 3년 연속 전년 대비 개선 (최근 4개년, v0 < v1 < v2 < v3)
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
            recent_dates = sorted_dates[-4:]
            if len(recent_dates) < 4:
                continue

            ratios = []
            for d in recent_dates:
                fcf = fcf_dates[d]
                rev = rev_by_cik.get(cik, {}).get(d, 0.0)
                if rev and rev > 0:
                    ratios.append(fcf / rev)
                else:
                    ratios.append(0.0)

            # Check if 3 years consecutively improved: v0 < v1 < v2 < v3
            if all(ratios[i] < ratios[i+1] for i in range(len(ratios) - 1)):
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(ratios[-1] * 100, 2),
                            history=[round(r * 100, 2) for r in ratios],
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "earnings-quality-high":
        # 8. 이익 품질 우량주
        # FCF ÷ 순이익 >= 0.9 (3년 평균)
        res_fcf = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "fcf")
            .eq("period_type", "annual")
            .execute()
        )
        res_netinc = (
            db.table("facts")
            .select("cik,end_date,value")
            .eq("tag", "NetIncomeLoss")
            .eq("period_type", "annual")
            .execute()
        )

        fcf_by_cik = {}
        for row in (res_fcf.data or []):
            cik = row["cik"]
            fcf_by_cik.setdefault(cik, {})[row["end_date"]] = row["value"]

        netinc_by_cik = {}
        for row in (res_netinc.data or []):
            cik = row["cik"]
            netinc_by_cik.setdefault(cik, {})[row["end_date"]] = row["value"]

        for cik, fcf_dates in fcf_by_cik.items():
            sorted_dates = sorted(fcf_dates.keys())
            recent_dates = sorted_dates[-5:]
            if len(recent_dates) < 3:
                continue

            ratios = []
            for d in recent_dates:
                fcf = fcf_dates[d]
                net = netinc_by_cik.get(cik, {}).get(d, 0.0)
                if net and net > 0:
                    ratios.append(fcf / net)
                else:
                    ratios.append(0.0)

            # Check if all last 3 years have positive net income
            if any(r <= 0 for r in ratios[-3:]):
                continue

            avg_quality = sum(ratios[-3:]) / 3
            if avg_quality >= 0.9:
                c_info = companies_map.get(cik)
                if c_info:
                    result.append(
                        ThemeCompany(
                            **c_info,
                            value=round(avg_quality * 100, 2),
                            history=[round(r * 100, 2) for r in ratios],
                        )
                    )
        result = sorted(result, key=lambda x: x.value, reverse=True)[:limit]

    elif theme_type == "zero-debt-strict":
        # 9. 이자비용 제로 & 무차입
        # Interest Expense = 0 AND Long-term Debt = 0 (최근 연도)
        res_interest = (
            db.table("facts")
            .select("cik,end_date,value")
            .eq("tag", "InterestExpense")
            .eq("period_type", "annual")
            .execute()
        )
        res_ltdebt = (
            db.table("facts")
            .select("cik,end_date,value")
            .eq("tag", "LongTermDebt")
            .execute()
        )
        res_debt = (
            db.table("metrics")
            .select("cik,end_date,value")
            .eq("metric", "debt_to_equity")
            .eq("period_type", "annual")
            .execute()
        )

        interest_by_cik = {}
        for row in (res_interest.data or []):
            cik = row["cik"]
            interest_by_cik.setdefault(cik, []).append((row["end_date"], row["value"]))

        ltdebt_by_cik = {}
        for row in (res_ltdebt.data or []):
            cik = row["cik"]
            ltdebt_by_cik.setdefault(cik, []).append((row["end_date"], row["value"]))

        debt_by_cik = {}
        for row in (res_debt.data or []):
            cik = row["cik"]
            debt_by_cik.setdefault(cik, []).append((row["end_date"], row["value"]))

        for cik, points in debt_by_cik.items():
            sorted_points = sorted(points, key=lambda p: p[0])
            recent = sorted_points[-5:]
            if not recent:
                continue
            latest_debt = recent[-1][1]

            # Debt must be non-negative to avoid capital impairment
            if latest_debt < 0:
                continue

            interest_points = interest_by_cik.get(cik, [])
            latest_interest = 0.0
            if interest_points:
                latest_interest = sorted(interest_points, key=lambda p: p[0])[-1][1]

            ltdebt_points = ltdebt_by_cik.get(cik, [])
            latest_ltdebt = 0.0
            if ltdebt_points:
                latest_ltdebt = sorted(ltdebt_points, key=lambda p: p[0])[-1][1]

            # Condition: InterestExpense = 0 AND Long-term Debt = 0 (or no values recorded)
            if latest_interest <= 0 and latest_ltdebt <= 0:
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
