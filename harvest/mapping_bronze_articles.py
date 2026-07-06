BRONZE_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
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
    },
    "mappings": {
        "dynamic": True,
        "properties": {
            "abstract": {"type": "text", "analyzer": "multilingual"},
            "abstract_with_lang": {
                "type": "object",
                "properties": {
                    "language": {"type": "keyword", "ignore_above": 256},
                    "text": {"type": "text", "analyzer": "multilingual"},
                },
            },
            "author_country_codes": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "authors_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "authorships": {
                "type": "object",
                "properties": {
                    "countries": {
                        "type": "text",
                        "copy_to": ["countries_search"],
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "institutions": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                            "country_code": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                            "name": {
                                "type": "text",
                                "analyzer": "multilingual",
                                "copy_to": [
                                    "institutions_search",
                                    "institutions_search_autocomplete",
                                ],
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                            "state": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                        },
                    },
                    "name": {
                        "type": "text",
                        "analyzer": "multilingual",
                        "copy_to": ["authors_search"],
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "orcid": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "position": {"type": "long"},
                },
            },
            "biblio": {
                "type": "object",
                "properties": {
                    "first_page": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "issue": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "last_page": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "volume": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                },
            },
            "code": {
                "type": "text",
                "copy_to": ["ids_search"],
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "collection": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "content_url": {"type": "keyword"},
            "countries_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "created_at": {"type": "date"},
            "document_type": {"type": "keyword"},
            "id": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "ids": {
                "type": "object",
                "properties": {
                    "doi": {"type": "keyword", "copy_to": ["ids_search"]},
                    "doi_with_lang": {
                        "type": "object",
                        "properties": {
                            "doi": {"type": "keyword", "copy_to": ["ids_search"]},
                            "language": {"type": "keyword"},
                        },
                    },
                },
            },
            "ids_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "institutions_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "institutions_search_autocomplete": {
                "type": "search_as_you_type",
                "doc_values": False,
                "max_shingle_size": 3,
            },
            "is_open_access": {"type": "boolean"},
            "journal_title": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "language": {
                "type": "keyword",
                "copy_to": ["language_search", "language_search_autocomplete"],
            },
            "language_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "language_search_autocomplete": {
                "type": "search_as_you_type",
                "doc_values": False,
                "max_shingle_size": 3,
            },
            "oca_data": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    }
                },
            },
            "open_access_status": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "primary_source_type": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "processing_date": {"type": "date"},
            "publication_date": {"type": "date"},
            "publication_year": {"type": "long"},
            "publishers": {
                "type": "object",
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "multilingual",
                        "copy_to": [
                            "publishers_search",
                            "publishers_search_autocomplete",
                        ],
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                },
            },
            "publishers_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "publishers_search_autocomplete": {
                "type": "search_as_you_type",
                "doc_values": False,
                "max_shingle_size": 3,
            },
            "sources": {
                "type": "object",
                "properties": {
                    "host_organization": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "id": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "is_open_access": {"type": "boolean"},
                    "issns": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "multilingual",
                        "copy_to": ["sources_search", "sources_search_autocomplete"],
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "type": {"type": "keyword"},
                    "version": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                },
            },
            "sources_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "sources_search_autocomplete": {
                "type": "search_as_you_type",
                "doc_values": False,
                "max_shingle_size": 3,
            },
            "title": {
                "type": "text",
                "analyzer": "multilingual",
                "copy_to": ["title_search"],
                "fields": {"keyword": {"type": "keyword", "ignore_above": 512}},
            },
            "title_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "title_with_lang": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "title": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                },
            },
            "type": {"type": "keyword"},
            "updated_at": {"type": "date"},
            "version": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
        },
    },
}
