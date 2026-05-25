"""
ETL 파싱 통계 수집기.
pipeline.py가 ParseStats 인스턴스를 생성해 parser/normalizer에 주입하고,
완료 후 save()로 보고서를 저장한다.
"""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


class ParseStats:
    def __init__(self):
        # 기업 수준
        self.companies_fetched = 0
        self.companies_no_xbrl = 0          # 404
        self.companies_no_target_tags = 0   # XBRL 있지만 TARGET_TAGS 전무
        self.companies_no_facts = 0         # 태그는 있지만 필터 후 0건

        # 엔트리 수준 (entry 하나 = 태그 × 날짜 × 제출 건)
        self.entries_scanned = 0
        self.skip_null = 0
        self.skip_unknown_form: Counter = Counter()
        self.skip_unknown_unit: Counter = Counter()
        self.skip_past_cutoff = 0
        self.skip_future_date = 0
        self.facts_extracted = 0
        self.facts_after_dedup = 0

        # 미수집 태그 (TARGET_TAGS 외) — 기업 수 기준
        self.unknown_tags: Counter = Counter()      # tag → 등장한 기업 수
        self.unknown_tags_entries: Counter = Counter()  # tag → 총 엔트리 수

        # TARGET_TAGS 기업 커버리지
        self.target_tag_companies: Counter = Counter()  # tag → 기업 수

        # 이상값 skip: tag → reason → 건수
        self.skip_invalid: dict[str, Counter] = {}

        # form ↔ period_type 불일치 관측 (skip 없음): "10-K/quarterly" → 건수
        self.form_period_mismatch: Counter = Counter()

        # metrics 계산 실패 사유: metric → 누락된 재료 태그 → 기업 수
        self.metrics_missing: dict[str, Counter] = {}

        # metrics 계산 성공
        self.metrics_computed = 0

    # ── 기업 수준 ────────────────────────────────────────────

    def mark_no_xbrl(self):
        self.companies_no_xbrl += 1

    def mark_fetched(self):
        self.companies_fetched += 1

    def mark_no_target_tags(self):
        self.companies_no_target_tags += 1

    def mark_no_facts(self):
        self.companies_no_facts += 1

    # ── 엔트리 수준 ──────────────────────────────────────────

    def scan(self):
        self.entries_scanned += 1

    def skip_null_value(self):
        self.skip_null += 1

    def skip_form(self, form: str):
        self.skip_unknown_form[form or "NULL"] += 1

    def skip_unit(self, unit: str):
        self.skip_unknown_unit[unit] += 1

    def skip_past(self):
        self.skip_past_cutoff += 1

    def skip_future(self):
        self.skip_future_date += 1

    def record_fact(self):
        self.facts_extracted += 1

    def record_dedup(self, count: int):
        self.facts_after_dedup += count

    def skip_invalid_value(self, tag: str, reason: str):
        if tag not in self.skip_invalid:
            self.skip_invalid[tag] = Counter()
        self.skip_invalid[tag][reason] += 1

    def note_mismatch(self, form: str, period_type: str):
        self.form_period_mismatch[f"{form}/{period_type}"] += 1

    # ── 태그 발견 ────────────────────────────────────────────

    def see_unknown_tag(self, tag: str, new_company: bool = False):
        """TARGET_TAGS에 없는 태그를 만났을 때 호출."""
        self.unknown_tags_entries[tag] += 1
        if new_company:
            self.unknown_tags[tag] += 1

    def see_target_tag(self, tag: str):
        self.target_tag_companies[tag] += 1

    # ── metrics ──────────────────────────────────────────────

    def metric_missing(self, metric: str, missing_tag: str):
        if metric not in self.metrics_missing:
            self.metrics_missing[metric] = Counter()
        self.metrics_missing[metric][missing_tag] += 1

    def metric_ok(self, count: int):
        self.metrics_computed += count

    # ── 저장 ─────────────────────────────────────────────────

    def save(self, out_dir: str = "docs") -> None:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)

        data = self._to_dict(now)
        json_path = os.path.join(out_dir, "parser_audit.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        md_path = os.path.join(out_dir, "parser_audit.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._to_markdown(now))

        print(f"[stats] 감사 보고서 저장: {json_path}, {md_path}")

    def _to_dict(self, now: datetime) -> dict:
        invalid_total = sum(
            sum(c.values()) for c in self.skip_invalid.values()
        )
        skip_total = (
            self.skip_null
            + sum(self.skip_unknown_form.values())
            + sum(self.skip_unknown_unit.values())
            + self.skip_past_cutoff
            + self.skip_future_date
            + invalid_total
        )
        return {
            "generated_at": now.isoformat(),
            "companies": {
                "fetched": self.companies_fetched,
                "no_xbrl_404": self.companies_no_xbrl,
                "no_target_tags": self.companies_no_target_tags,
                "no_facts_after_filter": self.companies_no_facts,
                "with_facts": (
                    self.companies_fetched
                    - self.companies_no_xbrl
                    - self.companies_no_target_tags
                    - self.companies_no_facts
                ),
            },
            "entries": {
                "scanned": self.entries_scanned,
                "extracted": self.facts_extracted,
                "after_dedup": self.facts_after_dedup,
                "skipped_total": skip_total,
                "skip_breakdown": {
                    "null_value": self.skip_null,
                    "past_cutoff": self.skip_past_cutoff,
                    "future_date": self.skip_future_date,
                    "invalid_value": {
                        tag: dict(c) for tag, c in self.skip_invalid.items()
                    },
                    "unknown_form": dict(self.skip_unknown_form.most_common(30)),
                    "unknown_unit": dict(self.skip_unknown_unit.most_common(20)),
                },
            },
            "form_period_mismatch": dict(self.form_period_mismatch.most_common()),
            "target_tag_company_coverage": dict(
                self.target_tag_companies.most_common()
            ),
            "unknown_tags_top50": dict(self.unknown_tags.most_common(50)),
            "metrics": {
                "computed": self.metrics_computed,
                "missing_by_metric": {
                    metric: dict(counter.most_common(10))
                    for metric, counter in sorted(self.metrics_missing.items())
                },
            },
        }

    def _to_markdown(self, now: datetime) -> str:
        d = self._to_dict(now)
        c = d["companies"]
        e = d["entries"]
        skip = e["skip_breakdown"]

        lines = [
            "# Parser 감사 보고서",
            "",
            f"> 생성: {now.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "---",
            "",
            "## 1. 기업 처리 현황",
            "",
            "| 구분 | 수 |",
            "|------|----|",
            f"| API 호출 (fetched) | {c['fetched']:,} |",
            f"| XBRL 없음 (404) | {c['no_xbrl_404']:,} |",
            f"| TARGET_TAGS 전무 | {c['no_target_tags']:,} |",
            f"| 필터 후 facts 0건 | {c['no_facts_after_filter']:,} |",
            f"| **facts 있음** | **{c['with_facts']:,}** |",
            "",
            "---",
            "",
            "## 2. 엔트리 처리 현황",
            "",
            "| 구분 | 수 |",
            "|------|----|",
            f"| 전체 스캔 | {e['scanned']:,} |",
            f"| skip 합계 | {e['skipped_total']:,} |",
            f"| 추출 성공 | {e['extracted']:,} |",
            f"| 중복 제거 후 | {e['after_dedup']:,} |",
            "",
            "### Skip 상세",
            "",
            "| 사유 | 건수 |",
            "|------|------|",
            f"| null value | {skip['null_value']:,} |",
            f"| past_cutoff | {skip['past_cutoff']:,} |",
            f"| future_date | {skip['future_date']:,} |",
        ]

        if skip["unknown_form"]:
            lines += [
                "",
                "**미허용 form (skip_unknown_form)**",
                "",
                "| form | 건수 |",
                "|------|------|",
            ]
            for form, cnt in sorted(
                skip["unknown_form"].items(), key=lambda x: -x[1]
            )[:20]:
                lines.append(f"| `{form}` | {cnt:,} |")

        if skip["unknown_unit"]:
            lines += [
                "",
                "**미허용 unit (skip_unknown_unit)**",
                "",
                "| unit | 건수 |",
                "|------|------|",
            ]
            for unit, cnt in sorted(
                skip["unknown_unit"].items(), key=lambda x: -x[1]
            )[:15]:
                lines.append(f"| `{unit}` | {cnt:,} |")

        if skip["invalid_value"]:
            lines += [
                "",
                "**이상값 skip (invalid_value)**",
                "",
                "| 태그 | 사유 | 건수 |",
                "|------|------|------|",
            ]
            for tag, reasons in sorted(skip["invalid_value"].items()):
                for reason, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
                    lines.append(f"| `{tag}` | {reason} | {cnt:,} |")

        if d.get("form_period_mismatch"):
            lines += [
                "",
                "**form ↔ period_type 불일치 (관측, skip 아님)**",
                "",
                "| form/period_type | 건수 |",
                "|------------------|------|",
            ]
            for key, cnt in sorted(
                d["form_period_mismatch"].items(), key=lambda x: -x[1]
            ):
                lines.append(f"| `{key}` | {cnt:,} |")

        lines += [
            "",
            "---",
            "",
            "## 3. TARGET_TAGS 기업 커버리지",
            "",
            "| 태그 | 기업 수 |",
            "|------|---------|",
        ]
        for tag, cnt in sorted(
            d["target_tag_company_coverage"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"| `{tag}` | {cnt:,} |")

        lines += [
            "",
            "---",
            "",
            "## 4. 미수집 태그 Top 50 (기업 수 기준)",
            "",
            "> TARGET_TAGS에 없는 us-gaap 태그. 기업 커버리지가 높은 것은 추가 검토 필요.",
            "",
            "| 태그 | 기업 수 |",
            "|------|---------|",
        ]
        for tag, cnt in list(d["unknown_tags_top50"].items())[:50]:
            lines.append(f"| `{tag}` | {cnt:,} |")

        lines += [
            "",
            "---",
            "",
            "## 5. Metrics 계산 실패 사유",
            "",
            "| Metric | 누락 재료 태그 | 기업 수 |",
            "|--------|--------------|---------|",
        ]
        for metric, missing in sorted(d["metrics"]["missing_by_metric"].items()):
            for missing_tag, cnt in sorted(
                missing.items(), key=lambda x: -x[1]
            ):
                lines.append(f"| `{metric}` | `{missing_tag}` | {cnt:,} |")

        return "\n".join(lines)
