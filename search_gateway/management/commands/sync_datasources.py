import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from search_gateway.models import DataSource


class Command(BaseCommand):
    help = "Sync canonical DataSource records from the bundled fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default=None,
            help="Path to a JSON fixture file. Defaults to search_gateway/fixtures/datasources.json.",
        )
        parser.add_argument(
            "--purge-missing",
            action="store_true",
            help="Delete DataSource records not present in the fixture.",
        )

    def handle(self, *args, **options):
        fixture_path = self._get_fixture_path(options.get("fixture"))
        payload = self._load_fixture(fixture_path)

        synced_index_names = []
        for item in payload:
            model_name = item.get("model")
            fields = item.get("fields") or {}
            index_name = fields.get("index_name")

            if model_name != DataSource._meta.label_lower:
                continue
            if not index_name:
                raise CommandError(f"Fixture item missing index_name: {item}")

            defaults = {
                "display_name": fields.get("display_name", ""),
                "source_fields": fields.get("source_fields", []),
                "field_settings": fields.get("field_settings", {}),
            }
            _, created = DataSource.objects.update_or_create(
                index_name=index_name,
                defaults=defaults,
            )
            synced_index_names.append(index_name)
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} DataSource '{index_name}'"))

        if options.get("purge_missing"):
            deleted_count, _ = DataSource.objects.exclude(index_name__in=synced_index_names).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted_count} stale DataSource record(s)"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {len(synced_index_names)} DataSource record(s) from {fixture_path}"
            )
        )

    def _get_fixture_path(self, explicit_path):
        if explicit_path:
            path = Path(explicit_path)
        else:
            path = Path(__file__).resolve().parents[2] / "fixtures" / "datasources.json"

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
