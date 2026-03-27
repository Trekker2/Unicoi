"""
Tradier Copy Bot - Positions Page

Displays live positions from the Tradier API across all connected accounts.
Read-only view with no action buttons. Uses a skeleton-first loading pattern:
serve_positions renders instantly, then update_positions populates via callback.

Page Layout:
    +------------------------------------------------------------------+
    |                       🗂️ Positions                               |
    |------------------------------------------------------------------|
    |  [Account 1: Master Account (VA231...) ⭐ Master]               |
    |  +--------------------------------------------------------------+|
    |  | Symbol    | Qty   | Cost Basis  | Date       |               ||
    |  |-----------|-------|-------------|------------|               ||
    |  | AAPL      | 100   | $15,230.00  | 2026-03-01 |               ||
    |  | SPY261218 | -5    | $3,400.00   | 2026-03-10 |               ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  [Account 2: Follower Account (VA442...)]                        |
    |  +--------------------------------------------------------------+|
    |  | Symbol | Qty | Cost Basis | Date |                            ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  > About Positions                                               |
    +------------------------------------------------------------------+

Key Features:
    - Skeleton loading for instant page render before API calls complete
    - Per-account sections with master badge indicator
    - Read-only display (no close/action buttons)
    - Supports equity and option position symbols

Shared Helper Functions (from style_manager):
    - build_page_title_row(): Page title with emoji
    - build_account_header(): Per-account section header with master badge
    - build_page_info_accordion(): About section accordion
    - get_theme_colors(): Dark/light theme color dict

Main Functions:
    - update_positions(color_mode): Build real position tables by account
    - serve_positions(color_mode): Build skeleton layout (returned instantly)
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from constants import *
from scripts.style_manager import *
from services.positions_service import do_get_positions


# ==============================================================================
# CONTENT BUILDER (called by deferred callback)
# ==============================================================================

def update_positions(color_mode="Dark"):
    """Build the real positions content grouped by account."""
    theme = get_theme_colors(color_mode)
    th_style = {
        "position": "sticky", "top": "0", "zIndex": "10",
        "backgroundColor": purple_hex, "color": "white",
        "border": "none", "whiteSpace": "nowrap",
        "boxShadow": "none",
    }

    try:
        account_data = do_get_positions()
    except Exception as e:
        return [html.P(f"Error loading positions: {e}", style={"color": DANGER, "textAlign": "center"})]

    sections = []
    for account, positions in account_data:
        alias = account.get("alias", account.get("account_number", ""))
        act_nbr = account.get("account_number", "")
        is_master = account.get("is_master", False)
        master_badge = " ⭐" if is_master else ""

        # Check for errors
        if positions and positions[0].get("_error"):
            error_header = build_account_header(len(sections) + 1, alias, act_nbr, is_master, color_mode)
            sections.append(html.Div([
                error_header,
                html.P(f"Error: {positions[0]['_error']}", style={"color": DANGER, "marginLeft": "1rem"}),
            ], style={"marginBottom": "2rem"}))
            continue

        # Build table rows
        table_rows = []
        for pos in positions:
            quantity = pos.get("quantity", 0)
            cost_basis = pos.get("cost_basis", 0)

            symbol = pos.get("symbol", "")

            row = html.Tr(
                children=[
                    html.Td(symbol, style={"color": "var(--text-primary)", "fontWeight": "500"}),
                    html.Td(str(quantity), style={"color": "var(--text-primary)"}),
                    html.Td(f"${cost_basis:,.2f}" if cost_basis else "", style={"color": "var(--text-secondary)"}),
                    html.Td(str(pos.get("date_acquired", ""))[:10], style={"color": "var(--text-secondary)"}),
                ]
            )
            table_rows.append(row)

        table_header = html.Thead(
            html.Tr([
                html.Th("Symbol", style=th_style),
                html.Th("Qty", style=th_style),
                html.Th("Cost Basis", style=th_style),
                html.Th("Date", style=th_style),
            ]),
        )
        if not table_rows:
            table_rows = [html.Tr(html.Td(
                "No positions.", colSpan=4,
                style={"color": "var(--text-secondary)", "textAlign": "center", "padding": "2rem"},
            ))]
        table = html.Table(
            children=[table_header, html.Tbody(table_rows)],
            className="app-table",
        )
        content = html.Div(table, className="app-table-container", style={"maxHeight": "500px"})

        account_header = build_account_header(
            account_num=len(sections) + 1,
            alias=alias,
            account_number=act_nbr,
            is_master=is_master,
            color_mode=color_mode,
        )
        sections.append(html.Div([account_header, content], style={"marginBottom": "2rem"}))

    if not sections:
        sections = [html.P("No accounts configured.", style={"color": "var(--text-secondary)", "textAlign": "center"})]

    return sections


# ==============================================================================
# PAGE LAYOUT (skeleton — returns instantly)
# ==============================================================================

def serve_positions(color_mode="Dark"):
    """Generate positions page skeleton layout."""
    theme = get_theme_colors(color_mode)

    skeleton_cards = [
        html.Div([
            dmc.Skeleton(height=45, radius="md", visible=True, style={"marginBottom": "1rem", "maxWidth": "450px"}),
            dmc.Skeleton(height=40, radius="sm", visible=True, style={"marginBottom": "0.5rem"}),
            dmc.Skeleton(height=200, radius="sm", visible=True),
        ], style={"marginBottom": "2rem"})
        for _ in range(2)
    ]

    layout = html.Div(
        children=[
            build_page_title_row("🗂️ Positions", color_mode),
            dcc.Interval(id="positions_initial_load", interval=100, max_intervals=1, n_intervals=0),
            dbc.Container(
                id="positions-page-content",
                children=skeleton_cards,
                fluid=True,
                style={"maxWidth": "1200px"},
            ),
            build_page_info_accordion(
                "Positions",
                "Live positions from the Tradier API displayed per connected account with skeleton loading.",
                [
                    {"Table Columns": [
                        "Symbol -- ticker or option contract symbol",
                        "Qty -- position quantity (negative for short positions)",
                        "Cost Basis -- total cost basis in dollars",
                        "Date -- date the position was acquired",
                    ]},
                    {"Features": [
                        "Per-account sections with master badge indicator",
                        "Skeleton loading renders instantly before API calls complete",
                        "Supports both equity and option position symbols",
                    ]},
                ],
                color_mode,
            ),
            html.Div(className="page-footer-spacer"),
        ]
    )

    return layout

# END
