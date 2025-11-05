const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('toggle-btn');
const themeToggle = document.getElementById('theme-toggle');

toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});

themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
});
