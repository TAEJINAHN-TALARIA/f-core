# 작업지시서: ETL 지표 확장 (TARGET_TAGS + 파생 metrics)

> 작성일: 2026-05-25
> 대상 브랜치: 신규 브랜치에서 작업 권장 (예: `feature/metrics-expansion`)
> 예상 소요: 코드 수정 1~2시간 + ETL 재실행 (수 시간)

---

## 0. 배경 및 목적

현재 SEC EDGAR ETL은 `us-gaap` 태그 29개를 수집하고 11개 파생 metric을 계산한다.
최근 audit 결과(`docs/parser_audit.md` 참고) 분석 결과, **수집 폭을 넓히기보다 핵심 투자 지표의 깊이를 늘리는 방향**이 옳다는 결론에 도달했다.

**이번 작업의 원칙:**
- "많이 수집"이 아닌 "투자 의사결정에 직접 쓰이는 핵심 지표"에 집중
- 시계열로 비교 가능한 지표만 추가
- TARGET_TAGS는 35개 내외로 유지 (현재 29개)

**해결하려는 문제:**
1. **EBITDA 계산 불가** — `Depreciation` 또는 `DepreciationDepletionAndAmortization`만으로는 부족, 정상 데이터 부재
2. **Diluted EPS 검증 불가** — Diluted shares 미수집
3. **Tech 기업 평가 왜곡** — SBC(주식기반보상) 미수집 → GAAP earnings 왜곡 보정 불가
4. **자본효율 분석 한계** — PP&E 미수집 → asset turnover, CapEx intensity 계산 불가

---

## 1. 사전 확인 사항 (작업 전 반드시 읽을 것)

### 1-1. CLAUDE.md 원칙 준수
- **Surgical Changes**: 지정된 파일·라인 외에는 건드리지 말 것. 인접 코드 "개선" 금지.
- **Simplicity First**: 새 metric은 단순 derive로 끝낼 것. 추상화 클래스 만들지 말 것.
- **Match existing style**: `_derive()` 함수의 기존 패턴을 그대로 따를 것.

### 1-2. 데이터 사실 (CLAUDE.md 발췌)
- `facts.tag`, `metrics.metric`은 모두 **`TEXT` 자유형**. 신규 태그·메트릭 추가 시 DB 스키마 변경 불필요.
- `facts` 테이블 conflict key: `(cik, tag, unit, end_date, period_type)` — upsert 멱등성 보장.
- `metrics` 테이블 conflict key: `(cik, end_date, period_type, metric)` — 재실행 안전.
- 매출 태그가 `Revenues`와 `RevenueFromContractWithCustomerExcludingAssessedTax` 두 가지로 분리됨.

### 1-3. 기존 코드 위치
| 항목 | 파일 | 라인 |
|------|------|------|
| TARGET_TAGS 정의 | `etl/config.py` | 16-51 |
| 파생 metric 계산 | `etl/normalizer.py` | `_derive()` 함수 (79-134) |
| 안전 연산 헬퍼 | `etl/normalizer.py` | `_safe_div` (144), `_safe_sub` (150) |
| 파이프라인 진입점 | `etl/pipeline.py` | `run()` (23) |

---

## 2. 작업 항목

### Task 1: TARGET_TAGS 5개 추가

**파일**: `etl/config.py`
**위치**: `TARGET_TAGS` set 내부

**추가할 태그** (audit에서 커버리지 4,000+ 확인됨):

```python
# 손익계산서 추가
"WeightedAverageNumberOfDilutedSharesOutstanding",  # 5,505 기업. Diluted EPS 검증
"ShareBasedCompensation",                            # 4,917 기업. SBC-adjusted earnings 계산용
# 재무상태표 추가
"PropertyPlantAndEquipmentNet",                      # 5,051 기업. Asset turnover, ROIC 계산
"CommonStockSharesIssued",                           # 5,147 기업. 희석 위험 측정
# 현금흐름/기타 추가
"Depreciation",                                      # 4,274 기업. EBITDA 계산용 (DDA와 별도)
```

**주의:**
- 알파벳 순 정렬 강요하지 말 것. 기존 그룹(주석으로 구분된 손익/재무상태/현금흐름) 안에 추가.
- 기존 태그(`PaymentsOfDividendsCommonStock`, `PaymentsForRepurchaseOfEquity`) 제거 금지. `_first()` fallback에서 쓰이고 있음.

**검증:**
```bash
python -c "from etl.config import TARGET_TAGS; print(len(TARGET_TAGS))"
# 기대: 34
```

---

### Task 2: 파생 metric 5개 추가

