/**
 * assets/0_theme_pre_init.js
 * ==========================
 * Loaded first (alphabetically) to pre-emptively apply theme variables.
 * Avoids the brief light/white flash on initial load.
 */
(function () {
    let theme = 'dark'; // Default fallback
    try {
        const stored = localStorage.getItem('theme-store');
        if (stored) {
            // Dash serializes values as JSON strings
            const parsed = JSON.parse(stored);
            if (parsed === 'dark' || parsed === 'light') {
                theme = parsed;
            }
        } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
            theme = 'light';
        }
    } catch (e) {
        // Fallback to dark if any storage exceptions occur
    }
    
    document.documentElement.setAttribute('data-theme', theme);
    if (document.body) {
        document.body.setAttribute('data-theme', theme);
    }
})();
