# Parser 감사 보고서

> 생성: 2026-06-13 00:28 UTC

---

## 1. 기업 처리 현황

| 구분 | 수 |
|------|----|
| API 호출 (fetched) | 6,936 |
| XBRL 없음 (404) | 0 |
| TARGET_TAGS 전무 | 913 |
| 필터 후 facts 0건 | 853 |
| **facts 있음** | **5,170** |

---

## 2. 엔트리 처리 현황

| 구분 | 수 |
|------|----|
| 전체 스캔 | 5,463,089 |
| skip 합계 | 5,006,241 |
| 추출 성공 | 426,509 |
| 중복 제거 후 | 207,984 |

### Skip 상세

| 사유 | 건수 |
|------|------|
| null value | 0 |
| past_cutoff | 1,101,266 |
| future_date | 1 |

**미허용 form (skip_unknown_form)**

| form | 건수 |
|------|------|
| `10-Q` | 3,633,605 |
| `20-F` | 73,134 |
| `10-Q/A` | 65,427 |
| `6-K` | 32,084 |
| `8-K` | 26,362 |
| `DEF 14A` | 5,896 |
| `20-F/A` | 5,569 |
| `10-KT` | 4,245 |
| `40-F` | 2,620 |
| `6-K/A` | 1,468 |
| `S-1` | 1,244 |
| `8-K/A` | 1,189 |
| `POS AM` | 794 |
| `S-1/A` | 722 |
| `PRE 14A` | 629 |
| `10-QT` | 512 |
| `S-4/A` | 437 |
| `F-1` | 326 |
| `40-F/A` | 241 |
| `10-KT/A` | 194 |

**미허용 unit (skip_unknown_unit)**

| unit | 건수 |
|------|------|
| `CNY` | 25,924 |
| `CAD` | 8,879 |
| `JPY` | 5,806 |
| `HKD` | 2,025 |
| `EUR` | 1,886 |
| `SGD` | 1,423 |
| `INR` | 420 |
| `KRW` | 297 |
| `RUB` | 287 |
| `CHF` | 150 |
| `ILS` | 141 |
| `BRL` | 128 |
| `TWD` | 77 |
| `VND` | 76 |
| `GBP` | 44 |

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
| `debt_to_equity` | `Liabilities` | 3,090 |
| `debt_to_equity` | `StockholdersEquity` | 1,069 |
| `fcf` | `PaymentsToAcquirePropertyPlantAndEquipment` | 7,611 |
| `fcf` | `NetCashProvidedByUsedInOperatingActivities` | 502 |
| `gross_margin` | `GrossProfit` | 8,426 |
| `gross_margin` | `revenue` | 6,127 |
| `interest_coverage` | `InterestExpense` | 11,013 |
| `interest_coverage` | `OperatingIncomeLoss` | 4,667 |
| `net_margin` | `revenue` | 6,127 |
| `net_margin` | `NetIncomeLoss` | 776 |
| `operating_margin` | `revenue` | 6,127 |
| `operating_margin` | `OperatingIncomeLoss` | 2,425 |
| `roe` | `StockholdersEquity` | 1,277 |
| `roe` | `NetIncomeLoss` | 967 |