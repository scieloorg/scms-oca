from wagtail import hooks


@hooks.register("register_icons")
def register_icons(icons):
    """
    Register custom icons for indicator pages.
    Add any custom SVG icons here if needed.
    """
    return icons
