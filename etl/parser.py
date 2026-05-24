import json
import logging
import zipfile
from pathlib import Path
from typing import Generator

from .config import TARGET_TAGS, TAXONOMY, HISTORY_CUTOFF

logger = logging.getLogger(__name__)


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


def extract_facts(data: dict) -> list[dict]:
    """핵심 XBRL 태그의 수치만 추출"""
    cik = str(data.get("cik", "")).zfill(10)
    facts_raw = data.get("facts", {}).get(TAXONOMY, {})
    results = []

    for tag, tag_data in facts_raw.items():
        if tag not in TARGET_TAGS:
            continue

        units = tag_data.get("units", {})
        for unit, entries in units.items():
            # USD, shares, USD/shares만 처리
            if unit not in ("USD", "shares", "USD/shares"):
                continue

            for entry in entries:
                end = entry.get("end")
                val = entry.get("val")
                form = entry.get("form", "")
                filed = entry.get("filed")
                frame = entry.get("frame")

                if end is None or val is None:
                    continue

                # 연간(10-K) 또는 분기(10-Q) 공시만
                if form not in ("10-K", "10-Q", "10-K/A", "10-Q/A"):
                    continue

                # 최근 N년 이내 데이터만 수집
                if end < HISTORY_CUTOFF:
                    continue

                results.append({
                    "cik": cik,
                    "tag": tag,
                    "unit": unit,
                    "period_type": _infer_period_type(entry),
                    "start_date": entry.get("start"),
                    "end_date": end,
                    "filed_date": filed,
                    "form": form,
                    "frame": frame,
                    "value": val,
                })

    return results


def _infer_period_type(entry: dict) -> str:
    start = entry.get("start")
    end = entry.get("end")
    if not start:
        return "instant"
    # 시작~끝 기간으로 연간/분기 구분
    from datetime import date
    try:
        d_start = date.fromisoformat(start)
        d_end = date.fromisoformat(end)
        days = (d_end - d_start).days
        if days > 300:
            return "annual"
        elif days > 60:
            return "quarterly"
        else:
            return "other"
    except Exception:
        return "duration"


