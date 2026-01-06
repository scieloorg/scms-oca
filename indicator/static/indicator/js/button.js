document.querySelectorAll('.toggle-not').forEach(button => {
    button.addEventListener('click', () => {
        const group = button.closest('.input-group');
        group.classList.toggle('not-active');
    });
});
