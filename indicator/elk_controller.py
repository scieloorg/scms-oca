import json
import urllib3
import warnings

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from elasticsearch import Elasticsearch
from urllib.parse import urlparse
from urllib3.exceptions import InsecureRequestWarning


urllib3.disable_warnings(InsecureRequestWarning)
warnings.filterwarnings(
    "ignore",
    message="Connecting to .* using TLS with verify_certs=False is insecure",
    category=Warning,
)

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


@require_GET
def get_filters(request):
    """
    Endpoint to return available filter options.
    """
    aggs = {
        "publication_year": {"terms": {"field": "publication_year", "size": 6, "order": {"_key": "desc"}}},
        "source_type": {"terms": {"field": "best_oa_location.source.type.keyword", "size": 5}},
        "source_index": {"terms": {"field": "indexed_in.keyword", "size": 5}},
        "document_type": {"terms": {"field": "type.keyword", "size": 20}},
        "open_access": {"terms": {"field": "open_access.is_oa", "size": 2}},
        "open_access_type": {"terms": {"field": "open_access.oa_status.keyword", "size": 6}},
        "country": {"terms": {"field": "authorships.countries.keyword", "size": 247}},
        "thematic_area_level_0": {"terms": {"field": "thematic_areas.level0.keyword", "size": 3}},
        "thematic_area_level_1": {"terms": {"field": "thematic_areas.level1.keyword", "size": 9}},
        "thematic_area_level_2": {"terms": {"field": "thematic_areas.level2.keyword", "size": 41}},
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
    Endpoint para retornar indicadores, agora com suporte a métricas absolutas e relativas.
    """
    filters = json.loads(request.body.decode())
    unit_study = filters.pop("unit_study", "document")
    metric = filters.pop("metric", "absolute")

    query = build_query(filters)

    if unit_study == "citation":
        aggs = build_citations_per_year_aggs()
    else:
        aggs = build_documents_per_year_aggs()

    body = {"size": 0, "query": query, "aggs": aggs}
    res = es.search(index=ES_INDEX, body=body)

    if unit_study == "citation":
        indicators = parse_citations_per_year_response(res)
    else:
        indicators = parse_documents_per_year_response(res)

    indicators["metric"] = metric
    return JsonResponse(indicators)

def build_query(filters):
	"""
	Build the Elasticsearch query from the received filters, mapping friendly names to real fields.
	"""
	field_map = {
		"year": "publication_year",
		"source_type": "best_oa_location.source.type.keyword",
		"source_index": "indexed_in.keyword",
		"document_type": "type.keyword",
		"open_access": "open_access.is_oa",
		"open_access_type": "open_access.oa_status.keyword",
		"country": "authorships.countries.keyword",
		"thematic_area_level_0": "thematic_areas.level0.keyword",
		"thematic_area_level_1": "thematic_areas.level1.keyword",
		"thematic_area_level_2": "thematic_areas.level2.keyword",
	}
	must = []

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

def build_indicators_aggs():
	"""
	Mount the aggregations for the number of documents per year, total documents, and total citations.
	"""
	return {
		"per_year": {
			"terms": {
				"field": "publication_year",
				"size": 100,
				"order": {"_key": "asc"}
			}
		},
		"total_documents": {"value_count": {"field": "id.keyword"}},
		"total_citations": {"sum": {"field": "cited_by_count"}},
	}

def parse_indicators_response(res):
	"""
	Extract only the values of the indicators for the number of documents per year and percentage.
	"""
	aggs = res.get("aggregations", {})
	
	years = []
	ndocs_per_year = []
	percent_ndocs_per_year = []
	
	total = aggs.get("total_documents", {}).get("value", 0) or 1
	
	for bucket in aggs.get("per_year", {}).get("buckets", []):
		years.append(str(bucket["key"]))
		ndocs_per_year.append(bucket["doc_count"])
		percent_ndocs_per_year.append(round(100 * bucket["doc_count"] / total, 2))
	
	return {
		"years": years,
		"ndocs_per_year": ndocs_per_year,
		"percent_ndocs_per_year": percent_ndocs_per_year,
	}
