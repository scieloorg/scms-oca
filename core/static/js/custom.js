/* your custom js go here */

$('.lang-select').change(function(){
    let url = $(this).find(':selected').attr('data-url');
    $('#language').val($(this).val());
    $('#form_lang').submit();
});

// Oculta o header quando o usuário rola para baixo e mostra ao rolar para cima.
// A classe no <body> controla o CSS (ver custom.css).
(function () {
    // Auto-hide desativado.
    document.body.classList.remove('header-hidden');
})();

// Mobile menu: em itens com submenu, o toque no rótulo também abre/fecha
// o acordeão (além do botão de seta), evitando navegação acidental imediata.
(function () {
    const mobileQuery = window.matchMedia('(max-width: 991.98px)');
    const rootSelector = '.primary-menu .mobile-primary-menu';
    const submenuSelector = '.sub-menu-container, .mega-menu-content';
    const triggerSelector = '.sub-menu-trigger';
    const menuSyncDelay = 220;
    const flatMenuItemSelector = '.mobile-flat-menu .flat-menu .menu-item';

    function syncTriggerStates(rootElement) {
        const root = rootElement && rootElement.length ? rootElement : $(rootSelector);

        root.find('.menu-item').each(function () {
            const menuItem = $(this);
            const submenu = menuItem.children(submenuSelector);
            const trigger = menuItem.children(triggerSelector);

            if (!submenu.length || !trigger.length) {
                return;
            }

            const isOpen = submenu.is(':visible');
            trigger.toggleClass('icon-rotate-90', isOpen);
            menuItem.toggleClass('submenu-open', isOpen);
        });
    }

    function toggleFlatMenuItem(menuItem) {
        const submenu = menuItem.children(submenuSelector);
        const trigger = menuItem.children(triggerSelector);
        if (!submenu.length || !trigger.length) {
            return false;
        }

        const shouldOpen = !submenu.is(':visible');
        const siblingItems = menuItem.siblings('.menu-item');

        siblingItems.children(submenuSelector).filter(':visible').stop(true, true).slideUp(menuSyncDelay);
        siblingItems.children(triggerSelector).removeClass('icon-rotate-90');
        siblingItems.removeClass('submenu-open');

        submenu.stop(true, true).slideToggle(menuSyncDelay);
        trigger.toggleClass('icon-rotate-90', shouldOpen);
        menuItem.toggleClass('submenu-open', shouldOpen);

        return true;
    }

    $(document).on('click', `${rootSelector} .menu-item > .menu-link`, function (event) {
        if (!mobileQuery.matches) {
            return;
        }

        const flatMenuItem = $(this).closest(flatMenuItemSelector);
        if (flatMenuItem.length) {
            const toggled = toggleFlatMenuItem(flatMenuItem);
            if (toggled) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
            return;
        }

        const menuItem = $(this).parent('.menu-item');
        const submenu = menuItem.children(submenuSelector);
        if (!submenu.length) {
            return;
        }

        event.preventDefault();
        const trigger = menuItem.children('.sub-menu-trigger');
        if (trigger.length) {
            trigger.trigger('click');
            const root = menuItem.closest(rootSelector);
            window.setTimeout(function () {
                syncTriggerStates(root);
            }, menuSyncDelay);
        }
    });

    $(document).on('click', `${rootSelector} .menu-item > .sub-menu-trigger`, function (event) {
        if (!mobileQuery.matches) {
            return;
        }

        const flatMenuItem = $(this).closest(flatMenuItemSelector);
        if (flatMenuItem.length) {
            const root = $(this).closest(rootSelector);
            window.setTimeout(function () {
                syncTriggerStates(root);
            }, menuSyncDelay);
            return;
        }

        const root = $(this).closest(rootSelector);
        window.setTimeout(function () {
            syncTriggerStates(root);
        }, menuSyncDelay);
    });
})();
