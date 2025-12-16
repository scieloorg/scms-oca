/* your custom js go here */

$('.lang-select').change(function(){
    let url = $(this).find(':selected').attr('data-url');
    $('#language').val($(this).val());
    $('#form_lang').submit();
});

// Oculta o header quando o usuário rola para baixo e mostra ao rolar para cima.
// A classe no <body> controla o CSS (ver custom.css).
(function () {
    const headerWrap = document.getElementById('header-wrap');
    if (!headerWrap) return;

    const body = document.body;
    let lastScrollY = window.scrollY || 0;
    const delta = 10; // ignora micro-movimentos
    const threshold = 120; // só esconde depois de passar uma altura mínima
    let ticking = false;

    function applyHeaderVisibility(currentScrollY) {
        // Se o menu mobile estiver aberto, não esconder (evita UX estranha)
        if (body.classList.contains('primary-menu-open')) {
            body.classList.remove('header-hidden');
            lastScrollY = currentScrollY;
            return;
        }

        if (currentScrollY <= 0) {
            body.classList.remove('header-hidden');
            lastScrollY = currentScrollY;
            return;
        }

        if (Math.abs(currentScrollY - lastScrollY) < delta) {
            lastScrollY = currentScrollY;
            return;
        }

        if (currentScrollY > lastScrollY && currentScrollY > threshold) {
            body.classList.add('header-hidden');
        } else {
            body.classList.remove('header-hidden');
        }

        lastScrollY = currentScrollY;
    }

    function onScroll() {
        const currentScrollY = window.scrollY || 0;
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(function () {
            applyHeaderVisibility(currentScrollY);
            ticking = false;
        });
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    applyHeaderVisibility(window.scrollY || 0);
})();