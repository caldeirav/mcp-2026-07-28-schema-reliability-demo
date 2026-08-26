"""Load JSON Schema documents shipped next to the FastMCP servers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SCHEMAS = Path(__file__).resolve().parent / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    path = _SCHEMAS / name
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"schema {name} must be an object")
    return data
