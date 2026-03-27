import json
import slugify

from django.core.management.base import BaseCommand
from wagtail.models import Site, Locale

from freepage.models import FreePage
from search.models import SearchPage
from search_gateway.models import DataSource


PAGE_TYPE_FREE_PAGE = "FreePage"
PAGE_TYPE_SEARCH_PAGE = "SearchPage"
HOME_PAGE_TITLES = {
    "pt-BR": "Início",
    "en": "Home",
    "es": "Inicio",
}


class Command(BaseCommand):
    help = "Cria páginas a partir de um JSON, preservando traduções via translation_key."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            default="core/fixtures/pages.json",
            help="Caminho do JSON com a árvore de páginas.",
        )

    def load_data(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Arquivo não encontrado: {path}"))
            return None

        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Erro ao decodificar JSON: {e}"))
            return None

    def fetch_site(self):
        site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()
        if not site:
            self.stdout.write(self.style.ERROR("Nenhum site Wagtail encontrado."))
            return None

        return site
    
    def get_home_for_locale(self, site, locale):
        root_page = site.root_page.specific

        if root_page.locale_id == locale.id:
            return root_page

        translated = root_page.get_translation_or_none(locale)
        return translated.specific if translated else None

    def get_or_create_locale(self, language_code):
        existing = Locale.objects.filter(language_code__iexact=language_code).first()
        if existing:
            return existing, False

        return Locale.objects.get_or_create(language_code=language_code)

    def ensure_home_for_locale(self, site, locale):
        home = self.get_home_for_locale(site, locale)
        if home:
            return home

        source_home = site.root_page.specific
        translated_home = source_home.copy_for_translation(locale)
        translated_home.title = HOME_PAGE_TITLES.get(
            locale.language_code,
            source_home.title,
        )
        translated_home.save_revision().publish()
        return translated_home.specific

    def handle(self, *args, **options):
        data = self.load_data(options["data"])
        if data is None:
            return

        site = self.fetch_site()
        if not site:
            return

        self.pages_by_key = {}

        for lang, pages in data.items():
            locale, _ = self.get_or_create_locale(lang)
            self.stdout.write(f"\nAdicionando páginas para idioma {locale.language_code}")

            home = self.ensure_home_for_locale(site, locale)

            self.add_pages(parent=home, locale=locale, pages=pages)

    def add_pages(self, parent, locale, pages, level=0):
        for page in pages:
            current_page = self.add_page(parent=parent, locale=locale, page=page, level=level)

            children = page.get("children", [])
            if children and current_page:
                self.add_pages(
                    parent=current_page,
                    locale=locale,
                    pages=children,
                    level=level + 1,
                )

    def add_page(self, parent, locale, page, level=0):
        p_key = page.get("key")
        p_title = page.get("title")
        p_slug = page.get("slug") or slugify.slugify(p_title)
        p_type = page.get("type", PAGE_TYPE_FREE_PAGE)
        p_datasource = page.get("data_source", "")

        self.stdout.write(
            "\t" * level + ",".join([
                p_key or "",
                p_title or "",
                p_slug or "",
                p_type or "",
                p_datasource or "",
            ])
        )

        if not p_key:
            self.stdout.write(self.style.ERROR(f"Página sem key: {p_title}"))
            return None

        if p_type == PAGE_TYPE_FREE_PAGE:
            return self.create_freepage(
                parent=parent,
                title=p_title,
                slug=p_slug,
                locale=locale,
                page_key=p_key,
            )

        if p_type == PAGE_TYPE_SEARCH_PAGE:
            return self.create_searchpage(
                parent=parent,
                title=p_title,
                slug=p_slug,
                locale=locale,
                data_source_name=p_datasource,
                page_key=p_key,
            )

        self.stdout.write(self.style.ERROR(f"Tipo de página inválido: {p_type}"))
        return None

    def get_page_from_memory(self, page_key, locale=None):
        if locale is not None:
            return self.pages_by_key.get((page_key, locale.language_code))

        for (stored_key, _lang), page in self.pages_by_key.items():
            if stored_key == page_key:
                return page

        return None

    def remember_page(self, page_key, locale, page):
        self.pages_by_key[(page_key, locale.language_code)] = page

    def create_freepage(self, parent, title, slug, locale, page_key):
        existing = self.get_page_from_memory(page_key, locale)
        if existing:
            return existing

        base_page = self.get_page_from_memory(page_key)

        if base_page:
            translated = base_page.get_translation_or_none(locale)
            if translated:
                self.remember_page(page_key, locale, translated)
                return translated

            p_obj = base_page.copy_for_translation(locale)
            p_obj.title = title
            p_obj.slug = slug
            p_obj.body = f"<p>{title}</p>"
            p_obj.save_revision().publish()

            self.remember_page(page_key, locale, p_obj)
            return p_obj

        sibling = parent.get_children().specific().filter(locale=locale, slug=slug).first()
        if sibling:
            self.remember_page(page_key, locale, sibling)
            return sibling

        p_obj = FreePage(
            title=title,
            slug=slug,
            body=f"<p>{title}</p>",
            locale=locale,
        )
        parent.add_child(instance=p_obj)
        p_obj.save_revision().publish()

        self.remember_page(page_key, locale, p_obj)
        return p_obj

    def create_searchpage(self, parent, title, slug, locale, data_source_name, page_key):
        existing = self.get_page_from_memory(page_key, locale)
        if existing:
            return existing

        ds = DataSource.objects.filter(index_name=data_source_name).first()
        if not ds:
            self.stdout.write(self.style.ERROR(
                f"DataSource não encontrado para {page_key}: {data_source_name}"
            ))
            return None

        base_page = self.get_page_from_memory(page_key)

        if base_page:
            translated = base_page.get_translation_or_none(locale)
            if translated:
                self.remember_page(page_key, locale, translated)
                return translated

            p_obj = base_page.copy_for_translation(locale)
            p_obj.title = title
            p_obj.slug = slug
            p_obj.data_source = ds
            p_obj.save_revision().publish()

            self.remember_page(page_key, locale, p_obj)
            return p_obj

        sibling = parent.get_children().specific().filter(locale=locale, slug=slug).first()
        if sibling:
            self.remember_page(page_key, locale, sibling)
            return sibling

        p_obj = SearchPage(
            title=title,
            slug=slug,
            data_source=ds,
            locale=locale,
        )
        parent.add_child(instance=p_obj)
        p_obj.save_revision().publish()

        self.remember_page(page_key, locale, p_obj)
        return p_obj
