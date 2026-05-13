SILVER_PROPERTIES = {
    "doc_id": {"type": "keyword"},
    "type": {"type": "keyword"},
    "publication_year": {"type": "integer"},
    "publication_date": {"type": "date", "ignore_malformed": True},
    "language": {"type": "keyword"},
    "title": {
        "type": "text",
        "fields": {"keyword": {"type": "keyword", "ignore_above": 512}},
    },
    "abstract": {"type": "text"},
    "description": {"type": "text"},
    "keywords": {"type": "keyword"},
    "subjects": {"type": "keyword"},
    "ids": {
        "properties": {
            "doi": {"type": "keyword"},
            "issn": {"type": "keyword"},
            "isbn": {"type": "keyword"},
            "openalex": {"type": "keyword"},
            "scielo": {"type": "keyword"},
        }
    },
    "source": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 512}},
            },
            "type": {"type": "keyword"},
            "issns": {"type": "keyword"},
        }
    },
    "content_url": {"type": "keyword"},
    "is_open_access": {"type": "boolean"},
    "open_access_status": {"type": "keyword"},
    "metrics": {
        "properties": {
            "received_citations": {
                "properties": {
                    "total": {"type": "integer"},
                }
            }
        }
    },
    "oca_data": {
        "properties": {
            "scope": {"type": "keyword"},
            "match_status": {"type": "keyword"},
            "match_strategy": {"type": "keyword"},
            "match_confidence": {"type": "keyword"},
            "merge_trace": {"type": "object", "enabled": True},
            "scielo": {"type": "object", "enabled": True},
            "openalex": {"type": "object", "enabled": True},
        }
    },
}

SILVER_MAPPING = {
    "settings": {
        "analysis": {
            "normalizer": {
                "lowercase_ascii": {
                    "type": "custom",
                    "filter": ["lowercase", "asciifolding"],
                }
            }
        }
    },
    "mappings": {
        "dynamic": "strict",
        "properties": SILVER_PROPERTIES,
    },
}

__all__ = ["SILVER_MAPPING", "SILVER_PROPERTIES"]
