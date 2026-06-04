from indicator.models import DocumentChartPage


def get_first_live_url(page_model, fallback=""):
    page = page_model.objects.filter(live=True).first()
    return page.url if page else fallback


def get_indicator_nav_urls(current_page, thematic_page_model, global_page_model):
    current_url = current_page.url
    return {
        "indicator_home_url": get_first_live_url(DocumentChartPage, current_url),
        "journal_thematic_url": (
            current_url
            if isinstance(current_page, thematic_page_model)
            else get_first_live_url(thematic_page_model, current_url)
        ),
        "journal_global_url": (
            current_url
            if isinstance(current_page, global_page_model)
            else get_first_live_url(global_page_model, current_url)
        ),
    }


def get_journal_profile_url(profile_page_model, language_code=None):
    qs = profile_page_model.objects.filter(live=True)

    if language_code:
        localized = qs.filter(locale__language_code=language_code).first()
        if localized:
            return localized.url

    page = qs.first()
    return page.url if page else ""
