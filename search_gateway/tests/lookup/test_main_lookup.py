from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from search_gateway.lookup import (
    LOOKUP_BUILDERS,
    InstitutionLookupBuilder,
    LookupBuilder,
    PublisherLookupBuilder,
    SourceLookupBuilder,
)
from search_gateway.lookup.base import LookupIndexBuildService
from search_gateway.models import ResolvedField
from search_gateway.query import build_lookup_hits_body
from search_gateway.response_parser import parse_lookup_hits
from search_gateway.service import SearchGatewayService


class LookupBuilderTests(SimpleTestCase):
    @override_settings(SEARCH_GATEWAY_LOOKUP_NUMBER_OF_SHARDS=7)
    def test_lookup_mapping_uses_shards_from_settings(self):
        mapping = LookupBuilder().mapping

        self.assertEqual(mapping["settings"]["index"]["number_of_shards"], 7)

    def test_publisher_accepts_missing_id_and_counts_once_per_document(self):
        builder = PublisherLookupBuilder()
        source = {
            "source": [{"type": "journal"}],
            "publishers": [
                {"name": "SciELO"},
                {"name": "SciELO"},
            ],
        }

        builder.collect(source)
        builder.collect({"source": {"type": "journal"}, "publishers": [{"name": "SciELO"}]})

        actions = list(builder.iter_actions("lookup_publisher"))

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["_source"]["value"], "SciELO")
        self.assertEqual(actions[0]["_source"]["label"], "SciELO")
        self.assertEqual(actions[0]["_source"]["size"], 2)

    def test_publisher_uses_name_as_value_even_when_id_exists(self):
        builder = PublisherLookupBuilder()
        builder.collect(
            {
                "source": [{"type": "journal"}],
                "publishers": [{"id": "https://openalex.org/P1", "name": "Elsevier BV"}],
            }
        )

        action = list(builder.iter_actions("lookup_publisher"))[0]

        self.assertEqual(action["_source"]["value"], "Elsevier BV")
        self.assertEqual(action["_source"]["publisher_id"], "https://openalex.org/P1")

    def test_institution_accepts_missing_id_and_sources_object_shape(self):
        builder = InstitutionLookupBuilder()
        builder.collect(
            {
                "authorships": [
                    {
                        "institutions": [
                            {"name": "Universidade de Sao Paulo", "country_code": "BR"},
                            {"name": "Universidade de Sao Paulo", "country_code": "BR"},
                        ]
                    }
                ]
            }
        )

        actions = list(builder.iter_actions("lookup_institution"))

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["_source"]["value"], "Universidade de Sao Paulo")
        self.assertEqual(actions[0]["_source"]["country_codes"], ["BR"])
        self.assertEqual(actions[0]["_source"]["size"], 1)

    def test_institution_uses_name_as_value_even_when_id_exists(self):
        builder = InstitutionLookupBuilder()
        builder.collect(
            {
                "authorships": [
                    {
                        "institutions": [
                            {"id": "https://openalex.org/I1", "name": "University of Toronto"},
                        ]
                    }
                ]
            }
        )

        action = list(builder.iter_actions("lookup_institution"))[0]

        self.assertEqual(action["_source"]["value"], "University of Toronto")
        self.assertEqual(action["_source"]["institution_id"], "https://openalex.org/I1")

    def test_source_accepts_sources_as_list_or_object(self):
        builder = SourceLookupBuilder()
        builder.collect({"source": {"ids": {"openalex": "j1"}, "title": "Journal One", "type": "journal"}})
        builder.collect({"source": [{"ids": {"openalex": "j1"}, "title": "Journal One", "type": "journal"}]})

        actions = list(builder.iter_actions("lookup_source"))

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["_source"]["value"], "j1")
        self.assertEqual(actions[0]["_source"]["label"], "Journal One")
        self.assertEqual(actions[0]["_source"]["size"], 2)


