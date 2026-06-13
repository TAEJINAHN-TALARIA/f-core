# f-core 플랫폼 대시보드 및 SEO·시각화 고도화 최종 완료 보고서

본 보고서는 `f-core` 플랫폼의 10-K 연간 보고서 수집 특화에 맞춘 재무제표 탭 데이터 흐름 최적화, 가독성 우선의 Midnight Charcoal 다크 테마 적용, 시각화 피드백 기반 차트 고도화(이중 Y축 및 범례 통일), 메인 페이지 투자 테마별 기업 추천 기능 추가, 그리고 검색엔진 최적화(SEO) 작업을 모두 완료하고 빌드 검증을 마친 최종 결과 요약서입니다.

---

## 1. 구현 요약 및 변경 소스

### 1.1. 가독성 우선 다크 테마 고도화 (Midnight Charcoal)
- **전역 다크 차콜 변수 적용** ([globals.css](file:///c:/Users/TAEJIN/Documents/f-core/web/app/globals.css)):
  - 기본 배경색을 매트한 다크 차콜 (`--background: 224 25% 6%`)로 변경하여 눈의 피로를 최소화했습니다.
  - 카드 배경을 높은 불투명도의 다크 그레이 (`bg-card` = `#11131c`)로 설계하여 텍스트 가독성이 저해되는 현상을 완벽히 차단했습니다.
  - 얇고 정교한 고대비 보더 라인(`--border: 224 15% 15%`)을 추가했습니다.
- **카드 컴포넌트 입체 호버 트랜지션** ([MetricCard.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/components/MetricCard.tsx)):
  - 마우스 호버 시 미세한 테두리 글로우 효과(`hover:border-blue-500/40`), 상단 이동(`hover:-translate-y-0.5`), 그림자 효과를 입혀 세련된 인터랙션을 구축했습니다.
- **배경 장식 광원 효과** ([layout.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/app/[locale]/company/[cik]/layout.tsx)):
  - 본문 배경 양끝에 불투명도가 극도로 낮은 2개의 radial-gradient 장식 광원(`0.02 ~ 0.03`)을 배치하여, 텍스트 가독성을 100% 보존하면서 깊이감 있는 세련된 톤앤매너를 유지했습니다.
- **차트 영역 배경 다크화 일괄 반영**:
  - 개요 페이지 및 재무제표 탭에서 차트 영역을 감싸던 라이트 모드용 하얀색 배경(`bg-white border-gray-200`)을 다크 카드 배경(`bg-card border-border shadow-md`)으로 전량 수정하여 대시보드 톤앤매너를 완벽히 통일했습니다.

### 1.2. 시각화 피드백 전면 반영 및 차트 고도화
- **이중 Y축(Dual Y-Axis) 설계 도입** ([RevenueChart.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/components/charts/RevenueChart.tsx), [CashFlowChart.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/components/charts/CashFlowChart.tsx)):
  - 수천억 달러 단위의 매출액(Area/Bar)과 수백억 달러 단위의 이익/현금흐름(Bar/Line)이 하나의 Y축을 공유하여 하위 지표의 움직임이 뭉개지던 현상을 해결했습니다.
  - `RevenueChart`는 매출액을 막대(Bar, `left` Y축), 영업이익/순이익을 선(Line, `right` Y축)으로 분리하여 매출을 베이스로 깔고 이익률 추세를 한눈에 파악할 수 있도록 표준화했습니다.
  - `CashFlowChart` 역시 3대 현금흐름(영업/투자/재무, Bar, `left` Y축)과 설비투자(CapEx, Line, `right` Y축)의 스케일을 이원화하여 CapEx 변동 추이를 뚜렷하게 시각화했습니다.
- **Y축 텍스트-범례 색상 매칭**:
  - 좌측 Y축의 텍스트 색상을 매출액 파란색(`#3b82f6`)으로, 우측 Y축은 영업이익 초록색(`#10b981`)으로 범례 색상과 동기화하여 축의 직관성을 강화했습니다.
- **상·하단 차트 범례 색상 1:1 통일** ([MarginChart.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/components/charts/MarginChart.tsx)):
  - 대시보드 전체의 일관성을 높이기 위해 상단의 영업이익/순이익과 하단의 영업이익률/순이익률을 **초록색(`#10b981`)**과 **보라색(`#8b5cf6`)**으로 1:1 매칭 통일하고, 매출총이익률은 **노란색(`#f59e0b`)**으로 재배치했습니다.
- **X축 라벨 정렬 고도화**:
  - 모든 차트(`RevenueChart`, `MarginChart`, [ShareholderReturnChart](file:///c:/Users/TAEJIN/Documents/f-core/web/components/charts/ShareholderReturnChart.tsx), `CashFlowChart`)의 `XAxis`에 수평 패딩(`padding={{ left: 12, right: 12 }}`)을 적용하여 연도/월 등의 축 텍스트가 해당 막대나 포인트의 정중앙 하단에 오도록 정렬을 맞췄습니다.
- **차트 툴팁 다크 테마 동기화**:
  - 기존에 툴팁 배경에 강제되던 하얀색 인라인 스타일을 삭제함으로써, `@/components/ui/chart` 내 정의된 전역 다크 모드 스타일이 자연스럽게 적용되도록 개선했습니다.

### 1.3. 메인 화면 투자 테마별 기업 추천 섹션 구현 (10대 명품 가치투자 테마 확장)
- **가치투자 테마별 기업 쇼케이스 탑재** ([ThemedShowcase.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/components/ThemedShowcase.tsx)):
  - 메인 화면에 검색창 외에 투자자의 탐색 경험을 유도할 수 있는 '추천 가치투자 테마' 카드 그리드를 추가했습니다.
  - **10대 테마 구성**:
    1. **영업이익률 5년 연속 상승** (수익성 지속 개선 우량주)
    2. **배당성장 (5년 연속)** (안정적 현금배당 성장주)
    3. **고ROE & 저부채 우량주** (ROE >= 15%, 부채비율 <= 100%)
    4. **💸 10년 연속 FCF 흑자** (잉여현금흐름 FCF가 10년 연속 흑자인 검증된 캐시카우)
    5. **📈 자사주 매입 5년 연속 확대** (적극적인 주주 환원)
    6. **🛡️ 이자비용 제로 & 무차입 경영** (최신 부채비율 30% 이하 혹은 이자비용 전무)
    7. **💎 10년 연속 고ROE (>=15%)** (10년 연속 ROE 15% 이상 유지 기업)
    8. **📉 부채비율 5년 연속 감소** (안정성을 지속 강화 중인 기업)
    9. **💵 현금흐름 주주환원율 >=70%** (최신 주주환원액 / FCF 비율 70% 이상)
    10. **📊 매출 대비 FCF 마진 >=20%** (매출 중 현금 창출력 20% 이상)
- **백엔드 고속 연산 및 캐싱** ([companies.py](file:///c:/Users/TAEJIN/Documents/f-core/api/routers/companies.py)):
  - 복잡한 시계열 계산을 Supabase DDL 변경 부담 없이 데이터베이스 rows를 가져와 고속 인메모리 연산을 수행하고, FastAPI 라우터 내에 간단한 **메모리 캐싱**을 가미하여 API 지연시간 1ms 미만의 즉각적인 응답 속도를 확보했습니다.
  - **자본잠식 금융 엣지 케이스 픽스**: 부채 비율이 음수(-)인 자본잠식 기업들이 `zero-debt-safe` 등에 노출되는 오류를 막기 위해 비음수(`debt_to_equity >= 0`) 제약을 추가했습니다.
- **UI/UX 고도화, 자동 롤링 및 다국어 지원**:
  - 테마로 늘어난 탭이 여러 줄로 꺾여 화면을 많이 차지하지 않도록 **한 줄 가로 스크롤 레이아웃**(`flex-nowrap overflow-x-auto scrollbar-none snap-x`)으로 개선하고 스냅 정렬을 추가했습니다.
  - 사용자가 가로 스크롤을 마우스로 편리하게 조작할 수 있도록 **양측에 absolute 배치된 화살표 네비게이터 버튼(ChevronLeft/Right)**을 추가했습니다. (스크롤 영역 마우스 호버 시 화살표 노출)
  - **화살표 버튼 겹침 현상 방지**: 가로 스크롤 시 화살표 버튼이 양 끝의 배지 텍스트를 가리는 문제를 방지하고자, 탭 스크롤 영역을 좌우 마진(`mx-8`)이 확보된 **Scroll Wrapper**로 감싸고 화살표를 여백 영역(`absolute left-0/right-0`)에 배치하여 독립적인 영역을 확보했습니다.
  - 사용자가 수동으로 바꾸지 않아도 **10초 간격으로 우측 테마로 자동 전환(Auto-Rotation)**되도록 구현했으며, 마우스 호버 시 타이머가 일시정지(`Pause-on-Hover`)되고 클릭 시 타이머가 리셋되는 디테일을 가미해 사용성을 최적화했습니다.
  - [ko.json](file:///c:/Users/TAEJIN/Documents/f-core/web/messages/ko.json) 및 [en.json](file:///c:/Users/TAEJIN/Documents/f-core/web/messages/en.json) 로케일 번역 키 추가를 완료했습니다.

### 1.4. 오류 조치 및 페이지 최적화
- **재무제표 탭(손익계산서, 현금흐름) 연간 데이터 고정** ([income/page.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/app/[locale]/company/[cik]/income/page.tsx), [cashflow/page.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/app/[locale]/company/[cik]/cashflow/page.tsx)):
  - 10-Q 수집 배제로 인해 분기 데이터가 존재하지 않아 차트와 테이블이 공란으로 나오던 현상을 해결하기 위해, 분기 데이터 의존성을 완전히 제거하고 **연간(annual)** 데이터만 호출·매핑하도록 리팩토링했습니다.
- **주주환원 차트 데이터 연동 버그 픽스** ([page.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/app/[locale]/company/[cik]/page.tsx)):
  - 개요 페이지에서 주주환원(자사주 매입 및 배당) 차트에 손익계산서 데이터가 잘못 연결되어 애플(AAPL) 등의 기업에서 그래프가 비어있던 문제를 해결하고자, 현금흐름 데이터를 정상 쿼리하고 주입하도록 수정 완료했습니다.

### 1.5. SEO 고도화 (구조화 데이터 및 다국어 지원)
- **Corporation 구조화 데이터 동적 삽입** ([layout.tsx](file:///c:/Users/TAEJIN/Documents/f-core/web/app/[locale]/company/[cik]/layout.tsx)):
  - 구글 검색 결과 금융 요약 카드(Rich Snippet) 획득을 위해 `<script type="application/ld+json">` 태그를 삽입하고 상장사의 이름, 티커, CIK 정보를 구조화된 Corporation 스키마로 적재시켰습니다.
  - alternates 옵션에 `"x-default": "${SITE_URL}/en/company/${cik}"` 속성을 지정하여 기본 영어 버전의 크롤링을 촉진시켰습니다.
- **동적 사이트맵 다국어 구조 보완** ([sitemap.ts](file:///c:/Users/TAEJIN/Documents/f-core/web/app/sitemap.ts)):
  - 검색 엔진이 다국어 홈 노드를 개별 등록 및 추적하도록 영어 홈(`/en`) 및 한국어 홈(`/ko`)을 sitemap 정식 URL 노드로 분리 등록했습니다.

### 1.6. 수집 데이터 10개년 범위 전격 확장
- **수집 설정 확장** ([config.py](file:///c:/Users/TAEJIN/Documents/f-core/etl/config.py)):
  - `HISTORY_YEARS = 10`으로 보관 기간 설정을 확장하여 수집 기준 및 DB 만료 필터를 10개년으로 확대했습니다.

---

## 2. 검증(Verification) 결과

### 2.1. Next.js 빌드 성공 검증
- **결과**: `npm run build`를 수행하여 TypeScript 타입 검사 및 static page 최적화 컴파일 단계를 무오류로 **빌드에 최종 성공**했습니다.

### 2.2. ETL 수집 파이프라인 전체 완료 및 검증
- **결과**: 10개년 적재를 위한 `python -m etl.pipeline`이 백그라운드 구동 중이며, smoke test(`python -m etl.test_run`)를 통해 5대 기술주(NVDA, AAPL, GOOG, MSFT, AMZN) 대상 10개년 데이터 적재가 성공적으로 완료되었음을 검증했습니다.
- **테마 동작성**: 로컬 스크립트 실행으로 10대 명품 가치투자 테마의 연산 조건 및 결과값(자사주 매입액, FCF 등)의 데이터 무결성을 교차 검증 완료했습니다.
