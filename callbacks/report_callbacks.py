import base64, os, logging
from datetime import datetime
from dash import Input, Output, State, ctx, dcc
import dash
from services.report_service import (
    generate_weekly_report
)

logger = logging.getLogger(__name__)

REPORT_DATE_FILE = os.path.join(
    "data", "cache", "last_report_date.txt"
)

def _get_last_report_date() -> str:
    try:
        if os.path.exists(REPORT_DATE_FILE):
            with open(REPORT_DATE_FILE) as f:
                return f.read().strip()
    except Exception:
        pass
    return ""

def _save_last_report_date():
    try:
        os.makedirs(
            os.path.dirname(REPORT_DATE_FILE),
            exist_ok=True
        )
        with open(REPORT_DATE_FILE, "w") as f:
            f.write(
                datetime.now().strftime(
                    "%d %B %Y, %I:%M %p"
                )
            )
    except Exception as e:
        logger.warning(
            f"Could not save report date: {e}"
        )

def register_callbacks(app):

    @app.callback(
        Output("report-status-msg", "children"),
        Output("report-status-msg", "style"),
        Output("report-download-area", "style"),
        Output("last-report-date", "children"),
        Output("report-cache-store", "data"),
        Input("generate-report-btn", "n_clicks"),
        Input("url", "pathname"),
        State("portfolio-store", "data"),
        prevent_initial_call=False,
    )
    def handle_report_generation(
        n_clicks, pathname, portfolio_data
    ):
        # Only act on this page
        if pathname != "/reports":
            return (
                dash.no_update, dash.no_update,
                dash.no_update, dash.no_update,
                dash.no_update
            )
        
        # On page load just show last report date
        if ctx.triggered_id != "generate-report-btn":
            last_date = _get_last_report_date()
            last_text = (
                f"Last generated: {last_date}"
                if last_date else
                "No report generated yet"
            )
            return (
                "", {},
                {"display": "none"},
                last_text, dash.no_update
            )
        
        # Generate report on button click
        if not n_clicks or n_clicks < 1:
            return (
                "", {},
                {"display": "none"}, "", dash.no_update
            )
        
        try:
            api_key = os.getenv(
                "GEMINI_API_KEY", ""
            )
            
            # Orchestrate report generation
            pdf_bytes = generate_weekly_report(
                portfolio_data, api_key
            )
            
            # Encode PDF as base64 for session storage
            b64 = base64.b64encode(
                pdf_bytes
            ).decode("utf-8")
            
            # Save report date
            _save_last_report_date()
            
            last_text = (
                f"Last generated: "
                f"{datetime.now().strftime('%d %b %Y')}"
            )
            
            return (
                "✓ Report generated successfully.",
                {"color": "var(--green)",
                 "fontSize": "12px",
                 "marginTop": "12px"},
                {"display": "block"},
                last_text,
                b64
            )
            
        except Exception as e:
            logger.error(
                f"Report generation failed: {e}"
            )
            return (
                f"Failed to generate report. "
                f"Please try again.",
                {"color": "var(--red)",
                 "fontSize": "12px",
                 "marginTop": "12px"},
                {"display": "none"}, "", dash.no_update
            )

    @app.callback(
        Output("report-download", "data"),
        Input("report-pdf-link", "n_clicks"),
        State("report-cache-store", "data"),
        prevent_initial_call=True,
    )
    def trigger_download(n_clicks, b64_data):
        if not n_clicks or not b64_data:
            return dash.no_update
        
        pdf_bytes = base64.b64decode(b64_data)
        filename = f"Portfolio_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return dcc.send_bytes(pdf_bytes, filename=filename)
