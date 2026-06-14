"""Smoke tests for concept_map_schema validator.

Run: python -m etl.test_concept_map_schema
"""
import json
import os
import sys

from .concept_map_schema import validate_concept_map

CONCEPT_MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "web", "lib", "concept_map.json")


def expect_valid(name: str, data: dict) -> None:
    errs = validate_concept_map(data)
    assert not errs, f"[{name}] expected valid, got errors: {errs}"
    print(f"  ✅ {name}")


def expect_errors(name: str, data: dict, *needles: str) -> None:
    errs = validate_concept_map(data)
    assert errs, f"[{name}] expected errors, got none"
    for needle in needles:
        assert any(needle in e for e in errs), f"[{name}] missing error containing {needle!r}; got {errs}"
    print(f"  ✅ {name} ({len(errs)} errors as expected)")


def base_concept(tags=("Foo",), category="income", tag_meta=None):
    d = {"tags": list(tags), "category": category}
    if tag_meta is not None:
        d["tag_meta"] = tag_meta
    return d


def meta(scope="total", status="active", priority=0, source="seed", **extra):
    m = {
        "scope": scope,
        "status": status,
        "priority": priority,
        "provenance": {"source": source, **extra.pop("provenance_extra", {})},
    }
    m.update(extra)
    return m


def run() -> int:
    print("== Schema validator tests ==")

    # Positive: minimal valid (no meta)
    expect_valid("minimal-no-meta", {"revenue": base_concept()})

    # Positive: valid with one meta entry
    expect_valid(
        "with-meta-entry",
        {"revenue": base_concept(tag_meta={"Foo": meta()})},
    )

    # Negative: bad category
    expect_errors(
        "bad-category",
        {"revenue": base_concept(category="other")},
        "category",
    )

    # Negative: meta refers to tag not in tags[]
    expect_errors(
        "meta-orphan-tag",
        {"revenue": base_concept(tag_meta={"Ghost": meta()})},
        "not in tags[]",
    )

    # Negative: missing required meta fields
    expect_errors(
        "meta-missing-fields",
        {"revenue": base_concept(tag_meta={"Foo": {"scope": "total"}})},
        "missing required fields",
    )

    # Negative: invalid scope/status/priority
    expect_errors(
        "meta-bad-scope",
        {"revenue": base_concept(tag_meta={"Foo": meta(scope="wrong")})},
        "scope",
    )
    expect_errors(
        "meta-bad-status",
        {"revenue": base_concept(tag_meta={"Foo": meta(status="wrong")})},
        "status",
    )
    expect_errors(
        "meta-bad-priority",
        {"revenue": base_concept(tag_meta={"Foo": meta(priority=1000)})},
        "priority",
    )

    # Negative: invalid provenance source
    expect_errors(
        "bad-provenance-source",
        {"revenue": base_concept(tag_meta={"Foo": {
            "scope": "total", "status": "active", "priority": 0,
            "provenance": {"source": "made_up"},
        }})},
        "provenance.source",
    )

    # Real file: must currently validate (post-backfill).
    print("\n== Validating real concept_map.json ==")
    with open(CONCEPT_MAP_PATH, "r", encoding="utf-8") as f:
        real = json.load(f)
    real_errs = validate_concept_map(real)
    if real_errs:
        print(f"  ❌ {len(real_errs)} errors in real concept_map.json:")
        for e in real_errs:
            print(f"    - {e}")
        return 1
    print("  ✅ real concept_map.json is valid")
    return 0


if __name__ == "__main__":
    sys.exit(run())
