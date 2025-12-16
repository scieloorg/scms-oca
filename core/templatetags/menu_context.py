from __future__ import annotations

from django import template

register = template.Library()


@register.simple_tag
def get_menu_context(request):
    """Compute menu context booleans from the current request.

    This keeps complex/duplicated Django-template boolean logic out of templates.
    """

    path = getattr(request, "path", "") or ""
    get_params = getattr(request, "GET", None)
    menu_scope = get_params.get("menu_scope", "") if get_params is not None else ""

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
        or path.startswith("/indicators/social/")
        or str(menu_scope).startswith("evolucao-producaosocial-")
        or (path.startswith("/searchv2") and bool(menu_scope))
    )

    is_scientific_context = (
        is_about_producao_cientifica
        or path.startswith("/indicators/world/")
        or str(menu_scope).startswith("evolucao-producao-")
        or (path.startswith("/searchv2") and not bool(menu_scope))
    )

    return {
        "path": path,
        "menu_scope": menu_scope,
        "is_about_section": is_about_section,
        "is_about_indicadores": is_about_indicadores,
        "is_about_observacao": is_about_observacao,
        "is_about_busca": is_about_busca,
        "is_about_producao_cientifica": is_about_producao_cientifica,
        "is_about_producao_social": is_about_producao_social,
        "is_social_context": is_social_context,
        "is_scientific_context": is_scientific_context,
    }
