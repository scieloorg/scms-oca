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
            "authors_search": {"analyzer": "multilingual", "type": "text"},
            "authorships": {
                "type": "object",
                "properties": {
                    "link_resume": {"index": False, "type": "keyword"},
                    "name": {
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                            }
                        },
                        "copy_to": ["authors_search"],
                        "analyzer": "multilingual",
                        "type": "text",
                    },
                    "role": {"type": "keyword"},
                },
            },
            "biblio": {
                "type": "object",
                "properties": {
                    "city": {
                        "fields": {"keyword": {"type": "keyword"}},
                        "type": "text",
                    },
                    "country": {"type": "keyword"},
                    "format": {
                        "type": "object",
                        "properties": {
                            "height": {"type": "float"},
                            "width": {"type": "float"},
                        },
                    },
                    "order": {"type": "keyword"},
                    "first_page": {"type": "keyword"},
                    "last_page": {"type": "keyword"},
                    "pages": {
                        "fields": {"keyword": {"type": "keyword"}},
                        "type": "text",
                    },
                    "serie": {
                        "fields": {"keyword": {"type": "keyword"}},
                        "type": "text",
                    },
                },
            },
            "synopsis": {
                "type": "text",
                "analyzer": "multilingual",
            },
            "synopsis_with_lang": {
                "type": "object",
                "properties": {
                    "synopsis": {
                        "type": "text",
                        "analyzer": "multilingual",
                    },
                    "language": {"type": "keyword"},
                },
            },
            "id": {
                "fields": {
                    "keyword": {
                        "type": "keyword",
                    }
                },
                "type": "text",
            },
            "ids": {
                "type": "object",
                "properties": {
                    "bisac_code": {"type": "keyword", "copy_to": ["ids_search"]},
                    "doi": {"type": "keyword", "copy_to": ["ids_search"]},
                    "eisbn": {"type": "keyword", "copy_to": ["ids_search"]},
                    "isbn": {"type": "keyword", "copy_to": ["ids_search"]},
                    "monograph": {"type": "keyword", "copy_to": ["ids_search"]},
                    "scl_book_id": {"type": "keyword", "copy_to": ["ids_search"]},
                },
            },
            "ids_search": {"analyzer": "multilingual", "type": "text"},
            "language": {
                "copy_to": [
                    "language_search",
                    "language_search_autocomplete"
                ],
                "type": "keyword"
            },
            "language_search": {
                "fields": {
                    "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                    }
                },
                "analyzer": "multilingual",
                "type": "text"
            },
            "language_search_autocomplete": {
                "doc_values": False,
                "max_shingle_size": 3,
                "type": "search_as_you_type"
            },
            "language_normalized": {
                "type": "text",
                "fields": {
                    "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                    }
                }
            },
            "monograph": {
                "type": "object",
                "properties": {
                    "authorships": {
                        "type": "object",
                        "properties": {
                            "link_resume": {"index": False, "type": "keyword"},
                            "name": {
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                    }
                                },
                                "copy_to": ["authors_search"],
                                "analyzer": "multilingual",
                                "type": "text",
                            },
                            "role": {"type": "keyword"},
                        },
                    },
                    "id": {"type": "keyword"},
                    "language": {
                        "fields": {"keyword": {"type": "keyword"}},
                        "type": "text",
                    },
                    "publication_year": {"type": "long"},
                    "publishers": {
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                            }
                        },
                        "copy_to": ["publisher_search", "publisher_search_autocomplete"],
                        "analyzer": "multilingual",
                        "type": "text",
                    },
                    "title": {
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                            }
                        },
                        "copy_to": ["title_search"],
                        "analyzer": "multilingual",
                        "type": "text",
                    },
                },
            },
            "oca_data": {
                "type": "object",
                "properties": {"scope": {"type": "keyword"}},
            },
            "publication_year": {"type": "long"},
            "publishers": {
                "type": "object",
                "properties": {
                    "id": {
                    "type": "keyword"
                    },
                    "name": {
                    "fields": {
                        "keyword": {
                        "type": "keyword",
                        }
                    },
                    "copy_to": [
                        "publishers_search",
                        "publishers_search_autocomplete"
                    ],
                    "analyzer": "multilingual",
                    "type": "text"
                    }
                }
            },
            "publishers_search_autocomplete": {
                "doc_values": False,
                "max_shingle_size": 3,
                "type": "search_as_you_type",
            },
            "publishers_search": {
                "fields": {
                    "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                    }
                },
                "analyzer": "multilingual",
                "type": "text"
            },
            "synopsis": {"analyzer": "multilingual", "type": "text"},
            "synopsis_with_lang": {
                "type": "object",
                "properties": {
                    "language": {"type": "keyword"},
                    "synopsis": {"analyzer": "multilingual", "type": "text"},
                },
            },
            "title": {
                "fields": {
                    "keyword": {
                        "type": "keyword",
                    }
                },
                "copy_to": ["title_search"],
                "analyzer": "multilingual",
                "type": "text",
            },
            "title_search": {"analyzer": "multilingual", "type": "text"},
            "title_with_lang": {
                "type": "object",
                "properties": {
                    "language": {"type": "keyword"},
                    "title": {
                        "fields":{
                            "keyword":{
                                "type": "keyword",
                            }
                        },
                        "copy_to": ["title_search"],
                        "analyzer": "multilingual",
                        "type": "text",
                    },
                },
            },
            "type": {
                "type": "keyword"
            },
            "subjects_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "subjects_search_autocomplete": {
                "type": "search_as_you_type",
                "doc_values": False,
                "max_shingle_size": 3,
            },
            "sources": {
                "type": "object",
                "properties": {
                    "host_organization": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 256,
                                    }
                                },
                                "analyzer": "multilingual",
                                "type": "text",
                            },
                        },
                    },
                    "id": {"type": "keyword"},
                    "is_open_access": {"type": "boolean"},
                    "is_primary": {"type": "boolean"},
                    "landing_page_url": {"type": "keyword"},
                    "title": {
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                            }
                        },
                        "copy_to": [
                            "sources_search",
                            "sources_search_autocomplete",
                        ],
                        "analyzer": "multilingual",
                        "type": "text",
                    },
                    "type": {"type": "keyword"},
                },
            },
            "sources_search": {
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
                "analyzer": "multilingual",
                "type": "text",
            },
            "sources_search_autocomplete": {
                "doc_values": False,
                "max_shingle_size": 3,
                "type": "search_as_you_type",
            },
        },
    },
}

