"""
Tradier Copy Bot - Activity Page

Displays system activity logs with color-coded keyword highlighting.
Logs are fetched from the database and rendered in a scrollable table
with per-row delete buttons and a bulk clear-all action.

Page Layout:
    +------------------------------------------------------------------+
    |                       📋 Activity                                |
    |------------------------------------------------------------------|
    |  [Activity Log Card]                                             |
    |  +--------------------------------------------------------------+|
    |  |                              [🗑️ Clear All Logs]             ||
    |  | Datetime          | Log Message (color-coded)        | Del   ||
    |  |-------------------|----------------------------------|-------||
    |  | 2026-03-20 09:01  | Order FILLED for AAPL (green)    | [x]   ||
    |  | 2026-03-20 09:00  | Starting copy engine (cyan)      | [x]   ||
    |  | 2026-03-20 08:59  | ERROR connecting (red)            | [x]   ||
    |  +--------------------------------------------------------------+|
    |  |  Scrollable up to 200 rows, max-height 600px                 ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  (Clear All Confirmation Modal - hidden until triggered)         |
    +------------------------------------------------------------------+

Key Features:
    - Keyword coloring: green (success/filled), red (error/fail),
      orange (warning/pending), cyan (info/update)
    - Per-row delete buttons for individual log removal
    - Clear all logs with modal confirmation dialog
    - Scrollable table capped at 200 most recent entries
    - Alert container for action feedback

Functions:
    - colorize_log(log_text)       : Apply keyword-based color spans
    - serve_activity(color_mode)   : Build and return the full page layout
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import re

from dash import dcc, html
from dash_iconify import DashIconify
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from constants import *
from scripts.style_manager import *
from services.activity_service import do_get_logs


# ==============================================================================
# KEYWORD COLORING
# ==============================================================================

GREEN_PATTERN = re.compile(r'\b(true|success|filled|buy_to_open|buy_to_close|buy|long|active|connected|started|enabled|stored|completed)\b', re.IGNORECASE)
RED_PATTERN = re.compile(r'\b(false|error|fail|rejected|sell_to_open|sell_to_close|sell_short|sell|short|stopped|disabled|exit|cancel|canceled|expired)\b', re.IGNORECASE)
ORANGE_PATTERN = re.compile(r'\b(warning|warn|timeout|retry|slow|pending|stale|skipping)\b', re.IGNORECASE)
CYAN_PATTERN = re.compile(r'\b(info|status|check|update|refresh|fetch|copying|starting|cleaning)\b', re.IGNORECASE)
MASTER_PATTERN = re.compile(r'\bMaster\b')
FOLLOWER_PATTERN = re.compile(r'\bFollower\b')


def colorize_log(log_text):
    """Apply keyword coloring to a log message."""
    if not log_text:
        return log_text

    parts = []
    last_end = 0
    combined = re.compile(
        r'\b(Master|Follower|'
        r'buy_to_open|buy_to_close|sell_to_open|sell_to_close|sell_short|'
        r'true|success|filled|buy|long|active|connected|started|enabled|stored|completed|'
        r'false|error|fail|rejected|sell|short|stopped|disabled|exit|cancel|canceled|expired|'
        r'warning|warn|timeout|retry|slow|pending|stale|skipping|'
        r'info|status|check|update|refresh|fetch|copying|starting|cleaning)\b',
        re.IGNORECASE,
    )

    for match in combined.finditer(log_text):
        if match.start() > last_end:
            parts.append(log_text[last_end:match.start()])
        word = match.group()
        if MASTER_PATTERN.match(word):
            color = "#fbbf24"  # Gold/amber for master
        elif FOLLOWER_PATTERN.match(word):
            color = "#818cf8"  # Indigo/purple for follower
        elif GREEN_PATTERN.match(word):
            color = SUCCESS
        elif RED_PATTERN.match(word):
            color = DANGER
        elif ORANGE_PATTERN.match(word):
            color = WARNING
        else:
            color = "#06b6d4"
        parts.append(html.Span(word, style={"color": color, "fontWeight": "600"}))
        last_end = match.end()

    if last_end < len(log_text):
        parts.append(log_text[last_end:])

    return parts if parts else log_text


# ==============================================================================
# PAGE LAYOUT
# ==============================================================================

def serve_activity(color_mode="Dark"):
    """
    Generate activity page layout.

    Args:
        color_mode: "Dark" or "Light"

    Returns:
        html.Div: Activity page layout
    """
    theme = get_theme_colors(color_mode)
    logs = do_get_logs()

    # Build log table rows with delete buttons
    table_rows = []
    for i, log in enumerate(logs[:200]):
        row = html.Tr(
            id={"type": "activity_tr", "row": str(i)},
            children=[
                html.Td(
                    log.get("datetime", ""),
                    id={"type": "activity_datetime", "row": str(i)},
                    style={"color": "var(--text-secondary)", "whiteSpace": "nowrap", "fontSize": "0.85rem"},
                ),
                html.Td(
                    children=[
                        html.Span(
                            id={"type": "activity_log", "row": str(i)},
                            children=log.get("log", ""),
                            style={"display": "none"},
                        ),
                        html.Span(
                            id={"type": "activity_log_colored", "row": str(i)},
                            children=colorize_log(str(log.get("log", ""))),
                        ),
                    ],
                    style={"whiteSpace": "pre-wrap", "fontSize": "0.85rem"},
                ),
                html.Td(
                    html.Div(
                        id={"type": "activity_delete_div", "row": str(i)},
                        children=create_delete_button(
                            button_id={"type": "activity_button", "row": str(i)},
                        ),
                        style={"textAlign": "center"},
                    ),
                    style={"width": "40px"},
                ),
            ],
        )
        table_rows.append(row)

    header_cell_style = {
        "position": "sticky", "top": "0", "zIndex": "10",
        "backgroundColor": purple_hex, "color": "white",
        "border": "none", "whiteSpace": "nowrap",
        "boxShadow": "none",
    }
    table_header = html.Thead(
        html.Tr([
            html.Th("Datetime", style={**header_cell_style, "width": "180px"}),
            html.Th("Log", style=header_cell_style),
            html.Th("", style={**header_cell_style, "width": "40px"}),
        ]),
    )

    logs_table = html.Div(
        html.Table(
            id="activity_table",
            children=[table_header, html.Tbody(id={"type": "table_body", "_id": "activity"}, children=table_rows)],
            className="app-table",
        ),
        className="app-table-container",
        style={"maxHeight": "600px"},
    )

    # Action buttons
    action_btns = html.Div(
        children=[
            dmc.Button(
                children=[DashIconify(icon="mdi:download", width=18), " Export CSV"],
                id="export-logs-btn",
                color="blue",
                variant="outline",
                size="sm",
                style={"marginRight": "0.5rem"},
            ),
            dmc.Button(
                "🗑️ Clear All Logs",
                id="clear-all-logs",
                color="red",
                variant="outline",
                size="sm",
                style={"display": "none"},
            ),
        ],
        style={"textAlign": "right", "marginBottom": "1rem", "display": "flex", "justifyContent": "flex-end", "gap": "0.5rem"},
    )

    activity_content = html.Div([
        dcc.Download(id="download-logs"),
        action_btns,
        html.Div(id="activity-alert", children=[]),
        html.Div(
            id="activity-table-container",
            children=[logs_table] if table_rows else [
                html.P(
                    "No activity logs yet.",
                    style={"color": "var(--text-secondary)", "textAlign": "center"},
                )
            ],
            style={"maxHeight": "600px", "overflowY": "auto"},
        ),
    ])

    layout = html.Div(
        children=[
            build_page_title_row("📋 Activity", color_mode),
            dbc.Container(
                children=[activity_content],
                fluid=True,
                style={"maxWidth": "1200px"},
            ),
            build_page_info_accordion(
                "Activity",
                "View color-coded system activity logs for the copy engine and account operations.",
                [
                    {"Table Columns": [
                        "Datetime -- timestamp of the logged event",
                        "Log -- message with keyword coloring applied automatically",
                        "Delete -- per-row button to remove individual log entries",
                    ]},
                    {"Keyword Coloring": [
                        "Green -- success, filled, buy, long, active, connected, started, enabled, stored, completed",
                        "Red -- error, fail, rejected, sell, short, stopped, disabled, exit, cancel, canceled, expired",
                        "Orange -- warning, timeout, retry, slow, pending, stale, skipping",
                        "Cyan -- info, status, check, update, refresh, fetch, copying, starting, cleaning",
                    ]},
                    {"Actions": [
                        "Clear All Logs -- bulk delete all activity logs with confirmation modal",
                        "Per-row delete -- remove a single log entry instantly",
                        "Scrollable table capped at 200 most recent entries",
                    ]},
                ],
                color_mode,
            ),
            html.Div(className="page-footer-spacer"),

            # Clear all confirmation modal
            dmc.Modal(
                id="clear-logs-modal",
                title="Confirm Clear All Logs",
                centered=True,
                styles={
                    "header": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "title": {"color": "var(--text-primary)", "fontWeight": 600},
                    "body": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "close": {"color": "var(--text-primary)"},
                    "overlay": {"backgroundColor": "rgba(0, 0, 0, 0.5)"},
                },
                children=[
                    html.P("Are you sure you want to clear all activity logs? This cannot be undone.", style={"marginBottom": "20px"}),
                    html.Div(
                        children=[
                            dmc.Button("✅ Confirm", id="clear-logs-confirm", color="red", n_clicks=0, style={"marginRight": "10px"}),
                            dmc.Button("❌ Cancel", id="clear-logs-cancel", color="gray", variant="outline", n_clicks=0),
                        ],
                        style={"display": "flex", "justifyContent": "flex-end"},
                    ),
                ],
            ),
        ]
    )

    return layout

# END
