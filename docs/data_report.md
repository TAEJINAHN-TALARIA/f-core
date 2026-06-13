# DB 데이터 현황 보고서

> 생성일시: 2026-06-13 04:43 UTC  
> Supabase 프로젝트: `cfpplvqcfvxiozmdusgl`

---

## 1. 전체 요약

| 테이블 | 행 수 | 비고 |
|--------|-------|------|
| `companies` | 6,963 | 정확 |
| `facts` | 208,338 | planner 추정 *(query planner 추정값)* |
| `metrics` | 115,093 | planner 추정 *(query planner 추정값)* |

---

## 2. companies 테이블

- **총 기업 수:** 6,963개 (전수)
- **티커 보유:** 6,963개 / 미보유: 0개
- **최근 업데이트:** 2026-06-13
- **최초 업데이트:** 2026-05-25

### 거래소별 분포

| 거래소 | 기업 수 |
|--------|---------|
| `Nasdaq` | 3,309 |
| `NYSE` | 2,291 |
| `OTC` | 1,237 |
| `NULL` | 107 |
| `CBOE` | 19 |

### SIC 업종별 Top 10

| 업종 | 기업 수 |
|------|---------|
| Pharmaceutical Preparations | 588 |
| Blank Checks | 323 |
| Services-Prepackaged Software | 280 |
| Unknown | 279 |
| Real Estate Investment Trusts | 204 |
| State Commercial Banks | 186 |
| Biological Products, (No Diagnostic Substances) | 176 |
| Finance Services | 152 |
| Surgical & Medical Instruments & Apparatus | 149 |
| Services-Business Services, NEC | 135 |

---

## 3. facts 테이블

- **총 레코드:** 208,338개 (planner 추정)
- **분포 분석:** 샘플 50,000건 기준
- **샘플 내 기업 수:** 1,076개
- **데이터 기간:** 2021-06-23 ~ 2026-04-30

### period_type 분포

| period_type | 건수 (샘플 내) |
|-------------|----------------|
| `annual` | 35,612 |
| `instant` | 14,388 |

### unit 분포

| unit | 건수 (샘플 내) |
|------|----------------|
| `USD` | 50,000 |

### 제출 양식(form) 분포 Top 10

| form | 건수 (샘플 내) |
|------|----------------|
| `10-K` | 49,695 |
| `10-K/A` | 305 |

### XBRL 태그별 현황 (15개 태그 감지)

| 태그 | 건수 (샘플 내) | 기업 수 (샘플 내) |
|------|----------------|-------------------|
| `Assets` | 5,243 | 1,067 |
| `NetCashProvidedByUsedInOperatingActivities` | 5,115 | 1,055 |
| `StockholdersEquity` | 4,946 | 1,011 |
| `NetIncomeLoss` | 4,888 | 1,011 |
| `OperatingIncomeLoss` | 4,130 | 852 |
| `Liabilities` | 4,085 | 842 |
| `PaymentsForRepurchaseOfCommonStock` | 3,867 | 856 |
| `PaymentsToAcquirePropertyPlantAndEquipment` | 3,653 | 771 |
| `RevenueFromContractWithCustomerExcludingAssessedTax` | 3,427 | 720 |
| `InterestExpense` | 2,640 | 731 |
| `Revenues` | 2,282 | 495 |
| `PaymentsOfDividendsCommonStock` | 2,157 | 435 |
| `GrossProfit` | 2,125 | 448 |
| `PaymentsOfDividends` | 1,315 | 288 |
| `PaymentsForRepurchaseOfEquity` | 127 | 35 |

---

## 4. metrics 테이블

- **총 레코드:** 115,093개 (planner 추정)
- **분포 분석:** 샘플 50,000건 기준
- **샘플 내 기업 수:** 1,868개
- **데이터 기간:** 2021-06-25 ~ 2026-04-30

### period_type 분포

| period_type | 건수 (샘플 내) |
|-------------|----------------|
| `annual` | 50,000 |

### 파생 지표 목록

| metric | 건수 (샘플 내) |
|--------|----------------|
| `roe` | 8,040 |
| `net_margin` | 7,416 |
| `debt_to_equity` | 6,885 |
| `operating_margin` | 6,468 |
| `fcf` | 6,357 |
| `dividend_payout` | 4,250 |
| `buyback_to_fcf` | 3,908 |
| `gross_margin` | 3,488 |
| `interest_coverage` | 3,188 |

---

## 5. 개발 참고사항

### 데이터 갭 / 주의사항

- facts는 ETL `TARGET_TAGS` 기준 15개 XBRL 태그만 수집 (전체 us-gaap 중 선택적 수집)
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