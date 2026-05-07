import pytest
from django.core.management import call_command
from io import StringIO

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
from core.users.tests.factories import UserFactory
from education_directory.models import EducationDirectory
from usefulmodels.models import ThematicArea


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def thematic_area(db, user):
    return ThematicArea.objects.create(
        creator=user,
        level0="Ciências Exatas e da Terra",
        level1="Ciência da Computação",
        level2="Teoria da Computação",
    )


@pytest.fixture
def thematic_area_in_directory(db, user):
    ta = ThematicArea.objects.create(
        creator=user,
        level0="Ciências Humanas",
        level1="Educação",
        level2="Ensino-Aprendizagem",
    )
    ed = EducationDirectory.objects.create(creator=user)
    ed.thematic_areas.add(ta)
    return ta


@pytest.fixture
def article_license(db):
    return License.objects.create(name="CC-BY-4.0", url="https://creativecommons.org/licenses/by/4.0/")


@pytest.fixture
def journal(db):
    return Journal.objects.create(journal_name="Test Journal", journal_issn_l="1234-5678")


@pytest.fixture
def affiliation(db):
    return Affiliation.objects.create(name="Test University")


@pytest.fixture
def program(db, affiliation):
    return Program.objects.create(name="Test Program", affiliation=affiliation)


@pytest.fixture
def contributor(db, affiliation):
    c = Contributor.objects.create(family="Doe", given="John")
    c.affiliations.add(affiliation)
    return c


@pytest.fixture
def concept(db, thematic_area):
    c = Concepts.objects.create(specific_id="C123", name="Machine Learning", level=1)
    c.thematic_areas.add(thematic_area)
    return c


@pytest.fixture
def source_article(db):
    return SourceArticle.objects.create(
        specific_id="SA001",
        doi="10.1234/test",
        title="Test Source Article",
    )


@pytest.fixture
def article(db, article_license, journal, contributor, concept, program, user):
    a = Article.objects.create(
        title="Test Article",
        doi="10.1234/article",
        year="2023",
        license=article_license,
        journal=journal,
        creator=user,
    )
    a.contributors.add(contributor)
    a.concepts.add(concept)
    a.programs.add(program)
    return a


@pytest.mark.django_db
class TestDeleteArticleDataCommand:
    def test_deletes_articles(self, article):
        assert Article.objects.count() == 1
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert Article.objects.count() == 0
        assert "Deleted 1 Article(s)" in out.getvalue()

    def test_deletes_source_articles(self, source_article):
        assert SourceArticle.objects.count() == 1
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert SourceArticle.objects.count() == 0
        assert "Deleted 1 SourceArticle(s)" in out.getvalue()

    def test_deletes_contributors(self, contributor):
        assert Contributor.objects.count() == 1
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert Contributor.objects.count() == 0
        assert "Deleted 1 Contributor(s)" in out.getvalue()

    def test_deletes_affiliations(self, affiliation):
        assert Affiliation.objects.count() == 1
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert Affiliation.objects.count() == 0
        assert "Deleted 1 Affiliation(s)" in out.getvalue()

    def test_deletes_journals(self, journal):
        assert Journal.objects.count() == 1
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert Journal.objects.count() == 0
        assert "Deleted 1 Journal(s)" in out.getvalue()

    def test_deletes_programs(self, program):
        assert Program.objects.count() == 1
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert Program.objects.count() == 0
        assert "Deleted 1 Program(s)" in out.getvalue()

    def test_deletes_licenses(self, article_license):
        assert License.objects.count() == 1
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert License.objects.count() == 0
        assert "Deleted 1 License(s), skipped 0" in out.getvalue()

    def test_deletes_concepts(self, concept):
        assert Concepts.objects.count() == 1
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert Concepts.objects.count() == 0
        assert "Deleted 1 Concepts" in out.getvalue()

    def test_deletes_thematic_area_not_in_directory(self, concept, thematic_area):
        assert ThematicArea.objects.count() == 1
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert ThematicArea.objects.count() == 0
        assert "Deleted 1 ThematicArea(s), skipped 0" in out.getvalue()

    def test_skips_thematic_area_in_directory(
        self, concept, thematic_area, thematic_area_in_directory
    ):
        # thematic_area is used only by Concepts -> should be deleted
        # thematic_area_in_directory is used by EducationDirectory -> should be skipped
        concept.thematic_areas.add(thematic_area_in_directory)
        assert ThematicArea.objects.count() == 2
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        output = out.getvalue()
        # The one used by directory should remain
        assert ThematicArea.objects.count() == 1
        assert ThematicArea.objects.filter(id=thematic_area_in_directory.id).exists()
        assert "Deleted 1 ThematicArea(s), skipped 1" in output
        assert "is referenced by directory models. Skipping." in output

    def test_deletes_all_related_data(
        self,
        article,
        source_article,
        thematic_area,
    ):
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        assert Article.objects.count() == 0
        assert SourceArticle.objects.count() == 0
        assert Contributor.objects.count() == 0
        assert Affiliation.objects.count() == 0
        assert Journal.objects.count() == 0
        assert Program.objects.count() == 0
        assert License.objects.count() == 0
        assert Concepts.objects.count() == 0
        # ThematicArea not used by directories should be deleted
        assert ThematicArea.objects.filter(id=thematic_area.id).exists() is False

    def test_empty_database(self, db):
        out = StringIO()
        call_command("delete_article_data", stdout=out)
        output = out.getvalue()
        assert "Deleted 0 Article(s)" in output
        assert "Deleted 0 SourceArticle(s)" in output
        assert "Deleted 0 Contributor(s)" in output
        assert "Deleted 0 Affiliation(s)" in output
        assert "Deleted 0 Journal(s)" in output
        assert "Deleted 0 Program(s)" in output
        assert "Deleted 0 License(s), skipped 0" in output
        assert "Deleted 0 Concepts" in output
        assert "Deleted 0 ThematicArea(s), skipped 0" in output
