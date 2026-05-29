/**
 * assets/sync_hover.js
 * ====================
 * Implements latency-free, clientside hover and crosshair synchronization
 * across sibling time-series Plotly charts.
 * Leverages MutationObserver to survive Dash page loads and dynamic refreshes.
 */

(function () {
    let isSyncing = false;

    // Attach hover sync listeners to Plotly elements
    function setupSync() {
        const plots = Array.from(document.querySelectorAll('.js-plotly-plot'));
        if (plots.length < 2) return;

        plots.forEach(plot => {
            // Remove existing listeners to avoid duplicate bindings
            plot.removeAllListeners('plotly_hover');
            plot.removeAllListeners('plotly_unhover');

            plot.on('plotly_hover', function (eventdata) {
                if (isSyncing) return;
                isSyncing = true;

                try {
                    if (eventdata && eventdata.points && eventdata.points.length > 0) {
                        const xVal = eventdata.points[0].x;
                        
                        // Sync hover across all other plots on the same page
                        plots.forEach(targetPlot => {
                            if (targetPlot !== plot) {
                                // Trigger Unified Hover at same X position
                                Plotly.Fx.hover(targetPlot, { xval: xVal }, ['xy', 'x2y2']);
                            }
                        });
                    }
                } catch (err) {
                    // Fail silently to prevent crashing browser interactions
                } finally {
                    isSyncing = false;
                }
            });

            plot.on('plotly_unhover', function () {
                if (isSyncing) return;
                isSyncing = true;

                try {
                    plots.forEach(targetPlot => {
                        if (targetPlot !== plot) {
                            Plotly.Fx.unhover(targetPlot);
                        }
                    });
                } catch (err) {
                    // Ignore errors on unhover
                } finally {
                    isSyncing = false;
                }
            });
        });
    }

    // Monitor page mutations to re-bind when charts are destroyed and recreated
    const observer = new MutationObserver(() => {
        setupSync();
    });

    document.addEventListener('DOMContentLoaded', () => {
        setupSync();
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
})();
