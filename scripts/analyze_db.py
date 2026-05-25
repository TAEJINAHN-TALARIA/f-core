"""
Supabase DB 데이터 현황 분석 스크립트
실행: python scripts/analyze_db.py
출력: docs/data_report.md
"""

import sys
import os
import requests
from datetime import datetime, timezone
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

REST = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


def get_count_planned(table: str) -> int:
    """query planner 통계 기반 빠른 row 수 추정 (full scan 없음)."""
    res = requests.get(
        f"{REST}/{table}?select=*&limit=1",
        headers={**HEADERS, "Prefer": "count=planned"},
    )
    content_range = res.headers.get("Content-Range", "*/0")
    total = content_range.split("/")[-1]
    return int(total) if total.isdigit() else 0


def fetch_page(table: str, select: str, limit: int, offset: int = 0) -> list:
    res = requests.get(
        f"{REST}/{table}?select={select}&limit={limit}&offset={offset}",
        headers=HEADERS,
    )
    res.raise_for_status()
    return res.json()


def fetch_all_small(table: str, select: str) -> list:
    """작은 테이블 전체 수집 (companies 용)."""
    PAGE = 1000
    rows, offset = [], 0
    while True:
        batch = fetch_page(table, select, PAGE, offset)
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return rows


def fetch_sample(table: str, select: str, sample_size: int = 50_000) -> list:
    """대형 테이블 샘플 수집."""
    PAGE = 1000
    rows, offset = [], 0
    while len(rows) < sample_size:
        batch = fetch_page(table, select, PAGE, offset)
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return rows[:sample_size]


