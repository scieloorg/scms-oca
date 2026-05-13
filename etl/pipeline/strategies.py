from django.conf import settings

from etl.pipeline.defaults import (
    article_rules,
    book_chapter_rules,
    book_rules,
    preprint_rules,
)
from etl.pipeline.merger import merge
from etl.pipeline.standardizer import BookStandardizer, DefaultStandardizer

_BUILTIN_ALIASES: dict[str, str] = {
    "research-article": "article",
    "review": "article",
    "review-article": "article",
    "letter": "article",
    "editorial": "article",
    "correction": "article",
    "erratum": "article",
    "book-part": "book-chapter",
    "chapter": "book-chapter",
}


def _aliases() -> dict[str, str]:
    overrides = getattr(settings, "ETL_DOCUMENT_TYPE_ALIASES", None)
    if isinstance(overrides, dict):
        return {**_BUILTIN_ALIASES, **overrides}
    return _BUILTIN_ALIASES


class Strategy:
    def __init__(self, rules_fn, standardizer_cls, merger_fn):
        self._rules_fn = rules_fn
        self._standardizer_cls = standardizer_cls
        self._merger_fn = merger_fn

    @property
    def rules(self):
        return self._rules_fn()

    @property
    def standardizer(self):
        return self._standardizer_cls()

    @property
    def merger(self):
        return self._merger_fn


_STRATEGIES: dict[str, Strategy] = {
    "article": Strategy(article_rules, DefaultStandardizer, merge),
    "preprint": Strategy(preprint_rules, DefaultStandardizer, merge),
    "book": Strategy(book_rules, BookStandardizer, merge),
    "book-chapter": Strategy(book_chapter_rules, BookStandardizer, merge),
}


def normalize_document_type(value: str | None) -> str:
    if value in {None, ""}:
        raise ValueError("Document type is required")
    normalized = str(value).strip().lower().replace("_", "-")
    return _aliases().get(normalized, normalized)


def get_strategy(doc_type: str) -> Strategy:
    normalized = normalize_document_type(doc_type)
    strategy = _STRATEGIES.get(normalized)
    if not strategy:
        raise ValueError(
            f"No ETL strategy configured for document type: '{doc_type}' "
            f"(normalised: '{normalized}')."
        )
    return strategy
