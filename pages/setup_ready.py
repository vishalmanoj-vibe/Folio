# pages/setup_ready.py
"""
pages/setup_ready.py
===================
Onboarding Wizard: Page 3 — Ready Screen with Data Pre-fetch Progress Tracker
Route: /setup/ready
"""

import dash
import dash_mantine_components as dmc
from dash import dcc, html

dash.register_page(__name__, path="/setup/ready", title="Folio — Ready")


def layout() -> html.Div:
    return html.Div(
        [
            # Session-scoped store: tracks enqueued task IDs and fetch phase
            dcc.Store(id="setup-init-tasks-store", data=None, storage_type="session"),
            # Fires once after 1.5s to auto-start the data fetch
            dcc.Interval(
                id="setup-startup-interval", interval=1500, max_intervals=1, disabled=False
            ),
            # Polling interval: fires every 2s to update task progress (started by auto_start_fetch)
            dcc.Interval(id="setup-poll-interval", interval=2000, disabled=True, max_intervals=120),
            html.Div(
                [
                    # ── Step Indicators ──────────────────────────────────────
                    html.Div(
                        [
                            html.Div(
                                [html.Span("✓", className="setup-step-num"), "Portfolio"],
                                className="setup-step completed",
                            ),
                            html.Div(
                                [html.Span("✓", className="setup-step-num"), "Strategy & AI"],
                                className="setup-step completed",
                            ),
                            html.Div(
                                [html.Span("3", className="setup-step-num"), "Ready"],
                                className="setup-step active",
                            ),
                        ],
                        className="setup-steps-header",
                    ),
                    # ── Dynamic Title & Subtitle (updated by poll callback) ───
                    html.H1(
                        "Preparing Your Dashboard",
                        id="setup-init-title",
                        className="setup-title",
                    ),
                    html.P(
                        "Folio is fetching live market data for your holdings. "
                        "This usually takes 30–90 seconds.",
                        id="setup-init-subtitle",
                        className="setup-subtitle",
                    ),
                    # ── Phase A: Progress Tracker ─────────────────────────────
                    html.Div(
                        [
                            # Animated progress bar
                            html.Div(
                                html.Div(
                                    id="setup-init-progress-bar",
                                    className="setup-progress-bar-fill",
                                    style={"width": "0%"},
                                ),
                                className="setup-progress-bar-track",
                            ),
                            # "X of Y tasks complete" label
                            html.Div(
                                html.Span(
                                    "Starting…",
                                    id="setup-init-progress-label",
                                    className="setup-progress-label",
                                ),
                                className="setup-progress-label-row",
                            ),
                            # Per-task step list (rendered by poll callback)
                            html.Div(id="setup-init-step-list", className="setup-step-list"),
                        ],
                        id="setup-init-progress-container",
                        className="setup-progress-container",
                    ),
                    # ── Phase B: Ready Summary (hidden until fetch completes) ──
                    html.Div(
                        id="setup-ready-summary",
                        className="setup-summary-box",
                        style={"display": "none"},
                    ),
                    # Timeout / warning message area
                    html.Div(id="setup-init-status-msg", className="setup-init-status-area"),
                    # ── Action Buttons ────────────────────────────────────────
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
                                disabled=True,
                            ),
                        ],
                        className="setup-actions-row",
                    ),
                    # Redirect / error feedback slot
                    html.Div(id="setup-ready-feedback"),
                ],
                className="setup-card",
            ),
        ],
        className="setup-root",
    )
