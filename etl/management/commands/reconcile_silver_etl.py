import json

from django.core.management.base import BaseCommand

from etl.client import OpenSearchClient
from etl.models import EtlPipelineConfig
from etl.services import enqueue_etl_item


class Command(BaseCommand):
    help = "Recreate ETL pending items from input indices without processing them."

    def add_arguments(self, parser):
        parser.add_argument("--source-index")
        parser.add_argument("--since", help="Only documents with oca_indexed_at greater than this value.")
        parser.add_argument("--year", type=int, help="Only documents from this publication year.")
        parser.add_argument("--limit", type=int, default=1000)
        parser.add_argument("--batch-size", type=int, default=500)

    def handle(self, *args, **options):
        source_indices = (
            [options["source_index"]]
            if options.get("source_index")
            else sorted(config.input_index for config in EtlPipelineConfig.objects.enabled())
        )
        client = OpenSearchClient().client
        total = 0
        results = []
        for index_name in source_indices:
            filters = []
            if options.get("since"):
                filters.append({"range": {"oca_indexed_at": {"gt": options["since"]}}})
            if options.get("year"):
                filters.append({"term": {"publication_year": options["year"]}})
            query = {"bool": {"filter": filters}} if filters else {"match_all": {}}
            count = 0
            scroll_id = None
            try:
                response = client.search(
                    index=index_name,
                    body={"query": query, "size": options["batch_size"]},
                    scroll="5m",
                )
                scroll_id = response.get("_scroll_id")
                while True:
                    hits = response["hits"]["hits"]
                    if not hits:
                        break
                    for hit in hits:
                        if count >= options["limit"]:
                            break
                        enqueue_etl_item(
                            source_index=index_name,
                            external_id=hit["_id"],
                            source_payload=hit["_source"],
                        )
                        count += 1
                    if count >= options["limit"]:
                        break
                    response = client.scroll(scroll_id=scroll_id, scroll="5m")
                    scroll_id = response.get("_scroll_id")
            finally:
                if scroll_id:
                    client.clear_scroll(scroll_id=scroll_id)
            total += count
            results.append({"source_index": index_name, "enqueued": count})

        self.stdout.write(json.dumps({"total": total, "results": results}, indent=2))
