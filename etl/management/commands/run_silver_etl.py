import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from etl.models import EtlStatus
from etl.pipeline.defaults import PipelineTarget
from etl.pipeline.orchestrator import SilverETLPipeline
from etl.services import backfill_bronze_items, process_pending_items


class Command(BaseCommand):
    help = "Run the OCA Silver ETL pipeline for an explicit source index."

    def add_arguments(self, parser):
        parser.add_argument("--source-index", required=True)
        parser.add_argument("--document-type", required=True)
        parser.add_argument("--silver-index", required=True)
        parser.add_argument("--year", type=int, help="Only process one publication year.")
        parser.add_argument("--max-docs", type=int, help="Maximum documents to load.")
        parser.add_argument("--pending", action="store_true", help="Process pending ETL items.")
        parser.add_argument("--retry-failed", action="store_true", help="Retry failed ETL items.")
        parser.add_argument("--backfill", action="store_true", help="Enqueue bronze items before processing.")
        parser.add_argument("--limit", type=int, default=100, help="Maximum pending/failed items to process.")
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

        if options["backfill"]:
            enqueued = backfill_bronze_items(
                source_index=options["source_index"],
                document_type=options["document_type"],
                year=options.get("year"),
                limit=options.get("max_docs"),
                initial_status=EtlStatus.PENDING,
            )
            self.stdout.write(json.dumps({"enqueued": enqueued}, indent=2, sort_keys=True))
            return

        if options["pending"] or options["retry_failed"]:
            results = process_pending_items(
                source_index=options["source_index"],
                document_type=options["document_type"],
                silver_index_pattern=options["silver_index"],
                limit=options["limit"],
                retry_failed=options.get("retry_failed", False),
            )
        else:
            target = PipelineTarget(
                document_type=options["document_type"],
                source_index=options["source_index"],
                silver_index_pattern=options["silver_index"],
            )
            pipeline = SilverETLPipeline(
                target,
                opensearch_url=getattr(settings, "OS_URL", "http://localhost:9200"),
            )
            results = [
                {
                    **pipeline.run(
                        max_docs=options.get("max_docs"),
                        year_filter=options.get("year"),
                    ),
                    "indexed_indices": sorted(pipeline.indexed_index_names),
                }
            ]

        self.stdout.write(json.dumps(results, indent=2, sort_keys=True))
        if any(result.get("errors", 0) for result in results):
            raise CommandError("Silver ETL finished with errors.")
