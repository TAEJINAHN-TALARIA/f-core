# Parser 감사 보고서

> 생성: 2026-06-13 07:03 UTC

---

## 1. 기업 처리 현황

| 구분 | 수 |
|------|----|
| API 호출 (fetched) | 6,936 |
| XBRL 없음 (404) | 0 |
| TARGET_TAGS 전무 | 912 |
| 필터 후 facts 0건 | 831 |
| **facts 있음** | **5,193** |

---

## 2. 엔트리 처리 현황

| 구분 | 수 |
|------|----|
| 전체 스캔 | 5,581,472 |
| skip 합계 | 4,532,091 |
| 추출 성공 | 852,565 |
| 중복 제거 후 | 389,001 |

### Skip 상세

| 사유 | 건수 |
|------|------|
| null value | 0 |
| past_cutoff | 542,791 |
| future_date | 10 |

**미허용 form (skip_unknown_form)**

| form | 건수 |
|------|------|
| `10-Q` | 3,712,322 |
| `20-F` | 74,736 |
| `10-Q/A` | 66,348 |
| `6-K` | 32,909 |
| `8-K` | 27,047 |
| `DEF 14A` | 5,896 |
| `20-F/A` | 5,662 |
| `10-KT` | 4,340 |
| `40-F` | 2,758 |
| `6-K/A` | 1,513 |
| `S-1` | 1,273 |
| `8-K/A` | 1,216 |
| `POS AM` | 801 |
| `S-1/A` | 735 |
| `PRE 14A` | 629 |
| `10-QT` | 526 |
| `S-4/A` | 443 |
| `F-1` | 336 |
| `40-F/A` | 252 |
| `10-KT/A` | 195 |

**미허용 unit (skip_unknown_unit)**

| unit | 건수 |
|------|------|
| `CNY` | 26,351 |
| `CAD` | 8,983 |
| `JPY` | 6,071 |
| `HKD` | 2,076 |
| `EUR` | 1,954 |
| `SGD` | 1,480 |
| `INR` | 452 |
| `KRW` | 301 |
| `RUB` | 291 |
| `CHF` | 167 |
| `ILS` | 154 |
| `BRL` | 138 |
| `TWD` | 81 |
| `VND` | 76 |
| `GBP` | 49 |

**이상값 skip (invalid_value)**

| 태그 | 사유 | 건수 |
|------|------|------|
| `Liabilities` | negative_not_allowed | 9 |
| `LongTermDebt` | exceeds_max_usd | 1 |

---

## 3. TARGET_TAGS 기업 커버리지

| 태그 | 기업 수 |
|------|---------|
| `Assets` | 5,982 |
| `NetIncomeLoss` | 5,946 |
| `NetCashProvidedByUsedInOperatingActivities` | 5,934 |
| `StockholdersEquity` | 5,822 |
| `Liabilities` | 5,463 |
| `OperatingIncomeLoss` | 5,107 |
| `PaymentsToAcquirePropertyPlantAndEquipment` | 4,564 |
| `InterestExpense` | 4,185 |
| `Revenues` | 3,761 |
| `LongTermDebt` | 3,470 |
| `PaymentsForRepurchaseOfCommonStock` | 3,381 |
| `RevenueFromContractWithCustomerExcludingAssessedTax` | 3,240 |
| `GrossProfit` | 3,047 |
| `PaymentsOfDividends` | 1,543 |
| `PaymentsOfDividendsCommonStock` | 1,429 |
| `PaymentsForRepurchaseOfEquity` | 477 |

---

## 4. 미수집 태그 Top 50 (기업 수 기준)

> TARGET_TAGS에 없는 us-gaap 태그. 기업 커버리지가 높은 것은 추가 검토 필요.

