from django.core.management.base import BaseCommand, CommandError

from harvest.mapping_bronze_articles import BRONZE_MAPPING as BRONZE_MAPPING_ARTICLES
from harvest.mapping_bronze_books import BRONZE_MAPPING as BRONZE_MAPPING_BOOKS
from harvest.mapping_bronze_dataset import BRONZE_MAPPING as BRONZE_MAPPING_DATASET
from harvest.mapping_bronze_dataverse import BRONZE_MAPPING as BRONZE_MAPPING_DATAVERSE
from harvest.mapping_bronze_preprints import BRONZE_MAPPING as BRONZE_MAPPING_PREPRINT
from harvest.mapping_bronze_social_production import BRONZE_MAPPING as BRONZE_MAPPING_SOCIAL_PRODUCTION
from search_gateway.client import get_opensearch_client


class Command(BaseCommand):
    help = "Cria os índices bronze no OpenSearch para preprint, books e scielo data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--index",
            choices=[
                "article",
                "preprint",
                "books",
                "dataset",
                "dataverse",
                "social_production",
            ],
            help="Cria o índice bronze para o tipo escolhido. Padrão: all.",
        )

    def handle(self, *args, **options):
        client = get_opensearch_client()
        if client is None:
            raise CommandError("OpenSearch client não configurado.")

        indices = {
            "article": ("bronze_scielo_articles", BRONZE_MAPPING_ARTICLES),
            "preprint": ("bronze_scielo_preprint", BRONZE_MAPPING_PREPRINT),
            "books": ("bronze_scielo_books", BRONZE_MAPPING_BOOKS),
            "dataset": ("bronze_scielo_dataset", BRONZE_MAPPING_DATASET),
            "dataverse": ("bronze_scielo_dataverse", BRONZE_MAPPING_DATAVERSE),
            "social_production": (
                "bronze_social_production",
                BRONZE_MAPPING_SOCIAL_PRODUCTION,
            ),
        }

        index_choice = options["index"]
        selected_indices = {index_choice: indices[index_choice]} if index_choice else indices
        for _name, (index_name, bronze_mapping) in selected_indices.items():
            self.ensure_index_exists(client=client, index_name=index_name, bronze_mapping=bronze_mapping)
 
    def ensure_index_exists(self, client, index_name, bronze_mapping) -> None:
        """Create destination index with mapping if it doesn't exist."""
        if not client.indices.exists(index=index_name):
            print(f"Creating index '{index_name}' with bronze mapping...")
            client.indices.create(index=index_name, body=bronze_mapping)
            print(f"Index '{index_name}' created.")
        else:
            print(f"Index '{index_name}' already exists.")
