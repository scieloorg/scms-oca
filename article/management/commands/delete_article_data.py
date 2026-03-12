from django.core.management.base import BaseCommand

from article import models as article_models
from education_directory.models import EducationDirectory
from event_directory.models import EventDirectory
from infrastructure_directory.models import InfrastructureDirectory
from policy_directory.models import PolicyDirectory
from scholarly_articles.models import ScholarlyArticles
from usefulmodels.models import ThematicArea


class Command(BaseCommand):
    help = "Remove all Article data and related models data."

    def handle(self, *args, **options):
        # Delete Articles
        article_count = article_models.Article.objects.count()
        article_models.Article.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {article_count} Article(s)")
        )

        # Delete SourceArticles
        source_article_count = article_models.SourceArticle.objects.count()
        article_models.SourceArticle.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {source_article_count} SourceArticle(s)")
        )

        # Delete Contributors
        contributor_count = article_models.Contributor.objects.count()
        article_models.Contributor.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {contributor_count} Contributor(s)")
        )

        # Delete Affiliations
        affiliation_count = article_models.Affiliation.objects.count()
        article_models.Affiliation.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {affiliation_count} Affiliation(s)")
        )

        # Delete Journals
        journal_count = article_models.Journal.objects.count()
        article_models.Journal.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {journal_count} Journal(s)")
        )

        # Delete Programs
        program_count = article_models.Program.objects.count()
        article_models.Program.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {program_count} Program(s)")
        )

        # Delete Licenses (check ScholarlyArticles first)
        self._delete_licenses()

        # Collect ThematicArea IDs from Concepts, delete Concepts,
        # then delete ThematicAreas if not used by directory models
        self._delete_concepts_and_thematic_areas()

    def _delete_licenses(self):
        licenses = article_models.License.objects.all()
        deleted_count = 0
        skipped_count = 0

        for license_obj in licenses:
            if ScholarlyArticles.objects.filter(license_id=license_obj.pk).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"License '{license_obj}' is referenced by ScholarlyArticles. Skipping."
                    )
                )
                skipped_count += 1
            else:
                license_obj.delete()
                deleted_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} License(s), skipped {skipped_count}"
            )
        )

    def _delete_concepts_and_thematic_areas(self):
        # Collect ThematicArea IDs referenced by Concepts before deleting them
        thematic_area_ids = set(
            article_models.Concepts.objects.filter(
                thematic_areas__isnull=False
            ).values_list("thematic_areas__id", flat=True)
        )

        # Delete Concepts
        concepts_count = article_models.Concepts.objects.count()
        article_models.Concepts.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {concepts_count} Concepts")
        )

        # Try to delete the ThematicAreas that were associated with Concepts
        deleted_count = 0
        skipped_count = 0

        for ta in ThematicArea.objects.filter(id__in=thematic_area_ids):
            in_use = (
                EducationDirectory.objects.filter(thematic_areas=ta).exists()
                or InfrastructureDirectory.objects.filter(thematic_areas=ta).exists()
                or EventDirectory.objects.filter(thematic_areas=ta).exists()
                or PolicyDirectory.objects.filter(thematic_areas=ta).exists()
            )

            if in_use:
                self.stdout.write(
                    self.style.WARNING(
                        f"ThematicArea '{ta}' is referenced by directory models. Skipping."
                    )
                )
                skipped_count += 1
            else:
                ta.delete()
                deleted_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} ThematicArea(s), skipped {skipped_count}"
            )
        )
