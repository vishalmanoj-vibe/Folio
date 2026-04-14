# Project Architecture Reorganization

This document describes the improved project architecture and migration steps.

## New Architecture

```
portfolio_dashboard/
├── app.py                          # Entry point (minimal)
│
├── config/                         # Configuration layer
│   ├── __init__.py                 # Exports all config
│   ├── settings.py                 # Settings + env vars
│   ├── constants.py                # Colors, names, themes
│   └── logging.py                  # Logging configuration
│
├── core/                           # Core utilities
│   ├── __init__.py                 # Exports utilities
│   ├── cache.py                    # TTL cache (moved from services)
│   ├── validators.py               # Validation helpers
│   └── exceptions.py               # Custom exceptions
│
├── models/                         # Data models/schemas
│   ├── __init__.py                 # Portfolio models
│   └── transaction.py              # Transaction + Holding models
│
├── data/                           # Data layer
│   ├── csv_handler.py              # CSV I/O with backup
│   └── portfolio_builder.py        # Portfolio aggregation
│
├── services/                       # Business logic
│   ├── __init__.py                 # Exports services
│   ├── alerts.py                   # Alert detection (renamed)
│   └── market/                     # Market operations
│       ├── __init__.py
│       ├── fetcher.py              # API calls (from market_data.py)
│       └── status.py               # Market status (from market_status.py)
│
├── components/                     # UI components (unchanged)
├── callbacks/                      # Dash callbacks (unchanged)
├── pages/                          # Dash pages (unchanged)
├── assets/                         # Static assets (unchanged)
│
├── test/                           # Tests (reorganized)
│   ├── conftest.py                 # Pytest fixtures (moved from root)
│   ├── pytest.ini                  # Pytest config (moved from root)
│   ├── unit/                       # Unit tests
│   │   ├── test_validators.py
│   │   ├── test_handlers.py
│   │   └── ...
│   └── integration/                # Integration tests (new)
│
├── docs/ & archive/                # Documentation (unchanged)
├── requirements.txt
└── .env.example
```

## Key Improvements

