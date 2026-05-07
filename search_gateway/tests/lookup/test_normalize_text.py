from django.test import SimpleTestCase

from search_gateway.option_normalization import clean_text, normalize_text


class NormalizeTextTests(SimpleTestCase):
    def test_normalize_text_preserves_accents_and_capitalization(self):
        test_cases = [
            # Publishers
            ("Elsevier", "Elsevier"),
            ("Springer Nature", "Springer Nature"),
            ("Sociedade Brasileira de Matemática", "Sociedade Brasileira de Matemática"),
            ("Universidad de Buenos Aires", "Universidad de Buenos Aires"),
            
            # Institutions with accents
            ("Università di Roma", "Università di Roma"),
            ("Université Paris-Sud", "Université Paris-Sud"),
            ("Ciência e Cultura", "Ciência e Cultura"),
            ("Fundação de Amparo à Pesquisa", "Fundação de Amparo à Pesquisa"),
            
            # Complex names with special chars
            ("México-City Scientific Pub. Ltd.", "México-City Scientific Pub. Ltd."),
            ("Institut für Hochenergiephysik", "Institut für Hochenergiephysik"),
            ("Академия наук", "Академия наук"),
            
            # Normalization preserving accents
            ("Ceará University", "Ceará University"),
            ("Universidad Nacional Autónoma de México", "Universidad Nacional Autónoma de México"),
            ("Conselho Nacional de Pesquisas", "Conselho Nacional de Pesquisas"),
            
            # Added test cases with messy institution names - corrected expectations
            ("  University of São Paulo  ", "University of São Paulo"),
            ("Instituto de Pesquisas  Tecnológicas  ", "Instituto de Pesquisas Tecnológicas"),
            ("Universidade Estadual Paulista 'Júlio de Mesquita Filho'", "Universidade Estadual Paulista 'Júlio de Mesquita Filho'"),
            ("Centro Universitário 'Fundação Santo André'", "Centro Universitário 'Fundação Santo André'"),
            ("Faculdade de Tecnologia de São Paulo (FATEC)", "Faculdade de Tecnologia de São Paulo (FATEC)"),
            ("Instituto Superior Técnico / University of Lisbon", "Instituto Superior Técnico / University of Lisbon"),
            ("Universidade Federal do Rio de Janeiro (UFRJ)", "Universidade Federal do Rio de Janeiro (UFRJ)"),
            ("  Centro de Ciências da Saúde   /   UFRJ  ", "Centro de Ciências da Saúde / UFRJ"),
            ("Universidade de São Paulo - USP / Campus RP", "Universidade de São Paulo - USP / Campus RP"),
            ("Faculdade de Medicina de Ribeirão Preto ''USP''", "Faculdade de Medicina de Ribeirão Preto ''USP''"),  # Keep double quotes as is
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                result = normalize_text(original)
                self.assertEqual(result, expected)
                
                # Check that accents are preserved
                for char in original:
                    if ord(char) > 127:
                        self.assertIn(char, result)

    def test_clean_vs_normalize(self):
        test_cases = [
            "  Multiple    Spaces  ",
            "Special\nCharacters\tAnd\nNewlines",
            "Mixedácçênts And\tSpaces",
            "Duplicate   Accented   Words",
            "Instituição ''Suja'' com /// caracteres ((especiais))",
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                cleaned = clean_text(text)
                normalized = normalize_text(text)
                
                # Both should handle whitespace consistently
                self.assertEqual(cleaned, normalized)
                
                # Normalized should preserve case
                if any(c.isupper() for c in text):
                    self.assertTrue(any(c.isupper() for c in normalized))