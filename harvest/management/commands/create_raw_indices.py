from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from harvest.indexing import index_harvested_raw_data
from harvest.models import HarvestedBooks, HarvestedPreprint, HarvestedSciELOData
from search_gateway.client import get_opensearch_client


class Command(BaseCommand):
    help = "Cria os índices raw no OpenSearch para preprint, books e scielo data."


    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Se o índice já existir, remove e recria.",
        )
        parser.add_argument(
            "--index",
            choices=["preprint", "books", "data", "all"],
            default=None,
            help="Indexa itens raw para o tipo escolhido.",
        )

    def _index_items(self, index_choice):
        model_map = {
            "preprint": HarvestedPreprint,
            "books": HarvestedBooks,
            "data": HarvestedSciELOData,
        }
        if index_choice == "all":
            models_to_index = list(model_map.values())
        else:
            models_to_index = [model_map[index_choice]]

        for model in models_to_index:
            self.stdout.write(
                self.style.NOTICE(f"Indexando itens para {model.__name__}...")
            )
            index_harvested_raw_data(model=model, refresh=False)

    def handle(self, *args, **options):
        client = get_opensearch_client()
        if client is None:
            raise CommandError("OpenSearch client não configurado.")

        indices = {
            "HarvestedPreprint": getattr(
                settings, "OPENSEARCH_INDEX_RAW_PREPRINT", None
            ),
            "HarvestedBooks": getattr(settings, "OPENSEARCH_INDEX_RAW_BOOK", None),
            "HarvestedSciELOData": getattr(
                settings, "OPENSEARCH_INDEX_RAW_SCIELO_DATA", None
            ),
        }
        force = options["force"]
        index_choice = options["index"]

        for model_name, index_name in indices.items():
            if not index_name:
                self.stdout.write(
                    self.style.WARNING(
                        f"{model_name}: índice não configurado, pulando."
                    )
                )
                continue

            exists = client.indices.exists(index=index_name)
            if exists and force:
                self.stdout.write(
                    self.style.WARNING(f"{model_name}: removendo índice {index_name}.")
                )
                client.indices.delete(index=index_name)
                exists = False

            if exists:
                self.stdout.write(
                    self.style.NOTICE(
                        f"{model_name}: índice já existe: {index_name}."
                    )
                )
                continue

            client.indices.create(
                index=index_name,
                body={
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    },
                    "mappings": {
                        "properties": {
                            "raw_data": {"type": "object", "enabled": False}
                        }
                    },
                },
            )
            self.stdout.write(
                self.style.SUCCESS(f"{model_name}: índice criado: {index_name}.")
            )

        if index_choice:
            self._index_items(index_choice=index_choice)





