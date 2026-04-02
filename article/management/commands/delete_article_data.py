from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Q

from article.models import (
    Affiliation,
    Article,
    Concepts,
    Contributor,
    Journal,
    License,
    Program,
    SourceArticle,
)
from institution.models import Institution
from location.models import Location
from scholarly_articles.models import (
    Affiliations,
    Contributors,
    ErrorLog,
    Journals,
    RawUnpaywall,
    ScholarlyArticles,
    SupplementaryData,
)
from scholarly_articles.models import License as ScholarlyLicense
from usefulmodels.models import ThematicArea


# python manage.py delete_article_data --dry-run
# python manage.py delete_article_data --no-input
# python manage.py delete_article_data --models Article SourceArticle
# python manage.py delete_article_data --list-models
# python manage.py delete_article_data --directory-stats

# --- article app ---


def delete_articles():
    return Article.objects.all()


def delete_source_articles():
    return SourceArticle.objects.all()


def delete_contributors():
    return Contributor.objects.all()


def delete_programs():
    return Program.objects.all()


def delete_affiliations():
    return Affiliation.objects.all()


def delete_concepts():
    return Concepts.objects.all()


def delete_journals():
    return Journal.objects.all()


def delete_licenses():
    return License.objects.all()


# --- scholarly_articles app ---


def delete_scholarly_articles():
    return ScholarlyArticles.objects.all()


def delete_raw_unpaywall():
    return RawUnpaywall.objects.all()


def delete_supplementary_data():
    return SupplementaryData.objects.all()


def delete_error_logs():
    return ErrorLog.objects.all()


def delete_scholarly_contributors():
    return Contributors.objects.all()


def delete_scholarly_affiliations():
    return Affiliations.objects.all()


def delete_scholarly_journals():
    return Journals.objects.all()


def delete_scholarly_licenses():
    return ScholarlyLicense.objects.all()


# --- shared models (smart filtering) ---


def delete_thematic_areas():
    """Retorna apenas ThematicAreas que NÃO são referenciadas por nenhum Directory."""
    return ThematicArea.objects.exclude(
        Q(educationdirectory__isnull=False)
        | Q(infrastructuredirectory__isnull=False)
        | Q(eventdirectory__isnull=False)
        | Q(policydirectory__isnull=False)
    )


def delete_institutions():
    """Retorna apenas Institutions que NÃO são referenciadas por nenhum Directory."""
    return Institution.objects.exclude(
        Q(educationdirectory__isnull=False)
        | Q(infrastructuredirectory__isnull=False)
        | Q(eventdirectory__isnull=False)
        | Q(policydirectory__isnull=False)
    )


def delete_locations():
    """
    Retorna apenas Locations que NÃO são referenciadas por nenhum Directory
    e NÃO são referenciadas por nenhuma Institution restante.
    """
    return Location.objects.exclude(
        Q(educationdirectory__isnull=False)
        | Q(eventdirectory__isnull=False)
        | Q(institution__isnull=False)
    )


# Tabelas M2M cujo nome no banco não corresponde ao nome gerado pelo ORM atual
# (resultado de renomeação de modelo sem migração de renomeação de tabela).
# São limpas via SQL direto antes de deletar os modelos relacionados.
LEGACY_M2M_TABLES = [
    ("ScholarlyArticles→Contributors (M2M)", "scholarly_articles_article_contributors"),
]

DELETION_STEPS = [
    # article app
    ("Article", delete_articles),
    ("SourceArticle", delete_source_articles),
    ("Contributor", delete_contributors),
    ("Program", delete_programs),
    ("Affiliation", delete_affiliations),
    ("Concepts", delete_concepts),
    ("Journal", delete_journals),
    ("License", delete_licenses),
    # scholarly_articles app
    ("ScholarlyArticles", delete_scholarly_articles),
    ("RawUnpaywall", delete_raw_unpaywall),
    ("SupplementaryData", delete_supplementary_data),
    ("ErrorLog", delete_error_logs),
    ("Contributors", delete_scholarly_contributors),
    ("Affiliations", delete_scholarly_affiliations),
    ("Journals", delete_scholarly_journals),
    ("ScholarlyLicense", delete_scholarly_licenses),
    # shared models (smart filter - preserva os vinculados a Directory)
    ("ThematicArea", delete_thematic_areas),
    ("Institution", delete_institutions),
    ("Location", delete_locations),
]


