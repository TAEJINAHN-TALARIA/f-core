# DB 데이터 현황 보고서

> 생성일시: 2026-05-25 01:27 UTC  
> Supabase 프로젝트: `cfpplvqcfvxiozmdusgl`

---

## 1. 전체 요약

| 테이블 | 행 수 | 비고 |
|--------|-------|------|
| `companies` | 6,895 | 정확 |
| `facts` | 1,799,452 | planner 추정 *(query planner 추정값)* |
| `metrics` | 659,551 | planner 추정 *(query planner 추정값)* |

---

## 2. companies 테이블

- **총 기업 수:** 6,895개 (전수)
- **티커 보유:** 6,895개 / 미보유: 0개
- **최근 업데이트:** 2026-05-24
- **최초 업데이트:** 2026-05-24

### 거래소별 분포

| 거래소 | 기업 수 |
|--------|---------|
| `Nasdaq` | 3,288 |
| `NYSE` | 2,278 |
| `OTC` | 1,227 |
| `NULL` | 83 |
| `CBOE` | 19 |

### SIC 업종별 Top 10

| 업종 | 기업 수 |
|------|---------|
| Unknown | 6,895 |

---

## 3. facts 테이블

- **총 레코드:** 1,799,452개 (planner 추정)
- **분포 분석:** 샘플 50,000건 기준
- **샘플 내 기업 수:** 628개
- **데이터 기간:** 2021-05-29 ~ 2033-03-31

### period_type 분포

| period_type | 건수 (샘플 내) |
|-------------|----------------|
| `quarterly` | 23,844 |
| `instant` | 17,901 |
| `annual` | 8,233 |
| `other` | 22 |

### unit 분포

| unit | 건수 (샘플 내) |
|------|----------------|
| `USD` | 41,222 |
| `USD/shares` | 4,475 |
| `shares` | 4,303 |

### 제출 양식(form) 분포 Top 10

| form | 건수 (샘플 내) |
|------|----------------|
| `10-Q` | 36,895 |
| `10-K` | 12,409 |
| `10-K/A` | 464 |
| `10-Q/A` | 232 |

### XBRL 태그별 현황 (29개 태그 감지)

| 태그 | 건수 (샘플 내) | 기업 수 (샘플 내) |
|------|----------------|-------------------|
| `NetCashProvidedByUsedInOperatingActivities` | 2,622 | 190 |
| `NetCashProvidedByUsedInFinancingActivities` | 2,590 | 179 |
| `StockholdersEquity` | 2,559 | 182 |
| `NetIncomeLoss` | 2,529 | 192 |
| `WeightedAverageNumberOfSharesOutstandingBasic` | 2,450 | 180 |
| `NetCashProvidedByUsedInInvestingActivities` | 2,388 | 175 |
| `RetainedEarningsAccumulatedDeficit` | 2,381 | 177 |
| `EarningsPerShareBasic` | 2,285 | 172 |
| `Assets` | 2,283 | 187 |
| `Liabilities` | 2,231 | 163 |
| `EarningsPerShareDiluted` | 2,190 | 165 |
| `CashAndCashEquivalentsAtCarryingValue` | 2,083 | 155 |
| `IncomeTaxExpenseBenefit` | 2,069 | 176 |
| `PaymentsToAcquirePropertyPlantAndEquipment` | 1,987 | 148 |
| `OperatingIncomeLoss` | 1,946 | 149 |
| `LiabilitiesCurrent` | 1,888 | 139 |
| `CommonStockSharesOutstanding` | 1,853 | 138 |
| `AssetsCurrent` | 1,763 | 136 |
| `RevenueFromContractWithCustomerExcludingAssessedTax` | 1,410 | 128 |
| `DepreciationDepletionAndAmortization` | 1,346 | 108 |
| `InterestExpense` | 1,113 | 110 |
| `GrossProfit` | 1,039 | 86 |
| `PaymentsForRepurchaseOfCommonStock` | 1,036 | 111 |
| `Revenues` | 953 | 94 |
| `ResearchAndDevelopmentExpense` | 927 | 74 |
| `LongTermDebt` | 825 | 90 |
| `PaymentsOfDividendsCommonStock` | 670 | 49 |
| `PaymentsOfDividends` | 501 | 42 |
| `PaymentsForRepurchaseOfEquity` | 83 | 11 |

