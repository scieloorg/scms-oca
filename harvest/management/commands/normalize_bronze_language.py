from django.core.management.base import BaseCommand, CommandError

from harvest.language_normalizer import normalize_language_field
from search_gateway.client import get_opensearch_client


class Command(BaseCommand):
    help = "Normaliza o campo language para ISO 639-1 em índices bronze."

    DEFAULT_INDICES = {
        "bronze_scielo_books",
        "bronze_scielo_dataset",
        "bronze_scielo_preprint",
        "bronze_openalex_works"
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--index",
            choices=[
                "all",
                "bronze_scielo_books",
                "bronze_scielo_dataset",
                "bronze_scielo_preprint",
                "bronze_openalex_works"
            ],
            default="all",
            help="Índice bronze alvo. Use 'all' para todos os padrões.",
        )
        parser.add_argument(
            "--index-name",
            action="append",
            default=[],
            help="Nome de índice adicional/explícito. Pode repetir o argumento.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Quantidade de documentos por lote durante a leitura/escrita.",
        )
        parser.add_argument(
            "--scroll-ttl",
            default="2m",
            help="Tempo de vida do scroll (ex.: 2m, 30s).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Não grava alterações; apenas simula e mostra métricas.",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Executa refresh do índice após atualização.",
        )

    def handle(self, *args, **options):
        client = get_opensearch_client()
        if client is None:
            raise CommandError("OpenSearch client não configurado.")

        batch_size = options["batch_size"]
        if batch_size <= 0:
            raise CommandError("--batch-size deve ser maior que 0.")

        indices = self._resolve_target_indices(options)
        if not indices:
            raise CommandError("Nenhum índice alvo foi informado.")

        global_stats = {"read": 0, "changed": 0, "unchanged": 0, "errors": 0}
        for index_name in indices:
            if not client.indices.exists(index=index_name):
                self.stdout.write(
                    self.style.WARNING(f"[{index_name}] índice não existe; pulando.")
                )
                continue

            self.stdout.write(self.style.NOTICE(f"[{index_name}] iniciando processamento"))
            stats = self._normalize_index_language(
                client=client,
                index_name=index_name,
                batch_size=batch_size,
                scroll_ttl=options["scroll_ttl"],
                dry_run=options["dry_run"],
                refresh=options["refresh"],
            )
            global_stats["read"] += stats["read"]
            global_stats["changed"] += stats["changed"]
            global_stats["unchanged"] += stats["unchanged"]
            global_stats["errors"] += stats["errors"]

            self.stdout.write(
                self.style.SUCCESS(
                    (
                        f"[{index_name}] lidos={stats['read']} "
                        f"alterados={stats['changed']} "
                        f"inalterados={stats['unchanged']} "
                        f"erros={stats['errors']}"
                    )
                )
            )

        mode = "DRY-RUN" if options["dry_run"] else "EXECUCAO"
        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"[{mode}] total_lidos={global_stats['read']} "
                    f"total_alterados={global_stats['changed']} "
                    f"total_inalterados={global_stats['unchanged']} "
                    f"total_erros={global_stats['errors']}"
                )
            )
        )

    def _resolve_target_indices(self, options):
        explicit = [idx for idx in options.get("index_name", []) if idx]
        if explicit:
            return list(dict.fromkeys(explicit))

        selected = options["index"]
        if selected == "all":
            return sorted(self.DEFAULT_INDICES)
        return [selected]

    def _normalize_index_language(
        self,
        *,
        client,
        index_name,
        batch_size,
        scroll_ttl,
        dry_run,
        refresh,
    ):
        stats = {"read": 0, "changed": 0, "unchanged": 0, "errors": 0}
        operations = []
        scroll_id = None

        try:
            response = client.search(
                index=index_name,
                scroll=scroll_ttl,
                size=batch_size,
                body={
                    "query": {"exists": {"field": "language"}},
                    "_source": ["language"],
                    "sort": ["_doc"],
                },
            )
            scroll_id = response.get("_scroll_id")

            while True:
                hits = response.get("hits", {}).get("hits", [])
                if not hits:
                    break

                for hit in hits:
                    stats["read"] += 1
                    source = hit.get("_source", {})
                    current_language = source.get("language")
                    normalized_language = normalize_language_field(current_language)

                    if normalized_language == current_language:
                        stats["unchanged"] += 1
                        continue

                    stats["changed"] += 1
                    if dry_run:
                        continue

                    operations.append(
                        {"update": {"_index": index_name, "_id": hit["_id"]}}
                    )
                    operations.append({"doc": {"language": normalized_language}})

                    if len(operations) >= batch_size * 2:
                        stats["errors"] += self._flush_bulk_operations(
                            client=client,
                            operations=operations,
                        )
                        operations = []

                response = client.scroll(scroll_id=scroll_id, scroll=scroll_ttl)
                scroll_id = response.get("_scroll_id", scroll_id)

            if operations and not dry_run:
                stats["errors"] += self._flush_bulk_operations(
                    client=client,
                    operations=operations,
                )

            if refresh and not dry_run:
                client.indices.refresh(index=index_name)
        finally:
            if scroll_id:
                try:
                    client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    # no-op: cleanup best effort
                    pass

        return stats

    def _flush_bulk_operations(self, *, client, operations):
        response = client.bulk(body=operations, refresh=False)
        if not response.get("errors"):
            return 0

        error_count = 0
        for item in response.get("items", []):
            result = item.get("update", {})
            if result.get("error"):
                error_count += 1
        return error_count