**파일**: `etl/normalizer.py`
**위치**: `_derive()` 함수 (79-134)

**추가할 metric:**

```python
# _derive() 함수 내부에 추가할 변수
da = _first(t, "DepreciationDepletionAndAmortization", "Depreciation")
sbc = t.get("ShareBasedCompensation")
ppe = t.get("PropertyPlantAndEquipmentNet")
diluted_shares = t.get("WeightedAverageNumberOfDilutedSharesOutstanding")
basic_shares = t.get("WeightedAverageNumberOfSharesOutstandingBasic")

# EBITDA = OperatingIncome + D&A
ebitda = _safe_add(operating_income, da)
```

**computed dict에 추가할 항목:**

```python
"ebitda":           ebitda,
"ebitda_margin":    _safe_div(ebitda, revenue),
"cash_conversion":  _safe_div(fcf_val, net_income) if net_income and net_income > 0 else None,
"capex_intensity":  _safe_div(capex, revenue),
"sbc_ratio":        _safe_div(sbc, revenue),
```

**`missing` 추적 추가** (기존 패턴 따라):

```python
if computed["ebitda"] is None:
    missing["ebitda"] = "DepreciationDepletionAndAmortization" if operating_income else "OperatingIncomeLoss"
if computed["ebitda_margin"] is None:
    missing["ebitda_margin"] = "ebitda" if revenue else "revenue"
if computed["capex_intensity"] is None:
    missing["capex_intensity"] = "PaymentsToAcquirePropertyPlantAndEquipment" if revenue else "revenue"
if computed["sbc_ratio"] is None:
    missing["sbc_ratio"] = "ShareBasedCompensation" if revenue else "revenue"
```

**신규 헬퍼 추가** (`_safe_sub` 바로 아래):

```python
def _safe_add(a, b) -> float | None:
    if a is None or b is None:
        return None
    return a + b
```

**의도적으로 추가하지 않는 것 (놓치지 말 것):**
- **ROIC**: NOPAT/Invested Capital 정확 계산은 세율 가정 + invested capital 정의 필요. 근사치는 오해 소지 커서 제외.
- **dilution_ratio**: 단순 비율은 의미 부족. EPS 비교로 충분.
- **Valuation 지표 (P/E, EV/EBITDA)**: 주가 데이터 없음. 별도 작업.

**검증:**
```bash
python -c "
from etl.normalizer import _derive
t = {'Revenues': 1000, 'OperatingIncomeLoss': 200, 'DepreciationDepletionAndAmortization': 50,
     'NetIncomeLoss': 100, 'NetCashProvidedByUsedInOperatingActivities': 150,
     'PaymentsToAcquirePropertyPlantAndEquipment': 30, 'ShareBasedCompensation': 20}
c, m = _derive(t)
assert c['ebitda'] == 250, c['ebitda']
assert c['ebitda_margin'] == 0.25, c['ebitda_margin']
assert c['cash_conversion'] == 1.2, c['cash_conversion']
assert c['capex_intensity'] == 0.03, c['capex_intensity']
assert c['sbc_ratio'] == 0.02, c['sbc_ratio']
print('OK')
"
```

---

### Task 3: ETL 재실행

**전제**: Task 1, 2의 코드 수정 + unit test 통과 후 진행.

**3-1. 기존 데이터 처리 방침 결정**

ETL은 upsert 기반이라 **재실행하면 새 태그·메트릭이 자동으로 채워짐**. truncate 불필요.

**3-2. 실행 명령**

```bash
# 가상환경 활성화 가정. 환경변수(EDGAR_USER_AGENT, SUPABASE_URL, SUPABASE_KEY) 설정 필요.
python -m etl.pipeline 2>&1 | tee /tmp/etl_run_$(date +%Y%m%d_%H%M).log
```

**예상 소요**: SEC rate limit (10 req/s) 고려, 약 6,900 기업 처리에 수 시간. 백그라운드 실행 권장.

**3-3. 진행 중 모니터링 포인트**
- 로그에 신규 태그 카운트가 정상적으로 잡히는지 (`ParseStats` 출력 확인)
- 429 rate limit 에러 발생 시 `etl/downloader.py`의 backoff 동작 확인

---

### Task 4: 검증

**4-1. DB에서 신규 태그·메트릭 적재 확인**

