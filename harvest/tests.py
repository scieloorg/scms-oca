from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from lxml import etree

from core.users.models import User
from harvest.language_normalizer import (
    normalize_language_field,
    normalize_language_value,
)

from .exception_logs import ExceptionContext
from .harvests.harvest_data import harvest_data
from .harvests.harvest_preprint import NODES, harvest_preprint
from .models import (
    HarvestedBooks,
    HarvestedPreprint,
    HarvestedSciELOData,
    HarvestErrorLogBooks,
    HarvestErrorLogPreprint,
    HarvestErrorLogSciELOData,
)
from .parse_info_oai_pmh import (
    get_date,
    get_identifier_source,
    get_info_article,
    parse_author_name,
)


class DummyHeader:
    def __init__(self, identifier, datestamp=None):
        self.identifier = identifier
        self.datestamp = datestamp


class DummyRec:
    def __init__(self, identifier, xml, datestamp=None):
        self.header = DummyHeader(identifier, datestamp=datestamp)
        self._xml = xml

    def __str__(self):
        return self._xml


class HarvestTestOAIPMH(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        self.sample_xml = """
            <record xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                    xmlns:dc="http://purl.org/dc/elements/1.1/">
                <dc:title xml:lang="pt">Titulo de teste</dc:title>
                <dc:creator>Silva, Maria</dc:creator>
                <dc:identifier>https://example.org/preprint/123</dc:identifier>
                <dc:identifier>doi:10.0000/xyz</dc:identifier>
                <dc:date>2024-05-20</dc:date>
                <dc:language>pt</dc:language>
            </record>
        """.strip()

    def test_parse_author_name_with_comma(self):
        data = parse_author_name("Silva, Maria")
        self.assertEqual(data["given_names"], "Maria")
        self.assertEqual(data["surname"], "Silva")

    def test_parse_author_name_without_comma(self):
        data = parse_author_name("Maria Silva")
        self.assertEqual(data["declared_name"], "Maria Silva")

    def test_get_identifier_source_only_urls(self):
        root = etree.fromstring(self.sample_xml)
        urls = get_identifier_source(
            root=root,
            exc_context=ExceptionContext(
                harvest_object=None, fk_field=None, log_model=None
            ),
        )
        self.assertEqual(urls, ["https://example.org/preprint/123"])

    def test_get_date_valid(self):
        root = etree.fromstring(self.sample_xml)
        date = get_date(
            root=root,
            exc_context=ExceptionContext(
                harvest_object=None, fk_field=None, log_model=None
            ),
        )
        self.assertEqual(date, {"day": 20, "month": 5, "year": 2024})

    def test_get_info_article_parses_fields(self):
        rec = DummyRec("oai:scielo:123", self.sample_xml, datestamp=timezone.now())
        data = get_info_article(
            rec,
            ExceptionContext(harvest_object=rec, fk_field=None, log_model=None),
            nodes=NODES,
        )
        self.assertEqual(data["title"][0]["text"], "Titulo de teste")
        self.assertEqual(data["language"], "pt")
        self.assertEqual(data["authors"][0]["surname"], "Silva")
        self.assertIn("https://example.org/preprint/123", data["source"])

    def test_harvest_preprint_creates_record(self):
        datestamp = timezone.now()
        rec = DummyRec("oai:scielo:123", self.sample_xml, datestamp=datestamp)
        harvest_preprint([rec], user=self.user)

        obj = HarvestedPreprint.objects.get(identifier="oai:scielo:123")
        self.assertEqual(obj.creator, self.user)
        self.assertEqual(obj.raw_data["title"][0]["text"], "Titulo de teste")
        self.assertEqual(obj.datestamp, datestamp)
        self.assertEqual(HarvestedPreprint.objects.count(), 1)
        self.assertEqual(HarvestedPreprint.objects.first().harvest_status, "success")

    def test_exception_context_saves_preprint_log(self):
        preprint = HarvestedPreprint.objects.create(
            identifier="oai:scielo:preprint:1",
            creator=self.user,
        )
        exc_context = ExceptionContext(
            harvest_object=preprint,
            log_model=HarvestErrorLogPreprint,
            fk_field="preprint",
        )
        exc_context.add_exception(
            exception=ValueError("Invalid date"),
            field_name="date",
        )
        exc_context.save_to_db()

        self.assertEqual(HarvestErrorLogPreprint.objects.count(), 1)
        log = HarvestErrorLogPreprint.objects.first()
        self.assertEqual(log.preprint, preprint)
        self.assertEqual(log.field_name, "date")
        self.assertEqual(log.exception_type, "ValueError")
        self.assertIn("Invalid date", log.exception_message)

    def test_exception_context_saves_preprint_log(self):
        preprint = HarvestedPreprint.objects.create(
            identifier="oai:scielo:preprint:1",
            creator=self.user,
        )
        exc_context = ExceptionContext(
            harvest_object=preprint,
            log_model=HarvestErrorLogPreprint,
            fk_field="preprint",
        )
        exc_context.add_exception(
            exception=IndexError("Error retrieving preprint data."),
            field_name="date",
        )
        exc_context.save_to_db()
        exc_context.verify_obj_as_failed()
        self.assertEqual(HarvestErrorLogPreprint.objects.count(), 1)
        log = HarvestErrorLogPreprint.objects.first()
        self.assertEqual(log.preprint, preprint)
        self.assertEqual(log.field_name, "date")
        self.assertEqual(log.exception_type, "IndexError")
        self.assertIn("Error retrieving preprint data", log.exception_message)
        self.assertEqual(preprint.harvest_status, "failed")
        self.assertEqual(preprint.harvest_error_log.count(), 1)
        self.assertEqual(
            preprint.harvest_error_log.first().exception_type, "IndexError"
        )

    def test_exception_context_saves_book_log(self):
        book = HarvestedBooks.objects.create(
            identifier="oai:scielo:book:1",
            creator=self.user,
        )
        exc_context = ExceptionContext(
            harvest_object=book,
            log_model=HarvestErrorLogBooks,
            fk_field="book",
        )
        exc_context.add_exception(
            exception=KeyError("missing field"),
            field_name="identifier",
        )
        exc_context.save_to_db()
        exc_context.verify_obj_as_failed()
        self.assertEqual(HarvestErrorLogBooks.objects.count(), 1)
        log = HarvestErrorLogBooks.objects.first()
        self.assertEqual(log.book, book)
        self.assertEqual(log.field_name, "identifier")
        self.assertEqual(log.exception_type, "KeyError")
        self.assertIn("missing field", log.exception_message)
        self.assertEqual(book.harvest_status, "failed")
        self.assertEqual(book.harvest_error_log.count(), 1)
        self.assertEqual(book.harvest_error_log.first().exception_type, "KeyError")

    def test_exception_context_saves_scielo_data_log(self):
        data = HarvestedSciELOData.objects.create(
            identifier="oai:scielo:data:1",
            creator=self.user,
        )
        exc_context = ExceptionContext(
            harvest_object=data,
            log_model=HarvestErrorLogSciELOData,
            fk_field="scielo_data",
        )
        exc_context.add_exception(
            exception=RuntimeError("unexpected"),
            field_name="creator",
            context_data={"value": None},
        )
        exc_context.save_to_db()
        exc_context.verify_obj_as_failed()
        self.assertEqual(HarvestErrorLogSciELOData.objects.count(), 1)
        log = HarvestErrorLogSciELOData.objects.first()
        self.assertEqual(log.scielo_data, data)
        self.assertEqual(log.field_name, "creator")
        self.assertEqual(log.exception_type, "RuntimeError")
        self.assertEqual(data.harvest_status, "failed")
        self.assertEqual(data.harvest_error_log.count(), 1)
        self.assertEqual(data.harvest_error_log.first().exception_type, "RuntimeError")

    @patch("harvest.harvests.harvest_data.fetch_dataset_data")
    @patch("harvest.harvests.harvest_data.fetch_search_page")
    def test_harvest_data_paginates_using_total_count(
        self, mock_fetch_search, mock_fetch_dataset
    ):
        dataverse_item = {
            "type": "dataverse",
            "identifier": "dv-1",
            "name": "Dataverse Test",
        }
        dataset_item = {
            "type": "dataset",
            "global_id": "doi:10.5072/FK2/TEST",
        }
        dataset_data = {
            "identifier": "ds-1",
            "title": "Dataset Test",
        }
        mock_fetch_search.side_effect = [
            ([dataverse_item, dataset_item], 2),
            ([], 2),
        ]
        mock_fetch_dataset.return_value = dataset_data

        harvest_data(
            user=self.user,
            base_url="https://data.scielo.org",
            per_page=2,
            start=0,
        )

        self.assertEqual(HarvestedSciELOData.objects.count(), 2)
        dataverse_obj = HarvestedSciELOData.objects.get(identifier="dv-1")
        dataset_obj = HarvestedSciELOData.objects.get(identifier="ds-1")
        self.assertEqual(dataverse_obj.raw_data["identifier"], "dv-1")
        self.assertEqual(dataset_obj.raw_data["identifier"], "ds-1")


class LanguageNormalizerTests(SimpleTestCase):
    def test_expected_examples_are_normalized(self):
        examples = {
            "English": "en",
            "ENG": "en",
            "Portuguese": "pt",
            "French": "fr",
            "Spanish Sign Language": "es",
            "Spanish": "es",
            "Castilian": "es",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(normalize_language_value(source), expected)

    def test_iso_639_2_codes(self):
        examples = {
            "por": "pt",
            "fre": "fr",
            "fra": "fr",
            "spa": "es",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(normalize_language_value(source), expected)

    def test_fallback_keeps_original(self):
        self.assertEqual(normalize_language_value("unknown-language-x"), "unknown-language-x")

    def test_list_input_deduplicates_preserving_order(self):
        languages = ["English", "ENG", "Portuguese", "pt", "Castilian", "Spanish", "EN-US", "Spanish Sign Language", "Spanish, Castilian", "DUTCH"]
        self.assertEqual(normalize_language_field(languages), ["en", "pt", "es", "nl"])
