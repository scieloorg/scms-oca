import argparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from search_gateway.client import get_opensearch_client
from search_gateway.lookup import (
    DEFAULT_LOOKUPS,
    LOOKUP_BUILDERS,
    BuildConfig,
    build_lookup_indices,
)
from search_gateway.option_normalization import clean_text
from search_gateway.tasks import build_lookup_indices_task


def parse_lookup_index_override(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected KEY=INDEX format for --lookup-index.")

    key, index_name = value.split("=", 1)
    key = clean_text(key)
    index_name = clean_text(index_name)

    if not key or not index_name:
        raise argparse.ArgumentTypeError("Both KEY and INDEX are required for --lookup-index.")
    if key not in LOOKUP_BUILDERS:
        valid = ", ".join(sorted(LOOKUP_BUILDERS.keys()))
        raise argparse.ArgumentTypeError(f"Unknown lookup '{key}'. Valid values: {valid}")

    return key, index_name


def parse_max_items(value: str) -> tuple[str, int]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected KEY=LIMIT format for --max-items.")

    key, limit_str = value.split("=", 1)
    key = clean_text(key)

    if key not in LOOKUP_BUILDERS:
        valid = ", ".join(sorted(LOOKUP_BUILDERS.keys()))
        raise argparse.ArgumentTypeError(f"Unknown lookup '{key}'. Valid values: {valid}")

    try:
        limit = int(limit_str)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("LIMIT for --max-items must be an integer.") from exc

    if limit < 1:
        raise argparse.ArgumentTypeError("LIMIT for --max-items must be >= 1.")

    return key, limit


class Command(BaseCommand):
    help = "Build lookup indexes from the scientific production source index or alias."

    def add_arguments(self, parser):
        default_source_index = getattr(
            settings,
            "SEARCH_GATEWAY_LOOKUP_SOURCE_INDEX",
            getattr(settings, "OP_INDEX_SCIENTIFIC_PRODUCTION", "scientific_production"),
        )
        default_batch_size = getattr(settings, "SEARCH_GATEWAY_LOOKUP_BATCH_SIZE", 500)
        parser.add_argument(
            "--source-index",
            default=default_source_index,
            help=f"Source index or alias. Default: {default_source_index}",
        )
        parser.add_argument(
            "--lookup",
            dest="lookups",
            action="append",
            choices=sorted(LOOKUP_BUILDERS.keys()),
            help="Lookup key to build. Repeat to build multiple lookups.",
        )
        parser.add_argument(
            "--lookup-index",
            action="append",
            default=[],
            help="Override destination index name in KEY=INDEX format. Repeat as needed.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=default_batch_size,
            help=f"Scroll and bulk batch size. Default: {default_batch_size}",
        )
        parser.add_argument(
            "--max-docs",
            type=int,
            default=None,
            help="Optional limit for source documents processed.",
        )
        parser.add_argument(
            "--max-items",
            action="append",
            default=[],
            help="Optional limit of unique values per lookup in KEY=LIMIT format. Repeat as needed.",
        )
        parser.add_argument(
            "--enqueue",
            action="store_true",
            help="Enqueue the build in Celery instead of running it in this process.",
        )

    def handle(self, *args, **options):
        if options["batch_size"] < 1:
            raise CommandError("--batch-size must be >= 1.")
        if options["max_docs"] is not None and options["max_docs"] < 1:
            raise CommandError("--max-docs must be >= 1.")

        try:
            lookup_index_overrides = dict(
                parse_lookup_index_override(item)
                for item in options["lookup_index"]
            )
            max_items = dict(parse_max_items(item) for item in options["max_items"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        config = BuildConfig(
            source_index=options["source_index"],
            batch_size=options["batch_size"],
            max_docs=options["max_docs"],
            selected_lookups=options["lookups"] or DEFAULT_LOOKUPS.copy(),
            lookup_index_overrides=lookup_index_overrides,
            max_items=max_items,
        )

        if options["enqueue"]:
            result = build_lookup_indices_task.delay(
                source_index=config.source_index,
                batch_size=config.batch_size,
                max_docs=config.max_docs,
                selected_lookups=config.selected_lookups,
                lookup_index_overrides=config.lookup_index_overrides,
                max_items=config.max_items,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Enqueued lookup build task {result.id} for '{config.source_index}'."
                )
            )
            return

        client = get_opensearch_client()

        try:
            counts = build_lookup_indices(
                client,
                config,
                lookup_builders=LOOKUP_BUILDERS,
                progress=lambda message: self.stdout.write(message),
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        processed_docs = counts.pop("_processed_docs", 0)
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {processed_docs:,} source document(s) from '{config.source_index}'."
            )
        )
        for lookup_key, indexed_count in counts.items():
            self.stdout.write(
                self.style.SUCCESS(
                    f"Indexed {indexed_count:,} document(s) for lookup '{lookup_key}'."
                )
            )
