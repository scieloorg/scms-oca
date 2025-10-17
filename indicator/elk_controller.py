import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from elasticsearch import Elasticsearch
from urllib.parse import urlparse


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

# Field mapping OpenAlex Works
FIELD_MAP_OPENALEX_WORKS = {
    "publication_year": "publication_year",
    "source_type": "best_oa_location.source.type.keyword",
    "source_index": "indexed_in.keyword",
    "document_type": "type.keyword",
    "document_language": "language.keyword",
    "open_access": "open_access.is_oa",
    "access_type": "open_access.oa_status.keyword",
    "region_world": "geos.scimago_regions.keyword",
    "country": "authorships.countries.keyword",
    "subject_area_level_0": "thematic_areas.level0.keyword",
    "subject_area_level_1": "thematic_areas.level1.keyword",
    "subject_area_level_2": "thematic_areas.level2.keyword",
}

# Field mapping for SciELO
FIELD_MAP_SCIELO = {
    "publication_year": "publication_year",
    "document_type": "type.keyword",
    "document_language": "languages.keyword",
    "access_type": "open_access.oa_status.keyword",
    "journal": "journal.keyword",
    "country": "authorships.countries.keyword",
}

# Field mapping for Social Production
FIELD_MAP_SOCIAL_PRODUCTION = {
    "action": "action.enum",
    "classification": "classification.enum",
    "directory_type": "directory_type.enum",
    "institutions": "institutions.enum",
    "cities": "cities.enum",
    "states": "states.enum",
    "practice": "practice.enum",
    "publication_year": "year",
}

# Dictionary 
MAX_BUCKETS = {
    "publication_year": 1000,
    "year": 1000,
}

FILTERS_CACHE = {}

@require_GET
def get_filters(request):
    """
    Endpoint to return available filter options.
    Select ES index via GET parameter (data_source=...)
    """
    data_source = request.GET.get('data_source', 'openalex_works')
    cache_key = data_source.lower() if data_source else ""
    if cache_key in FILTERS_CACHE:
        return JsonResponse(FILTERS_CACHE[cache_key])

    es_index, _, _ = get_es_index_and_flags(data_source, None)

    # Choose mapping and fields for aggs
    if data_source.lower() == "scielo":
        aggs_fields = [
            ("publication_year", "publication_year", 100, {"_key": "desc"}),
            ("document_type", "type.keyword", 100, {"_key": "asc"}),
            ("document_language", "languages.keyword", 100, {"_key": "asc"}),
            ("access_type", "open_access.oa_status.keyword", 20, {"_key": "asc"}),
            ("journal", "journal.keyword", 2500, {"_key": "asc"}),
            ("country", "authorships.countries.keyword", 500, {"_key": "asc"}),
        ]
    elif data_source.lower() == "social_production":
        aggs_fields = [
            ("publication_year", "year", 1000, {"_key": "desc"}),
            ("action", "action.enum", 1000, {"_key": "asc"}),
            ("classification", "classification.enum", 1000, {"_key": "asc"}),
            ("institutions", "institutions.enum", 1000, {"_key": "asc"}),
            ("cities", "cities.enum", 1000, {"_key": "asc"}),
            ("states", "states.enum", 1000, {"_key": "asc"}),
            ("practice", "practice.enum", 1000, {"_key": "asc"}),
            ("directory_type", "directory_type.enum", 1000, {"_key": "asc"}),
        ]
    elif data_source.lower() == "openalex_works":
        aggs_fields = [
            ("publication_year", "publication_year", 100, {"_key": "desc"}),
            ("source_type", "best_oa_location.source.type.keyword", 100, {"_key": "asc"}),
            ("source_index", "indexed_in.keyword", 100, {"_key": "asc"}),
            ("document_type", "type.keyword", 100, {"_key": "asc"}),
            ("document_language", "language.keyword", 100, {"_key": "asc"}),
            ("open_access", "open_access.is_oa", 2, {"_key": "asc"}),
            ("access_type", "open_access.oa_status.keyword", 20, {"_key": "asc"}),
            ("region_world", "geos.scimago_regions.keyword", 20, {"_key": "asc"}),
            ("country", "authorships.countries.keyword", 500, {"_key": "asc"}),
            ("subject_area_level_0", "thematic_areas.level0.keyword", 3, {"_key": "asc"}),
            ("subject_area_level_1", "thematic_areas.level1.keyword", 9, {"_key": "asc"}),
            ("subject_area_level_2", "thematic_areas.level2.keyword", 41, {"_key": "asc"}),
        ]
    else:
        return JsonResponse({"error": "Invalid or missing data_source parameter."}, status=400)

    aggs = {}
    for name, field, size, order in aggs_fields:
        terms = {"field": field, "size": size}
        if order:
            terms["order"] = order
        aggs[name] = {"terms": terms}

    body = {"size": 0, "aggs": aggs}

    try:
        res = es.search(index=es_index, body=body)
        filters = {k: [b["key"] for b in v["buckets"]] for k, v in res["aggregations"].items()}
        FILTERS_CACHE[cache_key] = filters
        return JsonResponse(filters)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_POST
