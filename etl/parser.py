import json
import logging
import zipfile
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Generator

from .config import TARGET_TAGS, TAXONOMY, HISTORY_CUTOFF

if TYPE_CHECKING:
    from .stats import ParseStats

logger = logging.getLogger(__name__)

_ALLOWED_FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
_ALLOWED_UNITS = {"USD", "shares", "USD/shares"}


def iter_companyfacts(zip_path: Path) -> Generator[dict, None, None]:
    """ZIP 안의 각 기업 JSON을 순서대로 yield"""
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        logger.info(f"Total companies in ZIP: {len(names)}")

        for i, name in enumerate(names):
            if i % 1000 == 0:
                logger.info(f"  Parsing {i}/{len(names)}...")
            try:
                with zf.open(name) as f:
                    yield json.load(f)
            except Exception as e:
                logger.warning(f"Failed to parse {name}: {e}")


def extract_company_info(data: dict) -> dict | None:
    """기업 메타데이터 추출"""
    cik = data.get("cik")
    if not cik:
        return None

    meta = data.get("_meta", {})
    return {
        "cik": str(cik).zfill(10),
        "name": meta.get("name") or data.get("entityName", ""),
        "sic": data.get("sic"),
        "sic_description": data.get("sicDescription", ""),
        "ticker": meta.get("ticker"),
        "exchange": meta.get("exchange"),
    }


def extract_facts(data: dict, stats: "ParseStats | None" = None) -> list[dict]:
    """핵심 XBRL 태그의 수치만 추출"""
    cik = str(data.get("cik", "")).zfill(10)
    facts_raw = data.get("facts", {}).get(TAXONOMY, {})
    today = date.today().isoformat()
    results = []

    # 미수집 태그 중복 제거용 (기업당 1회만 카운트)
    seen_unknown: set[str] = set()
    seen_target: set[str] = set()

    has_target_tag = False

    for tag, tag_data in facts_raw.items():
        if tag not in TARGET_TAGS:
            if stats:
                # 미수집 태그: 기업당 첫 등장만 기업 수 카운트
                is_new = tag not in seen_unknown
                seen_unknown.add(tag)
                stats.see_unknown_tag(tag, new_company=is_new)
            continue

        has_target_tag = True
        if stats and tag not in seen_target:
            seen_target.add(tag)
            stats.see_target_tag(tag)

        units = tag_data.get("units", {})
        for unit, entries in units.items():
            if unit not in _ALLOWED_UNITS:
                if stats:
                    for _ in entries:
                        stats.scan()
                        stats.skip_unit(unit)
                continue

            for entry in entries:
                if stats:
                    stats.scan()

                end = entry.get("end")
                val = entry.get("val")

                if end is None or val is None:
                    if stats:
                        stats.skip_null_value()
                    continue

                form = entry.get("form", "")
                if form not in _ALLOWED_FORMS:
                    if stats:
                        stats.skip_form(form)
                    continue

                if end < HISTORY_CUTOFF:
                    if stats:
                        stats.skip_past()
                    continue

                if end > today:
                    if stats:
                        stats.skip_future()
                    continue

                results.append({
                    "cik": cik,
                    "tag": tag,
                    "unit": unit,
                    "period_type": _infer_period_type(entry),
                    "start_date": entry.get("start"),
                    "end_date": end,
                    "filed_date": entry.get("filed"),
                    "form": form,
                    "frame": entry.get("frame"),
                    "value": val,
                })
                if stats:
                    stats.record_fact()

    if stats:
        if not has_target_tag:
            stats.mark_no_target_tags()
        elif not results:
            stats.mark_no_facts()

    return results


def _infer_period_type(entry: dict) -> str:
    start = entry.get("start")
    end = entry.get("end")
    if not start:
        return "instant"
    try:
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days
        if days > 300:
            return "annual"
        elif days > 60:
            return "quarterly"
        else:
            return "other"
    except Exception:
        return "duration"
