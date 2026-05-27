from typing import Any


def _text(
    *,
    copy_to: str | list[str] | None = None,
    ignore_above: int = 256,
    keyword: bool = True,
) -> dict[str, Any]:
    field: dict[str, Any] = {
        "type": "text",
        "analyzer": "multilingual",
    }
    if keyword:
        field["fields"] = {"keyword": {"type": "keyword", "ignore_above": ignore_above}}
    if copy_to:
        field["copy_to"] = copy_to if isinstance(copy_to, list) else [copy_to]
    return field


SILVER_SETTINGS = {
    "index": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "refresh_interval": "30s",
        "mapping.nested_objects.limit": 50000,
    },
    "analysis": {
        "analyzer": {
            "multilingual": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "asciifolding"],
            },
        },
    },
}


SILVER_PROPERTIES = {
    "doc_id": {"type": "keyword"},
    "oca_data": {
        "type": "object",
        "properties": {
            "scope": {"type": "keyword"},
            "match_status": {"type": "keyword"},
            "match_strategy": {"type": "keyword"},
            "match_confidence": {"type": "keyword"},
            "merge_trace": {
                "type": "object",
                "properties": {
                    "scielo_matches": {
                        "type": "object",
                        "properties": {
                            "doc_ids": {"type": "keyword"},
                            "collections": {"type": "keyword"},
                        },
                    },
                    "openalex_matches": {
                        "type": "object",
                        "properties": {
                            "doc_id": {"type": "keyword"},
                            "match_strategy": {"type": "keyword"},
                            "confidence": {"type": "keyword"},
                            "validation": {
                                "type": "object",
                                "properties": {
                                    "reasons": {"type": "keyword"},
                                    "score": {"type": "long"},
                                    "year_check": {"type": "keyword"},
                                    "doi_check": {"type": "keyword"},
                                    "journal_check": {"type": "keyword"},
                                    "isbn_check": {"type": "keyword"},
                                    "title_similarity": {"type": "float"},
                                },
                            },
                        },
                    },
                },
            },
            "scielo": {
                "type": "object",
                "properties": {
                    "ids": {"type": "keyword"},
                    "collection": {"type": "keyword"},
                    "pid_v2": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "source": {
                        "type": "object",
                        "properties": {
                            "country_code": {"type": "keyword"},
                            "indexed_in": {"type": "keyword"},
                        },
                    },
                },
            },
            "openalex": {
                "type": "object",
                "properties": {
                    "ids": {"type": "keyword"},
                    "versions": {
                        "type": "nested",
                        "properties": {
                            "id": {"type": "keyword"},
                            "doi": {"type": "keyword"},
                            "title": _text(ignore_above=512),
                            "language": {"type": "keyword"},
                            "content_url": {"type": "keyword"},
                            "is_open_access": {"type": "boolean"},
                            "open_access_status": {"type": "keyword"},
                            "metrics": {
                                "type": "object",
                                "properties": {
                                    "received_citations": {
                                        "type": "object",
                                        "properties": {
                                            "total": {"type": "long"},
                                            "by_year": {
                                                "type": "object",
                                                "properties": {
                                                    "year": {"type": "long"},
                                                    "total": {"type": "long"},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    },
    "ids": {
        "type": "object",
        "properties": {
            "doi": {"type": "keyword", "copy_to": "ids_search"},
            "doi_with_lang": {
                "type": "object",
                "properties": {
                    "language": {"type": "keyword"},
                    "doi": {"type": "keyword", "copy_to": "ids_search"},
                },
            },
            "issn": {"type": "keyword", "copy_to": "ids_search"},
            "isbn": {"type": "keyword", "copy_to": "ids_search"},
            "mag": {"type": "keyword", "copy_to": "ids_search"},
            "openalex": {"type": "keyword", "copy_to": "ids_search"},
            "openalex_with_lang": {
                "type": "object",
                "properties": {
                    "language": {"type": "keyword"},
                    "openalex": {"type": "keyword", "copy_to": "ids_search"},
                },
            },
            "pmcid": {"type": "keyword", "copy_to": "ids_search"},
            "pmid": {"type": "keyword", "copy_to": "ids_search"},
            "scielo": {"type": "keyword", "copy_to": "ids_search"},
        },
    },
    "ids_search": _text(),
    "type": {"type": "keyword"},
    "indexed_in": {"type": "keyword"},
    "language": {
        "type": "keyword",
        "copy_to": ["language_search"],
    },
    "language_search": _text(),
    "title": _text(
        copy_to=["title_search", "search_all_text"],
        ignore_above=512,
    ),
    "title_search": _text(),
    "title_with_lang": {
        "type": "object",
        "properties": {
            "title": _text(
                copy_to=["title_search", "search_all_text"],
                ignore_above=512,
            ),
            "language": {"type": "keyword"},
        },
    },
    "abstract": _text(
        copy_to=["abstract_search", "search_all_text"],
        keyword=False,
    ),
    "abstract_search": _text(keyword=False),
    "abstract_with_lang": {
        "type": "object",
        "properties": {
            "abstract": _text(
                copy_to=["abstract_search", "search_all_text"],
                keyword=False,
            ),
            "language": {"type": "keyword"},
        },
    },
    "description": _text(copy_to=["description_search", "search_all_text"], keyword=False),
    "description_search": _text(keyword=False),
    "description_with_lang": {
        "type": "object",
        "properties": {
            "description": _text(copy_to=["description_search", "search_all_text"], keyword=False),
            "language": {"type": "keyword"},
        },
    },
    "keywords": _text(copy_to=["keywords_search", "search_all_text"], ignore_above=512),
    "keywords_search": _text(),
    "keywords_with_lang": {
        "type": "object",
        "properties": {
            "keywords": _text(copy_to=["keywords_search", "search_all_text"], ignore_above=512),
            "language": {"type": "keyword"},
        },
    },
    "subjects": _text(copy_to=["subjects_search", "search_all_text"], ignore_above=512),
    "subjects_search": _text(),
    "subjects_with_lang": {
        "type": "object",
        "properties": {
            "subjects": _text(copy_to=["subjects_search", "search_all_text"], ignore_above=512),
            "language": {"type": "keyword"},
        },
    },
    "publication_date": {"type": "date", "ignore_malformed": True},
    "publication_year": {"type": "long"},
    "is_open_access": {"type": "boolean"},
    "open_access_status": {"type": "keyword"},
    "content_url": {
        "type": "object",
        "properties": {
            "url": {"type": "keyword"},
            "type": {"type": "keyword"},
            "language": {"type": "keyword"},
        },
    },
    "content_url_with_lang": {
        "type": "object",
        "properties": {
            "content_url": {"type": "keyword"},
            "language": {"type": "keyword"},
        },
    },
    "biblio": {
        "type": "object",
        "properties": {
            "volume": {"type": "keyword"},
            "issue": {"type": "keyword"},
            "first_page": {"type": "keyword"},
            "last_page": {"type": "keyword"},
        },
    },
    "parent_book": {
        "type": "object",
        "properties": {
            "id": {"type": "keyword"},
            "title": _text(ignore_above=512),
            "publication_year": {"type": "long"},
            "language": {"type": "keyword"},
            "ids": {
                "type": "object",
                "properties": {
                    "scl_book_id": {"type": "keyword"},
                    "doi": {"type": "keyword"},
                    "isbn": {"type": "keyword"},
                    "eisbn": {"type": "keyword"},
                },
            },
            "publishers": {
                "type": "object",
                "properties": {
                    "name": _text(copy_to=["publishers_search", "search_all_text"]),
                },
            },
            "authorships": {
                "type": "object",
                "properties": {
                    "role": {"type": "keyword"},
                    "name": _text(),
                    "orcid": {"type": "keyword"},
                },
            },
        },
    },
    "referenced_works": {
        "type": "object",
        "dynamic": False,
        "properties": {
            "ids": {
                "type": "object",
                "dynamic": False,
                "properties": {
                    "openalex": {"type": "keyword"},
                },
            },
        },
    },
    "authorships": {
        "type": "nested",
        "properties": {
            "author_position": {"type": "keyword"},
            "name": _text(copy_to=["authors_search", "search_all_text"]),
            "id": {"type": "keyword"},
            "orcid": {"type": "keyword"},
            "institutions": {
                "type": "nested",
                "properties": {
                    "name": _text(copy_to=["institutions_search", "search_all_text"]),
                    "id": {"type": "keyword"},
                    "ror": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "country_code": {"type": "keyword"},
                },
            },
        },
    },
    "author_country_codes": {"type": "keyword"},
    "institutions": {"type": "keyword"},
    "authors_search": _text(copy_to="search_all_text"),
    "institutions_search": _text(copy_to="search_all_text"),
    "publishers_search": _text(copy_to="search_all_text"),
    "search_all_text": _text(keyword=False),
    "funders": {
        "type": "object",
        "properties": {
            "name": _text(),
            "id": {"type": "keyword"},
            "ror": {"type": "keyword"},
            "country_code": {"type": "keyword"},
        },
    },
    "awards": {
        "type": "object",
        "properties": {
            "funder_name": _text(),
            "funder_id": {"type": "keyword"},
            "award_id": {"type": "keyword"},
        },
    },
    "publishers": {
        "type": "object",
        "properties": {
            "id": {"type": "keyword"},
            "name": _text(copy_to=["publishers_search", "search_all_text"]),
        },
    },
    "source": {
        "type": "object",
        "properties": {
            "acronym": {"type": "keyword"},
            "title": _text(copy_to=["source_title_search", "search_all_text"], ignore_above=512),
            "type": {"type": "keyword"},
            "is_open_access": {"type": "boolean"},
            "landing_page_url": {"type": "keyword"},
            "issns": {"type": "keyword"},
            "issn_l": {"type": "keyword"},
            "host_organization": {"type": "keyword"},
            "host_organization_name": _text(),
            "ids": {
                "type": "object",
                "properties": {
                    "openalex": {"type": "keyword"},
                },
            },
        },
    },
    "source_title_search": _text(copy_to="search_all_text"),
    "primary_topic_name": {"type": "keyword"},
    "primary_topic_domain": {"type": "keyword"},
    "primary_topic_field": {"type": "keyword"},
    "primary_topic_subfield": {"type": "keyword"},
    "primary_topic_score": {"type": "float"},
    "apc": {
        "type": "object",
        "properties": {
            "apc_list": {
                "type": "object",
                "properties": {
                    "currency": {"type": "keyword"},
                    "value": {"type": "long"},
                    "value_usd": {"type": "long"},
                },
            },
            "apc_paid": {
                "type": "object",
                "properties": {
                    "currency": {"type": "keyword"},
                    "value": {"type": "long"},
                    "value_usd": {"type": "long"},
                },
            },
        },
    },
    "authors_count": {"type": "integer"},
    "references_count": {"type": "integer"},
    "sustainable_development_goals": {
        "type": "object",
        "properties": {
            "id": {"type": "keyword"},
            "display_name": {"type": "keyword"},
            "score": {"type": "float"},
        },
    },
    "sdg_names": {"type": "keyword"},
    "metrics": {
        "type": "object",
        "properties": {
            "fwci": {"type": "float"},
            "received_citations": {
                "type": "object",
                "properties": {
                    "total": {"type": "long"},
                    "by_year": {
                        "type": "nested",
                        "properties": {
                            "year": {"type": "long"},
                            "total": {"type": "long"},
                        },
                    },
                },
            },
        },
    },
}


SILVER_MAPPING = {
    "settings": SILVER_SETTINGS,
    "mappings": {"dynamic": "strict", "properties": SILVER_PROPERTIES},
}
