from typing import Any, List


def normalize_int(value: Any, fallback: Any = None) -> Any:
    if value in (None, ""):
        return fallback
    try:
        return int(value)
    except (ValueError, TypeError):
        return fallback


def normalize_float(value: Any, fallback: Any = None) -> Any:
    if value in (None, ""):
        return fallback
    try:
        return float(value)
    except (ValueError, TypeError):
        return fallback


def normalize_option(
    value: Any,
    options: List[str],
    fallback: Any = None,
    lower: bool = False,
) -> Any:
    if value in (None, ""):
        return fallback

    val_str = str(value).strip()
    val_match = val_str.lower() if lower else val_str
    opts_list = [o.lower() for o in options] if lower else options

    if val_match in opts_list:
        if lower:
            for o in options:
                if o.lower() == val_match:
                    return o
        return val_str

    return fallback
