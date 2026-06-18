"""Fill django.po msgstr for observation dimension labels (pt_BR, pt, es)."""

from pathlib import Path

import polib
from django.core.management.base import BaseCommand

# msgid → msgstr per locale (English msgids from observation/dimension_i18n.py)
TRANSLATIONS = {
    "pt_BR": {
        "Affiliation - Region of the World": "Afiliação - Região do Mundo",
        "Region of the World": "Região do Mundo",
        "Affiliation \u2013 Country": "Afiliação \u2013 País",
        "Affiliation \u2013 Institution": "Afiliação \u2013 Instituição",
        "Thematic \u00e1rea": "Área temática",
        "Events": "Eventos",
        "Types": "Tipos",
        "Regions": "Regiões",
        "Division": "Divisão",
        (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation - Region of the World"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Afiliação - Região do Mundo"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation \u2013 Country"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Afiliação \u2013 País"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation \u2013 Institution"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Afiliação \u2013 Instituição"
        ),
        (
            "Evolution of scientific production - World - number of documents by Publisher"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Editora"
        ),
        (
            "Evolution of scientific production - World - number of documents by Journal"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Periódico"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Thematic \u00e1rea"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Área temática"
        ),
        (
            "Evolution of scientific production - World - number of documents by Domain"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Domínio"
        ),
        (
            "Evolution of scientific production - World - number of documents by Subfield"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Subárea"
        ),
        (
            "Evolution of scientific production - World - number of documents by Document Type"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Tipo de documento"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Document Language"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Idioma do documento"
        ),
        (
            "Evolution of scientific production - World - number of documents by Open Access"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Acesso aberto"
        ),
        (
            "Evolution of scientific production - World - number of documents by Access Type"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Tipo de acesso"
        ),
        (
            "Evolution of scientific production - World - number of documents by Source Type"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Tipo de fonte"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Source Country"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "País da fonte"
        ),
        (
            "Evolution of scientific production - World - number of documents by Funder"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Financiador"
        ),
        "Brazil - Social Production - Country - Documents - Events": (
            "Brasil - Produção Social - País - Documentos - Eventos"
        ),
        "Brazil - Social Production - Country - Documents - Institutions": (
            "Brasil - Produção Social - País - Documentos - Instituições"
        ),
        "Brazil - Social Production - Country - Documents - States": (
            "Brasil - Produção Social - País - Documentos - Estados"
        ),
        "Brazil - Social Production - Country - Documents - Regions": (
            "Brasil - Produção Social - País - Documentos - Regiões"
        ),
        "Brazil - Social Production - Country - Documents - Cities": (
            "Brasil - Produção Social - País - Documentos - Cidades"
        ),
        "Brazil - Social Production - Country - Documents - Action": (
            "Brasil - Produção Social - País - Documentos - Ação"
        ),
        "Brazil - Social Production - Country - Documents - Practice": (
            "Brasil - Produção Social - País - Documentos - Prática"
        ),
        "Brazil - Social Production - Country - Documents - Classification": (
            "Brasil - Produção Social - País - Documentos - Classificação"
        ),
        "Brazil - Social Production - Country - Documents - Division": (
            "Brasil - Produção Social - País - Documentos - Divisão"
        ),
        "Brazil - Social Production - Country - Documents - Area": (
            "Brasil - Produção Social - País - Documentos - Área"
        ),
        "Brazil - Social Production - Country - Documents - Subarea": (
            "Brasil - Produção Social - País - Documentos - Subárea"
        ),
        "Select an observation table:": "Selecione uma tabela de observação:",
        "Select an observation table on social production in Brazil by:": (
            "Selecione uma tabela de observação sobre a produção social no Brasil por:"
        ),
        "Institutions": "Instituições",
        "States": "Estados",
        "Cities": "Cidades",
        "Action": "Ação",
        "Practice": "Prática",
        "Classification": "Classificação",
        "Area": "Área",
        "Subarea": "Subárea",
        "Level": "Nível",
        "Documents": "Documentos",
        "Journals": "Periódicos",
        "Indexed In (OpenAlex)": "Indexed In (OpenAlex)",
        "Indexed In (SciELO)": "Indexed In (SciELO)",
        "SciELO Collection": "Coleção SciELO",
        "Scope": "Escopo",
        (
            "Evolution of scientific production - World - number of journals by "
            "Indexed In (OpenAlex)"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "Indexed In (OpenAlex)"
        ),
        (
            "Evolution of scientific production - World - number of journals by "
            "Indexed In (SciELO)"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "Indexed In (SciELO)"
        ),
        (
            "Evolution of scientific production - World - number of journals by "
            "SciELO Collection"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "Coleção SciELO"
        ),
        (
            "Evolution of scientific production - World - number of journals by Scope"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por Escopo"
        ),
        (
            "Evolution of scientific production - World - number of journals by Publisher"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por Editora"
        ),
        (
            "Evolution of scientific production - World - number of journals by Source Type"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "Tipo de Fonte"
        ),
        (
            "Evolution of scientific production - World - number of journals by "
            "Source Country"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "País de Origem"
        ),
    },
    "pt": {
        "Affiliation - Region of the World": "Afiliação - Região do Mundo",
        "Region of the World": "Região do Mundo",
        "Affiliation \u2013 Country": "Afiliação \u2013 País",
        "Affiliation \u2013 Institution": "Afiliação \u2013 Instituição",
        "Thematic \u00e1rea": "Área temática",
        "Events": "Eventos",
        "Types": "Tipos",
        "Regions": "Regiões",
        "Division": "Divisão",
        (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation - Region of the World"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Afiliação - Região do Mundo"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation \u2013 Country"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Afiliação \u2013 País"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation \u2013 Institution"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Afiliação \u2013 Instituição"
        ),
        (
            "Evolution of scientific production - World - number of documents by Publisher"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Editora"
        ),
        (
            "Evolution of scientific production - World - number of documents by Journal"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Periódico"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Thematic \u00e1rea"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Área temática"
        ),
        (
            "Evolution of scientific production - World - number of documents by Domain"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Domínio"
        ),
        (
            "Evolution of scientific production - World - number of documents by Subfield"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Subárea"
        ),
        (
            "Evolution of scientific production - World - number of documents by Document Type"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Tipo de documento"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Document Language"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Idioma do documento"
        ),
        (
            "Evolution of scientific production - World - number of documents by Open Access"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Acesso aberto"
        ),
        (
            "Evolution of scientific production - World - number of documents by Access Type"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Tipo de acesso"
        ),
        (
            "Evolution of scientific production - World - number of documents by Source Type"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "Tipo de fonte"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Source Country"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por "
            "País da fonte"
        ),
        (
            "Evolution of scientific production - World - number of documents by Funder"
        ): (
            "Evolução da produção científica - Mundo - número de documentos por Financiador"
        ),
        "Brazil - Social Production - Country - Documents - Events": (
            "Brasil - Produção Social - País - Documentos - Eventos"
        ),
        "Brazil - Social Production - Country - Documents - Institutions": (
            "Brasil - Produção Social - País - Documentos - Instituições"
        ),
        "Brazil - Social Production - Country - Documents - States": (
            "Brasil - Produção Social - País - Documentos - Estados"
        ),
        "Brazil - Social Production - Country - Documents - Regions": (
            "Brasil - Produção Social - País - Documentos - Regiões"
        ),
        "Brazil - Social Production - Country - Documents - Cities": (
            "Brasil - Produção Social - País - Documentos - Cidades"
        ),
        "Brazil - Social Production - Country - Documents - Action": (
            "Brasil - Produção Social - País - Documentos - Ação"
        ),
        "Brazil - Social Production - Country - Documents - Practice": (
            "Brasil - Produção Social - País - Documentos - Prática"
        ),
        "Brazil - Social Production - Country - Documents - Classification": (
            "Brasil - Produção Social - País - Documentos - Classificação"
        ),
        "Brazil - Social Production - Country - Documents - Division": (
            "Brasil - Produção Social - País - Documentos - Divisão"
        ),
        "Brazil - Social Production - Country - Documents - Area": (
            "Brasil - Produção Social - País - Documentos - Área"
        ),
        "Brazil - Social Production - Country - Documents - Subarea": (
            "Brasil - Produção Social - País - Documentos - Subárea"
        ),
        "Select an observation table:": "Selecione uma tabela de observação:",
        "Select an observation table on social production in Brazil by:": (
            "Selecione uma tabela de observação sobre a produção social no Brasil por:"
        ),
        "Institutions": "Instituições",
        "States": "Estados",
        "Cities": "Cidades",
        "Action": "Ação",
        "Practice": "Prática",
        "Classification": "Classificação",
        "Area": "Área",
        "Subarea": "Subárea",
        "Level": "Nível",
        "Documents": "Documentos",
        "Journals": "Periódicos",
        "Indexed In (OpenAlex)": "Indexed In (OpenAlex)",
        "Indexed In (SciELO)": "Indexed In (SciELO)",
        "SciELO Collection": "Coleção SciELO",
        "Scope": "Escopo",
        (
            "Evolution of scientific production - World - number of journals by "
            "Indexed In (OpenAlex)"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "Indexed In (OpenAlex)"
        ),
        (
            "Evolution of scientific production - World - number of journals by "
            "Indexed In (SciELO)"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "Indexed In (SciELO)"
        ),
        (
            "Evolution of scientific production - World - number of journals by "
            "SciELO Collection"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "Coleção SciELO"
        ),
        (
            "Evolution of scientific production - World - number of journals by Scope"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por Escopo"
        ),
        (
            "Evolution of scientific production - World - number of journals by Publisher"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por Editora"
        ),
        (
            "Evolution of scientific production - World - number of journals by Source Type"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "Tipo de Fonte"
        ),
        (
            "Evolution of scientific production - World - number of journals by "
            "Source Country"
        ): (
            "Evolução da produção científica - Mundo - número de periódicos por "
            "País de Origem"
        ),
    },
    "es": {
        "Affiliation - Region of the World": "Afiliación - Región del mundo",
        "Region of the World": "Región del mundo",
        "Affiliation \u2013 Country": "Afiliación \u2013 País",
        "Affiliation \u2013 Institution": "Afiliación \u2013 Institución",
        "Thematic \u00e1rea": "Área temática",
        "Events": "Eventos",
        "Types": "Tipos",
        "Regions": "Regiones",
        "Division": "División",
        (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation - Region of the World"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Afiliación - Región del mundo"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation \u2013 Country"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Afiliación \u2013 País"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Affiliation \u2013 Institution"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Afiliación \u2013 Institución"
        ),
        (
            "Evolution of scientific production - World - number of documents by Publisher"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Editorial"
        ),
        (
            "Evolution of scientific production - World - number of documents by Journal"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Revista"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Thematic \u00e1rea"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Área temática"
        ),
        (
            "Evolution of scientific production - World - number of documents by Domain"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Dominio"
        ),
        (
            "Evolution of scientific production - World - number of documents by Subfield"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Subárea"
        ),
        (
            "Evolution of scientific production - World - number of documents by Document Type"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Tipo de documento"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Document Language"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Idioma del documento"
        ),
        (
            "Evolution of scientific production - World - number of documents by Open Access"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Acceso abierto"
        ),
        (
            "Evolution of scientific production - World - number of documents by Access Type"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Tipo de acceso"
        ),
        (
            "Evolution of scientific production - World - number of documents by Source Type"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Tipo de fuente"
        ),
        (
            "Evolution of scientific production - World - number of documents by "
            "Source Country"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "País de la fuente"
        ),
        (
            "Evolution of scientific production - World - number of documents by Funder"
        ): (
            "Evolución de la producción científica - Mundo - número de documentos por "
            "Financiador"
        ),
        "Brazil - Social Production - Country - Documents - Events": (
            "Brasil - Producción Social - País - Documentos - Eventos"
        ),
        "Brazil - Social Production - Country - Documents - Institutions": (
            "Brasil - Producción Social - País - Documentos - Instituciones"
        ),
        "Brazil - Social Production - Country - Documents - States": (
            "Brasil - Producción Social - País - Documentos - Estados"
        ),
        "Brazil - Social Production - Country - Documents - Regions": (
            "Brasil - Producción Social - País - Documentos - Regiones"
        ),
        "Brazil - Social Production - Country - Documents - Cities": (
            "Brasil - Producción Social - País - Documentos - Ciudades"
        ),
        "Brazil - Social Production - Country - Documents - Action": (
            "Brasil - Producción Social - País - Documentos - Acción"
        ),
        "Brazil - Social Production - Country - Documents - Practice": (
            "Brasil - Producción Social - País - Documentos - Práctica"
        ),
        "Brazil - Social Production - Country - Documents - Classification": (
            "Brasil - Producción Social - País - Documentos - Clasificación"
        ),
        "Brazil - Social Production - Country - Documents - Division": (
            "Brasil - Producción Social - País - Documentos - División"
        ),
        "Brazil - Social Production - Country - Documents - Area": (
            "Brasil - Producción Social - País - Documentos - Área"
        ),
        "Brazil - Social Production - Country - Documents - Subarea": (
            "Brasil - Producción Social - País - Documentos - Subárea"
        ),
        "Select an observation table:": "Seleccione una tabla de observación:",
        "Select an observation table on social production in Brazil by:": (
            "Seleccione una tabla de observación sobre la producción social en Brasil por:"
        ),
        "Institutions": "Instituciones",
        "States": "Estados",
        "Cities": "Ciudades",
        "Action": "Acción",
        "Practice": "Práctica",
        "Classification": "Clasificación",
        "Area": "Área",
        "Subarea": "Subárea",
        "Level": "Nivel",
        "Documents": "Documentos",
        "Journals": "Revistas",
        "Indexed In (OpenAlex)": "Indexed In (OpenAlex)",
        "Indexed In (SciELO)": "Indexed In (SciELO)",
        "SciELO Collection": "Colección SciELO",
        "Scope": "Alcance",
        (
            "Evolution of scientific production - World - number of journals by "
            "Indexed In (OpenAlex)"
        ): (
            "Evolución de la producción científica - Mundo - número de revistas por "
            "Indexed In (OpenAlex)"
        ),
        (
            "Evolution of scientific production - World - number of journals by "
            "Indexed In (SciELO)"
        ): (
            "Evolución de la producción científica - Mundo - número de revistas por "
            "Indexed In (SciELO)"
        ),
        (
            "Evolution of scientific production - World - number of journals by "
            "SciELO Collection"
        ): (
            "Evolución de la producción científica - Mundo - número de revistas por "
            "Colección SciELO"
        ),
        (
            "Evolution of scientific production - World - number of journals by Scope"
        ): (
            "Evolución de la producción científica - Mundo - número de revistas por "
            "Alcance"
        ),
        (
            "Evolution of scientific production - World - number of journals by Publisher"
        ): (
            "Evolución de la producción científica - Mundo - número de revistas por "
            "Editorial"
        ),
        (
            "Evolution of scientific production - World - number of journals by Source Type"
        ): (
            "Evolución de la producción científica - Mundo - número de revistas por "
            "Tipo de fuente"
        ),
        (
            "Evolution of scientific production - World - number of journals by "
            "Source Country"
        ): (
            "Evolución de la producción científica - Mundo - número de revistas por "
            "País de origen"
        ),
    },
}


class Command(BaseCommand):
    help = "Update django.po msgstr entries for observation dimension labels."

    def handle(self, *args, **options):
        locale_root = Path(__file__).resolve().parents[3] / "locale"
        updated = 0
        added = 0

        for locale_code, catalog in TRANSLATIONS.items():
            po_path = locale_root / locale_code / "LC_MESSAGES" / "django.po"
            if not po_path.exists():
                self.stdout.write(self.style.WARNING(f"Skip missing: {po_path}"))
                continue

            po = polib.pofile(str(po_path))
            for msgid, msgstr in catalog.items():
                entry = po.find(msgid)
                if entry is None:
                    entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
                    po.append(entry)
                    added += 1
                else:
                    entry.msgstr = msgstr
                    updated += 1
                if "fuzzy" in entry.flags:
                    entry.flags.remove("fuzzy")

            po.save(str(po_path))
            self.stdout.write(self.style.SUCCESS(f"Updated {po_path}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Applied {updated} translation update(s), added {added} new entry(ies)."
            )
        )