class LookupQueryTests(SimpleTestCase):
    def test_lookup_sort_by_size_is_desc(self):
        body = build_lookup_hits_body(sort_field="size")

        self.assertEqual(body["sort"], [{"size": {"order": "desc", "unmapped_type": "long"}}])

    def test_lookup_sort_by_label_is_asc(self):
        body = build_lookup_hits_body(sort_field="label")

        self.assertEqual(body["sort"], [{"label": {"order": "asc", "unmapped_type": "keyword"}}])

    def test_parse_lookup_hits_returns_size(self):
        response = {
            "hits": {
                "hits": [
                    {"_source": {"value": "abc", "label": "ABC", "size": 12}},
                ]
            }
        }
        lookup_config = {
            "source_value_field": "value",
            "source_label_field": "label",
        }

        self.assertEqual(parse_lookup_hits(response, lookup_config), [{"value": "abc", "label": "ABC", "size": 12}])


class LookupServiceTests(SimpleTestCase):
    def test_lookup_options_fallback_returns_empty_options_on_error(self):
        service = SearchGatewayService(index_name="scientific_production", client=Mock())
        field = ResolvedField(
            "publisher",
            {
                "lookup": {
                    "index_name": "lookup_publisher",
                    "search_field": "label_search",
                    "sort_field": "size",
                    "value_field": "value",
                    "source_value_field": "value",
                    "source_label_field": "label",
                },
                "settings": {"widget": "lookup"},
            },
        )

        with patch.object(service, "_resolve_field", return_value=(field, None)):
            with patch.object(service, "_search_lookup_options", side_effect=Exception("missing index")):
                options, error = service.get_field_options("publisher")

        self.assertEqual(options, [])
        self.assertIn("missing index", error)


