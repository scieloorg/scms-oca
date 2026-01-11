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
