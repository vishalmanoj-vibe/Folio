/**
 * assets/spotlight.js
 * ====================
 * Tracks mouse movements over cards and dynamically updates CSS custom variables
 * to apply hardware-accelerated spotlight gradient effects.
 * Uses event delegation for maximum performance and compatibility with Dash DOM updates.
 */

(function () {
    document.addEventListener('mousemove', function (e) {
        const card = e.target.closest('.stat-card-container, .card');
        if (!card) return;

        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        card.style.setProperty('--mouse-x', x + 'px');
        card.style.setProperty('--mouse-y', y + 'px');
    });
})();
