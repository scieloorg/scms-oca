from etl.transform.normalizers import normalize_issn
from harvest.global_metrics.parsing import (
    append_unique,
    coerce_int,
    global_metric_row_from_hit,
    issn_terms,
    issns_overlap,
)
from search_gateway.option_normalization import clean_text


def iter_silver_issn_year_groups(client, silver_index):
    body = {
        "query": {
            "bool": {
                "filter": [
                    {"exists": {"field": "publication_year"}},
                    {"exists": {"field": "source.issns"}},
                ]
            }
        },
        "_source": ["publication_year", "source.issns"],
        "size": 5000,
    }
    processed = set()
    for hit in scroll_hits(client, silver_index, body):
        source = hit.get("_source") or {}
        year = coerce_int(source.get("publication_year"))
        source_data = source.get("source") if isinstance(source.get("source"), dict) else {}
        issns = issn_terms(source_data.get("issns"))
        if year is None or not issns:
            continue

        for issn in issns:
            canonical_issn = normalize_issn(issn) or clean_text(issn)
            if not canonical_issn:
                continue
            key = (year, canonical_issn)
            if key in processed:
                continue
            processed.add(key)
            group_issns = []
            append_unique(group_issns, issn)
            append_unique(group_issns, canonical_issn)
            yield {
                "year": year,
                "issns": group_issns,
            }


def find_global_metric_group_for_silver_group(
    client,
    harvest_index,
    source_file,
    silver_group,
):
    group = {
        "year": silver_group["year"],
        "issns": silver_group["issns"],
        "indexed_in": set(),
        "country_codes": [],
        "countries": [],
        "metric_rows": 0,
        "unresolved_countries": [],
    }
    lookup_body = build_harvest_metric_lookup_body(
        source_file=source_file,
        year=silver_group["year"],
        issns=silver_group["issns"],
    )
    for hit in scroll_hits(client, harvest_index, lookup_body):
        row = global_metric_row_from_hit(hit)
        if not row or row["year"] != silver_group["year"]:
            continue
        if not issns_overlap(row["issns"], silver_group["issns"]):
            continue

        group["metric_rows"] += 1
        group["indexed_in"].update(row["indexed_in"])
        append_unique(group["country_codes"], row.get("country_code"))
        append_unique(group["countries"], row.get("country"))
        if row.get("country") and not row.get("country_code"):
            append_unique(group["unresolved_countries"], row["country"])

    if not group["indexed_in"] and not group["country_codes"]:
        return None
    return group


def build_harvest_metric_lookup_body(source_file, year, issns):
    issn_should = []
    for issn in issns:
        issn_should.extend(
            [
                {"term": {"raw_data.issns.keyword": issn}},
                {"term": {"raw_data.issns": issn}},
                {"match_phrase": {"raw_data.issns": issn}},
            ]
        )

    return {
        "query": {
            "bool": {
                "filter": [
                    source_file_query(source_file),
                    {
                        "bool": {
                            "should": [
                                {"term": {"raw_data.year": year}},
                                {"term": {"raw_data.year.keyword": str(year)}},
                                {"match_phrase": {"raw_data.year": str(year)}},
                            ],
                            "minimum_should_match": 1,
                        }
                    },
                ],
                "must": [
                    {
                        "bool": {
                            "should": issn_should,
                            "minimum_should_match": 1,
                        }
                    }
                ],
            }
        },
        "size": 1000,
    }


def source_file_query(source_file):
    return {
        "bool": {
            "should": [
                {"term": {"source_file.keyword": source_file}},
                {"term": {"source_file": source_file}},
                {"match_phrase": {"source_file": source_file}},
            ],
            "minimum_should_match": 1,
        }
    }


def global_metrics_update_script():
    return """
        if (ctx._source.oca_data == null) {
            ctx._source.oca_data = new HashMap();
        }
        if (ctx._source.oca_data.scielo == null) {
            ctx._source.oca_data.scielo = new HashMap();
        }
        if (ctx._source.oca_data.scielo.source == null) {
            ctx._source.oca_data.scielo.source = new HashMap();
        }
        if (params.indexed_in != null && params.indexed_in.size() > 0) {
            def current = ctx._source.oca_data.scielo.source.indexed_in;
            if (current == null) {
                ctx._source.oca_data.scielo.source.indexed_in = new ArrayList();
            } else if (!(current instanceof List)) {
                def values = new ArrayList();
                values.add(current);
                ctx._source.oca_data.scielo.source.indexed_in = values;
            }
            for (def value : params.indexed_in) {
                if (!ctx._source.oca_data.scielo.source.indexed_in.contains(value)) {
                    ctx._source.oca_data.scielo.source.indexed_in.add(value);
                }
            }
        }
        if (params.country_codes != null && params.country_codes.size() > 0) {
            ctx._source.oca_data.scielo.source.country_code = params.country_codes.get(0);
        }
    """


def build_global_metrics_update_by_query_body(group):
    return {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"publication_year": group["year"]}},
                    {"terms": {"source.issns": group["issns"]}},
                ]
            }
        },
        "script": {
            "lang": "painless",
            "source": global_metrics_update_script(),
            "params": {
                "indexed_in": sorted(group["indexed_in"]),
                "country_codes": group["country_codes"],
            },
        },
    }


def update_silver_group_by_query(client, silver_index, group):
    return client.update_by_query(
        index=silver_index,
        body=build_global_metrics_update_by_query_body(group),
        conflicts="proceed",
        refresh=True,
    )


def scroll_hits(client, index, body, scroll="5m"):
    response = client.search(index=index, body=body, scroll=scroll)
    scroll_id = response.get("_scroll_id")
    try:
        while True:
            hits = response.get("hits", {}).get("hits", [])
            if not hits:
                break
            yield from hits
            response = client.scroll(scroll_id=scroll_id, scroll=scroll)
            scroll_id = response.get("_scroll_id")
    finally:
        if scroll_id:
            client.clear_scroll(scroll_id=scroll_id)
