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
        'dynamic': 'strict',
        'properties': {
            'authorships': {
                'type': 'object',
                'properties': {
                    'link_resume': {
                        'index': False,
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
                    },
                    'role': {
                        'type': 'keyword'
                    }
                }
            },
            'biblio': {
                'type': 'object',
                'properties': {
                    'city': {
                        'fields': {
                            'keyword': {
                                'type': 'keyword'
                            }
                        },
                        'type': 'text'
                    },
                    'country': {
                        'type': 'keyword'
                    },
                    'format': {
                        'type': 'object',
                        'properties': {
                            'height': {
                                'type': 'float'
                            },
                            'width': {
                                'type': 'float'
                            }
                        }
                    },
                    'order': {
                        'type': 'keyword'
                    },
                    'first_page': {
                        'type': 'keyword'
                    },
                    'last_page': {
                        'type': 'keyword'
                    },
                    'pages': {
                        'fields': {
                            'keyword': {
                                'type': 'keyword'
                            }
                        },
                        'type': 'text'
                    },
                    'serie': {
                        'fields': {
                            'keyword': {
                                'type': 'keyword'
                            }
                        },
                        'type': 'text'
                    }
                }
            },
            'synopsis': {
                'type': 'text',
                'analyzer': 'multilingual'
            },
            'synopsis_with_lang': {
                'type': 'object',
                'properties': {
                    'synopsis': {
                        'type': 'text',
                        'analyzer': 'multilingual'
                    },
                    'language': {
                        'type': 'keyword'
                    }
                }
            },
            'id': {
                'fields': {
                    'keyword': {
                        'type': 'keyword'
                    }
                },
                'type': 'text'
            },
            'ids': {
                'type': 'object',
                'properties': {
                    'bisac_code': {
                        'type': 'keyword'
                    },
                    'doi': {
                        'type': 'keyword'
                    },
                    'eisbn': {
                        'type': 'keyword'
                    },
                    'isbn': {
                        'type': 'keyword'
                    },
                    'monograph': {
                        'type': 'keyword'
                    },
                    'scl_book_id': {
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
            'oca_indexed_at': {
                'type': 'date'
            },
            'oca_source_hash': {
                'type': 'keyword'
            },
            'monograph': {
                'type': 'object',
                'properties': {
                    'authorships': {
                        'type': 'object',
                        'properties': {
                            'link_resume': {
                                'index': False,
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
                            },
                            'role': {
                                'type': 'keyword'
                            }
                        }
                    },
                    'id': {
                        'type': 'keyword'
                    },
                    'language': {
                        'fields': {
                            'keyword': {
                                'type': 'keyword'
                            }
                        },
                        'type': 'text'
                    },
                    'publication_year': {
                        'type': 'long'
                    },
                    'publishers': {
                        'fields': {
                            'keyword': {
                                'type': 'keyword'
                            }
                        },
                        'analyzer': 'multilingual',
                        'type': 'text'
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
            'oca_data': {
                'type': 'object',
                'properties': {
                    'scope': {
                        'type': 'keyword'
                    }
                }
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
            'title': {
                'fields': {
                    'keyword': {
                        'type': 'keyword'
                    }
                },
                'analyzer': 'multilingual',
                'type': 'text'
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
