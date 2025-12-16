/* your custom js go here */

$('.lang-select').change(function(){
    let url = $(this).find(':selected').attr('data-url');
    $('#language').val($(this).val());
    $('#form_lang').submit();
});

// Oculta o header quando o usuário rola para baixo e mostra ao rolar para cima.
// A classe no <body> controla o CSS (ver custom.css).
(function () {
    // Auto-hide desativado: estava causando tremor/jitter no header.
    // Mantém o header sempre visível.
    document.body.classList.remove('header-hidden');
})();