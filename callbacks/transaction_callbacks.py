import pandas as pd
from datetime import datetime
from dash import Input, Output, State

from config import GREEN, RED
from data.csv_handler import save_csv
from components.ui_helpers import txn_table


def register_callbacks(app) -> None:

    @app.callback(
        Output("txn-store",  "data"),
        Output("txn-msg",    "children"),
        Output("txn-msg",    "style"),
        Input("txn-submit",  "n_clicks"),
        State("txn-type",    "value"),
        State("txn-ticker",  "value"),
        State("txn-shares",  "value"),
        State("txn-price",   "value"),
        State("txn-date",    "value"),
        State("txn-store",   "data"),
        prevent_initial_call=True,
    )
    def add_transaction(_, txn_type, ticker, shares, price, date, history):
        base = {"fontSize": "12px", "marginTop": "8px", "minHeight": "18px"}

        # ── Basic validation ──────────────────────────────────────────────────
        if not ticker or shares is None or price is None:
            return history, "Please fill in ticker, shares and price.", {**base, "color": RED}

        ticker = ticker.strip().upper()
        try:
            shares = float(shares)
            price  = float(price)
        except (TypeError, ValueError):
            return history, "Shares and price must be numbers.", {**base, "color": RED}

        if shares <= 0 or price <= 0:
            return history, "Shares and price must be positive.", {**base, "color": RED}

        try:
            datetime.strptime(date.strip(), "%Y-%m-%d")
        except (ValueError, AttributeError):
            return history, "Date must be YYYY-MM-DD (e.g. 2026-03-30).", {**base, "color": RED}

        # ── Sell validation ───────────────────────────────────────────────────
        if txn_type == "sell":
            df = pd.DataFrame(history)
            if df.empty or ticker not in df["ticker"].values:
                return history, f"No holdings found for {ticker}.", {**base, "color": RED}
            grp  = df[df["ticker"] == ticker]
            held = (
                grp[grp["type"] == "buy"]["shares"].sum()
                - grp[grp["type"] == "sell"]["shares"].sum()
                if "sell" in grp["type"].values
                else grp[grp["type"] == "buy"]["shares"].sum()
            )
            if shares > held:
                return history, f"Cannot sell {shares} — only holding {held}.", {**base, "color": RED}

        # ── Commit ────────────────────────────────────────────────────────────
        new_txn = {
            "type":   txn_type,
            "ticker": ticker,
            "shares": shares,
            "price":  price,
            "date":   date.strip(),
        }
        updated = history + [new_txn]

        try:
            save_csv(updated)
            msg = f"{txn_type.capitalize()} {shares} {ticker} @ ${price:.4f} saved to CSV."
        except Exception as e:
            msg = f"Added to dashboard but CSV save failed: {e}"

        color = GREEN if txn_type == "buy" else RED
        return updated, msg, {**base, "color": color}

    # ── Transaction log display ───────────────────────────────────────────────

    @app.callback(
        Output("txn-log", "children"),
        Input("txn-store", "data"),
    )
    def update_txn_log(history):
        return txn_table(history)
