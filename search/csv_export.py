"""Build CSV export content from raw document payload using ``CSLSourceExtractor``.

Unlike ``bib``/``ris`` exports, CSV is a tabular dump of bibliographic fields
rather than a rendered citation. Each row is produced by reading fields
directly from a ``CSLSourceExtractor`` instance bound to the document source.
"""

from __future__ import annotations

import csv
import io
import re

from .csl_json import CSLSourceExtractor

CSV_EXPORT_BATCH_SIZE = 500

CSV_COLUMNS = (
    "id",
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


class _CsvBuffer:
    def write(self, value):
        return value


def _format_authors(authors):
    if not isinstance(authors, list):
        return ""
    return " | ".join(authors)


def _sanitize_csv_cell(value):
    """Normalize invisible separators that can break spreadsheet imports."""
    if value is None:
        return ""
    text = str(value)
    # Covers common and uncommon line/tab separators from upstream metadata.
    text = re.sub(r"[\r\n\t\v\f\u2028\u2029]+", " ", text)
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    return re.sub(r" {2,}", " ", text).strip()


def _row_for(extractor, doc_id):
    doi = extractor.doi()
    return {
        "id": str(doc_id),
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
    }


def _valid_rows(documents, *, language=None):
    for entry in documents or []:
        if not isinstance(entry, dict):
            continue
        doc_id = entry.get("id")
        source = entry.get("source")
        if doc_id is None or not isinstance(source, dict):
            continue

        entry_lang = entry.get("language_code")
        entry_lang = str(entry_lang).strip() if entry_lang not in (None, "") else None
        extractor = CSLSourceExtractor(source, language=entry_lang or language)
        row = _row_for(extractor, doc_id)
        yield {k: _sanitize_csv_cell(v) for k, v in row.items()}


def stream_csv(documents, *, language=None, batch_size=CSV_EXPORT_BATCH_SIZE):
    """Yield CSV content in small chunks for ``StreamingHttpResponse``."""
    writer = csv.DictWriter(
        _CsvBuffer(),
        fieldnames=CSV_COLUMNS,
        # Quote all fields to improve compatibility with spreadsheet tools
        # that auto-detect ';' as delimiter in some locales.
        quoting=csv.QUOTE_ALL,
        lineterminator="\n",
    )
    yield "\ufeff" + writer.writeheader()

    batch = []
    for row in _valid_rows(documents, language=language):
        batch.append(writer.writerow(row))
        if len(batch) >= batch_size:
            yield "".join(batch)
            batch = []

    if batch:
        yield "".join(batch)


def render_csv(documents, *, language=None):
    """Return a CSV string (UTF-8 BOM-prefixed for spreadsheet compatibility).

    Iterates entries of shape ``{id, source, language_code?}`` and builds one
    row per valid entry using :class:`CSLSourceExtractor`.
    """
    buf = io.StringIO()
    for chunk in stream_csv(documents, language=language):
        buf.write(chunk)
    return buf.getvalue()
