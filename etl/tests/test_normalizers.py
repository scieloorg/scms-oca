from django.test import SimpleTestCase

from etl.normalizers import stz_doi, stz_isbn, stz_issn


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
