from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk as es_bulk
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk as os_bulk
from slugify import slugify
from tqdm import tqdm

import argparse
import numpy as np
import os
import pandas as pd


def parse_args():
    """Parse CLI arguments for indexing journal metrics."""
    parser = argparse.ArgumentParser(description="Index journal metrics into Elasticsearch")

    parser.add_argument("--client_mode", choices=["elastic", "opensearch"], default="elastic", help="Elasticsearch client mode")
    parser.add_argument("--xlsx", required=True, help="Path to the journal metrics XLSX file")
    parser.add_argument("--index", required=True, help="Elasticsearch index name")
    parser.add_argument("--test-rows", type=int, default=None, help="Number of rows to read for test mode")
    parser.add_argument("--force-recreate", action="store_true", help="Force index recreation")
    
    return parser.parse_args()


def load_host():
    """Load Elasticsearch host from environment variables."""
    load_dotenv()

    host = os.getenv("ES_HOST") or os.getenv("ELASTICSEARCH_URL")
    if not host:
        raise RuntimeError("Environment variable ES_HOST or ELASTICSEARCH_URL not found in .env")

    return host

# Important columns (as they appear before slugification)
JOURNAL_COL = "Journal"
YEAR_COL = "YEAR"

# Elasticsearch index mapping
IGNORE_ISSN_STRINGS = [
    "1240-8093; 1777-5582",
    "1314-8680; 0007-3938",
    "1941-4935; 1941-4927",
    "2255-3576",
    "2325-0364; 2325-0356",
    "2701-6986; 2701-7818",
    "2783-2104",
    "2800-1400; 2773-2819",
]

def _normalize_issn_tuple(s: str):
    """Normalize a semicolon-separated ISSN string into a sorted tuple."""
    if s is None:
        return tuple()

    parts = [p.strip() for p in str(s).split(";") if p and str(p).strip()]

    return tuple(sorted(parts))

IGNORE_ISSN_TUPLES = { _normalize_issn_tuple(s) for s in IGNORE_ISSN_STRINGS }

