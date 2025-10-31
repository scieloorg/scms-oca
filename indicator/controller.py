from django.conf import settings
from elasticsearch import Elasticsearch

from urllib.parse import urlparse

from . import constants


es_url = settings.HAYSTACK_CONNECTIONS['es']['URL']  # ex: http://user:pass@host:9200/
parsed_url = urlparse(es_url)

ES_HOST = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
ES_USER = parsed_url.username or 'elastic'
ES_PASSWORD = parsed_url.password or ''
ES_VERIFY_CERTS = settings.HAYSTACK_CONNECTIONS['es'].get('KWARGS', {}).get('verify_certs', False)
ES_CA_CERTS = settings.HAYSTACK_CONNECTIONS['es'].get('KWARGS', {}).get('ca_certs', None)

es = Elasticsearch(
    ES_HOST,
    http_auth=(ES_USER, ES_PASSWORD),
    verify_certs=ES_VERIFY_CERTS,
    ca_certs=ES_CA_CERTS,
)


def translate_fields(filters, field_settings):
    """
    Translate form field names to Elasticsearch index field names
    based on the provided field settings.

    Args:
        filters (dict): A dictionary of form field names and their values.
        field_settings (dict): A dictionary mapping form field names to 
            their Elasticsearch index field names.

    Returns:
        dict: A dictionary with Elasticsearch index field names and their values.
    """
    translated = {}

    for field, value in filters.items():
        name = field_settings.get(field, {}).get("index_field_name")
        if name and value:
            translated[name] = value

    # Deal with publication year range
    start_year = filters.get("document_publication_year_start")
    end_year = filters.get("document_publication_year_end")

    if start_year and end_year:
        years = year_range_to_list(start_year, end_year)
        name = field_settings.get("publication_year", {}).get("index_field_name")
        translated[name] = years

    # Deal with open access field
    oa_filter = filters.get("open_access")
    if oa_filter:
        name = field_settings.get("open_access", {}).get("index_field_name")
        if oa_filter == "Yes":
            translated[name] = True
        elif oa_filter == "No":
            translated[name] = False

    return translated


def get_supported_query_fields(data_source):
    """
    Get the fields that support query operators for a given data source.

    Args:
        data_source (str): The name of the data source.
    
    Returns:
        dict: A dictionary mapping form field names to Elasticsearch index field names
              for fields that support query operators.
    """
    supported_query_fields = {}

    ds_field_settings = constants.DSNAME_TO_FIELD_SETTINGS.get(data_source, {})

    for field_name, data in ds_field_settings.items():
        if data.get("filter", {}).get("support_query_operator"):
            supported_query_fields[field_name] = data.get("index_field_name")

    return supported_query_fields


def get_and_operator_fields(data_source, language_query_operator=None, country_query_operator=None):
    """
    Get the fields that should use the "and" operator based on the query operators.

    Args:
        data_source (str): The name of the data source.
        language_query_operator (str): The query operator for document language ("and" or "or").
        country_query_operator (str): The query operator for country ("and" or "or").

    Returns:
        list: A list of Elasticsearch index field names that should use the "and" operator.
    """
    supported_query_fields = get_supported_query_fields(data_source)

    and_operator_fields = []
    if language_query_operator == "and":
        and_operator_fields.append(supported_query_fields.get("document_language"))

    if country_query_operator == "and":
        and_operator_fields.append(supported_query_fields.get("country"))

    return and_operator_fields


def year_range_to_list(start_year, end_year):
    """
    Convert start and end year to a list of years (as strings).

    Args:
        start_year (int or str): The starting year.
        end_year (int or str): The ending year.

    Returns:
        list: A list of years as strings.
    """
    years = []

    if start_year and end_year:
        for y in range(int(start_year), int(end_year) + 1):
            years.append(str(y))

    return years


