# pages/setup_portfolio.py
"""
pages/setup_portfolio.py
========================
Onboarding Wizard: Page 1 — Portfolio Setup
Route: /setup/portfolio
"""

import dash
import dash_mantine_components as dmc
from dash import dcc, html

from components.ui_helpers import section

dash.register_page(__name__, path="/setup/portfolio", title="Folio — Portfolio Setup")


def layout() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="setup-portfolio-rows-store", data=[0], storage_type="session"),
            dcc.Store(id="setup-portfolio-redirect-store", data=None, storage_type="session"),
            html.Div(
                [
                    # Step indicators
                    html.Div(
                        [
                            html.Div(
                                [html.Span("1", className="setup-step-num"), "Portfolio"],
                                className="setup-step active",
                            ),
                            html.Div(
                                [html.Span("2", className="setup-step-num"), "AI Analyst"],
                                className="setup-step",
                            ),
                            html.Div(
                                [html.Span("3", className="setup-step-num"), "Ready"],
                                className="setup-step",
                            ),
                        ],
                        className="setup-steps-header",
                    ),
                    # Title & Description
                    html.H1("Add your first holding", className="setup-title"),
                    html.P(
                        "Welcome to Folio! Let's initialize your portfolio with at least one transaction. "
                        "Add transactions for the Australian tickers you hold (e.g. VAS, A200, IVV). Tickers are saved without '.AX'.",
                        className="setup-subtitle",
                    ),
                    # Portfolio setup form container
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Table(
                                        [
                                            html.Thead(
                                                html.Tr(
                                                    [
                                                        html.Th(
                                                            "Ticker (e.g. VAS)",
                                                            style={"width": "25%"},
                                                        ),
                                                        html.Th("Shares", style={"width": "20%"}),
                                                        html.Th(
                                                            "Avg Cost ($)", style={"width": "20%"}
                                                        ),
                                                        html.Th(
                                                            "Purchase Date", style={"width": "25%"}
                                                        ),
                                                        html.Th(
                                                            "", style={"width": "10%"}
                                                        ),  # For potential delete button
                                                    ]
                                                )
                                            ),
                                            html.Tbody(id="setup-portfolio-table-body"),
                                        ],
                                        className="setup-table",
                                    )
                                ],
                                className="setup-table-container",
                            ),
                            # Buttons row
                            html.Div(
                                [
                                    html.Button(
                                        "+ Add Ticker",
                                        id="setup-add-row-btn",
                                        className="setup-btn-secondary",
                                        type="button",
                                    ),
                                    html.Button(
                                        "Continue",
                                        id="setup-portfolio-continue-btn",
                                        className="setup-btn-primary",
                                        disabled=True,
                                        type="button",
                                    ),
                                ],
                                className="setup-actions-row",
                            ),
                            # Feedback / Errors
                            html.Div(id="setup-portfolio-feedback", className="setup-feedback"),
                        ],
                        id="setup-portfolio-container",
                    ),
                ],
                className="setup-card",
            ),
        ],
        className="setup-root",
    )
