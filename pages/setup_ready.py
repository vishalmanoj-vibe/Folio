# pages/setup_ready.py
"""
pages/setup_ready.py
===================
Onboarding Wizard: Page 3 — Ready Screen startup gate
Route: /setup/ready
"""

import dash
import dash_mantine_components as dmc
from dash import dcc, html

dash.register_page(__name__, path="/setup/ready", title="Folio — Ready")


def layout() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="setup-ready-redirect-store", data=None, storage_type="session"),
            html.Div(
                [
                    # Step indicators
                    html.Div(
                        [
                            html.Div(
                                [html.Span("✓", className="setup-step-num"), "Portfolio"],
                                className="setup-step completed",
                            ),
                            html.Div(
                                [html.Span("✓", className="setup-step-num"), "AI Analyst"],
                                className="setup-step completed",
                            ),
                            html.Div(
                                [html.Span("3", className="setup-step-num"), "Ready"],
                                className="setup-step active",
                            ),
                        ],
                        className="setup-steps-header",
                    ),
                    # Title & Description
                    html.H1("Folio is ready", className="setup-title"),
                    html.P(
                        "Your onboarding setup is complete! We have initialized your database. "
                        "Click 'Launch Dashboard' to open your premium portfolio interface.",
                        className="setup-subtitle",
                    ),
                    # Ready Summary container
                    html.Div(
                        [
                            # Summary details box
                            html.Div(id="setup-ready-summary", className="setup-summary-box"),
                            # Action buttons row
                            html.Div(
                                [
                                    html.Button(
                                        "Back",
                                        id="setup-ready-back-btn",
                                        className="setup-btn-secondary",
                                        type="button",
                                    ),
                                    html.Button(
                                        "Launch Dashboard",
                                        id="setup-ready-launch-btn",
                                        className="setup-btn-primary",
                                        type="button",
                                    ),
                                ],
                                className="setup-actions-row",
                            ),
                            # Feedback / Redirects
                            html.Div(id="setup-ready-feedback"),
                        ],
                        id="setup-ready-container",
                    ),
                ],
                className="setup-card",
            ),
        ],
        className="setup-root",
    )
