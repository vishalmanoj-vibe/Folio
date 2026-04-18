# Developer Guide & Architecture Overview

This document outlines the architecture, layer model, and folder structure of the Portfolio Dashboard. 

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

## Directory Structure

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
│   ├── cache.py                    # TTL cache
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
│   ├── alerts.py                   # Alert detection
│   └── market/                     # Market operations
│       ├── __init__.py
│       ├── fetcher.py              # API calls
│       └── status.py               # Market status
│
├── components/                     # UI components
│   ├── charts/                     # Chart generation functions
│   │   └── intel_*.py              # Intelligence page charts
│   ├── layout.py                   # Main layout container
│   └── ui_helpers.py               # Common UI components
│
├── callbacks/                      # Dash callbacks
│   ├── alert_callbacks.py
│   ├── chart_callbacks.py          # Dashboard interactions
│   ├── core_callbacks.py           # State management
│   ├── intelligence_callbacks.py   # Intelligence page callbacks
│   ├── transaction_callbacks.py
│   └── ui_callbacks.py
│
├── pages/                          # Dash pages
│   ├── portfolio.py
│   ├── intelligence.py
│   └── etf_detail.py
│
├── assets/                         # Static assets (CSS, JS)
│
└── test/                           # Tests
    ├── conftest.py                 # Pytest fixtures
    ├── pytest.ini                  # Pytest config
    ├── unit/                       # Unit tests
    └── integration/                # Integration tests
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

## Key Principles

1. **Single Responsibility** - Each module has one clear purpose. Example: Callbacks handle Dash events and routing, while pure functions in `components/charts/` handle returning `go.Figure`s.
2. **Clear Hierarchy** - UI → Services → Data → Core → Config
3. **Organized Growth** - Add new features cleanly to `services/`, e.g. `services/reporting/`.
4. **Testability** - Clear data contracts and dependencies across layers.
5. **Configurability** - Important settings should be in `config/` or accessed via environment variables.

## Historical Reorganization Context

Prior to April 2026, the codebase used a monolithic configuration (`config.py`) and a flat `services/` structure with root-level tests. The codebase was refactored into the modular structure above to enforce strict separation of concerns, adding robust validation and explicit data models.
