from collections import defaultdict

from django.core.management.base import BaseCommand

from etl.models import EtlItemProcess
from etl.transform.normalizers import normalize_document_type_for_etl


class Command(BaseCommand):
    help = "Normalize persisted ETL item document_type values using ETL aliases."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Update records. Without this flag the command only reports changes.",
        )
        parser.add_argument(
            "--source-index",
            help="Only normalize items from this source_index.",
        )
        parser.add_argument(
            "--from-type",
            dest="from_type",
            help="Only normalize items currently stored with this document_type.",
        )

    def handle(self, *args, **options):
        qs = EtlItemProcess.objects.all()
        if options.get("source_index"):
            qs = qs.filter(source_index=options["source_index"])
        if options.get("from_type"):
            qs = qs.filter(document_type=options["from_type"])

        current_types = (
            qs.values_list("document_type", flat=True)
            .distinct()
            .order_by("document_type")
        )

        planned = []
        invalid = []
        for current_type in current_types:
            try:
                normalized_type = normalize_document_type_for_etl(current_type)
            except ValueError:
                invalid.append(current_type)
                continue
            if normalized_type == current_type:
                continue
            count = qs.filter(document_type=current_type).count()
            planned.append((current_type, normalized_type, count))

        if not planned:
            self.stdout.write("No document_type values need normalization.")
        else:
            self.stdout.write("Planned document_type normalization:")
            for current_type, normalized_type, count in planned:
                self.stdout.write(f"  {current_type} -> {normalized_type}: {count}")

        if invalid:
            self.stdout.write(
                self.style.WARNING(
                    "Invalid/empty document_type values ignored: "
                    + ", ".join(str(value) for value in invalid)
                )
            )

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Dry-run only. Re-run with --apply to update."))
            return

        updated_by_target = defaultdict(int)
        for current_type, normalized_type, _count in planned:
            updated = qs.filter(document_type=current_type).update(
                document_type=normalized_type
            )
            updated_by_target[normalized_type] += updated

        total_updated = sum(updated_by_target.values())
        self.stdout.write(self.style.SUCCESS(f"Updated {total_updated} ETL item(s)."))
        for normalized_type, count in sorted(updated_by_target.items()):
            self.stdout.write(f"  {normalized_type}: {count}")
