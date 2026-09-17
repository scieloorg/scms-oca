import gzip
import io
import json
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from lxml import etree

from core.users.models import User
from harvest.language_normalizer import (
    normalize_language_field,
    normalize_language_value,
)

from .bronze_transform import (
    _build_reindex_body,
    _refresh_source_for_page,
    _reindex_page,
    transform_documents_batch,
    transform_documents_page,
    transform_indexed_page,
)
from .exception_logs import ExceptionContext
from .global_metrics.constants import GLOBAL_METRICS_REQUIRED_COLUMNS
from .global_metrics.indexing import (
    GlobalMetricsIndexingError,
    index_prepared_rows,
    iter_file_rows,
)
from .global_metrics.opensearch import (
    build_global_metrics_update_by_query_body,
    iter_harvest_metric_groups,
    source_file_query,
    update_silver_group_by_query,
    wait_for_update_task,
)
from .global_metrics.parsing import global_metric_row_from_hit
from .global_metrics.process import process_global_metrics_upload_file
from .harvesters.article import (
    fetch_article_identifiers_page,
    harvest_articles,
)
from .harvesters.dataset import harvest_data
from .harvesters.openalex import (
    harvest_openalex_works,
    index_openalex_batch,
    iter_gzip_jsonl_works,
    iter_part_files,
    iter_part_works,
    parse_updated_date_from_url,
    s3_url_to_https,
)
from .harvesters.preprint import NODES, harvest_preprint
from .indexing import get_index_name
from .models import (
    GlobalMetricsUploadFile,
    HarvestedArticle,
    HarvestedBook,
    HarvestedPreprint,
    HarvestedSciELOData,
    HarvestErrorLogArticle,
    HarvestErrorLogBook,
    HarvestErrorLogOpenAlex,
    HarvestErrorLogPreprint,
    HarvestErrorLogSciELOData,
    HarvestModelChoice,
    OpenAlexHarvestRequest,
    TransformationScript,
)
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
                with self.captureOnCommitCallbacks(execute=True):
                    first.save()

                second_file = SimpleUploadedFile(
                    "metrics.xlsx",
                    b"second-version",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                second = GlobalMetricsUploadFile(creator=self.user)
                second.file = second_file
                with self.captureOnCommitCallbacks(execute=True):
                    second.save()

                self.assertEqual(GlobalMetricsUploadFile.objects.count(), 1)
                self.assertEqual(first.pk, second.pk)
                self.assertEqual(second.file.name, "global_metrics_uploads/metrics.xlsx")
                with second.file.open("rb") as stored_file:
                    self.assertEqual(stored_file.read(), b"second-version")
                self.assertEqual(mock_delay.call_count, 2)

    @patch("harvest.global_metrics.process.index_file_obj")
    @patch("harvest.tasks.process_global_metrics_upload_file.delay")
    def test_process_skips_reindex_when_already_processed(self, mock_delay, mock_index):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                upload_file = GlobalMetricsUploadFile(creator=self.user)
                upload_file.file = SimpleUploadedFile(
                    "metrics.xlsx",
                    b"already-indexed",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                with self.captureOnCommitCallbacks(execute=True):
                    upload_file.save()
                upload_file.mark_processed()

                result = process_global_metrics_upload_file(upload_file.pk)

        self.assertTrue(result["skipped"])
        mock_index.assert_not_called()

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
                    "country": "Brazil",
                }
            }
        }

        row = global_metric_row_from_hit(hit)

        self.assertEqual(row["issns"], ["12345678", "1234-5678", "8765-4321"])
        self.assertEqual(row["year"], 2024)
        self.assertEqual(row["indexed_in"], ["Scopus", "SciELO"])
        self.assertEqual(row["country"], "Brazil")
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

    def test_source_file_query_filters_upload_file(self):
        query = source_file_query("metrics.csv")

        self.assertEqual(query["bool"]["minimum_should_match"], 1)
        self.assertIn({"term": {"source_file.keyword": "metrics.csv"}}, query["bool"]["should"])

    def test_iter_harvest_metric_groups_groups_canonical_issns(self):
        client = DummyOpenSearchClient(
            [
                {
                    "_source": {
                        "raw_data": {
                            "issns": "12345678, 8765-4321",
                            "year": "2024",
                            "scopus_active_in_the_year": "1",
                            "wos_active_in_the_year": 0,
                            "scielo_active_and_valid_in_the_year": 0,
                            "country": "Brazil",
                        }
                    }
                }
            ]
        )

        groups = list(
            iter_harvest_metric_groups(client, "global_metrics_upload_file", "metrics.csv")
        )

        self.assertEqual(client.last_index, "global_metrics_upload_file")
        self.assertEqual(client.last_search_body["query"]["bool"]["minimum_should_match"], 1)
        self.assertEqual(
            [group["year"] for group in groups],
            [2024, 2024],
        )
        self.assertEqual(groups[0]["issns"], ["12345678", "1234-5678"])
        self.assertEqual(groups[1]["issns"], ["8765-4321"])
        self.assertEqual(groups[0]["indexed_in"], {"Scopus"})
        self.assertEqual(groups[0]["country_codes"], ["BR"])

    def test_iter_harvest_metric_groups_merges_rows_for_same_issn_year(self):
        client = DummyOpenSearchClient(
            [
                {
                    "_source": {
                        "raw_data": {
                            "issns": "1234-5678",
                            "year": "2024",
                            "scopus_active_in_the_year": "1",
                            "wos_active_in_the_year": 0,
                            "scielo_active_and_valid_in_the_year": 0,
                            "country": "Brasil",
                        }
                    }
                },
                {
                    "_source": {
                        "raw_data": {
                            "issns": "12345678",
                            "year": "2024",
                            "scopus_active_in_the_year": 0,
                            "wos_active_in_the_year": "1",
                            "scielo_active_and_valid_in_the_year": 0,
                            "country": "Brasil",
                        }
                    }
                },
            ]
        )

        groups = list(
            iter_harvest_metric_groups(client, "global_metrics_upload_file", "metrics.csv")
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["year"], 2024)
        self.assertEqual(groups[0]["issns"], ["1234-5678", "12345678"])
        self.assertEqual(groups[0]["indexed_in"], {"Scopus", "WoS"})
        self.assertEqual(groups[0]["metric_rows"], 2)

    def test_iter_harvest_metric_groups_skips_rows_without_applicable_metrics(self):
        client = DummyOpenSearchClient(
            [
                {
                    "_source": {
                        "raw_data": {
                            "issns": "1234-5678",
                            "year": "2024",
                            "scopus_active_in_the_year": 0,
                            "wos_active_in_the_year": 0,
                            "scielo_active_and_valid_in_the_year": 0,
                            "country": "",
                        }
                    }
                }
            ]
        )

        groups = list(
            iter_harvest_metric_groups(client, "global_metrics_upload_file", "metrics.csv")
        )

        self.assertEqual(groups, [])

    def test_build_global_metrics_update_by_query_body_preserves_params(self):
        body = build_global_metrics_update_by_query_body(
            {
                "year": 2024,
                "issns": ["12345678", "1234-5678"],
                "indexed_in": {"WoS", "Scopus"},
                "country_codes": ["BR"],
                "countries": ["Brasil"],
            }
        )

        filters = body["query"]["bool"]["filter"]
        self.assertEqual(filters[0], {"term": {"publication_year": 2024}})
        self.assertEqual(filters[1], {"terms": {"source.issns": ["12345678", "1234-5678"]}})
        params = body["script"]["params"]
        self.assertEqual(params["indexed_in"], ["Scopus", "WoS"])
        self.assertEqual(params["country_codes"], ["BR"])
        self.assertEqual(params["world_region"], "South America")
        self.assertIn("oca_data.scielo.source", body["script"]["source"])

    def test_update_silver_group_by_query_does_not_wait_for_completion(self):
        client = MagicMock()
        client.update_by_query.return_value = {"task": "task-1"}

        response = update_silver_group_by_query(
            client=client,
            silver_index="silver_scientific_production",
            group={
                "year": 2024,
                "issns": ["1234-5678"],
                "indexed_in": {"Scopus"},
                "country_codes": ["BR"],
            },
        )

        self.assertEqual(response, {"task": "task-1"})
        kwargs = client.update_by_query.call_args.kwargs
        self.assertFalse(kwargs["wait_for_completion"])
        self.assertFalse(kwargs["refresh"])

    @patch("harvest.global_metrics.opensearch.time.sleep")
    def test_update_silver_group_by_query_retries_on_429(self, mock_sleep):
        from opensearchpy.exceptions import TransportError

        client = MagicMock()
        client.update_by_query.side_effect = [
            TransportError(429, "circuit_breaking_exception", "too large"),
            {"task": "task-2"},
        ]

        response = update_silver_group_by_query(
            client=client,
            silver_index="silver_scientific_production",
            group={
                "year": 2024,
                "issns": ["1234-5678"],
                "indexed_in": {"Scopus"},
                "country_codes": ["BR"],
            },
        )

        self.assertEqual(response, {"task": "task-2"})
        self.assertEqual(client.update_by_query.call_count, 2)
        mock_sleep.assert_called()

    @patch("harvest.global_metrics.opensearch.time.sleep")
    def test_wait_for_update_task_returns_completed_response(self, mock_sleep):
        client = MagicMock()
        client.tasks.get.side_effect = [
            {"completed": False},
            {
                "completed": True,
                "response": {"total": 3, "updated": 2},
            },
        ]

        response = wait_for_update_task(client, "t1", poll_interval=0.1)

        self.assertEqual(response, {"total": 3, "updated": 2})
        mock_sleep.assert_called_once_with(0.1)

    def test_wait_for_update_task_raises_when_task_is_missing(self):
        from opensearchpy.exceptions import NotFoundError

        client = MagicMock()
        client.tasks.get.side_effect = NotFoundError(404, "not found", {})

        with self.assertRaisesMessage(RuntimeError, "gone"):
            wait_for_update_task(client, "gone")

    def test_wait_for_update_task_raises_on_task_error(self):
        client = MagicMock()
        client.tasks.get.return_value = {
            "completed": True,
            "error": {"type": "circuit_breaking_exception"},
        }

        with self.assertRaisesMessage(
            RuntimeError,
            "circuit_breaking_exception",
        ):
            wait_for_update_task(client, "failed-task")

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
    def test_upload_error_index_failure_raises(
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

        with self.assertRaises(RuntimeError):
            index_prepared_rows(
                rows=iter([(2, {"baseid": "B123", "year": "2024"})]),
                file_name="metrics.csv",
                extension=".csv",
                index_name="global_metrics_upload_file",
                chunk_size=1,
            )

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
        self.last_index = None
        self.last_search_body = None

    def search(self, index, body, scroll):
        self.last_index = index
        self.last_search_body = body
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
        book = HarvestedBook.objects.create(
            identifier="oai:scielo:book:1",
            creator=self.user,
        )
        exc_context = ExceptionContext(
            harvest_object=book,
            log_model=HarvestErrorLogBook,
            fk_field="book",
        )
        exc_context.add_exception(
            exception=KeyError("missing field"),
            field_name="identifier",
        )
        exc_context.save_to_db()
        exc_context.verify_obj_as_failed()
        self.assertEqual(HarvestErrorLogBook.objects.count(), 1)
        log = HarvestErrorLogBook.objects.first()
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


class HarvestArticlesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="article-user", password="teste")
        self.identifier_item = {
            "code": "S0100-879X1998000800011",
            "collection": "scl",
            "doi": "10.1590/S0100-879X1998000800011",
            "processing_date": "1998-09-21",
        }
        self.article_payload = {
            "code": "S0100-879X1998000800011",
            "doi": "10.1590/S0100-879X1998000800011",
            "collection": "scl",
            "processing_date": "1998-09-21",
            "publication_year": "1998",
            "publication_date": "1998-08",
            "title": {
                "v100": [{"_": "Brazilian Journal of Medical and Biological Research"}],
                "v310": [{"_": "BR"}],
                "issns": ["1414-431X", "0100-879X"],
            },
            "article": {
                "v12": [{"l": "en", "_": "High dietary calcium decreases blood pressure"}],
                "v83": [{"l": "en", "a": "This study evaluates calcium."}],
                "v40": [{"_": "en"}],
                "v10": [{"n": "N.", "s": "Buassi", "_": ""}],
                "v31": [{"_": "31"}],
                "v32": [{"_": "8"}],
                "v14": [{"f": "1099", "_": ""}, {"l": "1101", "_": ""}],
                "v880": [{"_": "S0100-879X1998000800011"}],
                "v978": [{"l": "en", "k": "calcium carbonate", "_": ""}],
            },
        }

    @patch("harvest.harvesters.article.fetch_data")
    def test_fetch_article_identifiers_page_uses_incremental_params(self, mock_fetch_data):
        mock_fetch_data.return_value = {
            "objects": [self.identifier_item],
            "meta": {"offset": 10},
        }

        objects, meta = fetch_article_identifiers_page(
            limit=10,
            offset=20,
            from_date="2024-01-01",
            until_date="2024-01-31",
            collection="scl",
        )

        self.assertEqual(objects, [self.identifier_item])
        self.assertEqual(meta["offset"], 10)
        url = mock_fetch_data.call_args.args[0]
        self.assertIn("limit=10", url)
        self.assertIn("offset=20", url)
        self.assertIn("from=2024-01-01", url)
        self.assertIn("until=2024-01-31", url)
        self.assertIn("collection=scl", url)

    @patch("harvest.harvesters.article.transform_indexed_page")
    @patch("harvest.signals.index_harvested_instance")
    @patch("harvest.harvesters.article.fetch_article_detail")
    @patch("harvest.harvesters.article.fetch_article_identifiers_page")
    def test_harvest_articles_paginates_and_persists_success(
        self,
        mock_fetch_page,
        mock_fetch_detail,
        mock_index,
        mock_transform_page,
    ):
        mock_fetch_page.side_effect = [
            ([self.identifier_item], {}),
            ([], {}),
        ]
        mock_fetch_detail.return_value = self.article_payload

        def mark_indexed(instance, index_name=None, refresh=False):
            instance.index_status = "success"
            return True

        mock_index.side_effect = mark_indexed
        mock_transform_page.return_value = {"status": "success"}

        harvest_articles(user=self.user, limit=1, offset=0, from_date="1998-09-21")

        self.assertEqual(mock_fetch_page.call_count, 2)
        self.assertEqual(HarvestedArticle.objects.count(), 1)
        article = HarvestedArticle.objects.get(identifier="S0100-879X1998000800011")
        self.assertEqual(article.creator, self.user)
        self.assertEqual(article.harvest_status, "success")
        self.assertEqual(article.raw_data, self.article_payload)
        self.assertEqual(article.datestamp.date().isoformat(), "1998-09-21")
        mock_index.assert_called()
        mock_transform_page.assert_called_once_with(
            "HarvestedArticle",
            ["S0100-879X1998000800011"],
        )

    @patch("harvest.harvesters.article.transform_indexed_page")
    @patch("harvest.signals.index_harvested_instance")
    @patch("harvest.harvesters.article.fetch_article_detail")
    @patch("harvest.harvesters.article.fetch_article_identifiers_page")
    def test_harvest_articles_records_failed_article(
        self,
        mock_fetch_page,
        mock_fetch_detail,
        mock_index,
        mock_transform_page,
    ):
        mock_fetch_page.side_effect = [
            ([self.identifier_item], {}),
            ([], {}),
        ]
        mock_fetch_detail.return_value = {}

        harvest_articles(user=self.user, limit=1)

        article = HarvestedArticle.objects.get(identifier="S0100-879X1998000800011")
        self.assertEqual(article.harvest_status, "failed")
        self.assertEqual(HarvestErrorLogArticle.objects.count(), 1)
        self.assertEqual(article.harvest_error_log.first().field_name, "raw_data")
        mock_transform_page.assert_not_called()

    @patch("harvest.tasks.harvest_articles")
    def test_harvest_scielo_articles_uses_latest_datestamp_incrementally(self, mock_harvest_articles):
        HarvestedArticle.objects.create(
            identifier="S0100-879X1998000800011",
            creator=self.user,
            datestamp=timezone.make_aware(datetime(2024, 5, 2)),
        )

        from .tasks import harvest_scielo_articles

        harvest_scielo_articles(username=self.user.username, limit=10, offset=0)

        self.assertEqual(mock_harvest_articles.call_args.kwargs["from_date"], "2024-05-02")
        self.assertEqual(mock_harvest_articles.call_args.kwargs["limit"], 10)


class HarvestArticleIndexingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="indexing-user", password="teste")

    @override_settings(OS_INDEX_RAW_ARTICLE="raw_scielo_article_test")
    def test_get_index_name_supports_harvested_article(self):
        self.assertEqual(
            get_index_name(model_name="HarvestedArticle"),
            "raw_scielo_article_test",
        )

    @patch("harvest.harvesters.dataset._transform_batches_by_type")
    @patch("harvest.signals.index_harvested_instance")
    @patch("harvest.harvesters.dataset.fetch_dataverse_data")
    @patch("harvest.harvesters.dataset.fetch_search_page")
    def test_harvest_data_paginates_using_total_count(
        self, mock_fetch_search, mock_fetch_dataverse, mock_index, mock_transform_batches
    ):
        first_dataverse_item = {
            "type": "dataverse",
            "identifier": "dv-1",
            "name": "Dataverse Test",
        }
        second_dataverse_item = {
            "type": "dataverse",
            "identifier": "dv-2",
            "name": "Dataverse Test 2",
        }
        mock_fetch_search.side_effect = [
            ([first_dataverse_item, second_dataverse_item], 2),
            ([], 2),
        ]
        mock_fetch_dataverse.side_effect = [
            {"identifier": "dv-1"},
            {"identifier": "dv-2"},
        ]

        def mark_indexed(instance, index_name=None, refresh=False):
            instance.index_status = "success"
            return True

        mock_index.side_effect = mark_indexed

        harvest_data(
            user=self.user,
            type="dataverse",
            per_page=2,
            start=0,
        )

        self.assertEqual(HarvestedSciELOData.objects.count(), 2)
        dataverse_obj = HarvestedSciELOData.objects.get(identifier="dv-1")
        second_dataverse_obj = HarvestedSciELOData.objects.get(identifier="dv-2")
        self.assertEqual(dataverse_obj.raw_data["identifier"], "dv-1")
        self.assertEqual(second_dataverse_obj.raw_data["identifier"], "dv-2")
        mock_transform_batches.assert_called_once()
        self.assertEqual(mock_transform_batches.call_args.args[0], "HarvestedSciELOData")
        self.assertEqual(
            mock_transform_batches.call_args.args[1]["dataverse"],
            ["dv-1", "dv-2"],
        )


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


class ArticleBronzeTransformTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="bronze-article-user", password="teste")
        self.identifier = "S0100-879X1998000800011"
        self.source_index = "raw_scielo_article_test"
        self.dest_index = "bronze_scielo_articles_test"
        self.transform_script = "ctx._source = ctx._source.raw_data;"

        with patch("harvest.signals.index_harvested_instance"):
            self.article = HarvestedArticle.objects.create(
                identifier=self.identifier,
                creator=self.user,
                harvest_status="success",
                index_status="success",
                raw_data={
                    "code": self.identifier,
                    "processing_date": "1998-09-21",
                    "article": {"v12": [{"l": "en", "_": "Title"}]},
                },
            )

        self.script = TransformationScript.objects.create(
            name="ArticleMeta raw para bronze",
            source_index=self.source_index,
            dest_index=self.dest_index,
            transform_script=self.transform_script,
            harvest_model=HarvestModelChoice.ARTICLE,
            is_active=True,
            creator=self.user,
        )

    def test_build_reindex_body_uses_ids_query_for_identifier(self):
        body = _build_reindex_body(
            source_index=self.source_index,
            dest_index=self.dest_index,
            transform_script=self.transform_script,
            identifiers=[self.identifier],
        )

        self.assertEqual(body["source"]["index"], self.source_index)
        self.assertEqual(body["dest"]["index"], self.dest_index)
        self.assertEqual(body["script"]["source"], self.transform_script)
        self.assertEqual(
            body["source"]["query"],
            {"ids": {"values": [self.identifier]}},
        )

    def test_build_reindex_body_uses_ids_query_for_identifiers_page(self):
        identifiers = [self.identifier, "S0100-879X1998000800012"]
        body = _build_reindex_body(
            source_index=self.source_index,
            dest_index=self.dest_index,
            transform_script=self.transform_script,
            identifiers=identifiers,
        )

        self.assertEqual(
            body["source"]["query"],
            {"ids": {"values": identifiers}},
        )

    def test_build_reindex_body_has_no_query_by_default(self):
        body = _build_reindex_body(
            source_index=self.source_index,
            dest_index=self.dest_index,
            transform_script=self.transform_script,
        )

        self.assertEqual(body["source"]["index"], self.source_index)
        self.assertEqual(body["dest"]["index"], self.dest_index)
        self.assertNotIn("query", body["source"])

    def test_transform_documents_page_skips_empty_identifiers(self):
        result = transform_documents_page(self.script, [])

        self.assertEqual(result["status"], "skip")
        self.assertIn("Nenhum identifier", result["error"])

    @patch("harvest.bronze_transform._enqueue_transformed_bronze")
    @patch("harvest.bronze_transform.client")
    def test_transform_documents_page_refreshes_once_and_reindexes_ids(
        self,
        mock_client,
        mock_enqueue,
    ):
        identifiers = [self.identifier, "S0100-879X1998000800012"]
        mock_client.indices.exists.return_value = True
        mock_client.reindex.return_value = {
            "total": 2,
            "created": 2,
            "updated": 0,
        }
        mock_enqueue.return_value = True

        result = transform_documents_page(self.script, identifiers)

        mock_client.indices.refresh.assert_called_once_with(index=self.source_index)
        mock_client.reindex.assert_called_once()
        self.assertNotIn("refresh", mock_client.reindex.call_args.kwargs)
        body = mock_client.reindex.call_args.kwargs["body"]
        self.assertEqual(
            body["source"]["query"],
            {"ids": {"values": identifiers}},
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["enqueued"], 2)
        self.assertEqual(mock_enqueue.call_count, 2)

    @patch("harvest.bronze_transform._enqueue_transformed_bronze")
    @patch("harvest.bronze_transform.client")
    def test_transform_documents_page_errors_when_total_is_zero(
        self,
        mock_client,
        mock_enqueue,
    ):
        mock_client.indices.exists.return_value = True
        mock_client.reindex.return_value = {
            "total": 0,
            "created": 0,
            "updated": 0,
        }

        result = transform_documents_page(self.script, [self.identifier])

        self.assertEqual(result["status"], "error")
        self.assertIn("Nenhum documento encontrado", result["error"])
        mock_enqueue.assert_not_called()

    @patch("harvest.bronze_transform._enqueue_transformed_bronze")
    @patch("harvest.bronze_transform.client")
    def test_transform_documents_page_reindexes_single_id_and_enqueues_silver(
        self,
        mock_client,
        mock_enqueue,
    ):
        mock_client.indices.exists.return_value = True
        mock_client.reindex.return_value = {
            "total": 1,
            "created": 1,
            "updated": 0,
        }
        mock_enqueue.return_value = True

        result = transform_documents_page(self.script, [self.identifier])

        mock_client.indices.refresh.assert_called_once_with(index=self.source_index)
        mock_client.reindex.assert_called_once()
        self.assertNotIn("refresh", mock_client.reindex.call_args.kwargs)
        body = mock_client.reindex.call_args.kwargs["body"]
        self.assertEqual(body["source"]["index"], self.source_index)
        self.assertEqual(body["dest"]["index"], self.dest_index)
        self.assertEqual(
            body["source"]["query"],
            {"ids": {"values": [self.identifier]}},
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["index"], self.source_index)
        self.assertEqual(result["dest"], self.dest_index)
        self.assertIsNone(result["error"])
        mock_enqueue.assert_called_once_with(self.dest_index, self.identifier)

    @patch("harvest.bronze_transform.client")
    def test_transform_documents_batch_reindexes_without_ids_query(self, mock_client):
        mock_client.indices.exists.return_value = True
        mock_client.reindex.return_value = {
            "total": 2,
            "created": 2,
            "updated": 0,
        }

        result = transform_documents_batch(self.script)

        mock_client.reindex.assert_called_once()
        self.assertNotIn("refresh", mock_client.reindex.call_args.kwargs)
        mock_client.indices.refresh.assert_not_called()
        body = mock_client.reindex.call_args.kwargs["body"]
        self.assertEqual(body["source"]["index"], self.source_index)
        self.assertEqual(body["dest"]["index"], self.dest_index)
        self.assertNotIn("query", body["source"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["created"], 2)
        self.assertEqual(result["index"], self.source_index)
        self.assertEqual(result["dest"], self.dest_index)

    @patch("harvest.bronze_transform.transform_documents_page")
    def test_transform_indexed_page_uses_article_script(self, mock_transform_page):
        mock_transform_page.return_value = {"status": "success"}

        result = transform_indexed_page(
            "HarvestedArticle",
            [self.identifier],
        )

        mock_transform_page.assert_called_once_with(self.script, [self.identifier])
        self.assertEqual(result["status"], "success")

    def test_transform_indexed_page_returns_none_without_script(self):
        self.script.is_active = False
        self.script.save(update_fields=["is_active"])

        result = transform_indexed_page("HarvestedArticle", [self.identifier])

        self.assertIsNone(result)

    def test_transform_indexed_page_returns_none_for_empty_identifiers(self):
        self.assertIsNone(transform_indexed_page("HarvestedArticle", []))

    @patch("harvest.bronze_transform.transform_documents_page")
    def test_transform_indexed_page_logs_error_on_failure(self, mock_transform_page):
        mock_transform_page.return_value = {
            "status": "error",
            "error": "boom",
        }

        with self.assertLogs("harvest.bronze_transform", level="ERROR") as logs:
            result = transform_indexed_page("HarvestedArticle", [self.identifier])

        self.assertEqual(result["status"], "error")
        self.assertTrue(any("boom" in line for line in logs.output))

    @patch("harvest.bronze_transform.client")
    def test_refresh_source_for_page_returns_error_on_failure(self, mock_client):
        mock_client.indices.refresh.side_effect = RuntimeError("refresh failed")

        result = _refresh_source_for_page(self.script, [self.identifier])

        self.assertEqual(result["status"], "error")
        self.assertIn("refresh", result["error"].lower())

    @patch("harvest.bronze_transform.client")
    def test_refresh_source_for_page_returns_none_on_success(self, mock_client):
        result = _refresh_source_for_page(self.script, [self.identifier])

        mock_client.indices.refresh.assert_called_once_with(index=self.source_index)
        self.assertIsNone(result)

    @patch("harvest.bronze_transform.client")
    def test_reindex_page_errors_when_total_is_zero(self, mock_client):
        mock_client.indices.exists.return_value = True
        mock_client.reindex.return_value = {
            "total": 0,
            "created": 0,
            "updated": 0,
        }

        result = _reindex_page(self.script, [self.identifier])

        self.assertEqual(result["status"], "error")
        self.assertIn("Nenhum documento encontrado", result["error"])

    @patch("harvest.bronze_transform.transform_indexed_page")
    def test_reconcile_missing_bronze_etl_transforms_in_pages(self, mock_transform_page):
        from .bronze_transform import reconcile_missing_bronze_etl

        mock_transform_page.return_value = {"status": "success"}
        with patch("harvest.signals.index_harvested_instance"):
            HarvestedArticle.objects.create(
                identifier="S0100-879X1998000800012",
                creator=self.user,
                harvest_status="success",
                index_status="success",
                raw_data={"code": "S0100-879X1998000800012"},
            )
            HarvestedArticle.objects.create(
                identifier="S0100-879X1998000800013",
                creator=self.user,
                harvest_status="success",
                index_status="success",
                raw_data={"code": "S0100-879X1998000800013"},
            )

        reconcile_missing_bronze_etl(HarvestedArticle, page_size=2)

        self.assertEqual(mock_transform_page.call_count, 2)
        all_ids = []
        for call in mock_transform_page.call_args_list:
            self.assertEqual(call.args[0], "HarvestedArticle")
            self.assertLessEqual(len(call.args[1]), 2)
            all_ids.extend(call.args[1])
        self.assertCountEqual(
            all_ids,
            [
                self.identifier,
                "S0100-879X1998000800012",
                "S0100-879X1998000800013",
            ],
        )

    @patch("harvest.bronze_transform.transform_indexed_page")
    def test_reconcile_missing_bronze_etl_exits_when_empty(self, mock_transform_page):
        from .bronze_transform import reconcile_missing_bronze_etl
        from etl.models import EtlItemProcess

        EtlItemProcess.objects.create(
            source_index=self.dest_index,
            external_id=self.identifier,
            document_type="article",
        )

        reconcile_missing_bronze_etl(HarvestedArticle, page_size=2)

        mock_transform_page.assert_not_called()

    @patch("harvest.bronze_transform.transform_indexed_page")
    @patch("harvest.signals.index_harvested_instance", return_value=True)
    def test_signal_indexes_raw_without_transform(
        self,
        mock_index,
        mock_transform_page,
    ):
        HarvestedArticle.objects.create(
            identifier="S0100-879X1998000800099",
            creator=self.user,
            harvest_status="success",
            raw_data={"code": "S0100-879X1998000800099"},
        )

        mock_index.assert_called()
        mock_transform_page.assert_not_called()


def _gzip_jsonl(records):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as gz_file:
        for record in records:
            gz_file.write((json.dumps(record) + "\n").encode("utf-8"))
    return buffer.getvalue()


def _mock_fetch_payloads(mock_fetch_data, manifest, part_payload):
    def fake_fetch(url, headers=None, json=False, timeout=2, verify=True):
        if json:
            return manifest
        return part_payload

    mock_fetch_data.side_effect = fake_fetch


class HarvestOpenAlexSnapshotTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="openalex-user", password="test")
        client_patcher = patch("harvest.harvesters.openalex.OpenSearchClient")
        self.addCleanup(client_patcher.stop)
        self.mock_client_class = client_patcher.start()
        self.open_search = self.mock_client_class.return_value
        self.open_search.client.search.return_value = {"hits": {"hits": []}}
        self.open_search.client.bulk.return_value = {"errors": False, "items": []}
        self.manifest_url = (
            "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
        )
        self.old_part_s3 = (
            "s3://openalex/data/jsonl/works/updated_date=2026-02-01/part_0000.gz"
        )
        self.part_s3 = (
            "s3://openalex/data/jsonl/works/updated_date=2026-03-01/part_0000.gz"
        )
        self.part_https = (
            "https://openalex.s3.amazonaws.com/data/jsonl/works/"
            "updated_date=2026-03-01/part_0000.gz"
        )
        self.later_part_s3 = (
            "s3://openalex/data/jsonl/works/updated_date=2026-03-02/part_0000.gz"
        )
        self.later_part_https = (
            "https://openalex.s3.amazonaws.com/data/jsonl/works/"
            "updated_date=2026-03-02/part_0000.gz"
        )
        self.manifest = {
            "date": "2026-06-25",
            "format": "jsonl",
            "entity": "works",
            "files": [
                {
                    "url": self.old_part_s3,
                    "meta": {"record_count": 10, "content_length": 100},
                },
                {
                    "url": self.part_s3,
                    "meta": {"record_count": 2, "content_length": 200},
                },
                {
                    "url": self.later_part_s3,
                    "meta": {"record_count": 1, "content_length": 50},
                },
            ],
        }

    def test_s3_url_to_https(self):
        self.assertEqual(s3_url_to_https(self.part_s3), self.part_https)

    def test_parse_updated_date_from_url(self):
        parsed = parse_updated_date_from_url(self.part_s3)
        self.assertEqual(parsed.isoformat(), "2026-03-01")

    def test_iter_part_files_keeps_partitions_from_updated_date(self):
        parts = iter_part_files(self.manifest, "2026-03-01")
        urls = [item["https_url"] for item in parts]
        self.assertEqual(urls, [self.part_https, self.later_part_https])
        self.assertTrue(all(item["s3_url"].startswith("s3://") for item in parts))

    def test_iter_gzip_jsonl_works_filters_publication_year(self):
        payload = _gzip_jsonl(
            [
                {
                    "id": "https://openalex.org/W1",
                    "publication_year": 2017,
                    "is_xpac": False,
                },
                {
                    "id": "https://openalex.org/W2",
                    "publication_year": 2019,
                    "is_xpac": False,
                },
                {
                    "id": "https://openalex.org/W3",
                    "publication_year": 2020,
                },
            ]
        )

        ids = [
            work["id"]
            for work in iter_gzip_jsonl_works(
                io.BytesIO(payload),
                publication_year_from=2018,
                is_xpac=False,
            )
        ]

        self.assertEqual(ids, ["https://openalex.org/W2", "https://openalex.org/W3"])

    def test_iter_gzip_jsonl_works_skips_null_publication_year(self):
        payload = _gzip_jsonl(
            [
                {
                    "id": "https://openalex.org/W1",
                    "publication_year": None,
                },
                {
                    "id": "https://openalex.org/W2",
                    "publication_year": 2020,
                },
            ]
        )

        ids = [
            work["id"]
            for work in iter_gzip_jsonl_works(
                io.BytesIO(payload),
                publication_year_from=2018,
                is_xpac=False,
            )
        ]

        self.assertEqual(ids, ["https://openalex.org/W2"])

    def test_iter_gzip_jsonl_works_keeps_missing_is_xpac_when_filter_is_false(self):
        payload = _gzip_jsonl(
            [
                {
                    "id": "https://openalex.org/W1",
                    "publication_year": 2020,
                    "is_xpac": False,
                },
                {
                    "id": "https://openalex.org/W2",
                    "publication_year": 2020,
                    "is_xpac": True,
                },
                {
                    "id": "https://openalex.org/W3",
                    "publication_year": 2020,
                },
            ]
        )

        ids = [
            work["id"]
            for work in iter_gzip_jsonl_works(
                io.BytesIO(payload),
                publication_year_from=2018,
                is_xpac=False,
            )
        ]

        self.assertEqual(ids, ["https://openalex.org/W1", "https://openalex.org/W3"])

    def test_iter_gzip_jsonl_works_filters_is_xpac_true(self):
        payload = _gzip_jsonl(
            [
                {
                    "id": "https://openalex.org/W1",
                    "publication_year": 2020,
                    "is_xpac": False,
                },
                {
                    "id": "https://openalex.org/W2",
                    "publication_year": 2020,
                    "is_xpac": True,
                },
            ]
        )

        ids = [
            work["id"]
            for work in iter_gzip_jsonl_works(
                io.BytesIO(payload),
                publication_year_from=2018,
                is_xpac=True,
            )
        ]

        self.assertEqual(ids, ["https://openalex.org/W2"])

    @patch("harvest.harvesters.openalex.fetch_data")
    def test_iter_part_works_fetches_gzip_payload(self, mock_fetch_data):
        payload = _gzip_jsonl(
            [{"id": "https://openalex.org/W2", "publication_year": 2020}]
        )
        mock_fetch_data.return_value = payload

        ids = [
            work["id"]
            for work in iter_part_works(
                self.part_https,
                publication_year_from=2018,
                is_xpac=False,
            )
        ]

        self.assertEqual(ids, ["https://openalex.org/W2"])
        mock_fetch_data.assert_called_once()
        self.assertEqual(mock_fetch_data.call_args.args[0], self.part_https)
        self.assertFalse(mock_fetch_data.call_args.kwargs["json"])

    @override_settings(
        OPENALEX_WORKS_MANIFEST_URL=(
            "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
        )
    )
    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_indexes_filtered_works_without_persisting_ids(
        self,
        mock_fetch_data,
    ):
        gzip_payload = _gzip_jsonl(
            [
                {
                    "id": "https://openalex.org/W1",
                    "publication_year": 2017,
                    "title": "should not be stored",
                },
                {
                    "id": "https://openalex.org/W2",
                    "publication_year": 2019,
                    "title": "should not be stored either",
                    "authorships": [
                        {
                            "author": {"display_name": "Author"},
                            "institutions": [
                                {
                                    "display_name": "Universidade",
                                    "country_code": "BR",
                                }
                            ],
                        }
                    ],
                },
            ]
        )
        _mock_fetch_payloads(
            mock_fetch_data,
            {
                "date": "2026-06-25",
                "files": [
                    {
                        "url": self.part_s3,
                        "meta": {"record_count": 2},
                    }
                ],
            },
            gzip_payload,
        )

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
        )

        manifest_row = OpenAlexHarvestRequest.objects.get(request_kind="manifest")
        self.assertEqual(manifest_row.harvest_status, "success")
        self.assertEqual(manifest_row.updated_date.isoformat(), "2026-06-25")
        self.assertEqual(manifest_row.request_url, self.manifest_url)

        part_row = OpenAlexHarvestRequest.objects.get(request_kind="part")
        self.assertEqual(part_row.harvest_status, "success")
        self.assertEqual(part_row.index_status, "success")
        self.assertEqual(part_row.request_url, self.part_https)
        self.assertEqual(part_row.document_ids, [])
        self.assertEqual(part_row.result_count, 1)
        self.assertEqual(part_row.manifest_record_count, 2)
        self.assertEqual(part_row.updated_date.isoformat(), "2026-03-01")
        self.assertFalse(hasattr(part_row, "raw_data") and part_row.raw_data)
        self.open_search.ensure_rollover_index.assert_called_once()
        bulk_body = self.open_search.client.bulk.call_args.kwargs["body"]
        self.assertEqual(
            bulk_body[0]["index"]["_index"],
            "silver_openalex_write",
        )
        self.assertEqual(
            bulk_body[0]["index"]["_id"],
            "https://openalex.org/W2",
        )
        self.assertEqual(
            bulk_body[1]["oca_data"]["openalex"]["affiliations"]["world_regions"],
            ["South America"],
        )
        self.open_search.rollover.assert_called_once()

    def test_index_openalex_batch_indexes_by_openalex_id_on_write_alias(self):
        openalex_id = "https://openalex.org/W2"

        indexed = index_openalex_batch(
            self.open_search,
            [(openalex_id, {"ids": {"openalex": openalex_id}})],
        )

        bulk_body = self.open_search.client.bulk.call_args.kwargs["body"]
        self.assertEqual(
            bulk_body[0]["index"],
            {
                "_index": "silver_openalex_write",
                "_id": openalex_id,
            },
        )
        self.assertEqual(indexed, 1)
        self.open_search.client.search.assert_not_called()

    @patch("harvest.harvesters.openalex.add_affiliation_world_regions")
    @patch("harvest.harvesters.openalex.add_source_world_region")
    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_applies_standardization_and_region_steps_in_order(
        self,
        mock_fetch_data,
        mock_add_source_region,
        mock_add_affiliation_regions,
    ):
        gzip_payload = _gzip_jsonl(
            [
                {
                    "id": "https://openalex.org/W2",
                    "publication_year": 2020,
                }
            ]
        )
        _mock_fetch_payloads(
            mock_fetch_data,
            {
                "date": "2026-06-25",
                "files": [
                    {
                        "url": self.part_s3,
                        "meta": {"record_count": 1},
                    }
                ],
            },
            gzip_payload,
        )

        call_order = []
        mock_add_source_region.side_effect = lambda source: call_order.append("source")
        mock_add_affiliation_regions.side_effect = lambda source: call_order.append(
            "affiliations"
        )

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
            is_xpac=False,
        )

        indexed_source = self.open_search.client.bulk.call_args.kwargs["body"][1]
        self.assertEqual(
            indexed_source["ids"]["openalex"],
            "https://openalex.org/W2",
        )
        self.assertEqual(call_order, ["source", "affiliations"])

    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_marks_part_failed_when_bulk_indexing_fails(
        self,
        mock_fetch_data,
    ):
        gzip_payload = _gzip_jsonl(
            [
                {
                    "id": "https://openalex.org/W2",
                    "publication_year": 2020,
                }
            ]
        )
        _mock_fetch_payloads(mock_fetch_data, self.manifest, gzip_payload)
        self.open_search.client.bulk.return_value = {
            "errors": True,
            "items": [
                {
                    "index": {
                        "status": 500,
                        "error": {"type": "index_error"},
                    }
                }
            ],
        }

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
            is_xpac=False,
        )

        part = OpenAlexHarvestRequest.objects.get(request_kind="part")
        manifest = OpenAlexHarvestRequest.objects.get(request_kind="manifest")
        self.assertEqual(part.harvest_status, "failed")
        self.assertEqual(part.index_status, "failed")
        self.assertEqual(manifest.harvest_status, "failed")
        self.assertEqual(part.document_ids, [])
        self.assertIn(
            "Falha ao indexar",
            HarvestErrorLogOpenAlex.objects.get().exception_message,
        )

    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_skips_invalid_work_and_continues(
        self,
        mock_fetch_data,
    ):
        gzip_payload = _gzip_jsonl(
            [
                {
                    "publication_year": 2020,
                },
                {
                    "id": "https://openalex.org/W2",
                    "publication_year": 2020,
                },
            ]
        )
        _mock_fetch_payloads(
            mock_fetch_data,
            {
                "date": "2026-06-25",
                "files": [
                    {
                        "url": self.part_s3,
                        "meta": {"record_count": 2},
                    }
                ],
            },
            gzip_payload,
        )

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
            is_xpac=False,
        )

        part = OpenAlexHarvestRequest.objects.get(request_kind="part")
        self.assertEqual(part.harvest_status, "success")
        self.assertEqual(part.index_status, "success")
        self.assertEqual(part.result_count, 1)
        self.assertEqual(
            self.open_search.client.bulk.call_args.kwargs["body"][0]["index"]["_id"],
            "https://openalex.org/W2",
        )

    @override_settings(
        OPENALEX_WORKS_MANIFEST_URL=(
            "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
        )
    )
    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_skips_parts_already_successful(self, mock_fetch_data):
        OpenAlexHarvestRequest.objects.create(
            creator=self.user,
            request_url=self.part_https,
            request_kind="part",
            harvest_status="success",
            requested_at=timezone.now(),
        )

        def fake_fetch(url, headers=None, json=False, timeout=2, verify=True):
            if json:
                return {
                    "date": "2026-06-25",
                    "files": [
                        {
                            "url": self.part_s3,
                            "meta": {"record_count": 2},
                        }
                    ]
                }
            raise AssertionError("Part already harvested should not be fetched.")

        mock_fetch_data.side_effect = fake_fetch

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
        )

        self.assertEqual(
            OpenAlexHarvestRequest.objects.filter(request_kind="part").count(),
            1,
        )
        mock_fetch_data.assert_called_once()

    @override_settings(
        OPENALEX_WORKS_MANIFEST_URL=(
            "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
        )
    )
    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_does_not_process_registered_manifest(self, mock_fetch_data):
        OpenAlexHarvestRequest.objects.create(
            creator=self.user,
            request_url=self.manifest_url,
            request_kind="manifest",
            updated_date=datetime(2026, 6, 25).date(),
            publication_year_from=2018,
            harvest_status="success",
            requested_at=timezone.now(),
        )
        mock_fetch_data.return_value = self.manifest

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
        )

        self.assertEqual(
            OpenAlexHarvestRequest.objects.filter(request_kind="manifest").count(),
            1,
        )
        self.assertFalse(
            OpenAlexHarvestRequest.objects.filter(request_kind="part").exists()
        )
        mock_fetch_data.assert_called_once()

    @override_settings(
        OPENALEX_WORKS_MANIFEST_URL=(
            "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
        )
    )
    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_stops_on_part_failure(self, mock_fetch_data):
        def fake_fetch(url, headers=None, json=False, timeout=2, verify=True):
            if json:
                return self.manifest
            raise RuntimeError("S3 timeout")

        mock_fetch_data.side_effect = fake_fetch

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
        )

        part_rows = OpenAlexHarvestRequest.objects.filter(request_kind="part")
        self.assertEqual(part_rows.count(), 1)
        failed = part_rows.get()
        self.assertEqual(failed.harvest_status, "failed")
        self.assertEqual(failed.index_status, "pending")
        log = HarvestErrorLogOpenAlex.objects.get()
        self.assertIn("S3 timeout", log.exception_message)
        self.assertEqual(log.field_name, "part")
        self.assertEqual(failed.request_url, self.part_https)
        self.assertEqual(
            OpenAlexHarvestRequest.objects.get(
                request_kind="manifest"
            ).harvest_status,
            "failed",
        )

    @override_settings(
        OPENALEX_WORKS_MANIFEST_URL=(
            "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
        ),
    )
    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_collects_unregistered_parts_since_initial_date(
        self,
        mock_fetch_data,
    ):
        OpenAlexHarvestRequest.objects.create(
            creator=self.user,
            request_url=self.later_part_https,
            request_kind="part",
            updated_date=datetime(2026, 3, 2).date(),
            publication_year_from=2018,
            harvest_status="success",
            requested_at=timezone.now(),
        )
        _mock_fetch_payloads(
            mock_fetch_data,
            self.manifest,
            _gzip_jsonl(
                [{"id": "https://openalex.org/W3", "publication_year": 2020}]
            ),
        )

        harvest_openalex_works(
            user=self.user,
            publication_year_from=2018,
            from_updated_date="2026-03-01",
        )

        collected_urls = list(
            OpenAlexHarvestRequest.objects.filter(
                request_kind="part",
                request_url=self.part_https,
            ).values_list("request_url", flat=True)
        )
        self.assertEqual(collected_urls, [self.part_https])
        self.assertEqual(
            OpenAlexHarvestRequest.objects.filter(
                request_url=self.later_part_https,
            ).count(),
            1,
        )
        self.assertEqual(
            OpenAlexHarvestRequest.objects.get(
                request_kind="manifest"
            ).harvest_status,
            "success",
        )

    @override_settings(
        OPENALEX_WORKS_MANIFEST_URL=(
            "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
        )
    )
    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_reuses_failed_part_record(
        self,
        mock_fetch_data,
    ):
        existing = OpenAlexHarvestRequest.objects.create(
            creator=self.user,
            request_url=self.part_https,
            request_kind="part",
            updated_date=datetime(2026, 3, 1).date(),
            publication_year_from=2018,
            harvest_status="failed",
            index_status="failed",
            requested_at=timezone.now(),
        )
        _mock_fetch_payloads(
            mock_fetch_data,
            {
                "date": "2026-06-25",
                "files": [
                    {
                        "url": self.part_s3,
                        "meta": {"record_count": 2},
                    }
                ]
            },
            _gzip_jsonl(
                [
                    {
                        "id": "https://openalex.org/W2",
                        "publication_year": 2020,
                    }
                ]
            ),
        )

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
            is_xpac=False,
        )

        part_rows = OpenAlexHarvestRequest.objects.filter(request_kind="part")
        self.assertEqual(part_rows.count(), 1)
        reused = part_rows.get()
        self.assertEqual(reused.pk, existing.pk)
        self.assertEqual(reused.harvest_status, "success")
        self.assertEqual(reused.index_status, "success")
        self.assertEqual(reused.result_count, 1)
        self.assertEqual(reused.document_ids, [])

    @override_settings(
        OPENALEX_WORKS_MANIFEST_URL=(
            "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
        )
    )
    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_reuses_incomplete_manifest(
        self,
        mock_fetch_data,
    ):
        existing = OpenAlexHarvestRequest.objects.create(
            creator=self.user,
            request_url=self.manifest_url,
            request_kind="manifest",
            updated_date=datetime(2026, 6, 25).date(),
            publication_year_from=2018,
            harvest_status="in_progress",
            requested_at=timezone.now(),
        )
        _mock_fetch_payloads(
            mock_fetch_data,
            {
                "date": "2026-06-25",
                "files": [
                    {
                        "url": self.part_s3,
                        "meta": {"record_count": 1},
                    }
                ]
            },
            _gzip_jsonl(
                [{"id": "https://openalex.org/W2", "publication_year": 2020}]
            ),
        )

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
        )

        manifests = OpenAlexHarvestRequest.objects.filter(request_kind="manifest")
        self.assertEqual(manifests.count(), 1)
        reused = manifests.get()
        self.assertEqual(reused.pk, existing.pk)
        self.assertEqual(reused.harvest_status, "success")

    @patch("harvest.harvesters.openalex.fetch_data")
    def test_harvest_rollover_once_per_part_not_per_batch(
        self,
        mock_fetch_data,
    ):
        _mock_fetch_payloads(
            mock_fetch_data,
            {
                "date": "2026-06-25",
                "files": [
                    {
                        "url": self.part_s3,
                        "meta": {"record_count": 2},
                    }
                ]
            },
            _gzip_jsonl(
                [
                    {"id": "https://openalex.org/W1", "publication_year": 2020},
                    {"id": "https://openalex.org/W2", "publication_year": 2020},
                ]
            ),
        )

        harvest_openalex_works(
            user=self.user,
            from_updated_date="2026-03-01",
            publication_year_from=2018,
            batch_size=1,
        )

        self.assertEqual(self.open_search.client.bulk.call_count, 2)
        self.open_search.rollover.assert_called_once()
        self.open_search.ensure_rollover_index.assert_called_once()

    @patch("harvest.tasks.harvest_openalex_works")
    def test_task_delegates_manifest_scan_to_harvester(self, mock_harvest):
        from harvest.tasks import harvest_openalex_works_task

        harvest_openalex_works_task(
            username=self.user.username,
            publication_year_from=2018,
            from_updated_date="2026-03-01",
            batch_size=50,
        )

        self.assertEqual(mock_harvest.call_args.kwargs["publication_year_from"], 2018)
        self.assertEqual(
            mock_harvest.call_args.kwargs["from_updated_date"],
            "2026-03-01",
        )
        self.assertEqual(mock_harvest.call_args.kwargs["is_xpac"], False)
        self.assertEqual(mock_harvest.call_args.kwargs["batch_size"], 50)
        self.assertEqual(mock_harvest.call_args.kwargs["user"], self.user)
