import logging
import os
import pandas as pd
from config import CSV_PATH

logger = logging.getLogger(__name__)


def load_csv() -> list[dict]:
    """
    Load transactions from CSV.
    Returns list of dicts with keys: type, ticker, shares, price, date (YYYY-MM-DD).
    Raises FileNotFoundError / ValueError with clear messages if anything is wrong
    so the error prints to terminal rather than silently returning an empty list.

    Accepted date formats: YYYY-MM-DD and DD.MM.YYYY.
    The 'type' column is optional — defaults to 'buy' if absent.
    """
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"\n\nCSV file not found at:\n  {CSV_PATH}\n\n"
            "Please create it with columns: type,ticker,shares,price,date\n"
            "Example row:  buy,VHY,7,81.87,2026-03-30\n"
        )

    df = pd.read_csv(CSV_PATH)

    # Normalise column names — handle Title Case, lowercase, whitespace
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in ["ticker", "shares", "price", "date"] if c not in df.columns]
    if missing:
        raise ValueError(
            f"\n\nCSV is missing required columns: {missing}\n"
            f"Found columns: {list(df.columns)}\n"
            "Required: type, ticker, shares, price, date\n"
        )

    # 'type' column is optional — default to 'buy'
    if "type" not in df.columns:
        df["type"] = "buy"

    # Normalise values
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["type"]   = df["type"].astype(str).str.strip().str.lower()
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce")
    df["price"]  = pd.to_numeric(df["price"],  errors="coerce")

    # First-pass date parse: YYYY-MM-DD
    df["date"] = pd.to_datetime(df["date"], dayfirst=False, errors="coerce")
    mask_failed = df["date"].isna()
    if mask_failed.any():
        # Second-pass: DD.MM.YYYY
        raw_col = pd.read_csv(CSV_PATH).iloc[:, df.columns.tolist().index("date")]
        retry   = pd.to_datetime(raw_col, dayfirst=True, errors="coerce")
        df.loc[mask_failed, "date"] = retry[mask_failed]

    still_bad = (
        df["date"].isna().any()
        or df["shares"].isna().any()
        or df["price"].isna().any()
    )
    if still_bad:
        bad_rows = df[df[["date", "shares", "price"]].isna().any(axis=1)]
        raise ValueError(
            f"\n\nCSV has rows with invalid date, shares, or price:\n"
            f"{bad_rows.to_string()}\n\n"
            "Date format should be YYYY-MM-DD (e.g. 2026-03-30)\n"
        )

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    records = df[["type", "ticker", "shares", "price", "date"]].to_dict("records")
    logger.info("Loaded %d transactions from %s", len(records), CSV_PATH)
    return records


def save_csv(history: list[dict]) -> None:
    """Write the full transaction list back to CSV."""
    df = pd.DataFrame(history)[["type", "ticker", "shares", "price", "date"]]
    df.columns = ["Type", "Ticker", "Shares", "Price", "Date"]
    df.to_csv(CSV_PATH, index=False)
    logger.info("Saved %d transactions to %s", len(history), CSV_PATH)