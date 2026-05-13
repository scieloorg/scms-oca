from django.test import SimpleTestCase

from etl.transform.normalizers import (
    normalize_keywords,
    normalize_author_name,
    normalize_text,
    normalize_country_code,
    normalize_doi,
    normalize_isbn,
    normalize_issn,
    normalize_language,
)
from etl.transform.utils import (
    as_list,
    dict_or_empty,
    first_value,
    int_or_none,
    match_key,
    scalar_or_list,
    unique,
)


class IdentifierNormalizerTests(SimpleTestCase):
    def test_normalize_doi_strips_url_prefix_and_lowercases(self):
        self.assertEqual(
            normalize_doi("https://doi.org/10.1590/S0102-311X2024000100001"),
            "10.1590/s0102-311x2024000100001",
        )

    def test_normalize_doi_rejects_invalid_values(self):
        self.assertIsNone(normalize_doi("not-a-doi"))
        self.assertIsNone(normalize_doi(None))

    def test_normalize_isbn_accepts_isbn10_and_isbn13(self):
        self.assertEqual(normalize_isbn("85-359-0277-5"), "8535902775")
        self.assertEqual(normalize_isbn("978 65 0000000 1"), "9786500000001")

    def test_normalize_isbn_rejects_invalid_values(self):
        self.assertIsNone(normalize_isbn("123"))
        self.assertIsNone(normalize_isbn(None))

    def test_normalize_issn_formats_eight_digits(self):
        self.assertEqual(normalize_issn("0102-311X"), "0102-311X")
        self.assertEqual(normalize_issn("0102311X"), "0102-311X")

    def test_normalize_issn_rejects_invalid_values(self):
        self.assertIsNone(normalize_issn("123"))
        self.assertIsNone(normalize_issn(None))


class TextAndCollectionNormalizerTests(SimpleTestCase):
    def test_normalize_text_collapses_spaces_and_strips_accents(self):
        self.assertEqual(normalize_text("  Sa\u00fade   p\u00fablica  "), "Saude publica")
        self.assertIsNone(normalize_text(""))

    def test_normalize_text_can_preserve_accents(self):
        self.assertEqual(
            normalize_text("  Sa\u00fade   p\u00fablica  ", strip_accents=False),
            "Sa\u00fade p\u00fablica",
        )

    def test_normalize_name_is_case_and_dash_insensitive(self):
        self.assertEqual(normalize_author_name(" Jo\u00e3o\u2013Silva  "), "joao-silva")
        self.assertEqual(normalize_author_name(None), "")

    def test_normalize_name_can_preserve_accents(self):
        self.assertEqual(
            normalize_author_name(" Jo\u00e3o\u2013Silva  ", strip_accents=False),
            "jo\u00e3o-silva",
        )

    def test_normalize_keywords_deduplicates_and_sorts(self):
        self.assertEqual(
            normalize_keywords(["Sa\u00fade", "saude", "Epidemiologia"]),
            ["epidemiologia", "saude"],
        )

    def test_integer_helper_converts_safe_values(self):
        self.assertEqual(int_or_none("2024"), 2024)
        self.assertIsNone(int_or_none("not-a-year"))

    def test_dict_helper_accepts_dicts_only(self):
        self.assertEqual(dict_or_empty({"a": 1}), {"a": 1})
        self.assertEqual(dict_or_empty(None), {})
        self.assertEqual(dict_or_empty([]), {})

    def test_as_list_wraps_scalar_values(self):
        self.assertEqual(as_list("abc"), ["abc"])
        self.assertEqual(as_list([]), [])

    def test_unique_keeps_first_occurrence_order(self):
        self.assertEqual(unique(["b", "a", "b", None]), ["b", "a"])

    def test_scalar_or_list_returns_scalar_for_single_value(self):
        self.assertEqual(scalar_or_list(["a", "a"]), "a")
        self.assertEqual(scalar_or_list(["a", "b"]), ["a", "b"])

    def test_first_value_prefers_scielo_url(self):
        self.assertEqual(
            first_value(["https://example.org/file.pdf", "https://scielo.br/article"]),
            "https://scielo.br/article",
        )

    def test_match_key_normalizes_case_and_whitespace(self):
        self.assertEqual(match_key("  Mixed   Case  "), "mixed case")


class LanguageNormalizerTests(SimpleTestCase):
    def test_normalize_language_accepts_iso_639_codes(self):
        self.assertEqual(normalize_language("pt"), "pt")
        self.assertEqual(normalize_language("por"), "pt")
        self.assertEqual(normalize_language("eng"), "en")

    def test_normalize_language_accepts_language_names(self):
        self.assertEqual(normalize_language("Portuguese"), "pt")

    def test_normalize_language_rejects_unknown_values(self):
        self.assertIsNone(normalize_language("not-a-language"))
        self.assertIsNone(normalize_language(None))


class CountryNormalizerTests(SimpleTestCase):
    def test_normalize_country_code_accepts_alpha_codes(self):
        self.assertEqual(normalize_country_code("BR"), "BR")
        self.assertEqual(normalize_country_code("bra"), "BR")

    def test_normalize_country_code_accepts_country_names(self):
        self.assertEqual(normalize_country_code("Brazil"), "BR")

    def test_normalize_country_code_rejects_unknown_values(self):
        self.assertIsNone(normalize_country_code("not-a-country"))
        self.assertIsNone(normalize_country_code(None))