# FIXME: needs refactoring
def build_query(filters, field_settings, data_source, language_query_operator=None, country_query_operator=None):
    translated_filters = translate_fields(filters, field_settings)
    and_operator_fields = get_and_operator_fields(data_source, language_query_operator, country_query_operator)

    must = []

    # Add Brazil filter
    if data_source == settings.DSNAME_SCI_PROD_BRAZIL:
        name = field_settings.get("country", {}).get("index_field_name")
        must.append({"term": {name: "BR"}})

    # Add social production filter
    if data_source == settings.DSNAME_SOC_PROD:
        name = field_settings.get("action", {}).get("index_field_name")
        must.append({"exists": {"field": name}})

    for field, value in translated_filters.items():
        # Handle list values
        if isinstance(value, list):
            normalized_values = []
            seen = set()

            # Normalize values (trim, case) and remove duplicates
            for item in value:
                if item in (None, ""):
                    continue

                key = str(item).strip()
                stored_value = item

                # Normalize keys for specific fields
                if field == "language.keyword" or field == "languages.keyword":
                    stored_value = key.lower()
                    key = stored_value
                elif field == "authorships.countries.keyword":
                    stored_value = key.upper()
                    key = stored_value
                else:
                    stored_value = item
                
                if key in seen:
                    continue
                
                seen.add(key)
                normalized_values.append(stored_value)

            if not normalized_values:
                continue

            # Build query clauses based on operator
            if field in and_operator_fields:
                for single_value in normalized_values:
                    must.append({"term": {field: single_value}})
            else:
                must.append({"terms": {field: normalized_values}})

        else:
            if value in (None, ""):
                continue
            if field == "language.keyword" or field == "languages.keyword":
                term_value = str(value).strip().lower()
            elif field == "authorships.countries.keyword":
                term_value = str(value).strip().upper()
            else:
                term_value = value
            must.append({"term": {field: term_value}})

    return {"bool": {"must": must}} if must else {"match_all": {}}


def build_citations_per_year_aggs():
    return {
        "citations_per_year": {
            "terms": {
                "field": "publication_year",
                "order": {"_key": "asc"},
                "size": 1000,   # FIXME: use constant
            },
            "aggs": {
                "total_citations": {
                    "sum": {"field": "cited_by_count"}
                }
            }
        }
    }


def parse_citations_per_year_response(res):
    aggs = res.get("aggregations", {})
    buckets = aggs.get("citations_per_year", {}).get("buckets", [])

    years = []
    total_citations = []
    doc_counts = []

    for bucket in buckets:
        year = str(bucket["key"])
        citations = int(bucket["total_citations"]["value"])
        ndocs = bucket["doc_count"]

        years.append(year)
        total_citations.append(citations)
        doc_counts.append(ndocs)
    
    return {
        "years": years,
        "total_citations_per_year": total_citations,
        "ndocs_per_year": doc_counts,
    }


def build_documents_per_year_aggs(data_source):
    year_var = "publication_year" if data_source != "social" else "year"
    count_var = "directory_type.enum" if data_source == "social" else "id.keyword"
    return {
        "per_year": {
            "terms": {
                "field": year_var,
                "order": {"_key": "asc"},
                "size": 1000,   # FIXME: use constant
            }
        },
        "total_documents": {"value_count": {"field": count_var}},
    }


def parse_documents_per_year_response(res):
    """
    Extract the number of documents per year from the aggregation result.
    Returns absolute counts, percentage relative to global total,
    and percentage relative to the filtered set.
    """
    aggs = res.get("aggregations", {})

    years = []
    ndocs_per_year = []

    for bucket in aggs.get("per_year", {}).get("buckets", []):
        count = bucket["doc_count"]
        years.append(str(bucket["key"]))
        ndocs_per_year.append(count)

    return {
        "years": years,
        "ndocs_per_year": ndocs_per_year,
    }


def build_breakdown_citation_per_year_aggs(field_settings, breakdown_variable):
    """
    Build the aggregations for breakdown of citations per year.
    """
    name = field_settings.get(breakdown_variable, {}).get("index_field_name")
    return {
        "per_year": {
            "terms": {
                "field": "publication_year",
                "order": {"_key": "asc"},
                "size": 1000,   # FIXME: use constant
            },
            "aggs": {
                "breakdown": {
                    "terms": {
                        "field": name,
                        "order": {"_key": "asc"},
                        "size": 2500    # FIXME: use constant
                    },
                    "aggs": {
                        "total_citations": {
                            "sum": {"field": "cited_by_count"}
                        }
                    }
                }
            }
        }
    }


