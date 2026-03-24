// Custom JavaScript for Tradier Copy Bot

// Dark/Light mode body class toggle
document.addEventListener('DOMContentLoaded', function() {
    var mantine = document.querySelector('[data-mantine-color-scheme]');
    if (mantine) {
        var scheme = mantine.getAttribute('data-mantine-color-scheme');
        var bsTheme = scheme === 'dark' ? 'dark' : 'light';
        document.body.setAttribute('data-bs-theme', bsTheme);
        var mainPage = document.getElementById('main_page');
        if (mainPage) { mainPage.setAttribute('data-bs-theme', bsTheme); }
    }
});
