import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from etl.client import OpenSearchClient
from etl.documents import RawOpenAlexInputDocument
from etl.mapping_silver import SILVER_MAPPING
from etl.transform.normalizers import normalize_openalex_id
from etl.transform.standardizer import OpenAlexStandardizer
from harvest.utils import clean_source_payload

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill OpenAlex-only documents from raw_openalex_works into silver."

    def add_arguments(self, parser):
        parser.add_argument(
            "--openalex-index",
            default=settings.ETL_INPUT_OPENALEX_WORKS,
            help="Source OpenAlex index name.",
        )
        parser.add_argument(
            "--write-alias",
            default=settings.ETL_OPENALEX_ONLY_WRITE_ALIAS,
            help="Write alias for OpenAlex-only indices.",
        )
        parser.add_argument(
            "--public-alias",
            default=settings.ETL_PUBLIC_ALIAS,
            help="Public silver alias.",
        )
        parser.add_argument(
            "--rollover-max-size",
            default=settings.ETL_SILVER_ROLLOVER_MAX_SIZE,
            help="Max index size before rollover.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Deduplication and index batch size.",
        )
        parser.add_argument(
            "--max-docs",
            type=int,
            default=None,
            help="Maximum total documents to process.",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Filter by publication_year.",
        )
        parser.add_argument(
            "--dedupe-source",
            choices=["silver", "postgres", "both"],
            default="silver",
            help="Deduplication source.",
        )
        parser.add_argument(
            "--preload-existing-ids",
            action="store_true",
            help="Preload all existing OpenAlex IDs from silver into memory.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without mutating OpenSearch.",
        )
        parser.add_argument(
            "--log-level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="Logging level.",
        )

    def handle(self, *args, **options):
        logging.basicConfig(
            level=getattr(logging, options["log_level"]),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        openalex_index = options["openalex_index"]
        write_alias = options["write_alias"]
        public_alias = options["public_alias"]
        rollover_max_size = options["rollover_max_size"]
        batch_size = options["batch_size"]
        max_docs = options["max_docs"]
        year_filter = options["year"]
        dedupe_source = options["dedupe_source"]
        preload_existing_ids = options["preload_existing_ids"]
        dry_run = options["dry_run"]

        metrics = {
            "total_read": 0,
            "total_invalid_openalex_id": 0,
            "total_already_in_silver": 0,
            "total_eligible": 0,
            "total_indexed": 0,
            "total_skipped_no_publication_year": 0,
            "total_standardization_errors": 0,
            "total_index_errors": 0,
            "total_rollovers_executed": 0,
            "created_index_names": [],
            "dedupe_source": dedupe_source,
            "dry_run": dry_run,
        }

        client = OpenSearchClient()

        if not client.index_exists(openalex_index):
            raise CommandError(f"Source index '{openalex_index}' does not exist.")

        standardizer = OpenAlexStandardizer()

        public_alias_available = client.index_exists(public_alias)
        if dry_run and not public_alias_available:
            logger.warning(
                "Public alias '%s' does not exist; dry-run will assume no existing OpenAlex IDs.",
                public_alias,
            )

        preloaded_ids: set[str] = set()
        if preload_existing_ids and public_alias_available:
            logger.debug("Preloading existing OpenAlex IDs from silver public alias...")
            preloaded_ids = _preload_existing_openalex_ids(client, public_alias)
            logger.debug("Preloaded %s existing OpenAlex IDs.", len(preloaded_ids))

        if not dry_run:
            bootstrap_index = client.ensure_rollover_index(
                index_prefix=settings.ETL_OPENALEX_ONLY_INDEX_PATTERN,
                write_alias=write_alias,
                public_alias=public_alias,
                mapping=SILVER_MAPPING,
            )
            if bootstrap_index:
                metrics["created_index_names"].append(bootstrap_index)
                logger.debug("Created bootstrap index: %s", bootstrap_index)
            public_alias_available = True

        query: dict = {"bool": {"must_not": [{"term": {"is_xpac": True}}]}}
        if year_filter is not None:
            query["bool"]["filter"] = [{"term": {"publication_year": year_filter}}]

        scroll_size = min(batch_size, 1000) if max_docs is None else min(max_docs, 1000, batch_size)
        search_body = {"query": query, "size": scroll_size}

        response = client.client.search(index=openalex_index, body=search_body, scroll="5m")
        scroll_id = response.get("_scroll_id")

        total_read = 0
        total_indexed = 0
        total_skipped_year = 0
        total_invalid_id = 0
        total_already_exist = 0
        total_eligible = 0
        total_std_errors = 0
        total_idx_errors = 0
        rollovers = 0

        try:
            while True:
                hits = response["hits"]["hits"]
                if not hits:
                    break

                batch_oa_ids: list[str] = []
                batch_id_to_raw: dict[str, dict] = {}

                for hit in hits:
                    if max_docs is not None and total_read >= max_docs:
                        break
                    total_read += 1
                    raw = clean_source_payload(hit["_source"])
                    oa_id = normalize_openalex_id(raw.get("id"))
                    if not oa_id:
                        total_invalid_id += 1
                        logger.warning("Invalid/missing OpenAlex ID in document %s", hit.get("_id"))
                        metrics["total_invalid_openalex_id"] = total_invalid_id
                        continue
                    batch_oa_ids.append(oa_id)
                    batch_id_to_raw[oa_id] = raw

                if not batch_oa_ids:
                    metrics["total_read"] = total_read
                    if max_docs is not None and total_read >= max_docs:
                        break
                    response = client.client.scroll(scroll_id=scroll_id, scroll="5m")
                    scroll_id = response.get("_scroll_id")
                    continue

                if not public_alias_available:
                    existing_ids = set()
                elif preloaded_ids:
                    existing_ids = {oid for oid in batch_oa_ids if oid in preloaded_ids}
                else:
                    existing_ids = _lookup_existing_openalex_ids(
                        client,
                        public_alias,
                        batch_oa_ids,
                        batch_size,
                    )

                total_already_exist += len(existing_ids)
                metrics["total_already_in_silver"] = total_already_exist

                eligible_ids = [oid for oid in batch_oa_ids if oid not in existing_ids]
                total_eligible += len(eligible_ids)
                metrics["total_eligible"] = total_eligible

                actions = []
                for oa_id in eligible_ids:
                    raw = batch_id_to_raw[oa_id]
                    try:
                        input_doc = RawOpenAlexInputDocument.from_raw(raw)
                    except Exception as e:
                        total_std_errors += 1
                        metrics["total_standardization_errors"] = total_std_errors
                        logger.warning("Error creating input document for %s: %s", oa_id, e)
                        continue

                    if not input_doc.publication_year:
                        total_skipped_year += 1
                        metrics["total_skipped_no_publication_year"] = total_skipped_year
                        logger.warning("No publication_year for OpenAlex ID %s", oa_id)
                        continue

                    try:
                        silver_doc = standardizer.run(input_doc)
                    except Exception as e:
                        total_std_errors += 1
                        metrics["total_standardization_errors"] = total_std_errors
                        logger.warning("Error standardizing %s: %s", oa_id, e)
                        continue

                    if not dry_run:
                        actions.append({
                            "index": {
                                "_index": write_alias,
                                "_id": oa_id,
                            }
                        })
                        actions.append(silver_doc.to_index_dict())

                if actions and not dry_run:
                    try:
                        response_bulk = client.client.bulk(body=actions)
                        if response_bulk.get("errors"):
                            error_items = [
                                item.get("index", {})
                                for item in response_bulk["items"]
                                if item.get("index", {}).get("status", 200) >= 400
                            ]
                            error_count = len(error_items)
                            total_idx_errors += error_count
                            metrics["total_index_errors"] = total_idx_errors
                            for err_item in error_items[:5]:
                                logger.error("Index error: %s", err_item.get("error"))
                        else:
                            indexed_count = len(actions) // 2
                            total_indexed += indexed_count
                            metrics["total_indexed"] = total_indexed
                            logger.debug("Indexed %s OpenAlex-only documents.", indexed_count)

                            rollover_index = client.rollover(
                                write_alias=write_alias,
                                public_alias=public_alias,
                                mapping=SILVER_MAPPING,
                                max_size=rollover_max_size,
                            )
                            if rollover_index:
                                rollovers += 1
                                metrics["total_rollovers_executed"] = rollovers
                                metrics["created_index_names"].append(rollover_index)
                                logger.debug("Rollover executed, new index: %s", rollover_index)
                    except Exception as e:
                        total_idx_errors += 1
                        metrics["total_index_errors"] = total_idx_errors
                        logger.error("Bulk index failed: %s", e)

                metrics["total_read"] = total_read
                self.stdout.write(
                    "Progress: read=%s eligible=%s indexed=%s already_in_silver=%s "
                    "no_year=%s std_errors=%s idx_errors=%s" % (
                        total_read, total_eligible, total_indexed, total_already_exist,
                        total_skipped_year, total_std_errors, total_idx_errors,
                    )
                )

                if max_docs is not None and total_read >= max_docs:
                    break

                response = client.client.scroll(scroll_id=scroll_id, scroll="5m")
                scroll_id = response.get("_scroll_id")

        finally:
            if scroll_id:
                client.client.clear_scroll(scroll_id=scroll_id)

        self.stdout.write(json.dumps(metrics, indent=2, sort_keys=True))

        if total_idx_errors > 0:
            raise CommandError("OpenAlex-only backfill finished with index errors.")


def _lookup_existing_openalex_ids(
    client: OpenSearchClient,
    public_alias: str,
    oa_ids: list[str],
    batch_size: int,
) -> set[str]:
    existing: set[str] = set()
    for i in range(0, len(oa_ids), batch_size):
        chunk = oa_ids[i:i + batch_size]
        body = {
            "query": {
                "bool": {
                    "should": [
                        {"terms": {"ids.openalex": chunk}},
                        {"terms": {"oca_data.openalex.ids": chunk}},
                        {"ids": {"values": chunk}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            "size": len(chunk),
            "_source": True,
        }
        try:
            resp = client.client.search(index=public_alias, body=body)
            for hit in resp["hits"]["hits"]:
                src = hit.get("_source", {})
                ids_field = src.get("ids", {})
                oa_field = ids_field.get("openalex") if isinstance(ids_field, dict) else None
                if oa_field:
                    if isinstance(oa_field, list):
                        for item in oa_field:
                            if nid := normalize_openalex_id(item):
                                existing.add(nid)
                    elif nid := normalize_openalex_id(oa_field):
                        existing.add(nid)
                oca_data = src.get("oca_data", {})
                oca_openalex = oca_data.get("openalex", {})
                oca_ids_list = oca_openalex.get("ids") if isinstance(oca_openalex, dict) else None
                if oca_ids_list and isinstance(oca_ids_list, list):
                    for item in oca_ids_list:
                        if nid := normalize_openalex_id(item):
                            existing.add(nid)
        except Exception:
            logger.exception(
                "Deduplication lookup failed for chunk - aborting to avoid silent duplicates"
            )
            raise

    return existing


def _preload_existing_openalex_ids(
    client: OpenSearchClient,
    public_alias: str,
) -> set[str]:
    existing: set[str] = set()
    body = {
        "query": {
            "bool": {
                "should": [
                    {"exists": {"field": "ids.openalex"}},
                    {"exists": {"field": "oca_data.openalex.ids"}},
                ],
                "minimum_should_match": 1,
            }
        },
        "size": 10000,
        "_source": True,
    }
    response = client.client.search(index=public_alias, body=body, scroll="5m")
    scroll_id = response.get("_scroll_id")
    try:
        while True:
            hits = response["hits"]["hits"]
            if not hits:
                break
            for hit in hits:
                src = hit.get("_source", {})
                ids_field = src.get("ids", {})
                oa_field = ids_field.get("openalex") if isinstance(ids_field, dict) else None
                if oa_field:
                    if isinstance(oa_field, list):
                        for item in oa_field:
                            if nid := normalize_openalex_id(item):
                                existing.add(nid)
                    elif nid := normalize_openalex_id(oa_field):
                        existing.add(nid)
                oca_data = src.get("oca_data", {})
                oca_openalex = oca_data.get("openalex", {})
                oca_ids_list = oca_openalex.get("ids") if isinstance(oca_openalex, dict) else None
                if oca_ids_list and isinstance(oca_ids_list, list):
                    for item in oca_ids_list:
                        if nid := normalize_openalex_id(item):
                            existing.add(nid)
            response = client.client.scroll(scroll_id=scroll_id, scroll="5m")
            scroll_id = response.get("_scroll_id")
    finally:
        if scroll_id:
            client.client.clear_scroll(scroll_id=scroll_id)
    return existing
