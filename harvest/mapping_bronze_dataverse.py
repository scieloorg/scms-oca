#!/usr/bin/env python3
"""
Mapping and index creation for bronze_scielo_dataverse.
"""


# --- Mapping for destination index ---
BRONZE_MAPPING = {
    'settings': {
        'index': {
            'number_of_shards': 1,
            'number_of_replicas': 1
        },
        'analysis': {
            'analyzer': {
                'multilingual': {
                    'type': 'custom',
                    'tokenizer': 'standard',
                    'filter': ['lowercase', 'asciifolding']
                }
            }
        }
    },
    'mappings': {
        'dynamic': True,
        'properties': {
            'oca_data': {
                'type': 'object',
                'properties': {
                    'scope': {
                        'type': 'keyword'
                    }
                }
            },
            'title': {
                'type': 'text',
                'analyzer': 'multilingual',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 512
                    }
                }
            },
            'ids': {
                'type': 'object',
                'properties': {
                    'alias': {
                        'type': 'keyword'
                    }
                }
            },
            'content_url': {
                'type': 'object',
                'dynamic': True
            },
            'is_released': {
                'type': 'boolean'
            },
            'affiliation': {
                'type': 'text',
                'analyzer': 'multilingual',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            },
            'description': {
                'type': 'text',
                'analyzer': 'multilingual'
            },
            'description_with_lang': {
                'type': 'object',
                'properties': {
                    'description': {
                        'type': 'text',
                        'analyzer': 'multilingual'
                    },
                    'language': {
                        'type': 'keyword'
                    }
                }
            },
            'publication_date': {
                'type': 'date'
            },
            'publication_year': {
                'type': 'long'
            },
            'source': {
                'type': 'object',
                'properties': {
                    'host_organization': {
                        'type': 'object',
                        'properties': {
                            'id': {
                                'type': 'keyword'
                            },
                            'name': {
                                'fields': {
                                    'keyword': {
                                        'type': 'keyword',
                                        'ignore_above': 256
                                    }
                                },
                                'analyzer': 'multilingual',
                                'type': 'text'
                            }
                        }
                    },
                    'id': {
                        'type': 'keyword'
                    },
                    'is_open_access': {
                        'type': 'boolean'
                    },
                    'is_primary': {
                        'type': 'boolean'
                    },
                    'issn_l': {
                        'type': 'keyword'
                    },
                    'issns': {
                        'type': 'keyword'
                    },
                    'landing_page_url': {
                        'type': 'keyword'
                    },
                    'title': {
                        'fields': {
                            'keyword': {
                                'type': 'keyword',
                                'ignore_above': 256
                            }
                        },
                        'analyzer': 'multilingual',
                        'type': 'text'
                    },
                    'type': {
                        'type': 'keyword'
                    }
                }
            },
            'dataverse_contacts': {
                'type': 'object',
                'properties': {
                    'contact_email': {
                        'type': 'keyword'
                    },
                    'display_order': {
                        'type': 'integer'
                    }
                }
            }
        }
    }
}
