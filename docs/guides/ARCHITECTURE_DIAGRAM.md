# Architecture Diagram

## Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│  (components/, callbacks/, pages/ - Dash UI Components)     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌─────────────────────────┴────────────────────────────────────┐
│                   APPLICATION LOGIC                          │
│             (services/ - Business Logic Layer)              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────┐  │
│  │  services/alerts │  │ services/market  │  │ alerts  │  │
│  │                  │  │  ├─ fetcher.py   │  │         │  │
│  │  └─ alerts.py    │  │  └─ status.py    │  └─────────┘  │
│  └──────────────────┘  └──────────────────┘               │
└─────────────────────────┬────────────────────────────────────┘
                          │
┌─────────────────────────┴────────────────────────────────────┐
│                    DATA ACCESS LAYER                         │
│            (data/ - CSV I/O, Portfolio Building)            │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │  csv_handler.py      │  │  portfolio_builder.py     │    │
│  │  (Load/Save CSV)     │  │  (Aggregate Holdings)     │    │
│  └──────────────────────┘  └──────────────────────────┘    │
└─────────────────────────┬────────────────────────────────────┘
                          │
┌─────────────────────────┴────────────────────────────────────┐
│                    DATA MODELS                               │
│            (models/ - Type Definitions)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  transaction.py                                      │   │
│  │  • Transaction                                       │   │
│  │  • Holding                                           │   │
│  │  • EnrichedHolding                                   │   │
│  │  • Portfolio                                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬────────────────────────────────────┘
                          │
┌─────────────────────────┴────────────────────────────────────┐
│                  CORE UTILITIES                              │
│       (core/ - Reusable Utilities & Exceptions)            │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  cache.py    │  │ validators.py│  │  exceptions.py  │  │
│  │  (TTL Cache) │  │  (Validation)│  │  (Custom Errors)│  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────┬────────────────────────────────────┘
                          │
┌─────────────────────────┴────────────────────────────────────┐
│              CONFIGURATION & CONSTANTS                       │
│          (config/ - Settings & Environment)                │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐    │
│  │ settings.py  │  │ constants.py │  │  logging.py   │    │
│  │ (Env Vars)   │  │ (Colors, etc)│  │  (Log Config) │    │
│  └──────────────┘  └──────────────┘  └───────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Dependency Graph

```
                        app.py (Entry Point)
                            │
                ┌───────────┼───────────┐
                │           │           │
            config/      services/    components/
            (Settings)  (Business)    callbacks/
                │          Logic      pages/
                │       ┌────┴────┐    (UI)
                │       │         │
            core/    market/   alerts.py
         (Utils)   (Market)
                      │
                    data/
                  (CSV, etc)
                      │
                   models/
                  (TypeDefs)
```

## Module Organization

### Top Level
```
portfolio_dashboard/
├── app.py                       # Main entry point (5 imports)
├── config.py                    # ← DELETE (files moved to config/)
├── logging_config.py            # ← DELETE (moved to config/logging.py)
├── conftest.py                  # ← DELETE (moved to test/)
├── pytest.ini                   # ← DELETE (moved to test/)
├── requirements.txt
├── .env.example
└── docs/
```

### config/ - Configuration
```
config/
├── __init__.py                  # Exports: settings + constants + logging
├── settings.py                  # App settings + environment vars
├── constants.py                 # Colors, names, themes
└── logging.py                   # Logging configuration
```

### core/ - Core Utilities
```
core/
├── __init__.py                  # Exports: cache, validators, exceptions
├── cache.py                     # TTL cache (moved from services)
├── validators.py               # Transaction validation
└── exceptions.py                # Custom exception classes
```

### models/ - Data Schemas
```
models/
├── __init__.py                  # Portfolio type
└── transaction.py               # Transaction, Holding types
```

### services/ - Business Logic
```
services/
├── __init__.py                  # Exports: alerts, market
├── alerts.py                    # Alert detection (from alert_service.py)
└── market/                      # Market operations (new subpackage)
    ├── __init__.py
    ├── fetcher.py               # API fetching (from market_data.py)
    └── status.py                # Market status (from market_status.py)
```

### data/ - Data Layer (unchanged)
```
data/
├── csv_handler.py               # CSV I/O with backup
└── portfolio_builder.py         # Holdings aggregation with validation
```

### test/ - Tests
```
test/
├── conftest.py                  # Pytest fixtures (moved from root)
├── pytest.ini                   # Pytest config (moved from root)
├── unit/                        # ← NEW LOCATION
│   ├── test_validators.py
│   ├── test_handlers.py
│   ├── test_builders.py
│   ├── test_alerts.py
│   └── test_market_status.py
└── integration/                 # ← NEW (ready for future)
    └── __init__.py
```

## Import Paths Quick Reference

### Configuration
```python
from config import REFRESH_INTERVAL, GREEN, NAMES, setup_logging
from config.settings import CSV_PATH
from config.constants import COLORS, get_theme
from config.logging import setup_logging
```

### Core Utilities 
```python
from core import get_cache, set_cache, validate_transaction
from core.cache import get_cache, set_cache
from core.validators import validate_transaction
from core.exceptions import ValidationError, DataHandlerError
```

### Services
```python
from services import fetch_live, is_market_open, market_badge, check_alerts
from services.market import fetch_live, is_market_open, market_badge
from services.alerts import check_alerts
```

### Data Models
```python
from models.transaction import Transaction, Holding, EnrichedHolding
from models import Portfolio
```

### Data Layer
```python
from data.csv_handler import load_csv, save_csv
from data.portfolio_builder import build_holdings, validate_transaction
```

## File Movement Map

| Old Location | New Location | Changed? |
|--------------|--------------|----------|
| config.py | config/settings.py + config/constants.py | Yes |
| logging_config.py | config/logging.py | Yes |
| services/cache.py | core/cache.py | Moved |
| services/market_data.py | services/market/fetcher.py | Moved + Renamed |
| services/market_status.py | services/market/status.py | Moved |
| services/alert_service.py | services/alerts.py | Moved + Renamed |
| conftest.py | test/conftest.py | Moved |
| pytest.ini | test/pytest.ini | Moved |
| test/test_*.py | test/unit/test_*.py | Moved |

## Key Principles

1. **Single Responsibility** - Each module has one clear purpose
2. **Clear Hierarchy** - UI → Services → Data → Core → Config
3. **Organized Growth** - Easy to add new services (services/portfolio/, services/reporting/)
4. **Testability** - Clear data contracts and dependencies
5. **Configurability** - All settings via environment variables

## Scalability Example

As the project grows, you can easily add:

```
services/
├── market/          # Market operations
│   ├── fetcher.py
│   └── status.py
├── portfolio/       # Portfolio operations (NEW)
│   ├── calculator.py
│   └── optimizer.py
├── alerts/          # Alert operations (NEW)
├── reporting/       # Report generation (NEW)
│   └── pdf.py
└── analytics/       # Data analytics (NEW)
```

Each service would have:
- Clear imports from config/ and core/
- No circular dependencies
- Testable in isolation
- Easy to understand and extend

---

See ARCHITECTURE.md for detailed explanation and MIGRATION_CHECKLIST.md for step-by-step migration.
