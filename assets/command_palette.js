/**
 * assets/command_palette.js
 * =========================
 * Implements a premium, keyboard-accessible (CMD+K) Command Palette modal.
 * Supports arrow-key navigation, fuzzy search, and action dispatching.
 * Dynamically injected into the DOM to keep Python layouts untouched.
 */

(function () {
    const commands = [
        { id: 'nav_portfolio', label: 'Go to Portfolio Dashboard', icon: '📊', type: 'nav', target: '/' },
        { id: 'nav_positions', label: 'Go to Positions Overview', icon: '💼', type: 'nav', target: '/positions' },
        { id: 'nav_watchlist', label: 'Go to Watchlist Manager', icon: '⭐', type: 'nav', target: '/watchlist' },
        { id: 'nav_insights', label: 'Go to Smart Insights & Signals', icon: '🧠', type: 'nav', target: '/intelligence' },
        { id: 'nav_deepdive', label: 'Go to Deep Dive (Analytics)', icon: '📉', type: 'nav', target: '/analytics' },
        { id: 'nav_assistant', label: 'Go to AI Chat Assistant', icon: '💬', type: 'nav', target: '/ai-analyst' },
        { id: 'action_theme', label: 'Toggle Dark / Light Theme', icon: '🌓', type: 'action', target: 'theme-toggle', shortcut: '⌘T' },
        { id: 'action_refresh', label: 'Refresh Live Portfolio Data', icon: '🔄', type: 'action', target: 'refresh-btn', shortcut: '⌘R' },
        { id: 'action_pdf', label: 'Export PDF Summary Report', icon: '📥', type: 'action', target: 'pdf-btn' },
        { id: 'action_signals', label: 'Trigger Global Signal Analysis', icon: '🤖', type: 'action', target: 'global-generate-signals-btn' }
    ];

    let modal = null;
    let input = null;
    let resultsContainer = null;
    let selectedIndex = 0;
    let filteredCommands = [...commands];

    // Inject CSS variables-aware Command Palette HTML into the DOM
    function injectDOM() {
        if (document.getElementById('command-palette-modal')) return;

        modal = document.createElement('div');
        modal.id = 'command-palette-modal';
        modal.innerHTML = `
            <div class="command-palette-box">
                <div class="command-palette-header">
                    <span class="command-palette-search-icon">🔍</span>
                    <input type="text" class="command-palette-input" placeholder="Type a command or navigate..." autocomplete="off" spellcheck="false" />
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
            filteredCommands = [...commands];
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
                    No commands found. Try searching for something else.
                </div>
            `;
            return;
        }

        filteredCommands.forEach((cmd, idx) => {
            const item = document.createElement('div');
            item.className = `command-palette-item ${idx === selectedIndex ? 'selected' : ''}`;
            item.innerHTML = `
                <div class="command-palette-item-left">
                    <span class="command-palette-item-icon">${cmd.icon}</span>
                    <span class="command-palette-item-label">${cmd.label}</span>
                </div>
                ${cmd.shortcut ? `<span class="command-palette-item-shortcut">${cmd.shortcut}</span>` : ''}
            `;

            // Hover state
            item.addEventListener('mouseenter', () => {
                selectedIndex = idx;
                updateSelectionStyles();
            });

            // Click activation
            item.addEventListener('click', () => {
                executeCommand(cmd);
            });

            resultsContainer.appendChild(item);
        });

        // Ensure selected item is scrolled into view
        const activeItem = resultsContainer.querySelector('.selected');
        if (activeItem) {
            activeItem.scrollIntoView({ block: 'nearest' });
        }
    }

    function updateSelectionStyles() {
        const items = resultsContainer.querySelectorAll('.command-palette-item');
        items.forEach((item, idx) => {
            item.classList.toggle('selected', idx === selectedIndex);
        });
    }

    function handleSearch() {
        const query = input.value.toLowerCase().trim();
        if (query === '') {
            filteredCommands = [...commands];
        } else {
            filteredCommands = commands.filter(cmd => 
                cmd.label.toLowerCase().includes(query) || 
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
        }
    }

    // Global Key Bindings for opening the palette
    document.addEventListener('keydown', function (e) {
        // Toggle open on CMD+K (macOS) or CTRL+K (Windows/Linux)
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            toggleOpen();
        }
    });

    document.addEventListener('DOMContentLoaded', () => {
        injectDOM();
    });
})();
