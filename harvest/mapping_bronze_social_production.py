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
            'record_status': {
                'type': 'keyword'
            },
            'directory_type': {
                'type': 'keyword'
            },
            'type': {
                'type': 'keyword'
            },
            'title': {
                'type': 'text',
                'analyzer': 'multilingual',
                'fields': {
                    'keyword': {
                        'type': 'keyword'
                    }
                }
            },
            'text': {
                'type': 'text',
                'analyzer': 'multilingual'
            },
            'description': {
                'type': 'text',
                'analyzer': 'multilingual',
                'fields': {
                    'keyword': {
                        'type': 'keyword'
                    }
                }
            },
            'link': {
                'type': 'text'
            },
            'practice': {
                'type': 'keyword'
            },
            'action': {
                'type': 'keyword'
            },
            'classification': {
                'type': 'keyword'
            },
            'source': {
                'type': 'keyword'
            },
            'institutional_contribution': {
                'type': 'keyword'
            },
            'disclaimer': {
                'type': 'text',
                'analyzer': 'multilingual'
            },
            'attendance': {
                'type': 'keyword'
            },
            'pipeline': {
                'type': 'keyword'
            },
            'creator': {
                'type': 'keyword'
            },
            'updated_by': {
                'type': 'keyword'
            },
            'year': {
                'type': 'integer'
            },
            'publication_year': {
                'type': 'long'
            },
            'creation_year': {
                'type': 'keyword'
            },
            'created': {
                'type': 'date'
            },
            'updated': {
                'type': 'date'
            },
            'start_date': {
                'type': 'date'
            },
            'end_date': {
                'type': 'date'
            },
            'start_date_year': {
                'type': 'integer'
            },
            'end_date_year': {
                'type': 'integer'
            },
            'date': {
                'type': 'date'
            },
            'start_time': {
                'type': 'keyword'
            },
            'end_time': {
                'type': 'keyword'
            },
            'institutions': {
                'fields': {
                    'keyword': {
                        'type': 'keyword'
                    }
                },
                'analyzer': 'multilingual',
                'type': 'text'
            },
            'organization': {
                'fields': {
                    'keyword': {
                        'type': 'keyword'
                    }
                },
                'analyzer': 'multilingual',
                'type': 'text'
            },
            'cities': {
                'type': 'keyword'
            },
            'states': {
                'type': 'keyword'
            },
            'regions': {
                'type': 'keyword'
            },
            'countries': {
                'type': 'keyword'
            },
            'thematic_level_0': {
                'type': 'keyword'
            },
            'thematic_level_1': {
                'type': 'keyword'
            },
            'thematic_level_2': {
                'type': 'keyword'
            },
            'universe': {
                'type': 'keyword'
            },
            'scope': {
                'type': 'keyword'
            },
            'database': {
                'type': 'keyword'
            },
            'graphs': {
                'type': 'keyword'
            }
        }
    }
}
