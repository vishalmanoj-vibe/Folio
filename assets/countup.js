/**
 * assets/countup.js
 * ====================
 * Automatically detects changes inside elements styled with .stat-card-value
 * and interpolates values smoothly client-side.
 * Uses event delegation and MutationObservers to survive Dash DOM refreshes.
 */

(function () {
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            let target = mutation.target;
            if (mutation.type === 'characterData') {
                target = mutation.target.parentElement;
            }

            const statValueEl = target.closest ? target.closest('.stat-card-value') : null;
            if (statValueEl) {
                if (statValueEl.dataset.animating) continue;
                animateValue(statValueEl);
            }
        }
    });

    function animateValue(el) {
        const text = el.innerText.trim();
        // Regex to extract the first match that looks like a decimal number (can include commas and decimals)
        const matches = text.match(/[\d,.]+/);
        if (!matches) return;

        const rawString = matches[0];
        const rawNum = parseFloat(rawString.replace(/,/g, ''));
        if (isNaN(rawNum)) return;

        // Extract prefix and suffix
        const parts = text.split(rawString);
        const prefix = parts[0] || '';
        const suffix = parts[1] || '';

        // Get starting number
        const start = el.dataset.prevVal ? parseFloat(el.dataset.prevVal) : 0;
        const end = rawNum;
        if (start === end) return;

        // Set state flags to prevent infinite loops when we update innerText
        el.dataset.animating = 'true';
        el.dataset.prevVal = end.toString();

        let current = start;
        const duration = 250; // Snappy 250ms duration
        const frameRate = 60;
        const totalFrames = Math.round((duration / 1000) * frameRate);
        const step = (end - start) / totalFrames;
        let frameCount = 0;

        // Determine decimal places from destination string
        const decimalParts = rawString.split('.');
        const decimals = decimalParts.length > 1 ? decimalParts[1].length : 0;

        function update() {
            current += step;
            frameCount++;

            if (frameCount >= totalFrames) {
                // Ensure exact ending value and format
                el.innerText = text;
                delete el.dataset.animating;
            } else {
                // Format intermediate values with commas and decimals matching target
                const formatted = current.toLocaleString(undefined, {
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals
                });
                el.innerText = prefix + formatted + suffix;
                requestAnimationFrame(update);
            }
        }

        requestAnimationFrame(update);
    }

    document.addEventListener('DOMContentLoaded', () => {
        // Observe subtree modifications across the entire document
        observer.observe(document.body, {
            characterData: true,
            subtree: true,
            childList: true
        });

        // Initialize any values already present at page load
        document.querySelectorAll('.stat-card-value').forEach(el => {
            const text = el.innerText.trim();
            const matches = text.match(/[\d,.]+/);
            if (matches) {
                const rawNum = parseFloat(matches[0].replace(/,/g, ''));
                if (!isNaN(rawNum)) {
                    el.dataset.prevVal = rawNum.toString();
                }
            }
        });
    });
})();
