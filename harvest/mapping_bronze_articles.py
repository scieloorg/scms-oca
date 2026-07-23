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
            'abstract': {
                'type': 'text',
                'analyzer': 'multilingual'
            },
            'abstract_with_lang': {
                'type': 'object',
                'properties': {
                    'language': {
                        'type': 'keyword',
                        'ignore_above': 256
                    },
                    'text': {
                        'type': 'text',
                        'analyzer': 'multilingual'
                    }
                }
            },
            'author_country_codes': {
                'type': 'text',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            },
            'authorships': {
                'type': 'object',
                'properties': {
                    'countries': {
                        'type': 'keyword'
                    },
                    'institutions': {
                        'type': 'object',
                        'properties': {
                            'city': {
                                'type': 'text',
                                'fields': {
                                    'keyword': {
                                        'type': 'keyword',
                                        'ignore_above': 256
                                    }
                                }
                            },
                            'country_code': {
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
                            'state': {
                                'type': 'text',
                                'fields': {
                                    'keyword': {
                                        'type': 'keyword',
                                        'ignore_above': 256
                                    }
                                }
                            },
                            'organization_units': {
                                'type': 'object',
                                'properties': {
                                    'name': {
                                        'type': 'text',
                                        'fields': {
                                            'keyword': {
                                                'type': 'keyword',
                                                'ignore_above': 256
                                            }
                                        }
                                    }
                                }
                            }
                        }
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
                        'type': 'long'
                    }
                }
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
            'code': {
                'type': 'text',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            },
            'collection': {
                'type': 'text',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            },
            'content_url': {
                'type': 'object',
                'dynamic': True
            },
            'created_at': {
                'type': 'date'
            },
            'document_type': {
                'type': 'keyword'
            },
            'id': {
                'type': 'text',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
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
            'is_open_access': {
                'type': 'boolean'
            },
            'journal_title': {
                'type': 'text',
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
            'oca_data': {
                'type': 'object',
                'properties': {
                    'scope': {
                        'type': 'keyword'
                    }
                }
            },
            'open_access_status': {
                'type': 'text',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            },
            'primary_source_type': {
                'type': 'text',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            },
            'processing_date': {
                'type': 'date'
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
                        'type': 'text',
                        'analyzer': 'multilingual',
                        'fields': {
                            'keyword': {
                                'type': 'keyword'
                            }
                        }
                    }
                }
            },
            'source': {
                'type': 'object',
                'properties': {
                    'host_organization': {
                        'type': 'object',
                        'properties': {
                            'name': {
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
                    'id': {
                        'type': 'keyword'
                    },
                    'is_open_access': {
                        'type': 'boolean'
                    },
                    'issns': {
                        'type': 'keyword'
                    },
                    'title': {
                        'type': 'text',
                        'analyzer': 'multilingual',
                        'fields': {
                            'keyword': {
                                'type': 'keyword',
                                'ignore_above': 256
                            }
                        }
                    },
                    'type': {
                        'type': 'keyword'
                    },
                    'version': {
                        'type': 'text',
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
                        'type': 'text',
                        'fields': {
                            'keyword': {
                                'type': 'keyword',
                                'ignore_above': 256
                            }
                        }
                    }
                }
            },
            'type': {
                'type': 'keyword'
            },
            'legacy_type': {
                'type': 'keyword'
            },
            'updated_at': {
                'type': 'date'
            },
            'version': {
                'type': 'text',
                'fields': {
                    'keyword': {
                        'type': 'keyword',
                        'ignore_above': 256
                    }
                }
            }
        }
    }
}
