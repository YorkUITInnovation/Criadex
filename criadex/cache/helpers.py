"""
Shared cache utilities for Criadex.

@author Kiarash Bashokian
"""

import hashlib
import json
from typing import Any


def stable_hash(*parts: str) -> str:
    """Return a deterministic sha256 hex digest for the joined parts."""
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_cache_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def dumps_json(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def loads_json(raw: bytes | str) -> Any:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)
