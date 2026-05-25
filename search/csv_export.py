"""Build CSV export content from normalized row dictionaries."""

from __future__ import annotations

import csv
import re

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


def _sanitize_csv_cell(value):
    """Normalize invisible separators that can break spreadsheet imports."""
    if value is None:
        return ""
    text = str(value)
    # Covers common and uncommon line/tab separators from upstream metadata.
    text = re.sub(r"[\r\n\t\v\f\u2028\u2029]+", " ", text)
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    return re.sub(r" {2,}", " ", text).strip()


def stream_csv_rows(rows, *, columns=CSV_COLUMNS, batch_size=CSV_EXPORT_BATCH_SIZE):
    """Yield CSV chunks from already-normalized row dictionaries."""
    writer = csv.DictWriter(
        _CsvBuffer(),
        fieldnames=columns,
        quoting=csv.QUOTE_ALL,
        lineterminator="\n",
    )
    yield "\ufeff" + writer.writeheader()

    batch = []
    for row in rows or []:
        batch.append(
            writer.writerow(
                {key: _sanitize_csv_cell(row.get(key, "")) for key in columns}
            )
        )
        if len(batch) >= batch_size:
            yield "".join(batch)
            batch = []

    if batch:
        yield "".join(batch)