| 태그 | 기업 수 |
|------|---------|
| `NetCashProvidedByUsedInFinancingActivities` | 5,925 |
| `LiabilitiesAndStockholdersEquity` | 5,900 |
| `RetainedEarningsAccumulatedDeficit` | 5,793 |
| `NetCashProvidedByUsedInInvestingActivities` | 5,746 |
| `CashAndCashEquivalentsAtCarryingValue` | 5,580 |
| `EarningsPerShareBasic` | 5,552 |
| `WeightedAverageNumberOfSharesOutstandingBasic` | 5,540 |
| `EarningsPerShareDiluted` | 5,509 |
| `WeightedAverageNumberOfDilutedSharesOutstanding` | 5,501 |
| `IncomeTaxExpenseBenefit` | 5,308 |
| `CommonStockSharesIssued` | 5,140 |
| `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` | 5,129 |
| `EffectiveIncomeTaxRateReconciliationAtFederalStatutoryIncomeTaxRate` | 5,066 |
| `CommonStockSharesAuthorized` | 5,061 |
| `PropertyPlantAndEquipmentNet` | 5,039 |
| `CommonStockValue` | 5,034 |
| `AssetsCurrent` | 5,013 |
| `LiabilitiesCurrent` | 5,002 |
| `CommonStockParOrStatedValuePerShare` | 4,954 |
| `CommonStockSharesOutstanding` | 4,943 |
| `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 4,940 |
| `ShareBasedCompensation` | 4,905 |
| `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect` | 4,902 |
| `DeferredTaxAssetsValuationAllowance` | 4,861 |
| `OperatingLeaseRightOfUseAsset` | 4,811 |
| `AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment` | 4,731 |
| `EffectiveIncomeTaxRateContinuingOperations` | 4,729 |
| `OperatingLeaseLiability` | 4,729 |
| `InterestPaidNet` | 4,692 |
| `StockIssuedDuringPeriodValueNewIssues` | 4,636 |
| `LesseeOperatingLeaseLiabilityPaymentsDue` | 4,606 |
| `LesseeOperatingLeaseLiabilityPaymentsDueNextTwelveMonths` | 4,543 |
| `LesseeOperatingLeaseLiabilityPaymentsDueYearTwo` | 4,522 |
| `NumberOfReportableSegments` | 4,521 |
| `PropertyPlantAndEquipmentGross` | 4,471 |
| `LesseeOperatingLeaseLiabilityUndiscountedExcessAmount` | 4,467 |
| `DeferredTaxAssetsGross` | 4,407 |
| `ComprehensiveIncomeNetOfTax` | 4,400 |
| `IncomeTaxReconciliationIncomeTaxExpenseBenefitAtFederalStatutoryIncomeTaxRate` | 4,385 |
| `LesseeOperatingLeaseLiabilityPaymentsDueYearThree` | 4,376 |
| `OperatingLeaseWeightedAverageDiscountRatePercent` | 4,339 |
| `AccumulatedOtherComprehensiveIncomeLossNetOfTax` | 4,306 |
| `Depreciation` | 4,261 |
| `IncomeTaxesPaidNet` | 4,241 |
| `AdditionalPaidInCapital` | 4,240 |
| `PreferredStockSharesAuthorized` | 4,222 |
| `ProfitLoss` | 4,190 |
| `DeferredIncomeTaxExpenseBenefit` | 4,175 |
| `DeferredTaxAssetsOperatingLossCarryforwards` | 4,167 |
| `LesseeOperatingLeaseLiabilityPaymentsDueYearFour` | 4,162 |

---

## 5. Metrics 계산 실패 사유

| Metric | 누락 재료 태그 | 기업 수 |
|--------|--------------|---------|
| `debt_to_equity` | `Liabilities` | 6,750 |
| `debt_to_equity` | `StockholdersEquity` | 1,725 |
| `fcf` | `PaymentsToAcquirePropertyPlantAndEquipment` | 12,700 |
| `fcf` | `NetCashProvidedByUsedInOperatingActivities` | 1,161 |
| `gross_margin` | `GrossProfit` | 15,080 |
| `gross_margin` | `revenue` | 10,778 |
| `interest_coverage` | `InterestExpense` | 16,456 |
| `interest_coverage` | `OperatingIncomeLoss` | 8,441 |
| `net_margin` | `revenue` | 10,778 |
| `net_margin` | `NetIncomeLoss` | 1,528 |
| `operating_margin` | `revenue` | 10,778 |
| `operating_margin` | `OperatingIncomeLoss` | 4,356 |
| `roe` | `StockholdersEquity` | 2,198 |
| `roe` | `NetIncomeLoss` | 1,972 |