class BuildLookupCommandTests(SimpleTestCase):
    def test_build_service_reports_missing_source_index(self):
        client = Mock()
        client.ping.return_value = True
        client.indices.exists.return_value = False
        config = dict(
            source_index="scientific_production",
            batch_size=100,
            max_docs=None,
            selected_lookups=["publisher"],
            lookup_index_overrides={},
            max_items={},
        )

        with self.assertRaisesMessage(ValueError, "Source index or alias 'scientific_production' does not exist"):
            LookupIndexBuildService(client=client, lookup_builders=LOOKUP_BUILDERS, **config).run()

    def test_build_service_rejects_existing_target_index_before_creating_any_index(self):
        client = Mock()
        client.ping.return_value = True
        client.indices.exists.side_effect = lambda index: index in {
            "scientific_production",
            "silver_lookup_publisher",
        }
        config = dict(
            source_index="scientific_production",
            batch_size=100,
            max_docs=None,
            selected_lookups=["source", "publisher"],
            lookup_index_overrides={},
            max_items={},
        )

        with self.assertRaisesMessage(ValueError, "Target lookup index 'silver_lookup_publisher' already exists"):
            LookupIndexBuildService(client=client, lookup_builders=LOOKUP_BUILDERS, **config).run()

        client.indices.create.assert_not_called()

    def test_build_service_rejects_duplicate_target_index_names(self):
        client = Mock()
        config = dict(
            source_index="scientific_production",
            batch_size=100,
            max_docs=None,
            selected_lookups=["source", "publisher"],
            lookup_index_overrides={"source": "lookup_shared", "publisher": "lookup_shared"},
            max_items={},
        )

        with self.assertRaisesMessage(ValueError, "target the same index 'lookup_shared'"):
            LookupIndexBuildService(client=client, lookup_builders=LOOKUP_BUILDERS, **config).run()

        client.ping.assert_not_called()
        client.indices.create.assert_not_called()

    @patch("search_gateway.lookup.base.streaming_bulk")
    @patch("search_gateway.lookup.base.scan")
    def test_build_service_verifies_index_count_after_bulk(self, scan_mock, streaming_bulk_mock):
        client = Mock()
        client.ping.return_value = True
        client.indices.exists.side_effect = lambda index: index == "scientific_production"
        client.count.return_value = {"count": 1}
        scan_mock.return_value = [
            {
                "_source": {
                    "source": [{"type": "journal"}],
                    "publishers": [{"name": "SciELO"}],
                }
            }
        ]
        streaming_bulk_mock.return_value = [(True, {"index": {"_id": "SciELO"}})]
        config = dict(
            source_index="scientific_production",
            batch_size=100,
            max_docs=None,
            selected_lookups=["publisher"],
            lookup_index_overrides={},
            max_items={},
        )

        counts = LookupIndexBuildService(client=client, lookup_builders=LOOKUP_BUILDERS, **config).run()

        self.assertEqual(counts["publisher"], 1)
        client.indices.refresh.assert_called_once_with(index="silver_lookup_publisher")
        client.count.assert_called_once_with(index="silver_lookup_publisher")

    @patch("search_gateway.lookup.base.streaming_bulk")
    @patch("search_gateway.lookup.base.scan")
    def test_build_service_raises_when_index_count_does_not_match_bulk(self, scan_mock, streaming_bulk_mock):
        client = Mock()
        client.ping.return_value = True
        client.indices.exists.side_effect = lambda index: index == "scientific_production"
        client.count.return_value = {"count": 0}
        scan_mock.return_value = [
            {
                "_source": {
                    "source": [{"type": "journal"}],
                    "publishers": [{"name": "SciELO"}],
                }
            }
        ]
        streaming_bulk_mock.return_value = [(True, {"index": {"_id": "SciELO"}})]
        config = dict(
            source_index="scientific_production",
            batch_size=100,
            max_docs=None,
            selected_lookups=["publisher"],
            lookup_index_overrides={},
            max_items={},
        )

        with self.assertRaisesMessage(ValueError, "count mismatch after refresh"):
            LookupIndexBuildService(client=client, lookup_builders=LOOKUP_BUILDERS, **config).run()

    @patch("search_gateway.lookup.base.streaming_bulk")
    @patch("search_gateway.lookup.base.scan")
    def test_build_service_reports_partial_bulk_errors(self, scan_mock, streaming_bulk_mock):
        client = Mock()
        client.ping.return_value = True
        client.indices.exists.side_effect = lambda index: index == "scientific_production"
        client.count.return_value = {"count": 0}
        scan_mock.return_value = [
            {
                "_source": {
                    "source": [{"type": "journal"}],
                    "publishers": [{"name": "SciELO"}],
                }
            }
        ]
        streaming_bulk_mock.return_value = [
            (False, {"index": {"_id": "SciELO", "error": "mapping error"}})
        ]
        config = dict(
            source_index="scientific_production",
            batch_size=100,
            max_docs=None,
            selected_lookups=["publisher"],
            lookup_index_overrides={},
            max_items={},
        )

        counts = LookupIndexBuildService(client=client, lookup_builders=LOOKUP_BUILDERS, **config).run()

        self.assertEqual(counts["publisher"], 0)
        self.assertEqual(counts["_errors"]["publisher"], 1)
        client.index.assert_called_once()
        error_body = client.index.call_args.kwargs["body"]
        self.assertEqual(error_body["component"], "search_gateway.lookup")
        self.assertEqual(error_body["context"]["lookup_key"], "publisher")
        self.assertEqual(error_body["context"]["error_count"], 1)
        self.assertEqual(error_body["context"]["sample_errors"][0]["error"], "mapping error")
        client.indices.delete.assert_not_called()


    @patch("search_gateway.management.commands.build_lookup_indices.LookupIndexBuildService")
    @patch("search_gateway.management.commands.build_lookup_indices.get_opensearch_client")
    def test_command_validates_batch_size(self, get_client_mock, build_mock):
        with self.assertRaises(CommandError):
            call_command("build_lookup_indices", "--batch-size", "0")

        get_client_mock.assert_not_called()
        build_mock.assert_not_called()

    @patch("search_gateway.tasks.build_lookup_indices_task.delay")
    def test_command_can_enqueue_celery_task(self, delay_mock):
        delay_mock.return_value.id = "task-123"

        call_command(
            "build_lookup_indices",
            "--source-index",
            "scientific_production",
            "--lookup",
            "source",
            "--batch-size",
            "500",
            "--lookup-index",
            "source=lookup_source_v2",
            "--enqueue",
        )

        delay_mock.assert_called_once_with(
            source_index="scientific_production",
            batch_size=500,
            max_docs=None,
            selected_lookups=["source"],
            lookup_index_overrides={"source": "lookup_source_v2"},
            max_items={},
        )
