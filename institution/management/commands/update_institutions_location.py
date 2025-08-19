from __future__ import annotations

import csv
from typing import Optional

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


# Simulação (não grava)
# python manage.py update_institutions_location \
#   --csv /caminho/para/institutions_states_city.csv \
#   --institution-app institution \
#   --dry-run

# Gravando de fato, atribuindo creator (se necessário)
# python manage.py update_institutions_location \
#   --csv /caminho/para/institutions_states_city.csv \
#   --institution-app institution \
#   --user-id 1

class Command(BaseCommand):
    help = (
        "Atualiza Location.state e Location.city das Institutions a partir de um CSV "
        'com colunas "institution name", "institution state", "institution city". '
        "Busca Institution por nome (case-insensitive). "
        "Se a Institution não tiver Location, cria uma."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            required=True,
            help="Caminho do CSV (UTF-8) com as colunas exigidas.",
        )
        parser.add_argument(
            "--institution-app",
            default="institution",
            help=(
                "App label onde está o modelo Institution (ex.: 'institution', 'core', 'organizations'). "
                "Usado para apps.get_model(<app_label>, 'Institution')."
            ),
        )
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help=(
                "Opcional. ID do usuário a ser usado como creator ao criar Location/City/State "
                "(caso seus modelos exijam)."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Não grava alterações; apenas mostra o que seria feito.",
        )
        parser.add_argument(
            "--commit-every",
            type=int,
            default=200,
            help="Quantidade de linhas processadas antes de commitar (quando não for dry-run).",
        )
        parser.add_argument(
            "--skip-duplicates",
            action="store_true",
            default=True,
            help=(
                "Se múltiplas Institutions tiverem o mesmo nome, pula a linha ao invés de escolher uma arbitrariamente."
            ),
        )

    def handle(self, *args, **opts):
        csv_path: str = opts["csv"]
        app_label: str = opts["institution_app"]
        dry_run: bool = opts["dry_run"]
        user_id: Optional[int] = opts["user_id"]
        commit_every: int = max(1, int(opts["commit_every"]))
        skip_duplicates: bool = bool(opts["skip_duplicates"])

        # Resolve models dinamicamente (evita acoplar ao nome do app).
        Institution = apps.get_model(app_label, "Institution")
        if Institution is None:
            raise CommandError(
                f"Não foi possível localizar Institution em app '{app_label}'. "
                "Confirme o --institution-app ou ajuste seu INSTALLED_APPS."
            )

        # Estes app labels partem do seu código mostrado: location.models e usefulmodels.models
        Location = apps.get_model("location", "Location")
        City = apps.get_model("usefulmodels", "City")
        State = apps.get_model("usefulmodels", "State")
        if any(m is None for m in (Location, City, State)):
            raise CommandError(
                "Não foi possível localizar Location/City/State. "
                "Confirme os app labels: 'location' e 'usefulmodels' no INSTALLED_APPS."
            )

        # Resolve usuário, se informado.
        user = None
        if user_id is not None:
            User = get_user_model()
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                raise CommandError(f"User com id={user_id} não encontrado.")

        # Stats
        total = 0
        matched = 0
        skipped_no_inst = 0
        skipped_duplicates = 0
        created_locations = 0
        updated_locations = 0
        created_states = 0
        created_cities = 0
        errors = 0

        def _normalize_header(h: str) -> str:
            return (h or "").strip().lower()

        # Helpers para usar seus métodos get_or_create se existirem (com 'user') ou cair no ORM.
        def ensure_state(state_name: str):
            nonlocal created_states
            if not state_name:
                return None
            state_name = state_name.strip()
            # Tenta métodos utilitários se existirem
            get_or_create = getattr(State, "get_or_create", None)
            if callable(get_or_create):
                try:
                    if user is not None:
                        st = State.get_or_create(user, name=state_name)  # assinatura do seu Location.get_or_create
                        return st
                    else:
                        # Fallback quando não houver user disponível
                        st, created = State.objects.get_or_create(name=state_name)
                        if created:
                            created_states += 1
                        return st
                except TypeError:
                    # Caso a assinatura seja diferente, tenta genérico
                    st, created = State.objects.get_or_create(name=state_name)
                    if created:
                        created_states += 1
                    return st
            # Sem helper -> ORM direto
            st, created = State.objects.get_or_create(name=state_name)
            if created:
                created_states += 1
            return st

        def ensure_city(city_name: str):
            nonlocal created_cities
            if not city_name:
                return None
            city_name = city_name.strip()
            get_or_create = getattr(City, "get_or_create", None)
            if callable(get_or_create):
                try:
                    if user is not None:
                        ct = City.get_or_create(user, name=city_name)
                        return ct
                    else:
                        ct, created = City.objects.get_or_create(name=city_name)
                        if created:
                            created_cities += 1
                        return ct
                except TypeError:
                    ct, created = City.objects.get_or_create(name=city_name)
                    if created:
                        created_cities += 1
                    return ct
            ct, created = City.objects.get_or_create(name=city_name)
            if created:
                created_cities += 1
            return ct

        # Processa o CSV
        try:
            f = open(csv_path, newline="", encoding="utf-8")
        except FileNotFoundError:
            raise CommandError(f"CSV não encontrado: {csv_path}")
        except Exception as e:
            raise CommandError(f"Erro ao abrir CSV: {e}")

        with f:
            reader = csv.DictReader(f, delimiter=';')
            if not reader.fieldnames:
                raise CommandError("CSV sem cabeçalhos.")

            # Mapeia cabeçalhos independente de capitalização/acentos simples
            field_map = { _normalize_header(h): h for h in reader.fieldnames }    

            required = {
                "institution name",
                "institution country",
                "institution state",
                "institution city",
            }
            missing = [col for col in required if col not in field_map]
            if missing:
                raise CommandError(
                    "CSV faltando colunas obrigatórias: "
                    + ", ".join(missing)
                    + f". Cabeçalhos encontrados: {reader.fieldnames}"
                )

            batch = []
            for row in reader:
                total += 1
                # try:
                inst_name = (row[field_map["institution name"]] or "").strip()
                state_name = (row[field_map["institution state"]] or "").strip()
                city_name = (row[field_map["institution city"]] or "").strip()

                if not inst_name:
                    self.stdout.write(self.style.WARNING(f"[{total}] Linha sem 'institution name' — pulando."))
                    continue

                # Busca Institution por nome (case-insensitive)
                qs = Institution.objects.filter(name__iexact=inst_name)
                count = qs.count()

                if count == 0:
                    skipped_no_inst += 1
                    self.stdout.write(self.style.WARNING(f"[{total}] Institution não encontrada: '{inst_name}'."))
                    continue
                elif count > 1 and skip_duplicates:
                    skipped_duplicates += 1
                    self.stdout.write(self.style.WARNING(
                        f"[{total}] {count} Institutions com o mesmo nome '{inst_name}'. "
                        f"Use filtros/ajuste o CSV ou desabilite --skip-duplicates para assumir a primeira."
                    ))
                    continue

                inst = qs.first()
                matched += 1

                # Determina/Cria location
                loc = getattr(inst, "location", None)
                created_loc = False
                if loc is None:
                    if dry_run:
                        self.stdout.write(self.style.NOTICE(
                            f"[{total}] (dry-run) Criaria Location para '{inst_name}'."
                        ))
                    else:
                        loc = Location()
                        # Define creator, se disponível
                        if hasattr(loc, "creator") and user is not None:
                            setattr(loc, "creator", user)
                        loc.creator = user
                        loc.save()
                        inst.location = loc
                        inst.save(update_fields=["location"])
                        created_locations += 1
                        created_loc = True

                # Determina State/City
                st_obj = ensure_state(state_name) if state_name else None
                ct_obj = ensure_city(city_name) if city_name else None

                # Aplica no location
                if not dry_run:
                    fields_to_update = []
                    if loc is not None and st_obj is not None and loc.state_id != st_obj.id:
                        loc.state = st_obj
                        fields_to_update.append("state")
                    if loc is not None and ct_obj is not None and loc.city_id != ct_obj.id:
                        loc.city = ct_obj
                        fields_to_update.append("city")

                    if loc is not None and fields_to_update:
                        loc.save(update_fields=fields_to_update)
                        updated_locations += (0 if created_loc else 1)
                else:
                    self.stdout.write(self.style.NOTICE(
                        f"[{total}] (dry-run) Atualizaria '{inst_name}' -> "
                        f"state='{state_name or '-'}', city='{city_name or '-'}'."
                    ))

                # Commit por lote para reduzir locks/uso de transação longa
                if not dry_run:
                    batch.append(1)
                    if len(batch) >= commit_every:
                        with transaction.atomic():
                            # apenas força boundary; operações já foram salvas
                            pass
                        batch.clear()

                # except Exception as e:
                #     errors += 1
                #     self.stderr.write(self.style.ERROR(f"[{total}] ERRO na linha: {e}"))

        # Resumo
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Concluído!"))
        self.stdout.write(
            f"Linhas lidas: {total} | Institutions encontradas: {matched} | "
            f"Sem Institution: {skipped_no_inst} | Duplicadas (puladas): {skipped_duplicates} | "
            f"Locations criadas: {created_locations} | Locations atualizadas: {updated_locations} | "
            f"States criados: {created_states} | Cities criadas: {created_cities} | "
            f"Erros: {errors}"
        )
