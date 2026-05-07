import re


def stz_doi(doi: str | None) -> str | None:
    if not doi:
        return None

    normalized = str(doi).strip().lower()
    normalized = re.sub(r"^https?://(dx\.)?doi\.org/", "", normalized)
    normalized = re.sub(r"^doi:", "", normalized)
    normalized = re.sub(r"([0-9\-])([a-z]{2})$", r"\1", normalized)

    return normalized if re.match(r"^10\.\d{4,9}/\S+$", normalized) else None


def stz_isbn(isbn: str | None) -> str | None:
    if not isbn:
        return None

    normalized = str(isbn).strip().replace("-", "").replace(" ", "")
    if len(normalized) == 10 and re.match(r"^\d{9}[\dX]$", normalized, re.IGNORECASE):
        return normalized.upper()
    if len(normalized) == 13 and normalized.isdigit():
        return normalized

    return None


def stz_issn(issn: str | None) -> str | None:
    if not issn:
        return None

    normalized = re.sub(r"[^\dX]", "", str(issn).upper())
    if len(normalized) == 8:
        return f"{normalized[:4]}-{normalized[4:]}"
    return None
