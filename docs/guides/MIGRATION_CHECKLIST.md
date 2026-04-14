# Migration Checklist - From Old to New Architecture

This checklist guides you through migrating the codebase to the new architecture.

## Overview
- **New folders created** ✓ (config/, core/, models/, services/market/, test/unit/, test/integration/)
- **New files created** ✓ (All modules already in place)
- **Remaining work**: Update imports and move old files

## Phase 1: Update Import Statements (30-45 min)

### 1.1 app.py
```diff
- from logging_config import setup_logging
- from config import REFRESH_INTERVAL

+ from config import setup_logging, REFRESH_INTERVAL
```

### 1.2 callbacks/core_callbacks.py
```diff
- from services.market_data import fetch_live
- from services.market_status import market_badge

+ from services.market import fetch_live, market_badge
```

### 1.3 callbacks/alert_callbacks.py
```diff
- from services.alert_service import check_alerts

+ from services.alerts import check_alerts
```

### 1.4 callbacks/chart_callbacks.py
```diff
- from config import get_theme

+ from config import get_theme  # No change needed - re-exported
```

### 1.5 callbacks/ui_callbacks.py
```diff
- No changes needed (doesn't import from reorganized modules)
```

### 1.6 components/layout.py
```diff
- from config import GREEN, CSV_PATH

+ from config import GREEN, CSV_PATH  # No change needed
```

### 1.7 components/ui_helpers.py
```diff
- from config import GREEN, RED, CHART_INFO

+ from config import GREEN, RED, CHART_INFO  # No change needed
```

### 1.8 data/csv_handler.py
```diff
- from config import CSV_PATH

+ from config.settings import CSV_PATH
+ # OR keep as-is: from config import CSV_PATH
```

### 1.9 data/portfolio_builder.py
```diff
- from config import NAMES
+ from core.validators import validate_transaction
- from data.portfolio_builder import validate_transaction

+ # Already imports work, just verify at top:
+ from config.constants import NAMES
```

### 1.10 services/market/fetcher.py ✓
```
Already updated in new structure
```

### 1.11 services/market/status.py ✓
```
Already updated in new structure
```

### 1.12 services/alerts.py ✓
```
Already updated in new structure
```

### 1.13 pages/portfolio.py
```diff
- No changes needed
```

### 1.14 pages/etf_detail.py
```diff
- from config import (...)

+ from config import (...)  # No change needed - re-exported
```

## Phase 2: Test the Changes (10 min)

### 2.1 Verify Imports in Python
```bash
cd portfolio_dashboard

python3 -c "
import sys
sys.path.insert(0, '.')

# Test new imports
from config import REFRESH_INTERVAL, GREEN, setup_logging
from core import get_cache, set_cache, validate_transaction
from models.transaction import Transaction
from services import fetch_live, is_market_open, check_alerts
from services.market import fetch_live as fetch_live2

print('✅ All new imports work!')
"
```

### 2.2 Verify Old Backward-Compatible Imports Still Work
```bash
python3 -c "
import sys
sys.path.insert(0, '.')

# Test old imports still work (backward compatibility)
from config import ALERT_THRESHOLDS, COLORS, get_theme

print('✅ Backward compatible imports work!')
"
```

### 2.3 Run Tests in New Location
```bash
cd test/
pytest -v
```

## Phase 3: Move Test Files (10 min)

### 3.1 Copy test files to test/unit/ location
```bash
# Effectively done - the test files can stay in old location during transition
# or you can move them:

# cd test/
# mv test_portfolio_builder.py unit/
# mv test_alert_service.py unit/
# mv test_csv_handler.py unit/
# mv test_market_status.py unit/
```

### 3.2 Verify tests still run from new location
```bash
pytest test/unit/ -v
```

## Phase 4: Clean Up Old Files (5 min)

