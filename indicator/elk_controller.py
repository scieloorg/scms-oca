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
ES_INDEX = settings.HAYSTACK_CONNECTIONS['es']['INDEX_NAME']
ES_VERIFY_CERTS = settings.HAYSTACK_CONNECTIONS['es'].get('KWARGS', {}).get('verify_certs', False)
ES_CA_CERTS = settings.HAYSTACK_CONNECTIONS['es'].get('KWARGS', {}).get('ca_certs', None)

es = Elasticsearch(
    ES_HOST,
    http_auth=(ES_USER, ES_PASSWORD),
    verify_certs=ES_VERIFY_CERTS,
    ca_certs=ES_CA_CERTS,
)

# Field mapping global
FIELD_MAP = {
    "year": "publication_year",
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


@require_GET
def get_filters(request):
    """
    Endpoint to return available filter options.
    """
    aggs = {
        "publication_year": {"terms": {"field": "publication_year", "size": 100, "order": {"_key": "desc"}}},
        "source_type": {"terms": {"field": "best_oa_location.source.type.keyword", "size": 100}},
        "source_index": {"terms": {"field": "indexed_in.keyword", "size": 100}},
        "document_type": {"terms": {"field": "type.keyword", "size": 100}},
        "document_language": {"terms": {"field": "language.keyword", "size": 100}},
        "open_access": {"terms": {"field": "open_access.is_oa", "size": 2}},
        "access_type": {"terms": {"field": "open_access.oa_status.keyword", "size": 20}},
        "region_world": {"terms": {"field": "geos.scimago_regions.keyword", "size": 20}},
        "country": {"terms": {"field": "authorships.countries.keyword", "size": 500}},
        "subject_area_level_0": {"terms": {"field": "thematic_areas.level0.keyword", "size": 3}},
        "subject_area_level_1": {"terms": {"field": "thematic_areas.level1.keyword", "size": 9}},
        "subject_area_level_2": {"terms": {"field": "thematic_areas.level2.keyword", "size": 41}},
    }

    body = {"size": 0, "aggs": aggs}

    try:
        res = es.search(index=ES_INDEX, body=body)
        filters = {k: [b["key"] for b in v["buckets"]] for k, v in res["aggregations"].items()}
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

    query = build_query(filters)

    # Choose main aggregation
    if breakdown_variable:
        if study_unit == "citation":
            aggs = build_breakdown_citation_per_year_aggs(breakdown_variable)
        else:
            aggs = build_breakdown_documents_per_year_aggs(breakdown_variable)
    else:
        if study_unit == "citation":
            aggs = build_citations_per_year_aggs()
        else:
            aggs = build_documents_per_year_aggs()

    body = {"size": 0, "query": query, "aggs": aggs}
    res = es.search(index=ES_INDEX, body=body)

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

def build_query(filters):
    """
    Build the Elasticsearch query from the received filters, mapping friendly names to real fields.
    """
    must = []

    for field, value in filters.items():
        es_field = FIELD_MAP.get(field, field)

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

def build_citations_per_year_aggs():
    """
    Build the aggregations for citations per year.
    """
    return {
        "citations_per_year": {
            "terms": {
                "field": "publication_year",
                "order": {"_key": "asc"}
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

def build_documents_per_year_aggs():
    """
    Build the aggregations for the number of documents per year, total documents, and total citations.
    """
    return {
        "per_year": {
            "terms": {
                "field": "publication_year",
                "order": {"_key": "asc"}
            }
        },
        "total_documents": {"value_count": {"field": "id.keyword"}},
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

def build_breakdown_citation_per_year_aggs(breakdown_variable):
    """
    Build the aggregations for breakdown of citations per year.
    """
    es_field = FIELD_MAP.get(breakdown_variable, breakdown_variable)
    return {
        "per_year": {
            "terms": {
                "field": "publication_year",
                "order": {"_key": "asc"},
            },
            "aggs": {
                "breakdown": {
                    "terms": {
                        "field": es_field,
                        "order": {"_key": "asc"}
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

def build_breakdown_documents_per_year_aggs(breakdown_variable):
    """
    Build the aggregations for breakdown per year.
    """
    es_field = FIELD_MAP.get(breakdown_variable, breakdown_variable)
    return {
        "per_year": {
            "terms": {
                "field": "publication_year",
                "order": {"_key": "asc"},
            },
            "aggs": {
                "breakdown": {
                    "terms": {
                        "field": es_field,
                        "order": {"_key": "asc"}
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
    # Transform Open Access boolean values to Yes/No strings if applicable
    oa_map = {"1": "Yes", "0": "No"}
    if set(keys) == set(oa_map.keys()):
        for s in series:
            s["name"] = oa_map.get(s["name"], s["name"])

    return [oa_map.get(k, k) for k in keys]
