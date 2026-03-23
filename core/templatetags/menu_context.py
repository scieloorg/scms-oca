from __future__ import annotations

from django import template
from django.conf import settings

from search.models import SearchPage

register = template.Library()


def _get_menu_index_name(setting_name, default):
    return getattr(settings, setting_name, default)


def _get_menu_search_pages():
    live = SearchPage.objects.live().select_related("data_source")
    scientific_index = _get_menu_index_name(
        "OP_INDEX_SCIENTIFIC_PRODUCTION",
        "scientific_production",
    )
    social_index = _get_menu_index_name(
        "OP_INDEX_SOCIAL_PRODUCTION",
        "social_production",
    )

    scientific_page = live.filter(data_source__index_name=scientific_index).first()
    social_page = live.filter(data_source__index_name=social_index).first()

    return {
        "scientific": scientific_page,
        "social": social_page,
    }


@register.simple_tag
def get_menu_context(request):
    """Compute menu context booleans from the current request.

    This keeps complex/duplicated Django-template boolean logic out of templates.
    """

    path = getattr(request, "path", "") or ""
    get_params = getattr(request, "GET", None)
    menu_scope = get_params.get("menu_scope", "") if get_params is not None else ""
    is_search_page_path = "/search-page" in path or "/search/page/" in path
    is_indicators_path = path.startswith("/indicators/")
    social_indicator_index = _get_menu_index_name(
        "OP_INDEX_SOCIAL_PRODUCTION",
        "social_production",
    )
    scientific_indicator_index = _get_menu_index_name(
        "OP_INDEX_SCIENTIFIC_PRODUCTION",
        "scientific_production",
    )
    is_indicators_social_path = path.startswith(f"/indicators/{social_indicator_index}")
    menu_search_pages = _get_menu_search_pages()

    is_about_section = (
        "/sobre/" in path
        or "/sobre-indicadores" in path
        or "/sobre-observacao" in path
        or "/sobre-busca-bibliografica" in path
    )

    is_about_indicadores = "/sobre-indicadores" in path
    is_about_observacao = "/sobre-observacao" in path
    is_about_busca = "/sobre-busca-bibliografica" in path

    is_about_producao_cientifica = "/sobre-producao-cientifica" in path
    is_about_producao_social = "/sobre-producao-social" in path

    is_social_context = (
        is_about_producao_social
        or is_indicators_social_path
        or str(menu_scope).startswith("evolucao-producaosocial-")
        or (path.startswith("/searchv2") and bool(menu_scope))
    )

    is_scientific_context = (
        is_about_producao_cientifica
        or (is_indicators_path and not is_indicators_social_path)
        or str(menu_scope).startswith("evolucao-producao-")
        or (path.startswith("/searchv2") and not bool(menu_scope))
    )
    is_social_observation_active = str(menu_scope).startswith("evolucao-producaosocial-")
    is_scientific_observation_active = str(menu_scope).startswith("evolucao-producao-")

    return {
        "path": path,
        "menu_scope": menu_scope,
        "is_search_page_path": is_search_page_path,
        "is_indicators_path": is_indicators_path,
        "is_about_section": is_about_section,
        "is_about_indicadores": is_about_indicadores,
        "is_about_observacao": is_about_observacao,
        "is_about_busca": is_about_busca,
        "is_about_producao_cientifica": is_about_producao_cientifica,
        "is_about_producao_social": is_about_producao_social,
        "is_social_context": is_social_context,
        "is_scientific_context": is_scientific_context,
        "is_social_observation_active": is_social_observation_active,
        "is_scientific_observation_active": is_scientific_observation_active,
        "social_indicator_index": social_indicator_index,
        "scientific_indicator_index": scientific_indicator_index,
        "search_page_social": menu_search_pages["social"],
        "search_page_scientific": menu_search_pages["scientific"],
    }
