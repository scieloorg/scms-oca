from enrichment.models import WorldRegionsUpload
from search_gateway.client import get_opensearch_client


WORLD_REGIONS_UPDATE_SCRIPT = """
    boolean changed = false;
    def ocaData = ctx._source.oca_data;
    def scielo = ocaData != null ? ocaData.scielo : null;
    if (scielo != null && scielo.source != null) {
        def countryCode = scielo.source.country_code;
        def region = countryCode != null ? params.mapping[countryCode] : null;
        if (region != null && scielo.source.world_region != region) {
            scielo.source.world_region = region;
            changed = true;
        }
    }
    def regions = new HashSet();
    for (def countryCode : ctx._source.author_country_codes ?: []) {
        def region = params.mapping[countryCode];
        if (region != null) {
            regions.add(region);
        }
    }
    if (!regions.isEmpty()) {
        def expected = new ArrayList(regions);
        Collections.sort(expected);
        if (ocaData == null) {
            ocaData = new HashMap();
            ctx._source.oca_data = ocaData;
        }
        if (ocaData.openalex == null) {
            ocaData.openalex = new HashMap();
        }
        if (ocaData.openalex.affiliations == null) {
            ocaData.openalex.affiliations = new HashMap();
        }
        if (!expected.equals(ocaData.openalex.affiliations.world_regions)) {
            ocaData.openalex.affiliations.world_regions = expected;
            changed = true;
        }
    }
    if (!changed) {
        ctx.op = 'noop';
    }
"""


def concrete_indices(alias):
    client = get_opensearch_client()
    return sorted(client.indices.get_alias(name=alias))


def world_regions_update_body(mapping, document_ids=None):
    query = {
        "bool": {
            "should": [
                {"terms": {"oca_data.scielo.source.country_code": sorted(mapping)}},
                {"terms": {"author_country_codes": sorted(mapping)}},
            ],
            "minimum_should_match": 1,
        }
    }
    if document_ids is not None:
        query["bool"]["filter"] = [{"ids": {"values": document_ids}}]

    return {
        "query": query,
        "script": {
            "lang": "painless",
            "source": WORLD_REGIONS_UPDATE_SCRIPT,
            "params": {"mapping": mapping},
        },
    }


def apply_world_regions(
    index_name,
    mapping,
    slices="auto",
    requests_per_second=-1,
    document_ids=None,
):
    client = get_opensearch_client()
    response = client.update_by_query(
        index=index_name,
        body=world_regions_update_body(mapping, document_ids=document_ids),
        conflicts="proceed",
        refresh=False,
        wait_for_completion=False,
        slices=slices,
        requests_per_second=requests_per_second,
    )
    return response["task"]


def apply_world_regions_to_documents(document_ids, alias):
    upload = WorldRegionsUpload.objects.filter(active=True).first()
    if not upload or not upload.mapping:
        return

    return [
        apply_world_regions(
            index_name,
            upload.mapping,
            document_ids=document_ids,
        )
        for index_name in concrete_indices(alias)
    ]
