"""
Tradier Copy Bot - Orders Page

Displays live orders from the Tradier API across all connected accounts.
Uses a skeleton-first loading pattern: serve_orders renders instantly with
placeholder cards, then update_orders populates real data via deferred callback.

Page Layout:
    +------------------------------------------------------------------+
    |                         📝 Orders                                |
    |------------------------------------------------------------------|
    |                                           [📥 Export CSV]        |
    |                                                                  |
    |  [Account 1: Master Account (VA231...) ⭐ Master]               |
    |  +--------------------------------------------------------------+|
    |  | ID | Account | Symbol | Class | Side | Qty | Status | Type  ||
    |  |    | Price | Created (ET) | Filled (ET) | Tag | Action       ||
    |  |----|---------|--------|-------|------|-----|--------|-------||
    |  | 12 | Master  | AAPL   | eqty  | buy  | 10 | filled | mkt   ||
    |  | 34 | Master  | TSLA   | optn  | 2leg | 5  | open   | lmt   ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  [Account 2: Follower Account (VA442...)]                        |
    |  +--------------------------------------------------------------+|
    |  | ID | Account | Symbol | ... (same columns)                   ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  > About Orders                                                  |
    |  (Follower Details Modal - triggered by master order ID click)   |
    |  (Cancel Order Confirmation Modal - hidden until triggered)      |
    +------------------------------------------------------------------+

Key Features:
    - Skeleton loading for instant page render before API calls complete
    - Per-account sections with master badge indicator
    - Account column on each row for easy identification
    - Price column falls back to average fill price when limit price is empty
    - Filled (ET) column shows fill timestamp once the order fills
    - Timestamps converted from UTC to Eastern time (ET suffix)
    - Export CSV button downloads all orders across accounts
    - Color-coded status badges (green/blue/red/gray)
    - Clickable master order IDs show follower details in a modal
    - Cancel button for orders in open statuses with confirmation modal
    - Supports equity and multi-leg option orders

Local Helper Functions:
    - _format_eastern(date_str): Convert UTC timestamp to Eastern time

Shared Helper Functions (from style_manager):
    - build_page_title_row(): Page title with emoji
    - build_account_header(): Per-account section header with master badge
    - build_page_info_accordion(): About section accordion
    - get_theme_colors(): Dark/light theme color dict

Main Functions:
    - update_orders(color_mode): Build real order tables grouped by account
    - serve_orders(color_mode): Build skeleton layout (returned instantly)
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt

from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from constants import *
from scripts.style_manager import *
from services.orders_service import do_get_orders


# ==============================================================================
# HELPERS
# ==============================================================================

def _format_eastern(date_str):
    """Convert a UTC date string from Tradier to Eastern time for display."""
    if not date_str:
        return ""
    try:
        naive = dt.datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        if naive.tzinfo is None:
            naive = utc_timezone.localize(naive)
        eastern = naive.astimezone(market_timezone)
        return eastern.strftime("%Y-%m-%d %H:%M:%S ET")
    except Exception:
        return str(date_str)[:19]


# ==============================================================================
# CONTENT BUILDER (called by deferred callback)
# ==============================================================================

def update_orders(color_mode="Dark"):
    """Build the real orders content grouped by account."""
    theme = get_theme_colors(color_mode)
    th_style = {
        "position": "sticky", "top": "0", "zIndex": "10",
        "backgroundColor": purple_hex, "color": "white",
        "border": "none", "whiteSpace": "nowrap",
        "boxShadow": "none",
    }

    try:
        account_data = do_get_orders()
    except Exception as e:
        return [html.P(f"Error loading orders: {e}", style={"color": DANGER, "textAlign": "center"})]

    sections = []
    for account, orders in account_data:
        alias = account.get("alias", account.get("account_number", ""))
        act_nbr = account.get("account_number", "")
        is_master = account.get("is_master", False)
        master_badge = " ⭐" if is_master else ""

        # Account header
        header = html.Div(
            children=[
                html.H5(
                    f"{alias} ({act_nbr}){master_badge}",
                    style={"color": "var(--text-primary)", "fontWeight": "600", "marginBottom": "0.5rem"},
                ),
                html.Hr(style={"borderTop": f"2px solid {purple_hex}", "width": "60px", "margin": "0 0 1rem 0"}),
            ],
        )

        # Check for errors
        if orders and orders[0].get("_error"):
            error_msg = html.P(
                f"Error fetching orders: {orders[0]['_error']}",
                style={"color": DANGER, "fontStyle": "italic"},
            )
            sections.append(html.Div([header, error_msg], style={"marginBottom": "2rem"}))
            continue

        # Build table rows
        table_rows = []
        for order in orders:
            order_class = order.get("class", "equity")
            legs = order.get("leg", [])
            leg_info = f"{len(legs)} legs" if legs else order.get("side", "")
            order_id = order.get("id", "")

            status = order.get("status", "")
            if status in filled_statuses:
                badge_color = "green"
            elif status in open_statuses:
                badge_color = "blue"
            elif status in bad_statuses:
                badge_color = "red"
            else:
                badge_color = "gray"

            # ID cell — clickable on master accounts to show follower details
            if is_master and order_id:
                id_cell = html.Td(
                    html.A(
                        str(order_id),
                        id={"type": "master-order-id", "index": str(order_id)},
                        href="#",
                        style={"color": purple_hex, "cursor": "pointer", "textDecoration": "underline",
                               "fontWeight": "500"},
                    ),
                )
            else:
                id_cell = html.Td(str(order_id), style={"color": "var(--text-secondary)"})

            row = html.Tr(
                children=[
                    id_cell,
                    html.Td(order.get("_account_alias", ""), style={"color": "var(--text-secondary)"}),
                    html.Td(order.get("symbol", ""), style={"color": "var(--text-primary)", "fontWeight": "500"}),
                    html.Td(order_class, style={"color": "var(--text-secondary)"}),
                    html.Td(leg_info, style={"color": "var(--text-primary)"}),
                    html.Td(str(order.get("quantity", "")), style={"color": "var(--text-primary)"}),
                    html.Td(dmc.Badge(status, color=badge_color, variant="filled", size="sm"),
                            style={"minWidth": "90px"}),
                    html.Td(order.get("type", ""), style={"color": "var(--text-secondary)"}),
                    html.Td(str(order.get("price") or order.get("avg_fill_price") or order.get("last_fill_price") or ""), style={"color": "var(--text-primary)"}),
                    html.Td(_format_eastern(order.get("create_date", "")), style={"color": "var(--text-secondary)", "whiteSpace": "nowrap"}),
                    html.Td(_format_eastern(order.get("transaction_date", "")), style={"color": "var(--text-secondary)", "whiteSpace": "nowrap"}),
                    html.Td(order.get("tag", ""), style={"color": "var(--text-secondary)", "maxWidth": "140px",
                                                          "overflow": "hidden", "textOverflow": "ellipsis",
                                                          "whiteSpace": "nowrap"}),
                    html.Td(
                        dmc.Button(
                            "❌ Cancel",
                            id={"type": "cancel-order", "index": f"{act_nbr}:{order.get('id', '')}"},
                            color="red", size="xs", variant="outline",
                        ) if status in open_statuses else "",
                        style={"textAlign": "center"},
                    ),
                ]
            )
            table_rows.append(row)

        table_header = html.Thead(
            html.Tr([
                html.Th("ID", style=th_style),
                html.Th("Account", style=th_style),
                html.Th("Symbol", style=th_style),
                html.Th("Class", style=th_style),
                html.Th("Side", style=th_style),
                html.Th("Qty", style=th_style),
                html.Th("Status", style={**th_style, "minWidth": "90px"}),
                html.Th("Type", style=th_style),
                html.Th("Price", style=th_style),
                html.Th("Created", style=th_style),
                html.Th("Filled", style=th_style),
                html.Th("Tag", style={**th_style, "maxWidth": "140px"}),
                html.Th("Action", style={**th_style, "textAlign": "center"}),
            ]),
        )
        if not table_rows:
            table_rows = [html.Tr(html.Td(
                "No orders.", colSpan=13,
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

def serve_orders(color_mode="Dark"):
    """Generate orders page skeleton layout."""
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
            build_page_title_row("📝 Orders", color_mode),
            dcc.Interval(id="orders_initial_load", interval=100, max_intervals=1, n_intervals=0),
            html.Div(
                dmc.Button(
                    "Export CSV",
                    id="export-orders-csv-btn",
                    color="grape",
                    size="sm",
                    variant="outline",
                    leftSection=html.Span("📥"),
                ),
                style={"textAlign": "right", "maxWidth": "1400px", "margin": "0 auto 0.75rem auto"},
            ),
            dcc.Download(id="export-orders-csv-download"),
            dbc.Container(
                id="orders-page-content",
                children=skeleton_cards,
                fluid=True,
                style={"maxWidth": "1400px"},
            ),
            build_page_info_accordion(
                "Orders",
                "Live orders from the Tradier API displayed per connected account with skeleton loading.",
                [
                    {"Table Columns": [
                        "ID -- order ID (clickable on master account to view follower details)",
                        "Account -- account alias for this order",
                        "Symbol -- ticker symbol for the order",
                        "Class -- order class (equity or option)",
                        "Side -- buy/sell direction or number of legs for multi-leg orders",
                        "Qty -- order quantity",
                        "Status -- color-coded badge (green=filled, blue=open, red=rejected/canceled, gray=other)",
                        "Type -- order type (market, limit, stop, etc.)",
                        "Price -- limit/stop price; falls back to average fill price after the order fills",
                        "Created -- order creation timestamp in Eastern time",
                        "Filled -- order fill timestamp in Eastern time (blank until filled)",
                        "Tag -- order tag label if present",
                        "Action -- cancel button for orders in open statuses",
                    ]},
                    {"Features": [
                        "Per-account sections with master badge indicator",
                        "Clickable master order IDs show follower order details in a modal",
                        "Rejected master orders show explanation in follower modal",
                        "Skeleton loading renders instantly before API calls complete",
                        "Supports equity and multi-leg option orders",
                        "Cancel order with confirmation modal dialog",
                        "Timestamps converted from UTC to Eastern time",
                        "Export CSV button downloads all orders across accounts",
                    ]},
                ],
                color_mode,
            ),
            html.Div(className="page-footer-spacer"),

            # Follower details modal (triggered by clicking master order ID)
            dcc.Store(id="follower-details-order-id", data=""),
            dmc.Modal(
                id="follower-details-modal",
                title="Follower Order Details",
                centered=True,
                size="lg",
                styles={
                    "header": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "title": {"color": "var(--text-primary)", "fontWeight": 600},
                    "body": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "close": {"color": "var(--text-primary)"},
                    "overlay": {"backgroundColor": "rgba(0, 0, 0, 0.5)"},
                },
                children=[
                    html.Div(id="follower-details-content"),
                ],
            ),

            # Cancel order confirmation modal
            dcc.Store(id="cancel-order-pending", data=""),
            html.Div(id="orders-alert", children=[], style={"display": "none"}),
            dmc.Modal(
                id="cancel-order-modal",
                title="Confirm Cancel Order",
                centered=True,
                styles={
                    "header": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "title": {"color": "var(--text-primary)", "fontWeight": 600},
                    "body": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "close": {"color": "var(--text-primary)"},
                    "overlay": {"backgroundColor": "rgba(0, 0, 0, 0.5)"},
                },
                children=[
                    html.P(id="cancel-order-message", style={"marginBottom": "20px"}),
                    html.Div(
                        children=[
                            dmc.Button("✅ Confirm", id="cancel-order-confirm", color="red", n_clicks=0, style={"marginRight": "10px"}),
                            dmc.Button("❌ Cancel", id="cancel-order-cancel", color="gray", variant="outline", n_clicks=0),
                        ],
                        style={"display": "flex", "justifyContent": "flex-end"},
                    ),
                ],
            ),
        ]
    )

    return layout

# END