class Command(BaseCommand):
    help = (
        "Remove todos os dados de Article/ScholarlyArticles e seus modelos relacionados "
        "(SourceArticle, Contributor, Affiliation, Program, Concepts, Journal, License, "
        "Contributors, Affiliations, Journals, RawUnpaywall, SupplementaryData, ErrorLog). "
        "Para modelos compartilhados (ThematicArea, Institution, Location), remove apenas "
        "os objetos que NÃO são referenciados por nenhum Directory."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Apenas exibe a contagem de registros que seriam removidos, sem deletar.",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            default=False,
            help="Pula a confirmação interativa e executa diretamente.",
        )
        parser.add_argument(
            "--models",
            nargs="+",
            metavar="MODEL",
            default=None,
            help=(
                "Lista de modelos a deletar (nomes separados por espaço). "
                "Se omitido, todos os modelos são deletados. "
                "Use --list-models para ver os nomes disponíveis."
            ),
        )
        parser.add_argument(
            "--list-models",
            action="store_true",
            default=False,
            help="Lista todos os modelos disponíveis para deleção e encerra.",
        )
        parser.add_argument(
            "--directory-stats",
            action="store_true",
            default=False,
            help=(
                "Exibe a quantidade de ThematicArea, Institution e Location "
                "vinculados a cada modelo Directory (serão preservados) e encerra."
            ),
        )

    def _show_directory_stats(self):
        from education_directory.models import EducationDirectory
        from event_directory.models import EventDirectory
        from infrastructure_directory.models import InfrastructureDirectory
        from policy_directory.models import PolicyDirectory

        # (directory_name, model, has_location)
        # has_location indica se o Directory possui campo M2M para Location
        DIRECTORIES = [
            ("EducationDirectory",      EducationDirectory,      True),
            ("InfrastructureDirectory", InfrastructureDirectory, False),
            ("EventDirectory",          EventDirectory,          True),
            ("PolicyDirectory",         PolicyDirectory,         False),
        ]

        W = 26  # column width for shared model name
        C = 10  # column width for count
        SEP = "-" * (W + C + 4)

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Objetos vinculados a cada Directory (serão preservados):"))

        for dir_name, dir_model, has_location in DIRECTORIES:
            # reverse accessor name = model name in lowercase (Django default)
            reverse = dir_model._meta.model_name

            ta_count = (
                ThematicArea.objects
                .filter(**{f"{reverse}__isnull": False})
                .distinct()
                .count()
            )
            inst_count = (
                Institution.objects
                .filter(**{f"{reverse}__isnull": False})
                .distinct()
                .count()
            )
            loc_count = (
                Location.objects
                .filter(**{f"{reverse}__isnull": False})
                .distinct()
                .count()
                if has_location else 0
            )

            self.stdout.write("")
            self.stdout.write(self.style.NOTICE(f"  {dir_name}"))
            self.stdout.write(f"  {SEP}")
            self.stdout.write(f"  {'Modelo':{W}s} {'Qtd':>{C}}")
            self.stdout.write(f"  {SEP}")
            self.stdout.write(f"  {'ThematicArea':{W}s} {ta_count:>{C},}")
            self.stdout.write(f"  {'Institution':{W}s} {inst_count:>{C},}")
            self.stdout.write(f"  {'Location':{W}s} {loc_count:>{C},}")
            self.stdout.write(f"  {SEP}")

        # Totals: preserved = total - (those with no Directory reference)
        preserved_thematic    = ThematicArea.objects.count() - delete_thematic_areas().count()
        preserved_institution = Institution.objects.count()  - delete_institutions().count()
        preserved_location    = Location.objects.count()     - delete_locations().count()

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Total preservado (vinculado a qualquer Directory):"))
        self.stdout.write(f"  {SEP}")
        self.stdout.write(f"  {'ThematicArea':{W}s} {preserved_thematic:>{C},}")
        self.stdout.write(f"  {'Institution':{W}s} {preserved_institution:>{C},}")
        self.stdout.write(f"  {'Location':{W}s} {preserved_location:>{C},}")
        self.stdout.write(f"  {SEP}")
        self.stdout.write("")

    def _count_legacy_m2m(self):
        counts = {}
        for name, table in LEGACY_M2M_TABLES:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[name] = cursor.fetchone()[0]
        return counts

    def _delete_legacy_m2m(self):
        for name, table in LEGACY_M2M_TABLES:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
            if count == 0:
                self.stdout.write(f"  {name}: nenhum registro.")
                continue
            self.stdout.write(self.style.WARNING(f"  Deletando {name} ({count:,} registros)..."))
            with connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM {table}")
            self.stdout.write(
                self.style.SUCCESS(f"  {name}: {count:,} registros removidos no total.")
            )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        no_input = options["no_input"]
        selected_models = options["models"]

        all_names = [name for name, _ in DELETION_STEPS]

        if options["list_models"]:
            self.stdout.write(self.style.WARNING("Modelos disponíveis para deleção:"))
            for name in all_names:
                self.stdout.write(f"  {name}")
            return

        if options["directory_stats"]:
            self._show_directory_stats()
            return

        if selected_models:
            invalid = set(selected_models) - set(all_names)
            if invalid:
                self.stderr.write(
                    self.style.ERROR(
                        f"Modelos inválidos: {', '.join(sorted(invalid))}\n"
                        f"Use --list-models para ver os nomes disponíveis."
                    )
                )
                return
            active_steps = [(name, fn) for name, fn in DELETION_STEPS if name in selected_models]
        else:
            active_steps = DELETION_STEPS

        counts = {name: fn().count() for name, fn in active_steps}
        legacy_m2m_counts = (
            self._count_legacy_m2m()
            if not selected_models or "Contributors" in selected_models
            else {}
        )
        counts.update(legacy_m2m_counts)
        total = sum(counts.values())

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Registros que serão removidos:"))
        self.stdout.write("-" * 40)
        for name, count in counts.items():
            self.stdout.write(f"  {name:45s} {count:>10,}")
        self.stdout.write("-" * 40)
        self.stdout.write(f"  {'TOTAL':45s} {total:>10,}")
        self.stdout.write("")

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS("Nenhum registro encontrado. Nada a fazer.")
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    "Modo --dry-run ativo. Nenhum registro foi removido."
                )
            )
            return

        if not no_input:
            answer = input("Confirma a remoção de todos os registros acima? [s/N] ")
            if answer.lower() not in ("s", "sim", "y", "yes"):
                self.stdout.write(
                    self.style.WARNING("Operação cancelada pelo usuário.")
                )
                return

        legacy_m2m_done = False
        for name, fn in active_steps:
            # Limpa as tabelas M2M legadas antes de deletar Contributors
            if name == "Contributors" and not legacy_m2m_done:
                self._delete_legacy_m2m()
                legacy_m2m_done = True

            qs = fn()
            count = qs.count()
            if count == 0:
                self.stdout.write(f"  {name}: nenhum registro.")
                continue
            self.stdout.write(self.style.WARNING(f"  Deletando {name} ({count:,} registros)..."))
            deleted, details = qs.delete()
            for model_label, model_count in sorted(details.items()):
                self.stdout.write(f"    - {model_label}: {model_count:,}")
            self.stdout.write(
                self.style.SUCCESS(f"  {name}: {deleted:,} registros removidos no total.")
            )

        if not legacy_m2m_done:
            self._delete_legacy_m2m()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Concluído. Todos os dados de Article e ScholarlyArticles foram removidos."
            )
        )
