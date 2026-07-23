import io
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
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
    GlobalMetricsUploadFile,
    HarvestedBooks,
    HarvestedPreprint,
    HarvestedSciELOData,
    HarvestErrorLogBooks,
    HarvestErrorLogPreprint,
    HarvestErrorLogSciELOData,
)
from .global_metrics.constants import GLOBAL_METRICS_REQUIRED_COLUMNS
from .global_metrics.indexing import GlobalMetricsIndexingError, index_prepared_rows, iter_file_rows
from .global_metrics.opensearch import (
    build_global_metrics_update_by_query_body,
    build_harvest_metric_lookup_body,
    iter_silver_issn_year_groups,
)
from .global_metrics.parsing import global_metric_row_from_hit
from .parse_info_oai_pmh import (
    get_date,
    get_identifier_source,
    get_info_article,
    parse_author_name,
)
from .storage import global_metrics_upload_path, overwrite_media_storage


class GlobalMetricsUploadFileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="metrics-user", password="test")

    def test_upload_path_uses_flat_directory_and_original_filename(self):
        path = global_metrics_upload_path(None, "metrics.xlsx")
        self.assertEqual(path, "global_metrics_uploads/metrics.xlsx")

    @patch("harvest.tasks.process_global_metrics_upload_file.delay")
    def test_same_filename_reuses_existing_record_and_overwrites_file(self, mock_delay):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                first_file = SimpleUploadedFile(
                    "metrics.xlsx",
                    b"first-version",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                first = GlobalMetricsUploadFile(creator=self.user)
                first.file = first_file
                first.save()

                second_file = SimpleUploadedFile(
                    "metrics.xlsx",
                    b"second-version",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                second = GlobalMetricsUploadFile(creator=self.user)
                second.file = second_file
                second.save()

                self.assertEqual(GlobalMetricsUploadFile.objects.count(), 1)
                self.assertEqual(first.pk, second.pk)
                self.assertEqual(second.file.name, "global_metrics_uploads/metrics.xlsx")
                with second.file.open("rb") as stored_file:
                    self.assertEqual(stored_file.read(), b"second-version")
                self.assertEqual(mock_delay.call_count, 2)

    def test_overwrite_storage_does_not_add_suffix(self):
        storage_path = "global_metrics_uploads/metrics.xlsx"
        overwrite_media_storage.save(storage_path, SimpleUploadedFile("metrics.xlsx", b"v1"))
        available_name = overwrite_media_storage.get_available_name(storage_path)
        self.assertEqual(available_name, storage_path)


class GlobalMetricsUploadTaskTests(SimpleTestCase):
    def test_global_metric_row_normalizes_issns_flags_and_country(self):
        hit = {
            "_source": {
                "raw_data": {
                    "issns": "12345678, 8765-4321",
                    "year": "2024",
                    "scopus_active_in_the_year": "1",
                    "wos_active_in_the_year": 0,
                    "scielo_active_and_valid_in_the_year": 1,
                    "country": "Brasil",
                }
            }
        }

        row = global_metric_row_from_hit(hit)

        self.assertEqual(row["issns"], ["12345678", "1234-5678", "8765-4321"])
        self.assertEqual(row["year"], 2024)
        self.assertEqual(row["indexed_in"], ["Scopus", "SciELO"])
        self.assertEqual(row["country"], "Brasil")
        self.assertEqual(row["country_code"], "BR")

    def test_global_metrics_upload_requires_columns_used_by_processing(self):
        file_obj = io.BytesIO(
            b"issns;year;country;scopus_active_in_the_year;wos_active_in_the_year\n"
            b"1234-5678;2024;Brasil;1;0\n"
        )

        with self.assertRaisesMessage(
            GlobalMetricsIndexingError,
            "scielo_active_and_valid_in_the_year",
        ):
            list(
                iter_file_rows(
                    file_obj=file_obj,
                    file_name="metrics.csv",
                    required_columns=GLOBAL_METRICS_REQUIRED_COLUMNS,
                )
            )

    def test_global_metrics_upload_accepts_required_columns(self):
        file_obj = io.BytesIO(
            b"baseid;issns;year;country;scopus_active_in_the_year;wos_active_in_the_year;"
            b"scielo_active_and_valid_in_the_year\n"
            b"B1;1234-5678;2024;Brasil;1;0;1\n"
        )

        rows = list(
            iter_file_rows(
                file_obj=file_obj,
                file_name="metrics.csv",
                required_columns=GLOBAL_METRICS_REQUIRED_COLUMNS,
            )
        )

        self.assertEqual(rows[0][1]["scielo_active_and_valid_in_the_year"], "1")

    def test_iter_silver_issn_year_groups_deduplicates_combinations(self):
        client = DummyOpenSearchClient(
            [
                {
                    "_source": {
                        "publication_year": 2024,
                        "source": {"issns": ["12345678", "8765-4321"]},
                    }
                },
                {
                    "_source": {
                        "publication_year": 2024,
                        "source": {"issns": ["1234-5678"]},
                    }
                },
            ]
        )

        groups = list(iter_silver_issn_year_groups(client, "silver_scientific_production"))

        self.assertEqual(
            groups,
            [
                {"year": 2024, "issns": ["12345678", "1234-5678"]},
                {"year": 2024, "issns": ["8765-4321"]},
            ],
        )

    def test_build_harvest_metric_lookup_body_filters_upload_issn_and_year(self):
        body = build_harvest_metric_lookup_body(
            source_file="metrics.csv",
            year=2024,
            issns=["12345678", "1234-5678"],
        )

        query = body["query"]["bool"]
        self.assertEqual(query["filter"][0]["bool"]["minimum_should_match"], 1)
        self.assertIn({"term": {"raw_data.year": 2024}}, query["filter"][1]["bool"]["should"])
        self.assertIn(
            {"match_phrase": {"raw_data.issns": "1234-5678"}},
            query["must"][0]["bool"]["should"],
        )

    def test_build_global_metrics_update_by_query_body_preserves_params(self):
        body = build_global_metrics_update_by_query_body(
            {
                "year": 2024,
                "issns": ["12345678", "1234-5678"],
                "indexed_in": {"WoS", "Scopus"},
                "country_codes": ["BR"],
                "countries": ["Brasil"],
            },
            document_ids=["silver-1"],
        )

        filters = body["query"]["bool"]["filter"]
        self.assertEqual(filters[0], {"term": {"publication_year": 2024}})
        self.assertEqual(filters[1], {"terms": {"source.issns": ["12345678", "1234-5678"]}})
        self.assertEqual(filters[2], {"ids": {"values": ["silver-1"]}})
        params = body["script"]["params"]
        self.assertEqual(params["indexed_in"], ["Scopus", "WoS"])
        self.assertEqual(params["country_codes"], ["BR"])
        self.assertIn("oca_data.scielo.source", body["script"]["source"])

    @override_settings(GLOBAL_METRICS_UPLOAD_ERROR_INDEX="global_metrics_upload_errors")
    @patch("harvest.global_metrics.indexing.OpenSearchIndexClient")
    @patch("harvest.global_metrics.indexing.streaming_bulk")
    @patch("harvest.global_metrics.indexing.get_opensearch_client")
    def test_bulk_failure_is_indexed_in_upload_error_index(
        self,
        mock_get_client,
        mock_streaming_bulk,
        mock_index_client,
    ):
        client = object()
        mock_get_client.return_value = client
        bulk_result = {
            "index": {
                "_id": "B123-2024",
                "error": {
                    "type": "mapper_parsing_exception",
                    "reason": "failed to parse field",
                },
            }
        }

        def fake_streaming_bulk(client, actions, **kwargs):
            list(actions)
            yield False, bulk_result

        mock_streaming_bulk.side_effect = fake_streaming_bulk

        stats = index_prepared_rows(
            rows=iter([(2, {"baseid": "B123", "year": "2024"})]),
            file_name="metrics.csv",
            extension=".csv",
            index_name="global_metrics_upload_file",
            chunk_size=1,
        )

        self.assertEqual(stats.rows_read, 1)
        self.assertEqual(stats.failed, 1)
        mock_index_client.assert_called_once_with(client=client)
        mock_index_client.return_value.index_error.assert_called_once()
        kwargs = mock_index_client.return_value.index_error.call_args.kwargs
        self.assertEqual(kwargs["component"], "harvest.global_metrics")
        self.assertEqual(kwargs["operation"], "upload_indexing")
        self.assertEqual(kwargs["error_type"], "BulkIndexFailure")
        self.assertEqual(kwargs["error_index_name"], "global_metrics_upload_errors")
        self.assertEqual(kwargs["context"]["source_file"], "metrics.csv")
        self.assertEqual(kwargs["context"]["source_format"], "csv")
        self.assertEqual(kwargs["context"]["target_index"], "global_metrics_upload_file")
        self.assertEqual(kwargs["context"]["document_id"], "B123-2024")
        self.assertEqual(kwargs["context"]["bulk_result"], bulk_result)

    @patch("harvest.global_metrics.indexing.OpenSearchIndexClient")
    @patch("harvest.global_metrics.indexing.streaming_bulk")
    @patch("harvest.global_metrics.indexing.get_opensearch_client")
    def test_upload_error_index_failure_does_not_interrupt_import(
        self,
        mock_get_client,
        mock_streaming_bulk,
        mock_index_client,
    ):
        mock_get_client.return_value = object()
        mock_index_client.return_value.index_error.side_effect = RuntimeError("index unavailable")

        def fake_streaming_bulk(client, actions, **kwargs):
            list(actions)
            yield False, {"index": {"_id": "B123-2024", "error": "boom"}}

        mock_streaming_bulk.side_effect = fake_streaming_bulk

        stats = index_prepared_rows(
            rows=iter([(2, {"baseid": "B123", "year": "2024"})]),
            file_name="metrics.csv",
            extension=".csv",
            index_name="global_metrics_upload_file",
            chunk_size=1,
        )

        self.assertEqual(stats.failed, 1)
        self.assertEqual(len(stats.errors), 1)

    @patch("harvest.global_metrics.indexing.OpenSearchIndexClient")
    @patch("harvest.global_metrics.indexing.streaming_bulk")
    @patch("harvest.global_metrics.indexing.get_opensearch_client")
    def test_bulk_error_samples_are_limited(
        self,
        mock_get_client,
        mock_streaming_bulk,
        mock_index_client,
    ):
        mock_get_client.return_value = object()

        def fake_streaming_bulk(client, actions, **kwargs):
            for action in actions:
                yield False, {"index": {"_id": action["_id"], "error": "boom"}}

        mock_streaming_bulk.side_effect = fake_streaming_bulk
        rows = ((row_number, {"baseid": f"B{row_number}", "year": "2024"}) for row_number in range(2, 14))

        stats = index_prepared_rows(
            rows=rows,
            file_name="metrics.csv",
            extension=".csv",
            index_name="global_metrics_upload_file",
            chunk_size=1,
        )

        self.assertEqual(stats.failed, 12)
        self.assertEqual(len(stats.errors), 10)
        self.assertEqual(mock_index_client.return_value.index_error.call_count, 12)


class DummyOpenSearchClient:
    def __init__(self, hits):
        self.hits = hits

    def search(self, index, body, scroll):
        return {"_scroll_id": "scroll-1", "hits": {"hits": self.hits}}

    def scroll(self, scroll_id, scroll):
        return {"_scroll_id": scroll_id, "hits": {"hits": []}}

    def clear_scroll(self, scroll_id):
        return None


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
