"""Citation item builders for scientific production records."""

from ..csl_json import CSLSourceExtractor

SCIENTIFIC_PRODUCTION_CSV_COLUMNS = (
    "number",
    "type",
    "title",
    "authors",
    "publication_year",
    "source_title",
    "volume",
    "issue",
    "pages",
    "publisher",
    "doi",
    "url",
    "language",
)

_CONTAINER_TITLE_TYPES = frozenset({"article-journal", "article", "chapter", "review"})
_PUBLISHER_TYPES = frozenset({"book", "chapter", "dataset"})
_BIBTEX_TYPE_MAP = {
    "article": "article",
    "article-journal": "article",
    "book": "book",
    "chapter": "incollection",
    "dataset": "misc",
}


def _add_if(item, key, value):
    if value:
        item[key] = value


def _format_authors(authors):
    if not isinstance(authors, list):
        return ""
    return " | ".join(authors)


def build_csl_item(source, doc_id, *, language=None):
    """Build a CSL-JSON item from an indexed scientific production source."""
    extractor = CSLSourceExtractor(source, language=language)
    csl_type = extractor.csl_type()

    item = {
        "id": str(doc_id),
        "type": csl_type,
        "title": extractor.title(),
        "author": extractor.authors_with_given_family(),
    }
    _add_if(item, "issued", extractor.issued())

    doi = extractor.doi()
    _add_if(item, "DOI", doi)
    _add_if(item, "URL", extractor.url(doi=doi))

    if csl_type in _CONTAINER_TITLE_TYPES:
        _add_if(item, "container-title", extractor.source_title())

    _add_if(item, "volume", extractor.volume())
    _add_if(item, "issue", extractor.issue())
    _add_if(item, "page", extractor.pages())

    if csl_type in _PUBLISHER_TYPES:
        _add_if(item, "publisher", extractor.publisher())

    _add_if(item, "language", extractor.source_language())

    return item


def build_scientific_production_citation_item(entry, *, language=None, position=1):
    source = entry.get("source")
    entry_lang = entry.get("language_code")
    entry_lang = str(entry_lang).strip() if entry_lang not in (None, "") else None
    item_language = entry_lang or language
    extractor = CSLSourceExtractor(source, language=item_language)
    item = build_csl_item(source, doc_id=str(position), language=item_language)
    doi = item.get("DOI")
    item.update(
        {
            "bibtex_type": _BIBTEX_TYPE_MAP.get(item.get("type"), "misc"),
            "bibtex_key": f"item{position}",
            "ris_type": "JOUR",
            "csv_row": {
                "number": str(position),
                "type": extractor.csl_type(),
                "title": extractor.title(),
                "authors": _format_authors(extractor.authors()),
                "publication_year": extractor.publication_year() or "",
                "source_title": extractor.source_title() or "",
                "volume": extractor.volume() or "",
                "issue": extractor.issue() or "",
                "pages": extractor.pages() or "",
                "publisher": extractor.publisher() or "",
                "doi": doi or "",
                "url": extractor.url(doi=doi) or "",
                "language": extractor.currently_language or "",
            },
        }
    )
    return item