def build_breakdown_documents_per_year_aggs(field_settings, breakdown_variable, data_source):
    """
    Build the aggregations for breakdown per year.
    """
    name = field_settings.get(breakdown_variable, {}).get("index_field_name")
    year_var = "publication_year" if data_source != "social" else "year"

    return {
        "per_year": {
            "terms": {
                "field": year_var,
                "order": {"_key": "asc"},
                "size": 1000,   # FIXME: use constant
            },
            "aggs": {
                "breakdown": {
                    "terms": {
                        "field": name,
                        "order": {"_key": "asc"},
                        "size": 2500    # FIXME: use constant
                    }
                }
            }
        }
    }


def parse_breakdown_citation_per_year_response(res):
    """
    Extract the breakdown of citation counts per year from the aggregation result.
    """
    per_year_buckets = res.get("aggregations", {}).get("per_year", {}).get("buckets", [])
    years = [str(b["key"]) for b in per_year_buckets]
    breakdown_keys_set = set()

    # Collect all possible breakdowns
    for year_bucket in per_year_buckets:
        for b in year_bucket.get("breakdown", {}).get("buckets", []):
            breakdown_keys_set.add(str(b["key"]))

    breakdown_keys = sorted(list(breakdown_keys_set))

    # Build counts matrix: each row = breakdown, each column = year
    series = []
    for breakdown in breakdown_keys:
        data = []
        for year_bucket in per_year_buckets:
            found = False
            for b in year_bucket.get("breakdown", {}).get("buckets", []):
                if str(b["key"]) == breakdown:
                    data.append(int(b.get("total_citations", {}).get("value", 0)))
                    found = True
                    break
            if not found:
                data.append(0)
        series.append({"name": breakdown, "data": data})

    breakdown_keys = standardize_breakdown_keys(breakdown_keys, series)

    return {
        "years": years,
        "breakdown_keys": breakdown_keys,
        "series": series,
    }


def parse_breakdown_documents_per_year_response(res):
    """
    Extract the breakdown of document counts per year from the aggregation result.
    """
    per_year_buckets = res.get("aggregations", {}).get("per_year", {}).get("buckets", [])
    years = [str(b["key"]) for b in per_year_buckets]
    breakdown_keys_set = set()

    # Collect all possible breakdowns
    for year_bucket in per_year_buckets:
        for b in year_bucket.get("breakdown", {}).get("buckets", []):
            breakdown_keys_set.add(str(b["key"]))

    breakdown_keys = sorted(list(breakdown_keys_set))

    # Build counts matrix: each row = breakdown, each column = year
    series = []
    for breakdown in breakdown_keys:
        data = []
        for year_bucket in per_year_buckets:
            found = False
            for b in year_bucket.get("breakdown", {}).get("buckets", []):
                if str(b["key"]) == breakdown:
                    data.append(b["doc_count"])
                    found = True
                    break
            if not found:
                data.append(0)
        series.append({"name": breakdown, "data": data})

    breakdown_keys = standardize_breakdown_keys(breakdown_keys, series)

    return {
        "years": years,
        "breakdown_keys": breakdown_keys,
        "series": series,
    }


def standardize_breakdown_keys(keys, series):
    """
    Standardize certain known breakdown keys for better readability.
    E.g., for open_access field, convert "1"/"0" to "Yes"/"No".
    """
    oa_map = {"1": "Yes", "0": "No"}
    if set(keys) == set(oa_map.keys()):
        for s in series:
            s["name"] = oa_map.get(s["name"], s["name"])

    return [oa_map.get(k, k) for k in keys]


def get_index_name_from_data_source(data_source):
    data_source_stz = data_source.lower() if data_source else ""
    
    if data_source_stz == settings.DSNAME_SCI_PROD_WORLD:
        return settings.ES_INDEX_SCI_PROD_WORLD

    elif data_source_stz == settings.DSNAME_SCI_PROD_BRAZIL:
        return settings.ES_INDEX_SCI_PROD_BRAZIL

    elif data_source_stz == settings.DSNAME_SCI_PROD_SCIELO:
        return settings.ES_INDEX_SCI_PROD_SCIELO

    elif data_source_stz == settings.DSNAME_SOC_PROD:
        return settings.ES_INDEX_SOC_PROD
    
    # Default to scientific production world
    return settings.ES_INDEX_SCI_PROD_WORLD
