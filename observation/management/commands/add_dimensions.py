import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from observation.models import ObservationPage, ObservationDimension


class Command(BaseCommand):
    help = "Add or update canonical ObservationDimension records from a JSON fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default=None,
            help="Path to a JSON fixture file. Defaults to observation_dimensions.json in the workspace root.",
        )
        parser.add_argument(
            "--purge-missing",
            action="store_true",
            help="Delete ObservationDimension records not present in the fixture for the processed pages.",
        )

    def handle(self, *args, **options):
        fixture_path = self._get_fixture_path(options.get("fixture"))
        payload = self._load_fixture(fixture_path)

        PAGE_MAPPING = {
            137: ["scientific_production", "silver_scientific_production"],
            138: ["social_production"],
        }

        synced_slugs_by_page = {}
        processed_count = 0

        for item in payload:
            model_name = item.get("model")
            fields = item.get("fields") or {}
            original_page_id = fields.get("page")
            slug = fields.get("slug")

            if model_name != "observation.observationdimension":
                continue
            if not original_page_id:
                raise CommandError(f"Fixture item missing page: {item}")
            if not slug:
                raise CommandError(f"Fixture item missing slug: {item}")

            # Resolve target pages based on original page PK or DataSource mapping
            target_pages = []
            if original_page_id in PAGE_MAPPING:
                target_pages = list(
                    ObservationPage.objects.filter(
                        data_source__index_name__in=PAGE_MAPPING[original_page_id]
                    )
                )
            else:
                fallback_page = ObservationPage.objects.filter(pk=original_page_id).first()
                if fallback_page:
                    target_pages = [fallback_page]

            if not target_pages:
                continue

            for page in target_pages:
                defaults = {
                    "sort_order": fields.get("sort_order"),
                    "menu_label": fields.get("menu_label"),
                    "row_field_name": fields.get("row_field_name"),
                    "col_field_name": fields.get("col_field_name"),
                    "row_bucket_size": fields.get("row_bucket_size"),
                    "col_bucket_size": fields.get("col_bucket_size"),
                    "table_title": fields.get("table_title"),
                    "kpi_label": fields.get("kpi_label"),
                    "row_label": fields.get("row_label"),
                    "col_label": fields.get("col_label"),
                    "value_label": fields.get("value_label"),
                    "is_default": fields.get("is_default", False),
                }

                _, created = ObservationDimension.objects.update_or_create(
                    page=page,
                    slug=slug,
                    defaults=defaults,
                )

                if page.pk not in synced_slugs_by_page:
                    synced_slugs_by_page[page.pk] = []
                synced_slugs_by_page[page.pk].append(slug)

                processed_count += 1
                action = "Created" if created else "Updated"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{action} Dimension '{slug}' for page '{page.title}' ({page.locale.language_code})"
                    )
                )

        if options.get("purge_missing"):
            purged_total = 0
            for page_pk, slugs in synced_slugs_by_page.items():
                deleted_count, _ = (
                    ObservationDimension.objects.filter(page_id=page_pk)
                    .exclude(slug__in=slugs)
                    .delete()
                )
                if deleted_count:
                    purged_total += deleted_count
                    self.stdout.write(
                        self.style.WARNING(
                            f"Purged {deleted_count} stale dimension(s) for page ID {page_pk}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully synced {processed_count} dimensions across matched locale pages."
            )
        )

    def _get_fixture_path(self, explicit_path):
        if explicit_path:
            path = Path(explicit_path)
        else:
            path = Path(__file__).resolve().parents[3] / "observation_dimensions.json"

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
