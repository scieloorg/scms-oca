"""Citation item builders for social production records."""

from __future__ import annotations

from django.utils.translation import gettext as _

SOCIAL_PRODUCTION_CSV_COLUMNS = (
    "number",
    "action",
    "title",
    "link",
    "institution",
    "state",
    "city",
    "year",
)

_SOCIAL_PRODUCTION_INDEX = "social_production"


def is_social_production_document(entry):
    if not isinstance(entry, dict):
        return False

    index = str(entry.get("index") or "").strip()
    if index == _SOCIAL_PRODUCTION_INDEX or index.endswith(f".{_SOCIAL_PRODUCTION_INDEX}"):
        return True

    source = entry.get("source")
    return isinstance(source, dict) and source.get("type") == "directory"


def _join_values(values):
    if not values:
        return ""
    if isinstance(values, list):
        return ", ".join(str(value).strip() for value in values if value not in (None, ""))
    return str(values).strip()


def extract_social_production_fields(entry, *, language=None):
    source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
    title = entry.get("title")
    if title in (None, ""):
        title = source.get("title")
    year = source.get("start_date_year")
    if year in (None, ""):
        year = source.get("year") or ""

    return {
        "action": _join_values(source.get("action")),
        "title": "" if title in (None, "") else str(title).strip(),
        "link": _join_values(source.get("link")),
        "institution": _join_values(source.get("institutions")),
        "state": _join_values(source.get("states")),
        "city": _join_values(source.get("cities")),
        "year": "" if year in (None, "") else str(year),
    }


def build_social_production_citation_item(entry, *, language=None, position=1):
    fields = {"number": str(position), **extract_social_production_fields(entry, language=language)}
    title = fields["title"] or _("Untitled")
    item = {
        "id": str(position),
        "type": "webpage",
        "title": title,
        "author": [{"literal": fields["institution"]}] if fields["institution"] else [],
        "URL": fields["link"],
        "issued": {"date-parts": [[int(fields["year"])]]} if fields["year"].isdigit() else None,
        "bibtex_type": "misc",
        "bibtex_key": f"item{position}",
        "ris_type": "GEN",
        "ris_notes": [
            (_("Action"), fields["action"]),
            (_("Institution"), fields["institution"]),
        ],
        "ris_place": fields["city"],
        "ris_city": fields["state"],
        "csv_row": fields,
    }
    return {key: value for key, value in item.items() if value not in (None, "", [])}
