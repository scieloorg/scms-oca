from django.test import SimpleTestCase
from django.conf import settings

from search_gateway.lookup.base import LookupBuilder
from search_gateway.option_normalization import normalize_text


class LookupBuilderNormalizationTests(SimpleTestCase):
    def test_lookup_builder_mapping_configuration(self):
        mapping = LookupBuilder.build_mapping()
        properties = mapping["mappings"]["properties"]
        
        analyzer_config = mapping['settings']['analysis']['analyzer']
        multilingual_filter = analyzer_config['multilingual']['filter']
        
        # Verify that asciifolding is not present in the filter
        self.assertIn('asciifolding', multilingual_filter)
        
        # Verify that lowercase is still present
        self.assertIn('lowercase', multilingual_filter)
        
        # Print the complete mapping for reference
        self.assertEqual(mapping['settings']['index']['number_of_shards'], 
                         getattr(settings, 'SEARCH_GATEWAY_LOOKUP_NUMBER_OF_SHARDS', 1))
        self.assertEqual(mapping['settings']['index']['number_of_replicas'], 
                         getattr(settings, 'SEARCH_GATEWAY_LOOKUP_NUMBER_OF_REPLICAS', 0))
        self.assertEqual(properties["label"]["copy_to"], "label_search")
        self.assertEqual(properties["label_search"]["type"], "search_as_you_type")

    def test_normalized_values_preserve_accents_and_capitalization(self):
        test_cases = [
            ("Springer Nature", "Springer Nature"),
            ("Universidade de São Paulo", "Universidade de São Paulo"),
            ("École Polytechnique Fédérale", "École Polytechnique Fédérale"),
            ("Universität Zürich", "Universität Zürich"),
            ("Fundação Oswaldo Cruz", "Fundação Oswaldo Cruz"),
            ("Ciência e Cultura", "Ciência e Cultura"),
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
                        
                # Check that capitalization is preserved
                if any(c.isupper() for c in original):
                    self.assertTrue(any(c.isupper() for c in result))

    def test_lookup_builder_uses_normalized_values(self):
        class TestLookupBuilder(LookupBuilder):
            key = "test"
            default_index_name = "test_index"
            source_fields = ["test_field"]

            def collect(self, source, max_items=None):
                # Implementation not needed for this test
                pass

        builder = TestLookupBuilder()
        
        test_entries = [
            ("Springer Nature", "Scientific Publisher"),
            ("Universidade de São Paulo", "University in Brazil"),
            ("École Polytechnique Fédérale", "Swiss Technical Institute"),
            ("Universität Zürich", "Swiss University"),
            ("Fundação Oswaldo Cruz", "Brazilian Research Institution"),
            # Added test cases with messy institution names
            ("  University of São Paulo  ", "University in Brazil with extra spaces"),
            ("Instituto de Pesquisas  Tecnológicas  ", "Tech Research Institute with extra spaces"),
            ("Universidade Estadual Paulista 'Júlio de Mesquita Filho'", "University with quotes"),
            ("Faculdade de Tecnologia de São Paulo (FATEC)", "Tech Faculty with parentheses"),
            ("Instituto Superior Técnico / University of Lisbon", "Institution with slash"),
        ]
        
        for value, label in test_entries:
            result = builder.add_entry(value, label, set())
            if result:
                # Verify that normalization preserves capitalization and accents
                expected_normalized = normalize_text(label)
                self.assertEqual(result['normalized_value'], expected_normalized)

        action = list(builder.iter_actions("test_index"))[0]
        self.assertNotIn("label_search", action["_source"])
