import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from etl.models import EtlPipelineConfig


class Command(BaseCommand):
    help = "Add or update canonical ETL Pipeline Config records from the bundled fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default=None,
            help="Path to a JSON fixture file. Defaults to etl/fixtures/pipeline_configs.json.",
        )
        parser.add_argument(
            "--purge-missing",
            action="store_true",
            help="Delete EtlPipelineConfig records not present in the fixture.",
        )

    def handle(self, *args, **options):
        fixture_path = self._get_fixture_path(options.get("fixture"))
        payload = self._load_fixture(fixture_path)

        synced_names = []
        for item in payload:
            model_name = item.get("model")
            fields = item.get("fields") or {}
            name = fields.get("name")

            if model_name != EtlPipelineConfig._meta.label_lower:
                continue
            if not name:
                raise CommandError(f"Fixture item missing name: {item}")

            _, created = EtlPipelineConfig.objects.update_or_create(
                name=name,
                defaults=fields,
            )
            synced_names.append(name)
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} EtlPipelineConfig '{name}'"))

        if options.get("purge_missing"):
            deleted_count, _ = EtlPipelineConfig.objects.exclude(
                name__in=synced_names
            ).delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted_count} stale EtlPipelineConfig record(s)")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(synced_names)} EtlPipelineConfig record(s) from {fixture_path}"
            )
        )

    def _get_fixture_path(self, explicit_path):
        if explicit_path:
            path = Path(explicit_path)
        else:
            path = Path(__file__).resolve().parents[2] / "fixtures" / "pipeline_configs.json"

        if not path.exists():
            raise CommandError(f"Fixture file not found: {path}")
        return path

    def _load_fixture(self, fixture_path):
        try:
            payload = json.loads(fixture_path.read_text())
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON fixture: {fixture_path}") from exc

        if not isinstance(payload, list):
            raise CommandError("Fixture must contain a JSON list of objects")
        return payload