---

## 4. metrics 테이블

- **총 레코드:** 659,551개 (planner 추정)
- **분포 분석:** 샘플 50,000건 기준
- **샘플 내 기업 수:** 798개
- **데이터 기간:** 2021-05-29 ~ 2026-04-30

### period_type 분포

| period_type | 건수 (샘플 내) |
|-------------|----------------|
| `quarterly` | 34,974 |
| `annual` | 11,721 |
| `instant` | 3,250 |
| `other` | 55 |

### 파생 지표 목록

| metric | 건수 (샘플 내) |
|--------|----------------|
| `debt_ratio` | 7,693 |
| `debt_to_equity` | 7,190 |
| `roa` | 6,449 |
| `roe` | 6,149 |
| `net_margin` | 5,041 |
| `operating_margin` | 4,518 |
| `fcf` | 4,419 |
| `gross_margin` | 2,687 |
| `interest_coverage` | 2,136 |
| `dividend_payout` | 2,086 |
| `buyback_to_fcf` | 1,632 |

---

## 5. 개발 참고사항

### 데이터 갭 / 주의사항

- facts는 ETL `TARGET_TAGS` 기준 29개 XBRL 태그만 수집 (전체 us-gaap 중 선택적 수집)
- `period_type=instant`인 facts는 재무상태표 항목이며 `start_date=NULL`이 정상
- 동일 기업이 여러 태그명으로 같은 개념을 보고할 수 있음
  - 예: `Revenues` vs `RevenueFromContractWithCustomerExcludingAssessedTax`
- API에서 revenue 조회 시 두 태그 모두 시도해야 안전 (api/services/ttm.py 참고)
- metrics는 ETL이 facts에서 파생 계산한 값 — facts 없는 기업은 metrics도 없음
- 티커 미보유 기업 0개는 검색/매핑 시 CIK로만 접근 가능

### 자주 쓰는 쿼리 패턴

```sql
-- 특정 기업의 최근 분기 매출 (Apple: 0000320193)
SELECT end_date, value FROM facts
WHERE cik = '0000320193'
  AND tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax')
  AND period_type = 'quarterly'
ORDER BY end_date DESC LIMIT 8;

-- 기업명 퍼지 검색
SELECT cik, name, ticker FROM companies
WHERE name ILIKE '%apple%' LIMIT 10;

-- TTM 집계용 최근 4분기
SELECT end_date, value FROM facts
WHERE cik = '0000320193' AND tag = 'NetIncomeLoss'
  AND period_type = 'quarterly'
ORDER BY end_date DESC LIMIT 4;

-- 재무상태표 최신 스냅샷 (instant)
SELECT tag, end_date, value FROM facts
WHERE cik = '0000320193' AND period_type = 'instant'
ORDER BY end_date DESC, tag;
```

### ETL TARGET_TAGS (etl/config.py 기준)

| 분류 | 태그 |
|------|------|
| 손익계산서 | `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `GrossProfit`, `OperatingIncomeLoss`, `NetIncomeLoss`, `EarningsPerShareBasic`, `EarningsPerShareDiluted`, `WeightedAverageNumberOfSharesOutstandingBasic` |
| 재무상태표 | `Assets`, `AssetsCurrent`, `Liabilities`, `LiabilitiesCurrent`, `LongTermDebt`, `StockholdersEquity`, `CashAndCashEquivalentsAtCarryingValue`, `RetainedEarningsAccumulatedDeficit` |
| 현금흐름 | `NetCashProvidedByUsedInOperatingActivities`, `NetCashProvidedByUsedInInvestingActivities`, `NetCashProvidedByUsedInFinancingActivities`, `PaymentsToAcquirePropertyPlantAndEquipment` |
| 주주환원 | `PaymentsForRepurchaseOfCommonStock`, `PaymentsForRepurchaseOfEquity`, `PaymentsOfDividendsCommonStock`, `PaymentsOfDividends` |
| 기타 | `CommonStockSharesOutstanding`, `InterestExpense`, `IncomeTaxExpenseBenefit`, `DepreciationDepletionAndAmortization`, `ResearchAndDevelopmentExpense` |