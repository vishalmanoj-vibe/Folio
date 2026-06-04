# pages/settings.py
"""
pages/settings.py
=================
Investor Profile Settings Page.
Route: /settings
"""

import dash
from dash import dcc, html

from components.ui_helpers import section

dash.register_page(__name__, path="/settings", title="Folio — Settings")


def layout() -> html.Div:
    return html.Div(
        [
            # Page Header
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("Settings", className="header-title"),
                            html.P(
                                "Investor Profile & Strategy Customization",
                                className="header-subtitle",
                            ),
                        ],
                        className="header-title-row",
                    ),
                ],
                className="page-header-row",
            ),
            # Form and Weight Preview side-by-side
            html.Div(
                [
                    # Left Column: Form
                    html.Div(
                        [
                            section(
                                html.H3("Investor Profile", className="settings-section-title"),
                                html.Div(
                                    [
                                        # Investment Goal
                                        html.Div(
                                            [
                                                html.Label(
                                                    "Investment Goal", className="txn-label"
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-investment-goal",
                                                    options=[
                                                        {
                                                            "label": "Balanced (Default)",
                                                            "value": "Balanced",
                                                        },
                                                        {
                                                            "label": "Growth (Focus Trend & Momentum)",
                                                            "value": "Growth",
                                                        },
                                                        {
                                                            "label": "Income (Focus Cost Basis & Value)",
                                                            "value": "Income",
                                                        },
                                                        {
                                                            "label": "Capital Preservation (Focus Risk & Value)",
                                                            "value": "Capital Preservation",
                                                        },
                                                    ],
                                                    value="Balanced",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # Risk Tolerance
                                        html.Div(
                                            [
                                                html.Label("Risk Tolerance", className="txn-label"),
                                                dcc.Dropdown(
                                                    id="settings-risk-tolerance",
                                                    options=[
                                                        {
                                                            "label": "Low (Higher Risk Penalties)",
                                                            "value": "Low",
                                                        },
                                                        {
                                                            "label": "Moderate (Default)",
                                                            "value": "Moderate",
                                                        },
                                                        {
                                                            "label": "High (Muted Risk Penalties)",
                                                            "value": "High",
                                                        },
                                                    ],
                                                    value="Moderate",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # Tax Bracket
                                        html.Div(
                                            [
                                                html.Label(
                                                    "Tax Bracket (For CGT Warnings)",
                                                    className="txn-label",
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-tax-bracket",
                                                    options=[
                                                        {"label": "0% (No Tax)", "value": "0%"},
                                                        {
                                                            "label": "15% (Super Fund)",
                                                            "value": "15%",
                                                        },
                                                        {"label": "19%", "value": "19%"},
                                                        {"label": "30%", "value": "30%"},
                                                        {"label": "32.5%", "value": "32.5%"},
                                                        {"label": "37% (Default)", "value": "37%"},
                                                        {"label": "45%", "value": "45%"},
                                                    ],
                                                    value="37%",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # Save Button & Success notification
                                        html.Div(
                                            [
                                                html.Button(
                                                    "Save Profile Settings",
                                                    id="settings-save-btn",
                                                    className="setup-btn-primary",
                                                    type="button",
                                                    style={"marginTop": "16px"},
                                                ),
                                                html.Div(
                                                    id="settings-save-status",
                                                    className="settings-status-message",
                                                ),
                                            ],
                                            className="settings-action-row",
                                        ),
                                    ],
                                    className="settings-form-container",
                                ),
                            ),
                        ],
                        className="grid-item-2",
                    ),
                    # Right Column: Strategy Weight Preview
                    html.Div(
                        [
                            section(
                                html.H3(
                                    "Active Strategy Weight Profile",
                                    className="settings-section-title",
                                ),
                                html.Div(
                                    [
                                        html.P(
                                            "These weights are applied dynamically to compute technical indicator signal scores. "
                                            "Scores sum to 1.0. Signals: BUY >= 0.5, SELL <= -0.5.",
                                            className="settings-preview-description",
                                        ),
                                        html.Div(id="settings-weights-preview-container"),
                                    ],
                                    className="settings-preview-container",
                                ),
                            ),
                        ],
                        className="grid-item-2",
                    ),
                ],
                className="charts-grid-row",
            ),
        ],
        className="page-root",
    )
