import json

from django.test import RequestFactory, SimpleTestCase

from .citation.views import (
    citation_custom_style_view,
    citation_preview_view,
    export_view,
)
from .citation.render import render_bibtex
from .csl_json import (
    document_source_to_csl_item,
    documents_payload_to_csl_json,
    normalize_doi,
)
from .models import SearchPage
from .normalize import normalize_orcid, orcid_url
from .ris_export import render_ris_lines


class SearchPaginationTests(SimpleTestCase):
    def page_labels(self, page, total_pages):
        results = SearchPage.current_pagination(
            {"search_results": [{}], "total_results": total_pages * 25},
            page=page,
            page_size=25,
        )
        labels = []
        if results["page_numbers"] and results["page_numbers"][0] > 1:
            labels.append("<<")
        labels.append("<")
        labels.extend(str(n) for n in results["page_numbers"])
        labels.extend([">", ">>"])
        return labels

    def test_pagination_shows_first_page_shortcut(self):
        self.assertEqual(
            self.page_labels(page=12, total_pages=24),
            ["<<", "<", "10", "11", "12", "13", "14", ">", ">>"],
        )

    def test_pagination_shows_left_shortcut_near_start(self):
        self.assertEqual(
            self.page_labels(page=5, total_pages=24),
            ["<<", "<", "3", "4", "5", "6", "7", ">", ">>"],
        )
        self.assertEqual(
            self.page_labels(page=6, total_pages=24),
            ["<<", "<", "4", "5", "6", "7", "8", ">", ">>"],
        )

    def test_pagination_shows_last_page_shortcut(self):
        self.assertEqual(
            self.page_labels(page=19, total_pages=24),
            ["<<", "<", "17", "18", "19", "20", "21", ">", ">>"],
        )
        self.assertEqual(
            self.page_labels(page=20, total_pages=24),
            ["<<", "<", "18", "19", "20", "21", "22", ">", ">>"],
        )

    def test_pagination_is_limited_to_opensearch_result_window(self):
        results = SearchPage.current_pagination(
            {"search_results": [{}], "total_results": 3090622 * 25},
            page=400,
            page_size=25,
        )
        self.assertEqual(results["total_pages"], 400)
        self.assertFalse(results["has_next"])
        self.assertEqual(
            results["page_numbers"],
            [396, 397, 398, 399, 400],
        )
        self.assertEqual(
            self.page_labels(page=400, total_pages=3090622),
            ["<<", "<", "396", "397", "398", "399", "400", ">", ">>"],
        )

    def test_pagination_marks_when_result_window_limit_is_exceeded(self):
        results = SearchPage.current_pagination(
            {"search_results": [{}], "total_results": 10001},
            page=1,
            page_size=25,
        )

        self.assertEqual(results["accessible_results_limit"], 10000)
        self.assertTrue(results["accessible_results_limit_exceeded"])

    def test_pagination_does_not_mark_result_window_limit_at_boundary(self):
        results = SearchPage.current_pagination(
            {"search_results": [{}], "total_results": 10000},
            page=1,
            page_size=25,
        )

        self.assertFalse(results["accessible_results_limit_exceeded"])


class NormalizeDoiTests(SimpleTestCase):
    def test_strips_https_prefix(self):
        self.assertEqual(
            normalize_doi("https://doi.org/10.1234/foo"),
            "10.1234/foo",
        )


class NormalizeOrcidTests(SimpleTestCase):
    def test_strips_orcid_url_prefix(self):
        self.assertEqual(
            normalize_orcid("https://orcid.org/0000-0002-1825-0097"),
            "0000-0002-1825-0097",
        )

    def test_builds_orcid_url(self):
        self.assertEqual(
            orcid_url("0000-0002-1825-0097"),
            "https://orcid.org/0000-0002-1825-0097",
        )


