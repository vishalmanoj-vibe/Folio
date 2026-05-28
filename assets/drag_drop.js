/**
 * assets/drag_drop.js
 * ====================
 * Implements smooth drag-and-drop reordering for the Watchlist table rows.
 * Uses event delegation on the document level to survive Dash DOM updates.
 */

(function () {
    let draggedRow = null;
    let dragOverRow = null;

    // Helper: Find ancestor TR with draggable-row class
    function findDraggableRow(target) {
        while (target && target.tagName !== 'TR') {
            target = target.parentElement;
        }
        if (target && target.classList.contains('draggable-row')) {
            return target;
        }
        return null;
    }

    let canDragRow = false;

    // Detect if click was initiated on the drag handle
    document.addEventListener('mousedown', function (e) {
        const isHandle = e.target.classList.contains('drag-handle') || e.target.closest('.drag-handle');
        canDragRow = !!isHandle;
    });

    // 1. Drag Start
    document.addEventListener('dragstart', function (e) {
        const row = findDraggableRow(e.target);
        if (!row) return;

        // Ensure dragging only starts if initiated from the drag handle
        if (!canDragRow) {
            e.preventDefault();
            return;
        }

        draggedRow = row;
        row.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', row.getAttribute('data-ticker') || '');
    });

    // 2. Drag Over
    document.addEventListener('dragover', function (e) {
        if (!draggedRow) return;
        const row = findDraggableRow(e.target);
        if (!row || row === draggedRow) return;

        e.preventDefault(); // Required to allow drop!
        e.dataTransfer.dropEffect = 'move';

        // Add visual indicator of insertion point
        const rect = row.getBoundingClientRect();
        const next = (e.clientY - rect.top) > (rect.height / 2);

        // Remove previous dragover classes
        if (dragOverRow && dragOverRow !== row) {
            dragOverRow.classList.remove('drag-over-above', 'drag-over-below');
        }

        dragOverRow = row;
        if (next) {
            row.classList.add('drag-over-below');
            row.classList.remove('drag-over-above');
        } else {
            row.classList.add('drag-over-above');
            row.classList.remove('drag-over-below');
        }
    });

    // 3. Drag Leave
    document.addEventListener('dragleave', function (e) {
        const row = findDraggableRow(e.target);
        if (row && row === dragOverRow) {
            const rect = row.getBoundingClientRect();
            // Verify if actually leaving the bounds of the target row
            if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) {
                row.classList.remove('drag-over-above', 'drag-over-below');
                dragOverRow = null;
            }
        }
    });

    // 4. Drag End
    document.addEventListener('dragend', function (e) {
        const row = findDraggableRow(e.target);
        if (row) {
            row.classList.remove('dragging');
        }
        // Clean up all rows
        document.querySelectorAll('.draggable-row').forEach(r => {
            r.classList.remove('dragging', 'drag-over-above', 'drag-over-below');
        });
        draggedRow = null;
        dragOverRow = null;
    });

    // 5. Drop
    document.addEventListener('drop', function (e) {
        if (!draggedRow) return;
        e.preventDefault();

        const row = findDraggableRow(e.target);
        if (!row || row === draggedRow) return;

        const rect = row.getBoundingClientRect();
        const next = (e.clientY - rect.top) > (rect.height / 2);
        const parent = row.parentNode;

        // Perform DOM swap
        if (next) {
            parent.insertBefore(draggedRow, row.nextSibling);
        } else {
            parent.insertBefore(draggedRow, row);
        }

        // Clean up visual styles
        row.classList.remove('drag-over-above', 'drag-over-below');

        // Extract new order of tickers
        const rows = parent.querySelectorAll('.draggable-row');
        const tickerOrder = Array.from(rows).map(r => r.getAttribute('data-ticker')).filter(Boolean);

        // Send to Dash hidden input
        const input = document.getElementById('watchlist-order-input');
        if (input) {
            input.value = JSON.stringify(tickerOrder);
            // Dispatch both input and change events so Dash detects it
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }

        draggedRow = null;
        dragOverRow = null;
    });
})();
