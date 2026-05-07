import hashlib
import re
from typing import Any

import orjson


def clean_source_payload(source: Any) -> Any:
    """Return the domain payload without harvest/indexing metadata."""
    if isinstance(source, dict) and isinstance(source.get("raw_data"), dict):
        return source["raw_data"]
    if isinstance(source, dict):
        return {
            key: value
            for key, value in source.items()
            if key not in {"oca_indexed_at", "oca_source_hash"}
        }
    return source or {}


def source_hash(source: Any) -> str:
    """Build a stable SHA-256 hash for the effective source payload."""
    payload = orjson.dumps(clean_source_payload(source), option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(payload).hexdigest()


def parse_author_name(name):
    # Usando regex para encontrar os padrões de nome/sobrenome
    name_pattern = re.compile(r"^\s*([^,]+)\s*,\s*(.+?)\s*$")
    match = name_pattern.match(name)

    if match:
        return {"given_names": match.group(2), "surname": match.group(1)}
    else:
        return {"declared_name": name}