def main():
    print("Supabase DB 분석 중...")

    # ── 1. 행 수 추정 (query planner 기반) ─────────────────────
    n_companies = get_count_planned("companies")
    n_facts = get_count_planned("facts")
    n_metrics = get_count_planned("metrics")
    print(f"  행 수 추정: companies={n_companies:,}, facts={n_facts:,}, metrics={n_metrics:,}")

    # ── 2. companies 분석 (전체 수집) ───────────────────────────
    print("  companies 전체 수집 중...")
    companies = fetch_all_small("companies", "cik,name,ticker,exchange,sic,sic_description,updated_at")
    n_companies_exact = len(companies)

    exchanges = Counter(c.get("exchange") or "NULL" for c in companies)
    sics = Counter(c.get("sic_description") or "Unknown" for c in companies)
    top_sics = sics.most_common(10)
    tickers_with = sum(1 for c in companies if c.get("ticker"))
    tickers_without = n_companies_exact - tickers_with
    updated_dates = [c["updated_at"][:10] for c in companies if c.get("updated_at")]
    latest_update = max(updated_dates) if updated_dates else "N/A"
    oldest_update = min(updated_dates) if updated_dates else "N/A"

    # ── 3. facts 분석 (샘플 50,000건) ──────────────────────────
    print("  facts 샘플 수집 중 (최대 50,000건)...")
    facts_sample = fetch_sample("facts", "cik,tag,unit,period_type,end_date,form,value", 50_000)
    n_facts_sample = len(facts_sample)
    is_facts_sampled = n_facts_sample < n_facts

    tags = Counter(f["tag"] for f in facts_sample)
    period_types = Counter(f["period_type"] for f in facts_sample)
    units = Counter(f["unit"] for f in facts_sample)
    forms = Counter(f.get("form") or "NULL" for f in facts_sample)
    end_dates = [f["end_date"] for f in facts_sample if f.get("end_date")]
    facts_date_min = min(end_dates) if end_dates else "N/A"
    facts_date_max = max(end_dates) if end_dates else "N/A"
    facts_ciks = len(set(f["cik"] for f in facts_sample))

    tag_cik_map = defaultdict(set)
    for f in facts_sample:
        tag_cik_map[f["tag"]].add(f["cik"])

    # ── 4. metrics 분석 (샘플 50,000건) ────────────────────────
    print("  metrics 샘플 수집 중 (최대 50,000건)...")
    metrics_sample = fetch_sample("metrics", "cik,end_date,period_type,metric,value", 50_000)
    n_metrics_sample = len(metrics_sample)
    is_metrics_sampled = n_metrics_sample < n_metrics

    metric_names = Counter(m["metric"] for m in metrics_sample)
    metrics_period = Counter(m["period_type"] for m in metrics_sample)
    metrics_ciks = len(set(m["cik"] for m in metrics_sample))
    m_dates = [m["end_date"] for m in metrics_sample if m.get("end_date")]
    metrics_date_min = min(m_dates) if m_dates else "N/A"
    metrics_date_max = max(m_dates) if m_dates else "N/A"

    # ── 5. 보고서 생성 ─────────────────────────────────────────
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sample_note = " *(query planner 추정값)*"

    lines = [
        "# DB 데이터 현황 보고서",
        "",
        f"> 생성일시: {now}  ",
        "> Supabase 프로젝트: `cfpplvqcfvxiozmdusgl`",
        "",
        "---",
        "",
        "## 1. 전체 요약",
        "",
        "| 테이블 | 행 수 | 비고 |",
        "|--------|-------|------|",
        f"| `companies` | {n_companies_exact:,} | 정확 |",
        f"| `facts` | {n_facts:,} | planner 추정{sample_note} |",
        f"| `metrics` | {n_metrics:,} | planner 추정{sample_note} |",
        "",
        "---",
        "",
        "## 2. companies 테이블",
        "",
        f"- **총 기업 수:** {n_companies_exact:,}개 (전수)",
        f"- **티커 보유:** {tickers_with:,}개 / 미보유: {tickers_without:,}개",
        f"- **최근 업데이트:** {latest_update}",
        f"- **최초 업데이트:** {oldest_update}",
        "",
        "### 거래소별 분포",
        "",
        "| 거래소 | 기업 수 |",
        "|--------|---------|",
    ]
    for exchange, cnt in sorted(exchanges.items(), key=lambda x: -x[1]):
        lines.append(f"| `{exchange}` | {cnt:,} |")

    lines += [
        "",
        "### SIC 업종별 Top 10",
        "",
        "| 업종 | 기업 수 |",
        "|------|---------|",
    ]
    for sic_desc, cnt in top_sics:
        lines.append(f"| {sic_desc} | {cnt:,} |")

    facts_scope = f"샘플 {n_facts_sample:,}건 기준" if is_facts_sampled else "전수"

    lines += [
        "",
        "---",
        "",
        "## 3. facts 테이블",
        "",
        f"- **총 레코드:** {n_facts:,}개 (planner 추정)",
        f"- **분포 분석:** {facts_scope}",
        f"- **샘플 내 기업 수:** {facts_ciks:,}개",
        f"- **데이터 기간:** {facts_date_min} ~ {facts_date_max}",
        "",
        "### period_type 분포",
        "",
        "| period_type | 건수 (샘플 내) |",
        "|-------------|----------------|",
    ]
    for pt, cnt in period_types.most_common():
        lines.append(f"| `{pt}` | {cnt:,} |")

    lines += [
        "",
        "### unit 분포",
        "",
        "| unit | 건수 (샘플 내) |",
        "|------|----------------|",
    ]
    for u, cnt in units.most_common():
        lines.append(f"| `{u}` | {cnt:,} |")

    lines += [
        "",
        "### 제출 양식(form) 분포 Top 10",
        "",
        "| form | 건수 (샘플 내) |",
        "|------|----------------|",
    ]
    for form, cnt in forms.most_common(10):
        lines.append(f"| `{form}` | {cnt:,} |")

    lines += [
        "",
        f"### XBRL 태그별 현황 ({len(tags)}개 태그 감지)",
        "",
        "| 태그 | 건수 (샘플 내) | 기업 수 (샘플 내) |",
        "|------|----------------|-------------------|",
    ]
    for tag, cnt in sorted(tags.items(), key=lambda x: -x[1]):
        n_ciks = len(tag_cik_map[tag])
        lines.append(f"| `{tag}` | {cnt:,} | {n_ciks:,} |")

    metrics_scope = f"샘플 {n_metrics_sample:,}건 기준" if is_metrics_sampled else "전수"

    lines += [
        "",
        "---",
        "",
        "## 4. metrics 테이블",
        "",
        f"- **총 레코드:** {n_metrics:,}개 (planner 추정)",
        f"- **분포 분석:** {metrics_scope}",
        f"- **샘플 내 기업 수:** {metrics_ciks:,}개",
        f"- **데이터 기간:** {metrics_date_min} ~ {metrics_date_max}",
        "",
        "### period_type 분포",
        "",
        "| period_type | 건수 (샘플 내) |",
        "|-------------|----------------|",
    ]
    for pt, cnt in metrics_period.most_common():
        lines.append(f"| `{pt}` | {cnt:,} |")

    lines += [
        "",
        "### 파생 지표 목록",
        "",
        "| metric | 건수 (샘플 내) |",
        "|--------|----------------|",
    ]
    for m, cnt in metric_names.most_common():
        lines.append(f"| `{m}` | {cnt:,} |")

    lines += [
        "",
        "---",
        "",
        "## 5. 개발 참고사항",
        "",
        "### 데이터 갭 / 주의사항",
        "",
        f"- facts는 ETL `TARGET_TAGS` 기준 {len(tags)}개 XBRL 태그만 수집 (전체 us-gaap 중 선택적 수집)",
        "- `period_type=instant`인 facts는 재무상태표 항목이며 `start_date=NULL`이 정상",
        "- 동일 기업이 여러 태그명으로 같은 개념을 보고할 수 있음",
        "  - 예: `Revenues` vs `RevenueFromContractWithCustomerExcludingAssessedTax`",
        "- API에서 revenue 조회 시 두 태그 모두 시도해야 안전 (api/services/ttm.py 참고)",
        "- metrics는 ETL이 facts에서 파생 계산한 값 — facts 없는 기업은 metrics도 없음",
        f"- 티커 미보유 기업 {tickers_without:,}개는 검색/매핑 시 CIK로만 접근 가능",
        "",
        "### 자주 쓰는 쿼리 패턴",
        "",
        "```sql",
        "-- 특정 기업의 최근 분기 매출 (Apple: 0000320193)",
        "SELECT end_date, value FROM facts",
        "WHERE cik = '0000320193'",
        "  AND tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax')",
        "  AND period_type = 'quarterly'",
        "ORDER BY end_date DESC LIMIT 8;",
        "",
        "-- 기업명 퍼지 검색",
        "SELECT cik, name, ticker FROM companies",
        "WHERE name ILIKE '%apple%' LIMIT 10;",
        "",
        "-- TTM 집계용 최근 4분기",
        "SELECT end_date, value FROM facts",
        "WHERE cik = '0000320193' AND tag = 'NetIncomeLoss'",
        "  AND period_type = 'quarterly'",
        "ORDER BY end_date DESC LIMIT 4;",
        "",
        "-- 재무상태표 최신 스냅샷 (instant)",
        "SELECT tag, end_date, value FROM facts",
        "WHERE cik = '0000320193' AND period_type = 'instant'",
        "ORDER BY end_date DESC, tag;",
        "```",
        "",
        "### ETL TARGET_TAGS (etl/config.py 기준)",
        "",
        "| 분류 | 태그 |",
        "|------|------|",
        "| 손익계산서 | `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `GrossProfit`, `OperatingIncomeLoss`, `NetIncomeLoss`, `EarningsPerShareBasic`, `EarningsPerShareDiluted`, `WeightedAverageNumberOfSharesOutstandingBasic` |",
        "| 재무상태표 | `Assets`, `AssetsCurrent`, `Liabilities`, `LiabilitiesCurrent`, `LongTermDebt`, `StockholdersEquity`, `CashAndCashEquivalentsAtCarryingValue`, `RetainedEarningsAccumulatedDeficit` |",
        "| 현금흐름 | `NetCashProvidedByUsedInOperatingActivities`, `NetCashProvidedByUsedInInvestingActivities`, `NetCashProvidedByUsedInFinancingActivities`, `PaymentsToAcquirePropertyPlantAndEquipment` |",
        "| 주주환원 | `PaymentsForRepurchaseOfCommonStock`, `PaymentsForRepurchaseOfEquity`, `PaymentsOfDividendsCommonStock`, `PaymentsOfDividends` |",
        "| 기타 | `CommonStockSharesOutstanding`, `InterestExpense`, `IncomeTaxExpenseBenefit`, `DepreciationDepletionAndAmortization`, `ResearchAndDevelopmentExpense` |",
    ]

    report = "\n".join(lines)

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "data_report.md"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n보고서 저장 완료: {out_path}")
    print(f"  companies: {n_companies_exact:,} (전수), facts: {n_facts:,} (추정), metrics: {n_metrics:,} (추정)")


if __name__ == "__main__":
    main()