```sql
-- 신규 태그 적재 확인
SELECT tag, COUNT(DISTINCT cik) AS company_count
FROM facts
WHERE tag IN (
  'WeightedAverageNumberOfDilutedSharesOutstanding',
  'ShareBasedCompensation',
  'PropertyPlantAndEquipmentNet',
  'CommonStockSharesIssued',
  'Depreciation'
)
GROUP BY tag
ORDER BY company_count DESC;

-- 신규 메트릭 적재 확인
SELECT metric, COUNT(*) AS row_count, COUNT(DISTINCT cik) AS company_count
FROM metrics
WHERE metric IN ('ebitda', 'ebitda_margin', 'cash_conversion', 'capex_intensity', 'sbc_ratio')
GROUP BY metric;
```

**기대값** (audit 기반 대략):
- `ebitda`: 4,000+ 기업
- `ebitda_margin`: 3,500+ 기업 (revenue 있는 곳에 한정)
- `sbc_ratio`: 3,500+ 기업 (주로 Tech)

**4-2. 샘플 검증**

```sql
-- AAPL (CIK 320193) 최근 EBITDA 확인
SELECT end_date, period_type, metric, value
FROM metrics
WHERE cik = 320193 AND metric IN ('ebitda', 'ebitda_margin', 'operating_margin')
ORDER BY end_date DESC LIMIT 10;
```

**4-3. audit 재실행**

```bash
python scripts/audit_check.py
```

- `metrics.computed` 카운트가 626,464에서 의미 있게 증가했는지 확인
- 신규 metric의 `missing_by_metric` 항목이 합리적인지 확인

---

### Task 5: API 노출 여부 결정 (선택)

**확인할 파일**: `api/routers/financials.py`, `api/schemas.py`

신규 metric을 API로 노출할지 여부에 따라:
- **즉시 노출**: 라우터·스키마에 화이트리스트가 있다면 추가
- **내부 분석용으로만 사용**: API 변경 불필요

> **이 task는 사용자에게 확인 후 진행할 것.** 임의로 결정 금지.

---

## 3. 작업 순서 체크리스트

```
[ ] 1. 신규 브랜치 생성 (feature/metrics-expansion)
[ ] 2. Task 1: etl/config.py에 5개 태그 추가
[ ] 3. Task 1 검증: TARGET_TAGS 길이 34
[ ] 4. Task 2: etl/normalizer.py의 _derive()에 5개 metric 추가
[ ] 5. Task 2: _safe_add 헬퍼 추가
[ ] 6. Task 2 검증: 단위 테스트 한 줄 통과
[ ] 7. 사용자에게 ETL 재실행 승인 요청 (수 시간 소요 + Supabase 비용)
[ ] 8. Task 3: ETL 실행 (백그라운드)
[ ] 9. Task 4: SQL로 신규 데이터 적재 확인
[ ] 10. Task 4: audit_check.py 재실행 결과 비교
[ ] 11. Task 5: API 노출 여부 사용자 확인
[ ] 12. 커밋·푸시
```

---

## 4. 금지 사항 (Surgical Changes 원칙)

다음은 **이번 작업 범위 밖**이므로 절대 건드리지 말 것:

- 기존 11개 metric의 로직 변경 (버그 없는 한)
- `_first()`, `_safe_div()`, `_safe_sub()` 시그니처 변경
- `parser.py`, `downloader.py`, `loader.py` 수정
- `TAXONOMY` 변경 (us-gaap 유지)
- 외화/외국기업 처리 정책 변경 (별도 작업)
- form ↔ period_type 불일치 (53K건) 처리 — 별도 이슈
- 기존 태그 제거
- `HISTORY_CUTOFF` 변경

발견하더라도 코드 주석/README에 메모만 남기고 손대지 말 것. 사용자에게 별도 보고.

---

## 5. 완료 후 보고 사항

작업 완료 시 사용자에게 다음을 요약 보고:

1. 신규 태그별 적재 기업 수 (audit 기대값 대비)
2. 신규 metric별 계산 성공 기업 수
3. ETL 총 소요 시간
4. 발견된 부수 이슈 (있을 시)
5. API 노출 여부에 대한 판단 요청

---

## Appendix: 참고용 audit 발췌

신규 태그의 audit 기반 기대 커버리지:

| 태그 | 기업 수 (audit) |
|------|----------------|
| `WeightedAverageNumberOfDilutedSharesOutstanding` | 5,505 |
| `CommonStockSharesIssued` | 5,147 |
| `PropertyPlantAndEquipmentNet` | 5,051 |
| `ShareBasedCompensation` | 4,917 |
| `Depreciation` | 4,274 |

> 실제 적재 수는 `TARGET_TAGS`에 포함된 후 unit·period·cutoff 필터를 통과한 결과이므로 위 수치보다 작을 수 있음.
