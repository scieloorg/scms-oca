document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.toggle-not').forEach(button => {
        button.addEventListener('click', () => {
            const group = button.closest('.input-group');
            if (!group) return;
            group.classList.toggle('not-active');
            const status = button.getAttribute("aria-pressed") === "true";
            button.setAttribute('aria-pressed', !status);
        });
    });
});

// Django JS i18n fallback (jsi18n usually loads this)
if (typeof window !== 'undefined') {
    if (typeof window.gettext !== 'function') {
        window.gettext = function (msgid) { return msgid; };
    }
}

/* Função para facilitar a construção de objeto Datepicker */
function setupDatePicker(fieldId, format="yyyy", view_mode="years", min_view_mode="years", autoclose=true, start_date="1900", end_date="2100") {
    try {
        const dateElement = document.getElementById(fieldId);
        if (dateElement) {
            $(dateElement).datepicker({
                format: format,
                viewMode: view_mode,
                minViewMode: min_view_mode,
                autoclose: autoclose,
                startDate: start_date,
                endDate: end_date,
            });
        }
    } catch (error) {
        console.log('Error initializing datepicker for field', fieldId, '. Error: ', error)
    }
}

/* Função para facilitar construção de objeto Select2 do tipo single */
function setupSelect2Single(fieldId, placeholder="", allow_search=false, allow_clear=true, width="") {
    try {
        const selectElement = document.getElementById(fieldId);
        if (selectElement) {
            let opts = {theme: 'bootstrap-5', width: 'auto'}
            if (allow_clear) {opts.allowClear = allow_clear;}
            if (!allow_search) {opts.minimumResultsForSearch = Infinity;}
            if (placeholder !== "") {opts.placeholder = placeholder;}
            if (width !== "") {opts.width = width;}
            $(selectElement).select2(opts).on('select2:open', function (e) {
                document.querySelector(`[aria-controls="select2-${e.target.id}-results"]`).focus();
            });
        }
    } catch (error) {
        console.error('Error initializing Select2 for field', fieldId, '. Error: ', error)
    }
}

/* Função para facilitar construção de objeto Select2 do tipo múltiplo */
function setupSelect2Multiple(fieldId, placeholder="", allow_clear=true, width="") {
    try {
        const selectElement = document.getElementById(fieldId);
        if (selectElement) {
            let opts = {theme: 'bootstrap-5'}
            if (allow_clear) {opts.allowClear = allow_clear;}
            if (placeholder !== "") {opts.placeholder = placeholder;}
            if (width !== "") {opts.width = width;}
            $(selectElement).select2(opts).on('select2:open', function (e) {
                document.querySelector(`[aria-controls="select2-${e.target.id}-results"]`).focus();
            });
        }
    } catch (error) {
        console.error('Error initializing Select2 for field', fieldId, '. Error: ', error)
    }
}

/* Função para facilitar construção de objeto Select2 com busca em índice */
function setupSelect2SearchAsYouType(fieldId, data_source, placeholder="Start typing to search...", allow_clear=true) {
    try {
        const selectElement = document.getElementById(fieldId);
        if (selectElement) {
            $(selectElement).select2(
                {
                    ajax: {
                        url: `/search-gateway/search-item/?field_name=${fieldId}&data_source=${data_source}`,
                        dataType: 'json',
                        delay: 300,
                        data: params => ({q: params.term}),
                        processResults: data => {
                            return {
                                results: data.results.map(item => ({
                                    id: item.key,
                                    text: item.key
                                }))
                            };
                        }
                    },
                    minimumInputLength: 2,
                    placeholder: placeholder,
                    theme: 'bootstrap-5',
                    allowClear: allow_clear,
                }
            ).on('select2:open', function (e) {
                document.querySelector(`[aria-controls="select2-${e.target.id}-results"]`).focus();
            });
        }
    } catch (error) {
        console.error('Error initializing Select2 for field', fieldId, 'in data source', data_source, '. Error: ', error);
    }
}
