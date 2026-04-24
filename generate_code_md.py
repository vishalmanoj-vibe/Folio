import os

files_to_include = [
    "app.py",
    "components/portfolio_layout.py",
    "components/header.py",
    "components/ui_helpers.py",
    "callbacks/portfolio_callbacks.py",
    "callbacks/transaction_callbacks.py",
    "callbacks/chart_callbacks.py",
    "callbacks/alert_callbacks.py",
    "callbacks/ui_callbacks.py",
    "callbacks/intelligence_callbacks.py",
    "callbacks/positions_callbacks.py",
    "callbacks/dividend_callbacks.py",
    "core/engine/stats_engine.py",
    "core/engine/portfolio_engine.py",
    "data/csv_handler.py",
    "data/portfolio_builder.py",
    "services/market/data_fetcher.py",
    "services/market/market_status.py",
    "services/market/session_cache.py",
    "services/intelligence_service.py",
    "services/prediction_service.py",
    "services/alert_service.py",
    "assets/layout.css",
    "assets/ui-components.css",
    "assets/view-pages.css",
    "config/settings.py",
    "config/constants.py"
]

with open("portfolio_dashboard_code.md", "w") as out:
    out.write("# Portfolio Dashboard - Full Codebase\n\n")
    for file_path in files_to_include:
        if os.path.exists(file_path):
            ext = file_path.split(".")[-1]
            lang = "python" if ext == "py" else "css" if ext == "css" else ""
            out.write(f"## {file_path}\n\n")
            out.write(f"```{lang}\n")
            with open(file_path, "r") as f:
                out.write(f.read())
            out.write("\n```\n\n")
        else:
            out.write(f"## {file_path} (NOT FOUND)\n\n")

print("Generated portfolio_dashboard_code.md")