INDEX_MAPPING = {
   "baseid": {
       "type": "text",
       "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
   "country": {
       "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }
   },
   "publisher_name": {
        "type": "search_as_you_type",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }
    },
    "journal": {
        "type": "search_as_you_type",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }
    },
    "issns": {
        "type": "search_as_you_type",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }
    },
    "capes_agricultural_sciences": {"type": "boolean"},
    "capes_applied_social_sciences": {"type": "boolean"},
    "capes_biological_sciences": {"type": "boolean"},
    "capes_engineering": {"type": "boolean"},
    "capes_exact_and_earth_sciences": {"type": "boolean"},
    "capes_health_sciences": {"type": "boolean"},
    "capes_human_sciences": {"type": "boolean"},
    "capes_humanities": {"type": "boolean"},
    "capes_life_sciences": {"type": "boolean"},
    "capes_linguistics_letters_and_arts": {"type": "boolean"},
    "capes_multidisciplinary": {"type": "boolean"},
    "capes_phys_tech_multidisc_sciences": {"type": "boolean"},
    "doaj_id": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "doaj_inclusion_year": {
        "type": "integer"},
    "doaj_last_update": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "doaj_stopping_year": {"type": "integer"},
    "doaj_title": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "doaj_year_of_most_recent_article_added": {"type": "integer"},
    "is_ahci": {"type": "boolean"},
    "is_doaj": {"type": "boolean"},
    "is_esci": {"type": "boolean"},
    "is_lilacs": {"type": "boolean"},
    "is_medline": {"type": "boolean"},
    "is_openalex": {"type": "boolean"},
    "is_pmc": {"type": "boolean"},
    "is_qualis": {"type": "boolean"},
    "is_redalyc": {"type": "boolean"},
    "is_scie": {"type": "boolean"},
    "is_scielo": {"type": "boolean"},
    "is_scopus": {"type": "boolean"},
    "is_ssci": {"type": "boolean"},
    "is_wos": {"type": "boolean"},
    "lilacs_title": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "medline_title": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "openalex_id": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "openalex_publisher_name": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "openalex_region": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "openalex_title": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "qualis_area_mae": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "qualis_estrato": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "qualis_title": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "redalyc_id": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "redalyc_most_recent_publication_year": {"type": "integer"},
    "redalyc_oldest_publication_year": {"type": "integer"},
    "redalyc_title": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scielo_active_or_inactive_website": {
        "type": "boolean"},
    "scielo_collection_acronym": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scielo_collection_name": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scielo_id": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scielo_inclusion_year": {"type": "integer"},
    "scielo_is_thematic_collection": {"type": "boolean"},
    "scielo_issn": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scielo_journal_creation_year": {"type": "integer"},
    "scielo_network_country": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scielo_publisher_name": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scielo_stopping_year": {"type": "integer"},
    "scielo_thematic_areas": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scielo_thematic_collection_name": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scielo_title": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scimago_region": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scopus_active_or_inactive": {"type": "boolean"},
    "scopus_id": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scopus_inclusion_year": {"type": "integer"},
    "scopus_level_health_sciences": {"type": "integer"},
    "scopus_level_life_sciences": {"type": "integer"},
    "scopus_level_physical_sciences": {"type": "integer"},
    "scopus_level_social_sciences": {"type": "integer"},
    "scopus_publisher_name": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "scopus_stopping_year": {"type": "integer"},
    "scopus_title": {
        "type": "text",
         "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "source": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "source_type": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "wos_inclusion_year": {"type": "integer"},
    "wos_publisher_name": {
        "type": "keyword",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "wos_stopping_year": {"type": "integer"},
    "wos_title": {
        "type": "text",
        "fields": {
            "keyword": {
                "type": "keyword",
                "doc_values": True
            }
        }},
    "year_of_creation_of_the_periodical": {"type": "integer"},
    "yearly_info": {
        "type": "object",
        "dynamic": True
    }
}

# Build Elasticsearch mapping body for index creation
ES_MAPPING = {
    "mappings": {
        "properties": {
            **{k: v for k, v in INDEX_MAPPING.items() if k != "yearly_info"},
            "yearly_info": {"type": "object", "dynamic": True}
        },
        "dynamic_templates": [
            {"yi_float_cwts_snip": {"path_match": "yearly_info.*.cwts_snip", "mapping": {"type": "float"}}},
            {"yi_float_dimensions_citescore": {"path_match": "yearly_info.*.dimensions_citescore", "mapping": {"type": "float"}}},
            {"yi_float_dimensions_fi_2_years": {"path_match": "yearly_info.*.dimensions_fi_2_years", "mapping": {"type": "float"}}},
            {"yi_float_dimensions_fi_3_years": {"path_match": "yearly_info.*.dimensions_fi_3_years", "mapping": {"type": "float"}}},
            {"yi_bool_doaj_active_in_the_year": {"path_match": "yearly_info.*.doaj_active_in_the_year", "mapping": {"type": "boolean"}}},
            {"yi_int_doaj_num_docs": {"path_match": "yearly_info.*.doaj_num_docs", "mapping": {"type": "integer"}}},
            {"yi_float_google_scholar_h5": {"path_match": "yearly_info.*.google_scholar_h5", "mapping": {"type": "float"}}},
            {"yi_float_google_scholar_m5": {"path_match": "yearly_info.*.google_scholar_m5", "mapping": {"type": "float"}}},
            {"yi_float_jcr_article_influence_score": {"path_match": "yearly_info.*.jcr_article_influence_score", "mapping": {"type": "float"}}},
            {"yi_float_jcr_average_pct": {"path_match": "yearly_info.*.jcr_average_journal_impact_factor_percentile", "mapping": {"type": "float"}}},
            {"yi_int_jcr_citable_items": {"path_match": "yearly_info.*.jcr_citable_items", "mapping": {"type": "integer"}}},
            {"yi_float_jcr_cited_half_life": {"path_match": "yearly_info.*.jcr_cited_half_life", "mapping": {"type": "float"}}},
            {"yi_float_jcr_citing_half_life": {"path_match": "yearly_info.*.jcr_citing_half_life", "mapping": {"type": "float"}}},
            {"yi_float_jcr_eigenfactor_score": {"path_match": "yearly_info.*.jcr_eigenfactor_score", "mapping": {"type": "float"}}},
            {"yi_float_jcr_five_year_impact_factor": {"path_match": "yearly_info.*.jcr_five_year_impact_factor", "mapping": {"type": "float"}}},
            {"yi_float_jcr_immediacy_index": {"path_match": "yearly_info.*.jcr_immediacy_index", "mapping": {"type": "float"}}},
            {"yi_float_jcr_impact_factor": {"path_match": "yearly_info.*.jcr_impact_factor", "mapping": {"type": "float"}}},
            {"yi_float_jcr_if_wo_self": {"path_match": "yearly_info.*.jcr_impact_factor_without_journal_self_cites", "mapping": {"type": "float"}}},
            {"yi_float_jcr_jci": {"path_match": "yearly_info.*.jcr_journal_citation_indicator", "mapping": {"type": "float"}}},
            {"yi_float_jcr_normalized_eigenfactor": {"path_match": "yearly_info.*.jcr_normalized_eigenfactor", "mapping": {"type": "float"}}},
            {"yi_float_jcr_pct_articles": {"path_match": "yearly_info.*.jcr_percentage_articles_in_citables_items", "mapping": {"type": "float"}}},
            {"yi_float_jcr_pct_oa_gold": {"path_match": "yearly_info.*.jcr_percentage_oa_gold", "mapping": {"type": "float"}}},
            {"yi_int_jcr_total_articles": {"path_match": "yearly_info.*.jcr_total_articles", "mapping": {"type": "integer"}}},
            {"yi_int_jcr_total_cites": {"path_match": "yearly_info.*.jcr_total_cites", "mapping": {"type": "integer"}}},
            {"yi_bool_openalex_active": {"path_match": "yearly_info.*.openalex_active_in_the_year", "mapping": {"type": "boolean"}}},
            {"yi_bool_openalex_docs_2024_5": {"path_match": "yearly_info.*.openalex_docs_2024_5", "mapping": {"type": "boolean"}}},
            {"yi_int_openalex_num_articles_net": {"path_match": "yearly_info.*.openalex_num_articles_scielo_network_only", "mapping": {"type": "integer"}}},
            {"yi_int_openalex_num_docs": {"path_match": "yearly_info.*.openalex_num_docs", "mapping": {"type": "integer"}}},
            {"yi_bool_scielo_active_valid": {"path_match": "yearly_info.*.scielo_active_and_valid_in_the_year", "mapping": {"type": "boolean"}}},
            {"yi_int_scielo_num_articles": {"path_match": "yearly_info.*.scielo_num_articles", "mapping": {"type": "integer"}}},
            {"yi_int_scielo_num_docs": {"path_match": "yearly_info.*.scielo_num_docs", "mapping": {"type": "integer"}}},
            {"yi_keyword_scimago_best_quartile": {"path_match": "yearly_info.*.scimago_best_quartile", "mapping": {"type": "keyword"}}},
            {"yi_int_scimago_citables_docs_3_years": {"path_match": "yearly_info.*.scimago_citables_docs_3_years", "mapping": {"type": "integer"}}},
            {"yi_float_scimago_cites_by_doc_2_years": {"path_match": "yearly_info.*.scimago_cites_by_doc_2_years", "mapping": {"type": "float"}}},
            {"yi_float_scimago_estimated_apc": {"path_match": "yearly_info.*.scimago_estimated_apc", "mapping": {"type": "float"}}},
            {"yi_int_scimago_estimated_value": {"path_match": "yearly_info.*.scimago_estimated_value", "mapping": {"type": "integer"}}},
            {"yi_float_scimago_female_authors_percent": {"path_match": "yearly_info.*.scimago_female_authors_percent", "mapping": {"type": "float"}}},
            {"yi_int_scimago_overton": {"path_match": "yearly_info.*.scimago_overton", "mapping": {"type": "integer"}}},
            {"yi_int_scimago_sdg": {"path_match": "yearly_info.*.scimago_sdg", "mapping": {"type": "integer"}}},
            {"yi_float_scimago_sjr": {"path_match": "yearly_info.*.scimago_sjr", "mapping": {"type": "float"}}},
            {"yi_int_scimago_total_cites_3_years": {"path_match": "yearly_info.*.scimago_total_cites_3_years", "mapping": {"type": "integer"}}},
            {"yi_int_scimago_total_docs": {"path_match": "yearly_info.*.scimago_total_docs", "mapping": {"type": "integer"}}},
            {"yi_int_scimago_total_docs_3_years": {"path_match": "yearly_info.*.scimago_total_docs_3_years", "mapping": {"type": "integer"}}},
            {"yi_bool_scopus_active_in_the_year": {"path_match": "yearly_info.*.scopus_active_in_the_year", "mapping": {"type": "boolean"}}},
            {"yi_float_scopus_citescore": {"path_match": "yearly_info.*.scopus_citescore", "mapping": {"type": "float"}}},
            {"yi_keyword_scopus_code_asjc_percentile": {"path_match": "yearly_info.*.scopus_code_asjc_percentile", "mapping": {"type": "keyword"}}},
            {"yi_int_scopus_num_articles_scielo_network_only": {"path_match": "yearly_info.*.scopus_num_articles_scielo_network_only", "mapping": {"type": "integer"}}},
            {"yi_int_scopus_num_docs_scielo_network_only": {"path_match": "yearly_info.*.scopus_num_docs_scielo_network_only", "mapping": {"type": "integer"}}},
            {"yi_bool_wos_active_in_the_year": {"path_match": "yearly_info.*.wos_active_in_the_year", "mapping": {"type": "boolean"}}},
            {"yi_float_wos_alldbs_citescore": {"path_match": "yearly_info.*.wos_alldbs_citescore", "mapping": {"type": "float"}}},
            {"yi_float_wos_alldbs_fi_2_years": {"path_match": "yearly_info.*.wos_alldbs_fi_2_years", "mapping": {"type": "float"}}},
            {"yi_float_wos_alldbs_fi_3_years": {"path_match": "yearly_info.*.wos_alldbs_fi_3_years", "mapping": {"type": "float"}}},
            {"yi_float_wos_scieloci_citescore": {"path_match": "yearly_info.*.wos_scieloci_citescore", "mapping": {"type": "float"}}},
            {"yi_float_wos_scieloci_fi_2_years": {"path_match": "yearly_info.*.wos_scieloci_fi_2_years", "mapping": {"type": "float"}}},
            {"yi_float_wos_scieloci_fi_3_years": {"path_match": "yearly_info.*.wos_scieloci_fi_3_years", "mapping": {"type": "float"}}}
        ]
    }
}

# Yearly metric field types for building yearly_info and casting columns
YEARLY_FIELD_TYPES = {
    # floats
    "cwts_snip": "float",
    "dimensions_citescore": "float",
    "dimensions_fi_2_years": "float",
    "dimensions_fi_3_years": "float",
    "google_scholar_h5": "float",
    "google_scholar_m5": "float",
    "jcr_article_influence_score": "float",
    "jcr_average_journal_impact_factor_percentile": "float",
    "jcr_cited_half_life": "float",
    "jcr_citing_half_life": "float",
    "jcr_eigenfactor_score": "float",
    "jcr_five_year_impact_factor": "float",
    "jcr_immediacy_index": "float",
    "jcr_impact_factor": "float",
    "jcr_impact_factor_without_journal_self_cites": "float",
    "jcr_journal_citation_indicator": "float",
    "jcr_normalized_eigenfactor": "float",
    "jcr_percentage_articles_in_citables_items": "float",
    "jcr_percentage_oa_gold": "float",
    "scimago_cites_by_doc_2_years": "float",
    "scimago_estimated_apc": "float",
    "scimago_female_authors_percent": "float",
    "scimago_sjr": "float",
    "scopus_citescore": "float",
    "wos_alldbs_citescore": "float",
    "wos_alldbs_fi_2_years": "float",
    "wos_alldbs_fi_3_years": "float",
    "wos_scieloci_citescore": "float",
    "wos_scieloci_fi_2_years": "float",
    "wos_scieloci_fi_3_years": "float",
    # integers
    "doaj_num_docs": "integer",
    "jcr_citable_items": "integer",
    "jcr_total_articles": "integer",
    "jcr_total_cites": "integer",
    "openalex_num_articles_scielo_network_only": "integer",
    "openalex_num_docs": "integer",
    "scielo_num_articles": "integer",
    "scielo_num_docs": "integer",
    "scimago_citables_docs_3_years": "integer",
    "scimago_estimated_value": "integer",
    "scimago_overton": "integer",
    "scimago_sdg": "integer",
    "scimago_total_cites_3_years": "integer",
    "scimago_total_docs": "integer",
    "scimago_total_docs_3_years": "integer",
    "scopus_num_articles_scielo_network_only": "integer",
    "scopus_num_docs_scielo_network_only": "integer",
    # booleans
    "doaj_active_in_the_year": "boolean",
    "openalex_active_in_the_year": "boolean",
    "openalex_docs_2024_5": "boolean",
    "scielo_active_and_valid_in_the_year": "boolean",
    "scopus_active_in_the_year": "boolean",
    "wos_active_in_the_year": "boolean",
    # keywords
    "scimago_best_quartile": "keyword",
    "scopus_code_asjc_percentile": "keyword",
}


def create_index(es, index_name: str, force: bool):
    """Create (optionally recreate) the Elasticsearch index with ES_MAPPING."""
    exists = es.indices.exists(index=index_name)

    if exists and force:
        print(f"Deleting existing index '{index_name}'...")
        es.indices.delete(index=index_name)
        exists = False

    if not exists:
        print(f"Creating index '{index_name}'...")
        es.indices.create(index=index_name, body=ES_MAPPING)
        print("Index created.")


def to_bool(v):
    """Convert various string/number representations to boolean or None."""
    if pd.isna(v):
        return None

    if isinstance(v, (bool, np.bool_)):
        return bool(v)

    if isinstance(v, (int, np.integer, float, np.floating)):
        if pd.isna(v):
            return None
        return v != 0

    s = str(v).strip().lower()
    
    # Include a few common localized variants
    truthy = {"true", "t", "1", "yes", "y", "sim", "s", "ok", "x", "active", "ativo"}
    falsy = {"false", "f", "0", "no", "n", "nao", "não", "inativo", "inactive", "off", ""}

    if s in truthy:
        return True

    if s in falsy:
        return False

    return None


def read_metrics_xlsx(file_path: str, test_rows: int | None) -> pd.DataFrame:
    """Read the XLSX file and perform initial cleanup (drop NA, slugify columns)."""
    read_mode = f"the first {test_rows} rows" if test_rows else "the entire file"

    print(f"Reading {read_mode} from '{file_path}'...")
    df = pd.read_excel(file_path, nrows=test_rows)
 
    # Drop rows missing essential columns before slugify
    df.dropna(subset=[JOURNAL_COL, YEAR_COL], inplace=True)
 
    # Slugify column names to snake_case
    df.columns = [slugify(col, separator="_") for col in df.columns]
 
    return df


def cast_top_level_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Cast top-level columns according to INDEX_MAPPING."""
    for col, meta in INDEX_MAPPING.items():
        if col in df.columns:
            if meta["type"] in ["integer", "float"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            elif meta["type"] == "boolean":
                df[col] = df[col].apply(to_bool)

            else:
                if col in ["issns", "scielo_thematic_areas"]:
                    df[col] = df[col].fillna("").apply(lambda x: [a.strip() for a in str(x).split(";") if str(a).strip()])

                else:
                    df[col] = df[col].astype(str)
    return df


def filter_ignored_issn(df: pd.DataFrame) -> pd.DataFrame:
    """Filter out rows whose ISSN combinations are in the ignore list."""
    def _norm_issn_list_raw(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return tuple()
        parts = [p.strip() for p in str(val).split(";") if p and str(p).strip()]
        return tuple(sorted(parts))

    if "issns" in df.columns:
        df["_issn_set_key"] = df["issns"].apply(_norm_issn_list_raw)
        df = df[~df["_issn_set_key"].isin(IGNORE_ISSN_TUPLES)].copy()
        df.drop(columns=["_issn_set_key"], inplace=True)

    return df


def cast_yearly_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Cast yearly metric columns according to YEARLY_FIELD_TYPES."""
    for ncol, ntype in YEARLY_FIELD_TYPES.items():
        if ncol in df.columns:
            if ntype in ["integer", "float"]:
                df[ncol] = pd.to_numeric(df[ncol], errors="coerce")

            elif ntype == "boolean":
                df[ncol] = df[ncol].apply(to_bool)

            elif ntype == "keyword":
                df[ncol] = df[ncol].astype(str)

    return df


def build_yearly_info(df: pd.DataFrame) -> pd.DataFrame:
    """Build the yearly_info dictionary field and drop flattened yearly columns."""
    def make_yearly_info(row: pd.Series):
        # Build a dict: { "<year>": { other_fields... } }
        year_val = row.get("year") if isinstance(row, (dict, pd.Series)) else None
        try:
            y = int(year_val)
        except Exception:
            return None

        payload = {}

        for ncol in YEARLY_FIELD_TYPES.keys():
            if ncol == "year":
                continue

            if ncol in row:
                val = row[ncol]

                try:
                    is_na = pd.isna(val)
                except Exception:
                    is_na = False

                if val is None or is_na:
                    continue

                payload[ncol] = val

        return {str(y): payload} if payload else None

    df["yearly_info"] = df.apply(make_yearly_info, axis=1)

    # Drop flattened yearly metric columns now represented inside yearly_info
    cols_to_drop = [c for c in YEARLY_FIELD_TYPES.keys() if c in df.columns]
    if cols_to_drop:
        df.drop(columns=cols_to_drop, inplace=True)

    return df


def connect_es(host: str, client_mode: str = "elastic"):
    if client_mode == "opensearch":
        """Create an OpenSearch client and verify connectivity."""
        es = OpenSearch(host, verify_certs=False, ssl_show_warn=False)

        if not es.ping():
            raise ConnectionError("Could not connect to OpenSearch.")

        return es

    """Create an Elasticsearch client and verify connectivity."""
    es = Elasticsearch(host, verify_certs=False, ssl_show_warn=False)

    if not es.ping():
        raise ConnectionError("Could not connect to Elasticsearch.")

    return es


def _union_issns(series) -> list[str]:
    s: set[str] = set()

    for v in series:
        if isinstance(v, list):
            s.update([x for x in v if isinstance(x, str) and x.strip()])

    return sorted(s)


def _merge_yearly_infos(series) -> dict:
    merged: dict = {}

    for v in series:
        if not isinstance(v, dict):
            continue

        for y_str, payload in v.items():
            if not isinstance(payload, dict):
                continue

            prev = merged.get(y_str, {})
            out = dict(prev)

            for k, val in payload.items():
                if val is None:
                    continue

                try:
                    if pd.isna(val):
                        continue
                except Exception:
                    pass

                out[k] = val

            merged[y_str] = out

    return merged


def build_bulk_actions(df: pd.DataFrame, index_name: str) -> list[dict]:
    """Build bulk indexing actions, aggregating by baseid when present."""
    actions: list[dict] = []
    if "baseid" in df.columns:
        grouped = df.groupby("baseid", dropna=False)

        for baseid_value, g in tqdm(grouped, desc="Aggregating by baseid"):
            doc: dict = {"baseid": baseid_value}

            if "issns" in g.columns:
                all_sets = []

                for v in g["issns"]:
                    if isinstance(v, list):
                        all_sets.append([x.strip() for x in v if isinstance(x, str) and x.strip()])
                    else:
                        parts = [p.strip() for p in str(v).split(";") if p and str(p).strip()]
                        all_sets.append(parts)

                doc["issns"] = _union_issns(all_sets)

            top_cols = [
                c
                for c in INDEX_MAPPING.keys()
                if c not in ("yearly_info", "issns", "baseid") and c in g.columns
            ]

            for c in top_cols:
                for v in g[c]:
                    if v is None:
                        continue

                    try:
                        if pd.isna(v):
                            continue
                    except Exception:
                        pass

                    doc[c] = v

                    break

            if "yearly_info" in g.columns:
                doc["yearly_info"] = _merge_yearly_infos(g["yearly_info"])
            actions.append({"_index": index_name, "_id": baseid_value, "_source": doc})
    else:
        actions = [
            {"_index": index_name, "_source": record}
            for record in tqdm(df.to_dict(orient="records"), desc="Generating actions")
        ]

    return actions


def es_bulk_index(es: Elasticsearch, actions: list[dict]) -> tuple[int, int]:
    """Execute bulk indexing and return (success, failures)."""
    return es_bulk(es, actions)


def os_bulk_index(es: OpenSearch, actions: list[dict]) -> tuple[int, int]:
    """Execute bulk indexing and return (success, failures)."""
    return os_bulk(es, actions)


def run(xlsx_path: str, index_name: str, test_rows: int | None, force_recreate: bool, client_mode: str = "elastic"):
    """End-to-end execution: read, preprocess, build actions, and index into ES."""
    df = read_metrics_xlsx(xlsx_path, test_rows)
    df = cast_top_level_columns(df)
    df = filter_ignored_issn(df)
    df = cast_yearly_fields(df)
    df = build_yearly_info(df)

    # Normalize missing values
    df.replace({np.nan: None, pd.NaT: None, pd.NA: None}, inplace=True)
    df = df.replace({"nan": None, "NaN": None})

    es_host = load_host()
    es = connect_es(es_host, client_mode=client_mode)
    create_index(es, index_name, force_recreate)

    actions = build_bulk_actions(df, index_name)
    if client_mode == "opensearch":
        success, failed = os_bulk_index(es, actions)
    else:
        success, failed = es_bulk_index(es, actions)
    print(f"Indexing finished. Success: {success}, Failures: {failed}")


# Main function to read, process, and index data
def main():
    try:
        args = parse_args()
        run(
            xlsx_path=args.xlsx,
            index_name=args.index,
            test_rows=args.test_rows,
            force_recreate=args.force_recreate,
            client_mode=args.client_mode
        )
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()