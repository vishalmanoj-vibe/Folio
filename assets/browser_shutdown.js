/**
 * browser_shutdown.js
 * ===================
 * Sends a shutdown signal to the Folio server when the user closes the
 * browser tab or window.
 *
 * Mechanism:
 *   1. On `beforeunload`, fire a sendBeacon to /shutdown?token=<TOKEN>.
 *   2. The server starts a 3-second countdown timer before killing itself.
 *   3. On Dash SPA navigation (dcc.Location URL changes), fire a cancel
 *      beacon to /shutdown/cancel?token=<TOKEN> to abort the countdown.
 *
 * This means: navigating between pages or refreshing does NOT shut the server
 * down. Only closing the final tab/window does.
 *
 * NOTE: navigator.sendBeacon is used (not fetch) because it is guaranteed to
 * be dispatched even as the page is being destroyed.
 */
(function () {
    "use strict";

    // Read the shutdown token injected into the page's <meta> tag.
    function getShutdownToken() {
        const meta = document.querySelector('meta[name="shutdown-token"]');
        return meta ? meta.getAttribute("content") : null;
    }

    /**
     * Fires a cancel request so the server does not shut down.
     * Called whenever Dash triggers an internal SPA navigation.
     */
    function sendCancelBeacon() {
        const token = getShutdownToken();
        if (!token) return;
        const url = "/shutdown/cancel?token=" + encodeURIComponent(token);
        navigator.sendBeacon(url);
    }

    /**
     * Fires the shutdown beacon when the user actually closes the tab/window.
     */
    function sendShutdownBeacon() {
        const token = getShutdownToken();
        if (!token) return;
        const url = "/shutdown?token=" + encodeURIComponent(token);
        navigator.sendBeacon(url);
    }

    // ── beforeunload listener ──────────────────────────────────────────────────
    // Fires on every close/refresh/navigate. We always send the shutdown beacon.
    // The server-side debounce + cancel mechanism handles false positives.
    window.addEventListener("beforeunload", function () {
        sendShutdownBeacon();
    });

    // ── Dash SPA navigation detector ──────────────────────────────────────────
    // Dash changes the URL via History API without a full page reload.
    // We detect this and fire a cancel beacon immediately, which aborts the
    // 3-second server countdown before it triggers.
    //
    // Strategy: intercept history.pushState / history.replaceState and also
    // listen for the 'popstate' event.

    function wrapHistoryMethod(method) {
        const original = history[method];
        history[method] = function () {
            // Dash internal navigation — cancel any pending shutdown
            sendCancelBeacon();
            return original.apply(this, arguments);
        };
    }

    wrapHistoryMethod("pushState");
    wrapHistoryMethod("replaceState");

    window.addEventListener("popstate", function () {
        sendCancelBeacon();
    });

})();
