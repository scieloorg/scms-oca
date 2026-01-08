document.querySelectorAll('.toggle-not').forEach(button => {
    button.addEventListener('click', () => {
        const group = button.closest('.input-group');
        if (!group) return;
        group.classList.toggle('not-active');
        const status = button.getAttribute("aria-pressed") === "true";
        button.setAttribute('aria-pressed', !status);
    });
});
