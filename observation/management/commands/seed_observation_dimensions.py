from django.core.management.base import BaseCommand, CommandError

from observation.models import ObservationPage
from observation.seed_dimensions import seed_all_observation_pages, seed_observation_page_dimensions


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
            default=None,
            help=(
                "Filter pages by DataSource index_name "
                "(e.g. scientific_production, social_production). "
                "If omitted, all observation pages are processed."
            ),
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
            seed_observation_page_dimensions(
                page,
                stdout=self.stdout,
                style=self.style,
            )

        self.stdout.write(
            self.style.SUCCESS(f"Processed {len(pages)} observation page(s).")
        )