### 4.1 Delete Old Root-Level Config Files
```bash
# Only do this AFTER all imports are updated

cd portfolio_dashboard

# These are now in config/ folder
# rm config.py
# rm logging_config.py

# These are now in test/ folder
# rm conftest.py
# rm pytest.ini
```

### 4.2 Delete Old Services Files
```bash
# Only do this AFTER all imports are updated and verified

# These are now in services/market/ or services/
# rm services/market_data.py
# rm services/market_status.py
# rm services/alert_service.py
# rm services/cache.py
```

### 4.3 Delete Old Test Files (if moved)
```bash
# Only if you moved tests to test/unit/

# rm test/test_*.py  (keep if still in test/unit/)
```

## Phase 5: Verify App Runs (5 min)

### 5.1 Start the app
```bash
cd portfolio_dashboard
python app.py
```

### 5.2 Check logs for errors
```
Should see:
  "Portfolio Dashboard — Live P&L (multi-page)"
  "CSV: ..."
  "Logging configured: ..."
```

### 5.3 Test in browser
Open http://127.0.0.1:8050
- Main portfolio page loads ✓
- Data refreshes ✓  
- Charts render ✓
- Transactions work ✓

## Detailed Import Updates

Here are the exact changes needed for each file:

### app.py
**Lines to change:**
```python
# Line 35
- from logging_config import setup_logging
- from config import REFRESH_INTERVAL
+ from config import setup_logging, REFRESH_INTERVAL

# Line 45 (setup_logging call remains same)
```

### callbacks/core_callbacks.py
**Lines to change:**
```python
# Line 5-6
- from services.market_data import fetch_live
- from services.market_status import market_badge
+ from services.market import fetch_live, market_badge
```

### callbacks/alert_callbacks.py
**Lines to change:**
```python
# Line 4
- from services.alert_service import check_alerts
+ from services.alerts import check_alerts
```

### data/portfolio_builder.py
**Lines to change:**
```python
# Line 2
- from config import NAMES
+ from config.constants import NAMES
+
+ # Add at top if using validate_transaction directly:
+ from core.validators import validate_transaction
```

## Testing Checklist

- [ ] Python import checks pass (Phase 2.1)
- [ ] Backward compatible imports work (Phase 2.2)
- [ ] Unit tests run from new location (Phase 2.3)
- [ ] App starts without errors (Phase 5.1)
- [ ] App loads in browser (Phase 5.3)
- [ ] Charts render correctly
- [ ] Transactions can be added
- [ ] CSV loads properly
- [ ] No import errors in console

## Troubleshooting

### "ModuleNotFoundError: No module named 'config'"
- Verify you're running from project root
- Check PYTHONPATH is set correctly
- Ensure config/ folder exists

### "ModuleNotFoundError: No module named 'services.market'"
- Check services/market/__init__.py exists
- Verify services/market/fetcher.py and status.py exist
- Check import statements are updated

### Tests fail to find modules
- Ensure conftest.py adds project root to sys.path
- Run tests from project root: `pytest test/ -v`
- Or from test dir: `cd test/ && pytest -v`

### Old imports still work but new ones don't
- This is expected initially (backward compat)
- Make sure new modules are created
- Check config/__init__.py exports everything

## Success Criteria

Migration is complete when:

✅ All import statements updated  
✅ All tests pass in new locations  
✅ App starts and runs  
✅ Old files deleted  
✅ No import warnings or errors  
✅ Structure matches ARCHITECTURE.md  

## Estimated Time

- Phase 1 (Imports): 30-45 min
- Phase 2 (Testing): 10 min
- Phase 3 (Test files): 10 min
- Phase 4 (Cleanup): 5 min
- Phase 5 (Verification): 5 min

**Total: ~60-75 min**

---

If you get stuck, check:
1. ARCHITECTURE.md - Full architecture overview
2. config/__init__.py - What's exported and available
3. services/__init__.py - Service exports
4. core/__init__.py - Core utility exports