class CslJsonMapperTests(SimpleTestCase):
    def test_openalex_shaped_source(self):
        source = {
            "type": "article",
            "title": "Sample paper",
            "publication_year": 2021,
            "ids": {"doi": "10.1000/xyz"},
            "authorships": [
                {
                    "author": {
                        "display_name": "Maria Silva",
                    }
                },
                {"author": {"display_name": "Costa, João"}},
            ],
            "biblio": {"volume": "10", "issue": "2", "first_page": "1", "last_page": "10"},
        }
        item = document_source_to_csl_item(source, doc_id="W123")
        self.assertEqual(item["id"], "W123")
        self.assertEqual(item["type"], "article-journal")
        self.assertEqual(item["title"], "Sample paper")
        self.assertEqual(item["DOI"], "10.1000/xyz")
        self.assertEqual(item["volume"], "10")
        self.assertEqual(item["issue"], "2")
        self.assertEqual(len(item["author"]), 2)
        self.assertEqual(item["author"][0]["family"], "Silva")
        self.assertEqual(item["author"][0]["given"], "Maria")

    def test_documents_payload_to_csl_json(self):
        payload = [
            {"id": "a", "source": {"type": "article", "title": "One", "publication_year": 2020}},
            {"id": "b", "source": {"type": "article", "title": "Two", "publication_year": 2021}},
        ]
        csl = documents_payload_to_csl_json(payload)
        self.assertEqual(len(csl), 2)
        self.assertEqual(csl[0]["id"], "a")
        self.assertEqual(csl[1]["id"], "b")


class CitationExportApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_export_bib_one_document(self):
        body = {
            "format": "bib",
            "documents": [
                {
                    "id": "doc-a",
                    "source": {
                        "type": "article",
                        "title": "Alpha study",
                        "publication_year": 2020,
                        "authorships": [{"author": {"display_name": "Doe, Jane"}}],
                        "resolved_source_name": "J Test",
                    },
                },
            ],
        }
        request = self.factory.post(
            "/search/api/citation-export/",
            data=json.dumps(body),
            content_type="application/json",
        )
        r = export_view(request)
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r["Content-Disposition"])
        text = r.content.decode("utf-8")
        self.assertIn("Alpha study", text)
        self.assertIn("@article", text)

    def test_export_ris_one_document(self):
        body = {
            "format": "ris",
            "documents": [
                {
                    "id": "x1",
                    "source": {
                        "type": "article",
                        "title": "RIS one",
                        "publication_year": 2019,
                        "ids": {"doi": "10.9999/one"},
                    },
                },
            ],
        }
        request = self.factory.post(
            "/search/api/citation-export/",
            data=json.dumps(body),
            content_type="application/json",
        )
        r = export_view(request)
        self.assertEqual(r.status_code, 200)
        text = r.content.decode("utf-8")
        self.assertIn("TY  - JOUR", text)
        self.assertIn("TI  - RIS one", text)
        self.assertIn("ER  -", text)

    def test_export_csv_streams_multiple_documents(self):
        body = {
            "format": "csv",
            "documents": [
                {"id": "doc-a", "source": {"type": "article", "title": "Alpha study"}},
                {"id": "doc-b", "source": {"type": "article", "title": "Beta study"}},
            ],
        }
        request = self.factory.post(
            "/search/api/export-files/",
            data=json.dumps(body),
            content_type="application/json",
        )
        r = export_view(request)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.streaming)
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        text = b"".join(r.streaming_content).decode("utf-8")
        self.assertTrue(text.startswith("\ufeff"))
        self.assertIn('"id","type","title"', text)
        self.assertIn('"doc-a"', text)
        self.assertIn('"Alpha study"', text)
        self.assertIn('"doc-b"', text)
        self.assertIn('"Beta study"', text)

    def test_export_rejects_empty_documents(self):
        request = self.factory.post(
            "/search/api/citation-export/",
            data=json.dumps({"format": "bib", "documents": []}),
            content_type="application/json",
        )
        r = export_view(request)
        self.assertEqual(r.status_code, 400)

    def test_export_rejects_bad_format(self):
        request = self.factory.post(
            "/search/api/citation-export/",
            data=json.dumps(
                {
                    "format": "xml",
                    "documents": [{"id": "1", "source": {"title": "T", "type": "article"}}],
                }
            ),
            content_type="application/json",
        )
        r = export_view(request)
        self.assertEqual(r.status_code, 400)

    def test_export_bib_multiple_documents(self):
        body = {
            "format": "bib",
            "documents": [
                {"id": "doc-a", "source": {"type": "article", "title": "Alpha study"}},
                {"id": "doc-b", "source": {"type": "article", "title": "Beta study"}},
            ],
        }
        request = self.factory.post(
            "/search/api/citation-export/",
            data=json.dumps(body),
            content_type="application/json",
        )
        r = export_view(request)
        self.assertEqual(r.status_code, 200)
        text = r.content.decode("utf-8")
        self.assertIn("Alpha study", text)
        self.assertIn("Beta study", text)

    def test_preview_returns_presets(self):
        body = {
            "documents": [
                {
                    "id": "x1",
                    "source": {
                        "type": "article",
                        "title": "Preview citation",
                        "publication_year": 2019,
                        "ids": {"doi": "10.9999/one"},
                    },
                },
            ],
        }
        request = self.factory.post(
            "/search/api/citation-preview/",
            data=json.dumps(body),
            content_type="application/json",
        )
        r = citation_preview_view(request)
        self.assertEqual(r.status_code, 200)
        payload = json.loads(r.content.decode("utf-8"))
        preset_ids = {item["id"] for item in payload["presets"]}
        self.assertIn("vancouver", preset_ids)
        self.assertIn("apa", preset_ids)

    def test_custom_style_returns_citation(self):
        body = {
            "documents": [
                {
                    "id": "x1",
                    "source": {
                        "type": "article",
                        "title": "Custom citation",
                        "publication_year": 2019,
                        "ids": {"doi": "10.9999/one"},
                    },
                },
            ],
            "style": "harvard-cite-them-right",
        }
        request = self.factory.post(
            "/search/api/citation-custom-style/",
            data=json.dumps(body),
            content_type="application/json",
        )
        r = citation_custom_style_view(request)
        self.assertEqual(r.status_code, 200)
        payload = json.loads(r.content.decode("utf-8"))
        self.assertEqual(payload["id"], "harvard-cite-them-right")
        self.assertIn("citation", payload)

    def test_custom_style_rejects_empty_style(self):
        body = {
            "documents": [
                {
                    "id": "x1",
                    "source": {"type": "article", "title": "T"},
                },
            ],
            "style": "",
        }
        request = self.factory.post(
            "/search/api/citation-custom-style/",
            data=json.dumps(body),
            content_type="application/json",
        )
        r = citation_custom_style_view(request)
        self.assertEqual(r.status_code, 400)


class CiteprocIntegrationTests(SimpleTestCase):
    def test_render_bibtex_non_empty(self):
        csl = [
            {
                "id": "t1",
                "type": "article-journal",
                "title": "Hello",
                "author": [{"family": "Z", "given": "Y"}],
                "issued": {"date-parts": [[2022]]},
                "container-title": "J",
            }
        ]
        out = render_bibtex(csl)
        self.assertIn("Hello", out)
        self.assertIn("@article", out)

    def test_render_ris_non_empty(self):
        csl = [
            {
                "id": "t1",
                "type": "article-journal",
                "title": "RIS title",
                "issued": {"date-parts": [[2023]]},
                "DOI": "10.1/2",
            }
        ]
        out = render_ris_lines(csl)
        self.assertIn("TY  - JOUR", out)
        self.assertIn("RIS title", out)
        out = render_ris_lines(csl)
        self.assertIn("TY  - JOUR", out)
        self.assertIn("RIS title", out)
