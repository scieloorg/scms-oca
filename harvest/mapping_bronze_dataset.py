#!/usr/bin/env python3
"""
Reindex raw_scielo_data -> bronze_scielo_dataverse with transformation.
"""

# --- Mapping for destination index ---
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
            "publisher": {
                "type": "text",
                "analyzer": "multilingual",
                "copy_to": ["publisher_search", "publisher_search_autocomplete"],
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "publisher_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "publisher_search_autocomplete": {
                "doc_values": False,
                "max_shingle_size": 3,
                "type": "search_as_you_type",
            },
            "type": {
                "type": "keyword",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "sources": {
                "type": "object",
                "properties": {
                    "url": {"type": "keyword"},
                    "issn": {"type": "keyword"},
                },
            },
            "dataverse": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "multilingual",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                            }
                        },
                    },
                    "url": {"type": "keyword"},
                },
            },
            "license": {
                "type": "object",
                "properties": {
                    "url": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "multilingual",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                            }
                        },
                    },
                    "icon_url": {"type": "keyword"},
                },
            },
            "dataset_id": {"type": "long"},
            "create_time": {"type": "date"},
            "release_time": {"type": "date"},
            "citation_date": {"type": "date"},
            "version_state": {"type": "keyword"},
            "version_number": {"type": "long"},
            "latest_version_publishing_state": {"type": "keyword"},
            "publication_date": {"type": "date"},
            "publication_year": {"type": "long"},
            "content_url": {"type": "keyword", "index": False},
            "ids": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "keyword",
                        "copy_to": ["ids_search"],
                    },
                    "doi": {
                        "type": "keyword",
                        "copy_to": ["ids_search"],
                    },
                },
            },
            "ids_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "title": {
                "type": "text",
                "analyzer": "multilingual",
                "copy_to": ["title_search"],
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 512,
                    }
                },
            },
            "title_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "description": {
                "type": "text",
                "analyzer": "multilingual",
            },
            "files": {
                "type": "object",
                "properties": {
                    "pid_url": {"type": "keyword"},
                    "publication_date": {"type": "date"},
                    "ids": {"type": "keyword"},
                    "label": {
                        "type": "text",
                        "analyzer": "multilingual",
                        "copy_to": ["title_search"],
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 512,
                            }
                        },
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "multilingual",
                    },
                },
            },
            "authorships": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "multilingual",
                        "copy_to": ["authors_search"],
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                            }
                        },
                    },
                    "orcid": {"type": "keyword"},
                    "institutions": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "text",
                                "analyzer": "multilingual",
                                "copy_to": [
                                    "institutions_search",
                                    "institutions_search_autocomplete",
                                ],
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 256,
                                    }
                                },
                            }
                        },
                    },
                },
            },
            "authors_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "institutions_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "institutions_search_autocomplete": {
                "type": "search_as_you_type",
                "doc_values": False,
                "max_shingle_size": 3,
            },
            "subjects": {
                "type": "text",
                "analyzer": "multilingual",
                "copy_to": ["subjects_search", "subjects_search_autocomplete"],
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
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
            "keyword": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "keyword_search": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },
            "language": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "citation_name": {"type": "keyword"},
        },
    },
}
