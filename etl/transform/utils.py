from typing import Any


def int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def dict_or_empty(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list:
    if value in (None, [], {}):
        return []
    return value if isinstance(value, list) else [value]


def unique(values: list) -> list:
    return list(dict.fromkeys(value for value in values if value))


def scalar_or_list(values: list):
    values = unique(values)
    return values[0] if len(values) == 1 else values


def first_value(value: Any) -> Any:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and "scielo.br" in item:
                return item
        return value[0] if value else None
    return value
