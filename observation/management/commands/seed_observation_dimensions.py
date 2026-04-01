from django.core.management.base import BaseCommand, CommandError

from observation.models import ObservationDimension, ObservationPage


DIMENSION_SPECS = [
    {
        "slug": "documents-by-institution",
        "menu_label": "Evolution of Scientific Production - World - number of documents by Institution",
        "row_label": "Institution",
        "row_field_candidates": ["institutions", "institution"],
        "is_default": False,
    },
    {
        "slug": "documents-by-journal",
        "menu_label": "Evolution of Scientific Production - World - number of documents by Journal",
        "row_label": "Journal",
        "row_field_candidates": ["source_name", "journal_title", "primary_source_title"],
        "is_default": False,
    },
    {
        "slug": "documents-by-thematic-area",
        "menu_label": "Evolution of Scientific Production - World - number of documents by Thematic Area",
        "row_label": "Thematic Area",
        "row_field_candidates": ["subject_area_level_1", "topic_fields", "primary_topic_field"],
        "is_default": False,
    },
    {
        "slug": "documents-by-type-of-access",
        "menu_label": "Evolution of Scientific Production - World - number of documents by Type of Access",
        "row_label": "Type of Access",
        "row_field_candidates": ["open_access_status", "open_access"],
        "is_default": False,
    },
    {
        "slug": "documents-by-publisher",
        "menu_label": "Evolution of Scientific Production - World - number of documents by Publisher",
        "row_label": "Publisher",
        "row_field_candidates": ["publisher"],
        "is_default": False,
    },
    {
        "slug": "documents-by-country-region-affiliation",
        "menu_label": "Evolution of Scientific Production - World - number of documents by Country and Region of Affiliation",
        "row_label": "Country and Region of Affiliation",
        "row_field_candidates": ["country", "author_country_codes"],
        "is_default": True,
    },
]


class Command(BaseCommand):
    help = "Create/update default observation dimensions for ObservationPage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--page-id",
            type=int,
            help="ObservationPage ID to update. If omitted, updates all ObservationPage.",
        )
        parser.add_argument(
            "--index-name",
            default="scientific_production",
            help="Filter pages by DataSource index_name (default: scientific_production).",
        )

    def handle(self, *args, **options):
        page_id = options.get("page_id")
        index_name = options.get("index_name")

        queryset = ObservationPage.objects.select_related("data_source").all()
        if page_id:
            queryset = queryset.filter(id=page_id)
        elif index_name:
            queryset = queryset.filter(data_source__index_name=index_name)

        pages = list(queryset)
        if not pages:
            raise CommandError("No ObservationPage found for provided filters.")

        for page in pages:
            self._seed_page(page)

        self.stdout.write(
            self.style.SUCCESS(f"Processed {len(pages)} observation page(s).")
        )

    def _seed_page(self, page):
        if not page.data_source:
            self.stdout.write(
                self.style.WARNING(
                    f"[page={page.id}] skipped: page has no data_source."
                )
            )
            return

        field_settings = page.data_source.field_settings_dict or {}
        existing_slugs = set(
            page.dimensions.values_list("slug", flat=True)
        )

        created_or_updated = 0
        default_slug = None

        for spec in DIMENSION_SPECS:
            row_field_name = self._pick_row_field(field_settings, spec["row_field_candidates"])
            if not row_field_name:
                self.stdout.write(
                    self.style.WARNING(
                        f"[page={page.id}] skipped dimension '{spec['slug']}': "
                        f"none of {spec['row_field_candidates']} exists in DataSource."
                    )
                )
                continue

            col_field_name = "publication_year"
            if col_field_name not in field_settings:
                self.stdout.write(
                    self.style.WARNING(
                        f"[page={page.id}] skipped dimension '{spec['slug']}': "
                        "publication_year not configured in DataSource."
                    )
                )
                continue

            defaults = {
                "menu_label": spec["menu_label"],
                "row_field_name": row_field_name,
                "col_field_name": col_field_name,
                "row_bucket_size": 500,
                "col_bucket_size": 300,
                "table_title": spec["menu_label"],
                "kpi_label": "Documents",
                "row_label": spec["row_label"],
                "col_label": "Year",
                "value_label": "Documents",
                "is_default": False,
            }
            _, _created = ObservationDimension.objects.update_or_create(
                page=page,
                slug=spec["slug"],
                defaults=defaults,
            )
            created_or_updated += 1
            if spec.get("is_default"):
                default_slug = spec["slug"]

        if default_slug:
            page.dimensions.exclude(slug=default_slug).update(is_default=False)
            page.dimensions.filter(slug=default_slug).update(is_default=True)
        elif existing_slugs:
            first_slug = (
                page.dimensions.order_by("sort_order", "id")
                .values_list("slug", flat=True)
                .first()
            )
            if first_slug:
                page.dimensions.exclude(slug=first_slug).update(is_default=False)
                page.dimensions.filter(slug=first_slug).update(is_default=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"[page={page.id}] dimensions created/updated: {created_or_updated}"
            )
        )

    @staticmethod
    def _pick_row_field(field_settings, candidates):
        for candidate in candidates:
            if candidate in field_settings:
                return candidate
        return None
