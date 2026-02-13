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
            "descriptor": {
                "fields": {"keyword": {"type": "keyword"}},
                "analyzer": "multilingual",
                "type": "text",
            },
            "descriptors_with_lang": {
                "type": "object",
                "properties": {
                    "descriptor": {"analyzer": "multilingual", "type": "text"},
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
            "language": {"fields": {"keyword": {"type": "keyword"}}, "type": "text"},
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
                    "publisher": {
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
            "publisher": {
                "fields": {
                    "keyword": {
                        "type": "keyword",
                    }
                },
                "copy_to": ["publisher_search", "publisher_search_autocomplete"],
                "analyzer": "multilingual",
                "type": "text",
            },
            "publisher_search_autocomplete": {
                "doc_values": False,
                "max_shingle_size": 3,
                "type": "search_as_you_type",
            },
            "publisher_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                    }
                },
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
                        "copy_to": ["title_search"],
                        "analyzer": "multilingual",
                        "type": "text",
                    },
                },
            },
            "type": {
                "fields": {
                    "keyword": {
                        "type": "keyword",
                    }
                },
                "type": "keyword",
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
        },
    },
}

