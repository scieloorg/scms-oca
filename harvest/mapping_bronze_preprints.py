#!/usr/bin/env python3
"""
Mapping and index creation for bronze_preprint.
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
            'authorships': {
                'type': 'object',
                'properties': {
                    'id': {
                        'type': 'keyword'
                    },
                    'name': {
                        'type': 'text',
                        'analyzer': 'multilingual',
                        'fields': {
                            'keyword': {
                                'type': 'keyword',
                                'ignore_above': 256
                            }
                        }
                    },
                    'orcid': {
                        'type': 'keyword'
                    },
                    'position': {
                        'type': 'keyword'
                    },
                    'language': {
                        'type': 'keyword'
                    }
                }
            },
            'abstract': {
                'type': 'text',
                'analyzer': 'multilingual'
            },
            'abstract_with_lang': {
                'type': 'object',
                'properties': {
                    'abstract': {
                        'type': 'text',
                        'analyzer': 'multilingual'
                    },
                    'language': {
                        'type': 'keyword'
                    }
                }
            },
            'ids': {
                'type': 'object',
                'properties': {
                    'scl_preprint_id': {
                        'type': 'keyword'
                    },
                    'doi': {
                        'type': 'keyword'
                    }
                }
            },
            'language': {
                'type': 'keyword'
            },
            'language_normalized': {
                'type': 'text',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            },
            'oca_data': {
                'type': 'object',
                'properties': {
                    'scope': {
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
            'publishers': {
                'type': 'object',
                'properties': {
                    'id': {
                        'type': 'keyword'
                    },
                    'name': {
                        'fields': {
                            'keyword': {
                                'type': 'keyword'
                            }
                        },
                        'analyzer': 'multilingual',
                        'type': 'text'
                    }
                }
            },
            'rights': {
                'type': 'text',
                'analyzer': 'multilingual',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            },
            'rights_with_lang': {
                'type': 'object',
                'properties': {
                    'language': {
                        'type': 'keyword'
                    },
                    'rights': {
                        'type': 'text',
                        'analyzer': 'multilingual'
                    }
                }
            },
            'subjects': {
                'type': 'text',
                'analyzer': 'multilingual',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            },
            'subjects_with_lang': {
                'type': 'object',
                'properties': {
                    'language': {
                        'type': 'keyword'
                    },
                    'subjects': {
                        'type': 'text',
                        'analyzer': 'multilingual',
                        'fields': {
                            'keyword': {
                                'type': 'keyword',
                                'ignore_above': 256
                            }
                        }
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
            'title_with_lang': {
                'type': 'object',
                'properties': {
                    'language': {
                        'type': 'keyword'
                    },
                    'title': {
                        'fields': {
                            'keyword': {
                                'type': 'keyword'
                            }
                        },
                        'analyzer': 'multilingual',
                        'type': 'text'
                    }
                }
            },
            'type': {
                'type': 'keyword'
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
            }
        }
    }
}