def get_indicators(request):
    """
    Endpoint to return indicators.
    """
    filters = json.loads(request.body.decode())
    study_unit = filters.pop("study_unit", "document")
    breakdown_variable = filters.pop("breakdown_variable", None)
    data_source = filters.pop("data_source", None) or request.GET.get("data_source", None) or request.POST.get("data_source", None) or ""
    country_unit = filters.pop("country_unit", None) or request.GET.get("country_unit", None) or request.POST.get("country_unit", None) or ""

    es_index, flag_brazil, flag_social_production = get_es_index_and_flags(data_source, country_unit)

    if data_source.lower() == "scielo":
        field_map = FIELD_MAP_SCIELO
    elif data_source.lower() == "social_production":
        field_map = FIELD_MAP_SOCIAL_PRODUCTION
    else:
        field_map = FIELD_MAP_OPENALEX_WORKS

    query = build_query(filters, field_map, flag_brazil, flag_social_production)

    # Choose main aggregation
    if breakdown_variable:
        if study_unit == "citation":
            aggs = build_breakdown_citation_per_year_aggs(field_map, breakdown_variable)
        else:
            aggs = build_breakdown_documents_per_year_aggs(field_map, breakdown_variable, flag_social_production)
    else:
        if study_unit == "citation":
            aggs = build_citations_per_year_aggs(field_map)
        else:
            aggs = build_documents_per_year_aggs(field_map, flag_social_production)

    body = {"size": 0, "query": query, "aggs": aggs}
    res = es.search(index=es_index, body=body)

    # Parse response
    if breakdown_variable:
        if study_unit == "citation":
            indicators = parse_breakdown_citation_per_year_response(res)
        else:
            indicators = parse_breakdown_documents_per_year_response(res)
        indicators["breakdown_variable"] = breakdown_variable
    else:
        if study_unit == "citation":
            indicators = parse_citations_per_year_response(res)
        else:
            indicators = parse_documents_per_year_response(res)        

    return JsonResponse(indicators)

def build_query(filters, field_map, flag_brazil, flag_social_production):
    """
    Build the Elasticsearch query from the received filters, mapping friendly names to real fields.
    """
    must = []

    # Add Brazil filter
    if flag_brazil:
        es_field = field_map.get("country", "country")
        must.append({"term": {es_field: "BR"}})

    # Add social production filter
    if flag_social_production:
        es_field = field_map.get("action", "action")
        must.append({"exists": {"field": es_field}})

    for field, value in filters.items():
        es_field = field_map.get(field, field)

        if field == "open_access":
            def to_bool(v):
                if isinstance(v, bool):
                    return v
                if str(v).lower() in ("1", "true", "Yes"): return True
                if str(v).lower() in ("0", "false", "nao", "No"): return False
                return v
            if isinstance(value, list):
                value = [to_bool(v) for v in value]
            else:
                value = to_bool(value)

        if isinstance(value, list):
            must.append({"terms": {es_field: value}})
        else:
            must.append({"term": {es_field: value}})

    return {"bool": {"must": must}} if must else {"match_all": {}}

def build_citations_per_year_aggs(field_map):
    """
    Build the aggregations for citations per year.
    """
    return {
        "citations_per_year": {
            "terms": {
                "field": "publication_year",
                "order": {"_key": "asc"},
                "size": MAX_BUCKETS.get("publication_year", 1000),
            },
            "aggs": {
                "total_citations": {
                    "sum": {"field": "cited_by_count"}
                }
            }
        }
    }

def parse_citations_per_year_response(res):
    """
    Extract the number of citations per year from the aggregation result.
    Returns absolute counts and percentages (global and filtered).
    """
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

def build_documents_per_year_aggs(field_map, flag_social_production):
    """
    Build the aggregations for the number of documents per year, total documents, and total citations.
    """
    year_var = "publication_year" if not flag_social_production else "year"
    count_var = "directory_type.enum" if flag_social_production else "id.keyword"
    return {
        "per_year": {
            "terms": {
                "field": year_var,
                "order": {"_key": "asc"},
                "size": MAX_BUCKETS.get(year_var, 1000),
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

def build_breakdown_citation_per_year_aggs(field_map, breakdown_variable):
    """
    Build the aggregations for breakdown of citations per year.
    """
    es_field = field_map.get(breakdown_variable, breakdown_variable)
    return {
        "per_year": {
            "terms": {
                "field": "publication_year",
                "order": {"_key": "asc"},
                "size": MAX_BUCKETS.get("publication_year", 1000),
            },
            "aggs": {
                "breakdown": {
                    "terms": {
                        "field": es_field,
                        "order": {"_key": "asc"},
                        "size": 2500
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

def build_breakdown_documents_per_year_aggs(field_map, breakdown_variable, flag_social_production):
    """
    Build the aggregations for breakdown per year.
    """
    es_field = field_map.get(breakdown_variable, breakdown_variable)
    year_var = "publication_year" if not flag_social_production else "year"

    return {
        "per_year": {
            "terms": {
                "field": year_var,
                "order": {"_key": "asc"},
                "size": MAX_BUCKETS.get(year_var, 1000),
            },
            "aggs": {
                "breakdown": {
                    "terms": {
                        "field": es_field,
                        "order": {"_key": "asc"},
                        "size": 2500
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

def get_es_index_and_flags(data_source, country_unit):
    """
    Determine the Elasticsearch index and flags based on data source and country unit.

    Returns:
    - index (str): The Elasticsearch index to use.
    - flag_is_brazil (bool): True if country_unit is "BR", else False
    - flag_is_social_production (bool): True if data_source is "social_production", else False
    """
    flag_is_brazil = True if country_unit == "BR" else False
    flag_is_social_production = True if data_source.lower() == "social_production" else False

    if data_source.lower() == "social_production":
        es_index = settings.ES_INDEX_SOCIAL_PRODUCTION
    elif data_source.lower() == "scielo":
        es_index = settings.ES_INDEX_SCIELO
    elif data_source.lower() == "openalex_works":
        es_index = settings.ES_INDEX_WORLD

    return es_index, flag_is_brazil, flag_is_social_production
