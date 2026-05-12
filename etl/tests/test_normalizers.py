from django.test import SimpleTestCase

from etl.transform.normalizers import (
    as_list,
    int_or_none,
    normalize_keywords,
    normalize_name,
    normalize_text,
    scalar_or_list,
    stz_country_code,
    stz_doi,
    stz_isbn,
    stz_issn,
    stz_language,
    unique,
)


class IdentifierNormalizerTests(SimpleTestCase):
    def test_stz_doi_strips_url_prefix_and_lowercases(self):
        self.assertEqual(
            stz_doi("https://doi.org/10.1590/S0102-311X2024000100001"),
            "10.1590/s0102-311x2024000100001",
        )

    def test_stz_doi_rejects_invalid_values(self):
        self.assertIsNone(stz_doi("not-a-doi"))
        self.assertIsNone(stz_doi(None))

    def test_stz_isbn_accepts_isbn10_and_isbn13(self):
        self.assertEqual(stz_isbn("85-359-0277-5"), "8535902775")
        self.assertEqual(stz_isbn("978 65 0000000 1"), "9786500000001")

    def test_stz_isbn_rejects_invalid_values(self):
        self.assertIsNone(stz_isbn("123"))
        self.assertIsNone(stz_isbn(None))

    def test_stz_issn_formats_eight_digits(self):
        self.assertEqual(stz_issn("0102-311X"), "0102-311X")
        self.assertEqual(stz_issn("0102311X"), "0102-311X")

    def test_stz_issn_rejects_invalid_values(self):
        self.assertIsNone(stz_issn("123"))
        self.assertIsNone(stz_issn(None))


class TextAndCollectionNormalizerTests(SimpleTestCase):
    def test_normalize_text_collapses_spaces_and_strips_accents(self):
        self.assertEqual(normalize_text("  Sa\u00fade   p\u00fablica  "), "Saude publica")
        self.assertIsNone(normalize_text(""))

    def test_normalize_name_is_case_and_dash_insensitive(self):
        self.assertEqual(normalize_name(" Jo\u00e3o\u2013Silva  "), "joao-silva")
        self.assertEqual(normalize_name(None), "")

    def test_normalize_keywords_deduplicates_and_sorts(self):
        self.assertEqual(
            normalize_keywords(["Sa\u00fade", "saude", "Epidemiologia"]),
            ["epidemiologia", "saude"],
        )

    def test_int_or_none_converts_safe_values(self):
        self.assertEqual(int_or_none("2024"), 2024)
        self.assertIsNone(int_or_none("not-a-year"))

    def test_as_list_wraps_scalar_values(self):
        self.assertEqual(as_list("abc"), ["abc"])
        self.assertEqual(as_list([]), [])

    def test_unique_keeps_first_occurrence_order(self):
        self.assertEqual(unique(["b", "a", "b", None]), ["b", "a"])

    def test_scalar_or_list_returns_scalar_for_single_value(self):
        self.assertEqual(scalar_or_list(["a", "a"]), "a")
        self.assertEqual(scalar_or_list(["a", "b"]), ["a", "b"])


class LanguageNormalizerTests(SimpleTestCase):
    def test_stz_language_accepts_iso_639_codes(self):
        self.assertEqual(stz_language("pt"), "pt")
        self.assertEqual(stz_language("por"), "pt")
        self.assertEqual(stz_language("eng"), "en")

    def test_stz_language_accepts_language_names(self):
        self.assertEqual(stz_language("Portuguese"), "pt")

    def test_stz_language_rejects_unknown_values(self):
        self.assertIsNone(stz_language("not-a-language"))
        self.assertIsNone(stz_language(None))


class CountryNormalizerTests(SimpleTestCase):
    def test_stz_country_code_accepts_alpha_codes(self):
        self.assertEqual(stz_country_code("BR"), "BR")
        self.assertEqual(stz_country_code("bra"), "BR")

    def test_stz_country_code_accepts_country_names(self):
        self.assertEqual(stz_country_code("Brazil"), "BR")

    def test_stz_country_code_rejects_unknown_values(self):
        self.assertIsNone(stz_country_code("not-a-country"))
        self.assertIsNone(stz_country_code(None))
