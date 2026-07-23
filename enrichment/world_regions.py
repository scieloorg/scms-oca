import time

from django.conf import settings

from enrichment.exceptions import WorldRegionsProcessingError
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
    task_id = response.get("task")
    if not task_id:
        raise WorldRegionsProcessingError(
            f"O OpenSearch não retornou uma task para o índice {index_name}."
        )

    return task_id


def wait_for_task(task_id, poll_interval):
    client = get_opensearch_client()

    while True:
        result = client.tasks.get(task_id=task_id)

        if result.get("completed"):
            error = result.get("error")
            if error:
                reason = (
                    error.get("reason")
                    if isinstance(error, dict)
                    else str(error)
                )
                raise WorldRegionsProcessingError(reason)

            return result.get("response") or {}

        time.sleep(poll_interval)


def apply_world_regions_to_documents(document_ids, alias):
    upload = WorldRegionsUpload.objects.filter(
        active=True,
        target_data_source__index_name=alias,
    ).first()

    if not upload or not upload.mapping:
        raise WorldRegionsProcessingError(
            f"Não há upload ativo de regiões mundiais para o índice {alias}."
        )

    slices = getattr(settings, "WORLD_REGIONS_SLICES", "auto")
    requests_per_second = getattr(
        settings,
        "WORLD_REGIONS_REQUESTS_PER_SECOND",
        -1,
    )
    poll_interval = getattr(
        settings,
        "WORLD_REGIONS_TASK_POLL_INTERVAL",
        5,
    )
    results = []

    for index_name in concrete_indices(alias):
        task_id = apply_world_regions(
            index_name,
            upload.mapping,
            slices=slices,
            requests_per_second=requests_per_second,
            document_ids=document_ids,
        )
        response = wait_for_task(task_id, poll_interval)
        failures = response.get("failures") or []
        version_conflicts = response.get("version_conflicts", 0)

        if failures or version_conflicts:
            raise WorldRegionsProcessingError(
                f"Falha ao aplicar regiões mundiais em {index_name}: "
                f"{len(failures)} falha(s) e "
                f"{version_conflicts} conflito(s) de versão."
            )

        results.append({"index": index_name, **response})

    return results
