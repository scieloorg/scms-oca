import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from etl.services import process_pending_items
from etl.tasks import run_pipeline_targets


class Command(BaseCommand):
    help = "Run the OCA silver ETL pipeline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            default="article",
            help="Document type to process.",
        )
        parser.add_argument("--year", type=int, help="Only process one publication year.")
        parser.add_argument("--max-docs", type=int, help="Maximum documents to load.")
        parser.add_argument(
            "--pending",
            action="store_true",
            help="Process pending ETL items.",
        )
        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Retry failed ETL items.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum pending/failed ETL items to process.",
        )
        parser.add_argument(
            "--openalex-index",
            default=settings.ETL_OPENALEX_MATCH_INDEX,
            help="Silver OpenAlex candidate index or alias used for matching.",
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
        if options.get("pending") or options.get("retry_failed"):
            results = process_pending_items(
                limit=options["limit"],
                retry_failed=options.get("retry_failed", False),
            )
        else:
            results = run_pipeline_targets(
                options["type"],
                year=options.get("year"),
                max_docs=options.get("max_docs"),
                openalex_index=options.get("openalex_index") or settings.ETL_OPENALEX_MATCH_INDEX,
            )
        self.stdout.write(json.dumps(results, indent=2, sort_keys=True))

        if any(result.get("errors", 0) for result in results):
            raise CommandError("Silver ETL finished with errors.")
