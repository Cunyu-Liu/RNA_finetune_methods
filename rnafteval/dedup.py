"""Deduplicate records by sequence hash (BEACON ncRNA has 347 exact dups
across splits — dedup keeps FIRST occurrence so official train split wins)."""
from __future__ import annotations


def dedup(records: list[dict], key_field: str = "seq") -> list[dict]:
    seen: set[str] = set()
    out = []
    for r in records:
        k = str(r.get(key_field, ""))
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out