### 1. **Clear Separation of Concerns**
- **config/** - All configuration and constants
- **core/** - Shared utilities (cache, validators, exceptions)
- **models/** - Data structure definitions
- **data/** - Data access layer (CSV, portfolio building)
- **services/** - Business logic (alerts, market data)
- **components/, callbacks/, pages/** - UI layer

### 2. **Config Management**
Old: `config.py` (monolithic, mixed concerns)
New:
- `config/settings.py` - Environment variables & app settings
- `config/constants.py` - Colors, names, themes
- `config/logging.py` - Logging configuration
- `config/__init__.py` - Single import point

### 3. **Core Utilities**
Old: Scattered across codebase
New:
- `core/cache.py` - TTL cache (moved from services)
- `core/validators.py` - Data validation helpers
- `core/exceptions.py` - Custom exceptions
- `core/__init__.py` - Single import point

### 4. **Services Repository**
Old: Flat structure (market_data.py, market_status.py, etc.)
New:
- `services/market/` - Market-related operations
  - `fetcher.py` - API data fetching (from market_data.py)
  - `status.py` - Market status (from market_status.py)
- `services/alerts.py` - Alert detection (renamed from alert_service.py)
- `services/__init__.py` - Single import point

### 5. **Test Organization**
Old: Tests at root level (conftest.py, pytest.ini)
New:
- `test/conftest.py` - Fixtures and test config
- `test/pytest.ini` - Pytest configuration
- `test/unit/` - Unit tests (moved from root test/)
- `test/integration/` - Integration tests (new, for future)

## Migration Steps

### Step 1: Update Imports in Code

Replace old imports with new imports throughout codebase:

#### config.py imports
```python
# OLD
from config import (
    REFRESH_INTERVAL,
    CSV_PATH,
    BG, SURFACE, GREEN, RED, COLORS,
    get_theme,
    NAMES, CHART_INFO,
)
from logging_config import setup_logging

# NEW
from config import (
    REFRESH_INTERVAL,
    CSV_PATH,
    BG, SURFACE, GREEN, RED, COLORS,
    get_theme,
    NAMES, CHART_INFO,
    setup_logging,
)
```

#### services imports
```python
# OLD
from services.cache import get_cache, set_cache
from services.market_data import fetch_live
from services.market_status import is_market_open, market_badge
from services.alert_service import check_alerts

# NEW
from core import get_cache, set_cache
from services.market import fetch_live, is_market_open, market_badge
from services.alerts import check_alerts
```

#### validators imports
```python
# NEW
from core import validate_transaction
# or
from core.validators import validate_transaction
```

### Step 2: Files to Delete/Move

```bash
# Delete old root-level files (after code updates)
rm config.py
rm logging_config.py
rm conftest.py
rm pytest.ini

# Services reorganization
mv services/market_data.py services/market/fetcher.py     # (already created)
mv services/market_status.py services/market/status.py    # (already created)
mv services/alert_service.py services/alerts.py           # (already created)
rm services/cache.py                                      # (moved to core)

# Tests reorganization
mv test/test_portfolio_builder.py test/unit/test_portfolio_builder.py
mv test/test_alert_service.py test/unit/test_alert_service.py
mv test/test_csv_handler.py test/unit/test_csv_handler.py
mv test/test_market_status.py test/unit/test_market_status.py
```

### Step 3: Update All Import Statements

Files that need update (key files):

1. **app.py**
   ```python
   # OLD
   from logging_config import setup_logging
   from config import REFRESH_INTERVAL
   
   # NEW
   from config import setup_logging, REFRESH_INTERVAL
   ```

2. **callbacks/core_callbacks.py**
   ```python
   # OLD
   from services.market_data import fetch_live
   from services.market_status import market_badge
   
   # NEW
   from services.market import fetch_live, market_badge
   ```

3. **callbacks/alert_callbacks.py**
   ```python
   # OLD
   from services.alert_service import check_alerts
   
   # NEW
   from services.alerts import check_alerts
   ```

4. **data/portfolio_builder.py**
   ```python
   # OLD
   from config import NAMES
   
   # NEW
   from config.constants import NAMES
   # or just: from config import NAMES
   ```

5. **pages/etf_detail.py**
   ```python
   # OLD
   from config import BG, SURFACE, BORDER, GREEN, RED, COLORS, PLOTLY_BASE, NAMES
   
   # NEW
   from config import BG, SURFACE, BORDER, GREEN, RED, COLORS, PLOTLY_BASE, NAMES
   # (No change needed - handled by __init__.py)
   ```

### Step 4: Verify Tests Still Work

```bash
# Should work with new structure
cd test/
pytest -v

# Or from project root
pytest test/ -v
```

### Step 5: Run Import Validation

```python
# Quick test to verify all imports work
python -c "
from config import *
from core import *
from services import *
from models import *
print('✓ All imports successful!')
"
```

## Benefits of New Architecture

| Aspect | Before | After |
|--------|--------|-------|
| **Config Management** | Monolithic config.py | Organized by concern (settings, constants, logging) |
| **Import Clarity** | Complex imports | Single source imports (from config, from core, from services) |
| **Code Organization** | Scattered utilities | Centralized core module |
| **Services** | Flat structure | Hierarchical (services/market/, services/alerts) |
| **Test Location** | Root clutter | Organized by type (unit/, integration/) |
| **Future Scaling** | Difficult | Easy - add new services/market/*, add new core/* |
| **Dependencies** | Tangled | Clear flow: app → config/core/services → data/models |

## File Structure Checklist

After migration complete:

- [ ] config/ folder created with settings.py, constants.py, logging.py
- [ ] core/ folder created with cache.py, validators.py, exceptions.py
- [ ] models/ folder created with schemas
- [ ] services/market/ created with fetcher.py, status.py
- [ ] services/alerts.py created (renamed from alert_service.py)
- [ ] test/unit/ contains all unit tests
- [ ] test/integration/ ready for future tests
- [ ] test/conftest.py and test/pytest.ini in place
- [ ] Old root files deleted: config.py, logging_config.py, conftest.py, pytest.ini
- [ ] All imports updated in all files
- [ ] Tests run successfully: pytest test/ -v
- [ ] App runs: python app.py

## Backward Compatibility

The `config/__init__.py` file exports all symbols, so old imports continue to work:

```python
# Both work after migration
from config import get_theme
from config.constants import get_theme
```

This allows gradual migration of the codebase if needed.

## Future Enhancements

With this architecture, it's easy to add:
- `services/portfolio/` - Portfolio calculations
- `services/reporting/` - Report generation
- `core/logging/` - Custom logging utilities
- `models/` - More data structures
  
Ready to scale as the project grows!
