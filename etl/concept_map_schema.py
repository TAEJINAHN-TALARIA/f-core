"""Schema definition and validator for concept_map.json.

Schema (v1):
{
  "<concept>": {
    "tags":     [str, ...],
    "category": "income" | "balance_sheet" | "cashflow",
    "tag_meta": {                       # optional
      "<tag>": {
        "scope":      "total" | "industry_specific" | "component" | "segment",
        "status":     "active" | "pending_review" | "deprecated",
        "priority":   int (0..999),
        "provenance": {
          "source":             "seed" | "auto_llm" | "manual",
          "discovered_at":      ISO 8601 str,        # optional
          "discovered_for_cik": str (10-digit CIK),  # optional
          "model":              str                  # optional
        },
        "notes": str                                 # optional
      }
    }
  }
}

Hand-written validator (no jsonschema dep). Use:
    python -m etl.concept_map_schema [path]
"""
import json
import os
import sys
from typing import Any

VALID_CATEGORIES = {"income", "balance_sheet", "cashflow"}
VALID_SCOPES = {"total", "industry_specific", "component", "segment"}
VALID_STATUSES = {"active", "pending_review", "deprecated"}
VALID_SOURCES = {"seed", "auto_llm", "manual"}

REQUIRED_META_FIELDS = {"scope", "status", "priority", "provenance"}
REQUIRED_PROVENANCE_FIELDS = {"source"}


def _err(errors: list[str], path: str, msg: str) -> None:
    errors.append(f"{path}: {msg}")


def validate_concept_map(data: Any) -> list[str]:
    """Return list of error messages. Empty list = valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root: must be an object"]

    for concept, info in data.items():
        cpath = concept
        if not isinstance(info, dict):
            _err(errors, cpath, "concept value must be an object")
            continue

        tags = info.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            _err(errors, f"{cpath}.tags", "must be a list of strings")
            tags = []

        category = info.get("category")
        if category not in VALID_CATEGORIES:
            _err(errors, f"{cpath}.category", f"must be one of {sorted(VALID_CATEGORIES)}")

        tag_meta = info.get("tag_meta", {})
        if not isinstance(tag_meta, dict):
            _err(errors, f"{cpath}.tag_meta", "must be an object")
            continue

        tag_set = set(tags)
        for tag, meta in tag_meta.items():
            mpath = f"{cpath}.tag_meta.{tag}"
            if tag not in tag_set:
                _err(errors, mpath, "meta entry refers to tag not in tags[]")
            _validate_meta_entry(meta, mpath, errors)

    return errors


def _validate_meta_entry(meta: Any, path: str, errors: list[str]) -> None:
    if not isinstance(meta, dict):
        _err(errors, path, "must be an object")
        return

    missing = REQUIRED_META_FIELDS - meta.keys()
    if missing:
        _err(errors, path, f"missing required fields: {sorted(missing)}")

    if "scope" in meta and meta["scope"] not in VALID_SCOPES:
        _err(errors, f"{path}.scope", f"must be one of {sorted(VALID_SCOPES)}")
    if "status" in meta and meta["status"] not in VALID_STATUSES:
        _err(errors, f"{path}.status", f"must be one of {sorted(VALID_STATUSES)}")
    if "priority" in meta:
        p = meta["priority"]
        if not isinstance(p, int) or p < 0 or p > 999:
            _err(errors, f"{path}.priority", "must be int in [0, 999]")

    prov = meta.get("provenance")
    if prov is not None:
        if not isinstance(prov, dict):
            _err(errors, f"{path}.provenance", "must be an object")
        else:
            prov_missing = REQUIRED_PROVENANCE_FIELDS - prov.keys()
            if prov_missing:
                _err(errors, f"{path}.provenance", f"missing required fields: {sorted(prov_missing)}")
            if "source" in prov and prov["source"] not in VALID_SOURCES:
                _err(errors, f"{path}.provenance.source", f"must be one of {sorted(VALID_SOURCES)}")


def main() -> int:
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.path.join(os.path.dirname(__file__), "..", "web", "lib", "concept_map.json")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = validate_concept_map(data)
    if errors:
        print(f"❌ {len(errors)} validation error(s) in {path}:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"✅ {path} is valid (schema v1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
