/**
 * assets/command_palette.js
 * =========================
 * Implements a premium, keyboard-accessible (CMD+K) Command Palette modal.
 * Supports arrow-key navigation, fuzzy search, and action dispatching.
 * Dynamically injected into the DOM to keep Python layouts untouched.
 *
 * Dynamic Ticker Integration:
 * Reads `palette-ticker-store` (Dash dcc.Store) for live holdings/watchlist
 * tickers and merges them into the command list as grouped search results.
 */

(function () {
    const staticCommands = [
        { id: 'nav_portfolio', label: 'Go to Portfolio Dashboard', icon: '📊', type: 'nav', target: '/', group: 'Navigation' },
        { id: 'nav_positions', label: 'Go to Positions Overview', icon: '💼', type: 'nav', target: '/positions', group: 'Navigation' },
        { id: 'nav_watchlist', label: 'Go to Watchlist Manager', icon: '⭐', type: 'nav', target: '/watchlist', group: 'Navigation' },
        { id: 'nav_insights', label: 'Go to Smart Insights & Signals', icon: '🧠', type: 'nav', target: '/intelligence', group: 'Navigation' },
        { id: 'nav_deepdive', label: 'Go to Deep Dive (Analytics)', icon: '📉', type: 'nav', target: '/analytics', group: 'Navigation' },
        { id: 'nav_assistant', label: 'Go to AI Chat Assistant', icon: '💬', type: 'nav', target: '/ai-analyst', group: 'Navigation' },
        { id: 'nav_settings', label: 'Go to Settings & Profile', icon: '⚙', type: 'nav', target: '/settings', group: 'Navigation' },
        { id: 'action_theme', label: 'Toggle Dark / Light Theme', icon: '🌓', type: 'action', target: 'theme-toggle-hidden', shortcut: '⌘T', group: 'Actions' },
        { id: 'action_refresh', label: 'Refresh Live Portfolio Data', icon: '🔄', type: 'action', target: 'refresh-btn-hidden', shortcut: '⌘R', group: 'Actions' },
        { id: 'action_pdf', label: 'Export PDF Summary Report', icon: '📥', type: 'action', target: 'pdf-btn-hidden', group: 'Actions' },
        { id: 'action_signals', label: 'Trigger Global Signal Analysis', icon: '🤖', type: 'action', target: 'global-generate-signals-btn', group: 'Actions' }
    ];

    const RECENT_KEY = 'folio_cmd_recent';
    const MAX_RECENT = 5;

    let modal = null;
    let input = null;
    let resultsContainer = null;
    let selectedIndex = 0;
    let filteredCommands = [];

    // ── Recently Used ──────────────────────────────────────────────────────
    function getRecent() {
        try {
            return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
        } catch { return []; }
    }

    function addRecent(cmdId) {
        let recent = getRecent().filter(id => id !== cmdId);
        recent.unshift(cmdId);
        if (recent.length > MAX_RECENT) recent = recent.slice(0, MAX_RECENT);
        try { localStorage.setItem(RECENT_KEY, JSON.stringify(recent)); } catch {}
    }

    // ── Dynamic Ticker Commands ────────────────────────────────────────────
    function getTickerCommands() {
        const data = window.paletteTickerData || [];
        if (!Array.isArray(data)) return [];

        const cmds = [];
        const seen = new Set();
        data.forEach(function(item) {
            if (!item.ticker || seen.has(item.ticker + '_' + item.group)) return;
            seen.add(item.ticker + '_' + item.group);

            if (item.group === 'holdings') {
                const pnl = item.pnl_pct || 0;
                const sign = pnl >= 0 ? '+' : '';
                const signalBadge = item.signal ? ` · ${item.signal}` : '';
                cmds.push({
                    id: 'ticker_h_' + item.ticker,
                    label: `${item.ticker} — ${sign}${pnl.toFixed(1)}%${signalBadge}`,
                    icon: '📈',
                    type: 'ticker',
                    target: item.ticker,
                    page: '/positions',
                    group: 'Holdings'
                });
            } else if (item.group === 'watchlist') {
                cmds.push({
                    id: 'ticker_w_' + item.ticker,
                    label: `${item.ticker} in Watchlist`,
                    icon: '⭐',
                    type: 'ticker',
                    target: item.ticker,
                    page: '/watchlist',
                    group: 'Watchlist'
                });
            }
        });
        return cmds;
    }

    function getAllCommands() {
        return [...getTickerCommands(), ...staticCommands];
    }

    // ── DOM Injection ──────────────────────────────────────────────────────
    function injectDOM() {
        if (document.getElementById('command-palette-modal')) return;

        modal = document.createElement('div');
        modal.id = 'command-palette-modal';
        modal.innerHTML = `
            <div class="command-palette-box">
                <div class="command-palette-header">
                    <span class="command-palette-search-icon">🔍</span>
                    <input type="text" class="command-palette-input" placeholder="Search tickers, pages, actions..." autocomplete="off" spellcheck="false" />
                </div>
                <div class="command-palette-results"></div>
                <div class="command-palette-footer">
                    <div class="command-palette-help">
                        <span><span class="command-palette-kbd">↑↓</span> to navigate</span>
                        <span><span class="command-palette-kbd">Enter</span> to select</span>
                    </div>
                    <span><span class="command-palette-kbd">ESC</span> to close</span>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        input = modal.querySelector('.command-palette-input');
        resultsContainer = modal.querySelector('.command-palette-results');

        // Setup event listeners
        input.addEventListener('input', handleSearch);
        modal.addEventListener('click', handleOutsideClick);
        modal.addEventListener('keydown', handleKeydown);
    }

    function toggleOpen() {
        if (!modal) injectDOM();

        const isOpen = modal.classList.toggle('open');
        if (isOpen) {
            selectedIndex = 0;
            input.value = '';
            // Show recently used first, then all commands
            const allCmds = getAllCommands();
            const recent = getRecent();
            if (recent.length > 0) {
                const recentCmds = recent
                    .map(id => allCmds.find(c => c.id === id))
                    .filter(Boolean)
                    .map(c => ({ ...c, group: 'Recent' }));
                filteredCommands = [...recentCmds, ...allCmds];
            } else {
                filteredCommands = allCmds;
            }
            renderResults();
            setTimeout(() => input.focus(), 50);
        }
    }

    function renderResults() {
        if (!resultsContainer) return;
        resultsContainer.innerHTML = '';

        if (filteredCommands.length === 0) {
            resultsContainer.innerHTML = `
                <div style="padding: 20px; text-align: center; color: var(--t-sec); font-size: 13px;">
                    No results found. Try a different search.
                </div>
            `;
            return;
        }

        let currentGroup = null;
        let flatIndex = 0;

        filteredCommands.forEach((cmd) => {
            // Group header
            if (cmd.group && cmd.group !== currentGroup) {
                currentGroup = cmd.group;
                const header = document.createElement('div');
                header.className = 'cp-group-label';
                header.textContent = currentGroup;
                resultsContainer.appendChild(header);
            }

            const item = document.createElement('div');
            const idx = flatIndex;
            item.className = `command-palette-item ${idx === selectedIndex ? 'selected' : ''}`;
            item.setAttribute('data-index', idx);
            item.innerHTML = `
                <div class="command-palette-item-left">
                    <span class="command-palette-item-icon">${cmd.icon}</span>
                    <span class="command-palette-item-label">${cmd.label}</span>
                </div>
                ${cmd.shortcut ? `<span class="command-palette-item-shortcut">${cmd.shortcut}</span>` : ''}
            `;

            item.addEventListener('mouseenter', () => {
                selectedIndex = idx;
                updateSelectionStyles();
            });

            item.addEventListener('click', () => {
                executeCommand(cmd);
            });

            resultsContainer.appendChild(item);
            flatIndex++;
        });

        // Ensure selected item is scrolled into view
        const activeItem = resultsContainer.querySelector('.selected');
        if (activeItem) {
            activeItem.scrollIntoView({ block: 'nearest' });
        }
    }

    function updateSelectionStyles() {
        const items = resultsContainer.querySelectorAll('.command-palette-item');
        items.forEach((item) => {
            const idx = parseInt(item.getAttribute('data-index'), 10);
            item.classList.toggle('selected', idx === selectedIndex);
        });
    }

    function handleSearch() {
        const query = input.value.toLowerCase().trim();
        const allCmds = getAllCommands();
        if (query === '') {
            const recent = getRecent();
            if (recent.length > 0) {
                const recentCmds = recent
                    .map(id => allCmds.find(c => c.id === id))
                    .filter(Boolean)
                    .map(c => ({ ...c, group: 'Recent' }));
                filteredCommands = [...recentCmds, ...allCmds];
            } else {
                filteredCommands = allCmds;
            }
        } else {
            filteredCommands = allCmds.filter(cmd =>
                cmd.label.toLowerCase().includes(query) ||
                (cmd.target && cmd.target.toLowerCase().includes(query)) ||
                (cmd.shortcut && cmd.shortcut.toLowerCase().includes(query))
            );
        }
        selectedIndex = 0;
        renderResults();
    }

    function handleOutsideClick(e) {
        if (e.target === modal) {
            toggleOpen();
        }
    }

    function handleKeydown(e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            toggleOpen();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = (selectedIndex + 1) % filteredCommands.length;
            updateSelectionStyles();
            const activeItem = resultsContainer.querySelector('.selected');
            if (activeItem) activeItem.scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = (selectedIndex - 1 + filteredCommands.length) % filteredCommands.length;
            updateSelectionStyles();
            const activeItem = resultsContainer.querySelector('.selected');
            if (activeItem) activeItem.scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (filteredCommands[selectedIndex]) {
                executeCommand(filteredCommands[selectedIndex]);
            }
        }
    }

    function executeCommand(cmd) {
        addRecent(cmd.id);
        toggleOpen(); // Close palette first

        if (cmd.type === 'nav') {
            // Find active anchor in the global header to route natively via Dash SPA
            const navLinks = Array.from(document.querySelectorAll('.nav-link'));
            const targetLink = navLinks.find(link => link.getAttribute('href') === cmd.target);

            if (targetLink) {
                targetLink.click();
            } else {
                // Fallback to direct location update if header is absent
                window.location.pathname = cmd.target;
            }
        } else if (cmd.type === 'action') {
            // Try triggering the click on the ID element
            const el = document.getElementById(cmd.target);
            if (el) {
                el.click();
            }
        } else if (cmd.type === 'ticker') {
            // Navigate to the relevant page, then select the ticker
            const navLinks = Array.from(document.querySelectorAll('.nav-link'));
            const targetLink = navLinks.find(link => link.getAttribute('href') === cmd.page);

            if (targetLink) {
                targetLink.click();
            } else {
                window.location.pathname = cmd.page;
            }

            // After navigation, try to select the ticker card
            // Use a delay to wait for Dash to render the page
            setTimeout(() => {
                selectTickerOnPage(cmd.target, cmd.page);
            }, 800);
        }
    }

    function selectTickerOnPage(ticker, page) {
        if (page === '/positions') {
            // Click the position card for the ticker
            const cards = document.querySelectorAll('[id*="pos-card"]');
            cards.forEach(card => {
                try {
                    const idObj = JSON.parse(card.id);
                    if (idObj && idObj.index === ticker) {
                        card.click();
                    }
                } catch {
                    // Pattern-matched IDs are JSON strings in the DOM
                    if (card.getAttribute('data-ticker') === ticker) {
                        card.click();
                    }
                }
            });
        } else if (page === '/watchlist') {
            // Click the watchlist row for the ticker
            const rows = document.querySelectorAll('[data-ticker]');
            rows.forEach(row => {
                if (row.getAttribute('data-ticker') === ticker) {
                    row.click();
                }
            });
        }
    }

    // Global Key Bindings for opening the palette and global shortcuts
    document.addEventListener('keydown', function (e) {
        // Toggle open on CMD+K (macOS) or CTRL+K (Windows/Linux)
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            toggleOpen();
        }

        // Trigger action_theme on CMD+T (macOS) or CTRL+T (Windows/Linux)
        if ((e.metaKey || e.ctrlKey) && e.key === 't') {
            e.preventDefault();
            const el = document.getElementById('theme-toggle-hidden');
            if (el) el.click();
        }

        // Trigger action_refresh on CMD+R (macOS) or CTRL+R (Windows/Linux)
        if ((e.metaKey || e.ctrlKey) && e.key === 'r') {
            e.preventDefault();
            const el = document.getElementById('refresh-btn-hidden');
            if (el) el.click();
        }
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectDOM);
    } else {
        injectDOM();
    }
})();
