import sys
import os

# Add project root to path
sys.path.append("/Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard")

try:
    from services.market.data_fetcher import get_ticker_cached
    print("SUCCESS: get_ticker_cached imported from services.market.data_fetcher")
    
    from services.intelligence_service import fetch_etf_sector_weights
    print("SUCCESS: intelligence_service imported (it uses get_ticker_cached)")
except ImportError as e:
    print(f"FAILURE: {e}")
except Exception as e:
    print(f"ERROR: {e}")
