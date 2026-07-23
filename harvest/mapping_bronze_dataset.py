#!/usr/bin/env python3
"""
Reindex raw_scielo_data -> bronze_scielo_dataverse with transformation.
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
            },
            'dataverse': {
                'type': 'object',
                'properties': {
                    'identifier': {
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
                    'url': {
                        'type': 'keyword'
                    }
                }
            },
            'license': {
                'type': 'object',
                'properties': {
                    'url': {
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
                    'icon_url': {
                        'type': 'keyword'
                    }
                }
            },
            'dataset_id': {
                'type': 'long'
            },
            'create_time': {
                'type': 'date'
            },
            'release_time': {
                'type': 'date'
            },
            'citation_date': {
                'type': 'date'
            },
            'version_state': {
                'type': 'keyword'
            },
            'version_number': {
                'type': 'long'
            },
            'latest_version_publishing_state': {
                'type': 'keyword'
            },
            'publication_date': {
                'type': 'date'
            },
            'publication_year': {
                'type': 'long'
            },
            'content_url': {
                'type': 'object',
                'dynamic': True
            },
            'ids': {
                'type': 'object',
                'properties': {
                    'doi': {
                        'type': 'keyword'
                    },
                    'doi_with_lang': {
                        'type': 'object',
                        'properties': {
                            'doi': {
                                'type': 'keyword'
                            },
                            'language': {
                                'type': 'keyword'
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
            'files': {
                'type': 'object',
                'properties': {
                    'pid_url': {
                        'type': 'keyword'
                    },
                    'publication_date': {
                        'type': 'date'
                    },
                    'ids': {
                        'type': 'keyword'
                    },
                    'label': {
                        'type': 'text',
                        'analyzer': 'multilingual',
                        'fields': {
                            'keyword': {
                                'type': 'keyword',
                                'ignore_above': 512
                            }
                        }
                    },
                    'abstract': {
                        'type': 'text',
                        'analyzer': 'multilingual'
                    }
                }
            },
            'authorships': {
                'type': 'object',
                'properties': {
                    'countries': {
                        'type': 'keyword'
                    },
                    'id': {
                        'type': 'keyword'
                    },
                    'institutions': {
                        'type': 'object',
                        'properties': {
                            'country_code': {
                                'type': 'keyword'
                            },
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
                            },
                            'ror': {
                                'type': 'keyword'
                            },
                            'type': {
                                'type': 'keyword'
                            }
                        }
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
                    },
                    'orcid': {
                        'type': 'keyword'
                    },
                    'position': {
                        'type': 'keyword'
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
            'keyword': {
                'type': 'text',
                'analyzer': 'multilingual',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
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
            'citation_name': {
                'type': 'keyword'
            },
            'biblio': {
                'type': 'object',
                'properties': {
                    'first_page': {
                        'type': 'keyword'
                    },
                    'issue': {
                        'type': 'keyword'
                    },
                    'last_page': {
                        'type': 'keyword'
                    },
                    'volume': {
                        'type': 'keyword'
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
            }
        }
    }
}
