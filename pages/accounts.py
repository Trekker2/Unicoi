"""
Tradier Copy Bot - Accounts Page

Manages connected Tradier brokerage accounts. Users can view all linked
accounts, designate a master account for trade copying, add new accounts
via API key, and remove accounts with confirmation.

Page Layout:
    +------------------------------------------------------------------+
    |                        💼 Accounts                               |
    |------------------------------------------------------------------|
    |  [Connected Accounts Card]                                       |
    |  +--------------------------------------------------------------+|
    |  | Alias | Account # | API Key (masked) | Master ◉ | Delete 🗑 ||
    |  |-------|-----------|------------------|----------|------------||
    |  | Joe   | VA231...  | 9i7X***          |  [on]    |   [x]     ||
    |  | Acct2 | VA442...  | kR4z***          |  [off]   |   [x]     ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  [Add Account Card]                                              |
    |  +--------------------------------------------------------------+|
    |  | Alias [________]  Account # [________]  API Key [________]   ||
    |  |                                      [➕ Add Account]        ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  (Delete Account Confirmation Modal - hidden until triggered)    |
    +------------------------------------------------------------------+

Key Features:
    - Accounts table with masked API keys for security
    - Master account toggle switch (grape-colored, one active at a time)
    - Add account form with alias, account number, and API key fields
    - Delete account with modal confirmation dialog
    - Alert container for success/error feedback

Functions:
    - serve_accounts(color_mode) : Build and return the full page layout
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from constants import *
from helper import hide_text
from scripts.style_manager import *
from services.accounts_service import do_get_accounts


# ==============================================================================
# PAGE LAYOUT
# ==============================================================================

def serve_accounts(color_mode="Dark"):
    """
    Generate accounts page layout.

    Args:
        color_mode: "Dark" or "Light"

    Returns:
        html.Div: Accounts page layout
    """
    theme = get_theme_colors(color_mode)
    input_styles = get_input_styles(color_mode)
    accounts = do_get_accounts()

    # Build accounts table rows
    table_rows = []
    for account in accounts:
        act_nbr = account.get("account_number", "")
        alias = account.get("alias", "")
        api_key = account.get("api_key", "")
        is_master = account.get("is_master", False)

        row = html.Tr(
            children=[
                html.Td(alias, style={"color": theme["text_primary"]}),
                html.Td(act_nbr, style={"color": theme["text_primary"]}),
                html.Td(hide_text(api_key), style={"color": theme["text_secondary"]}),
                html.Td(
                    dmc.Switch(
                        id={"type": "master-radio", "index": act_nbr},
                        checked=is_master,
                        color="grape",
                        size="sm",
                    ),
                    style={"textAlign": "center"},
                ),
                html.Td(
                    create_delete_button(
                        {"type": "delete-account", "index": act_nbr}
                    ),
                    style={"textAlign": "center"},
                ),
            ]
        )
        table_rows.append(row)

    # Accounts table
    th_style = {
        "position": "sticky", "top": "0", "zIndex": "10",
        "backgroundColor": purple_hex, "color": "white",
        "border": "none", "whiteSpace": "nowrap",
        "boxShadow": "none",
    }
    table_header = html.Thead(
        html.Tr([
            html.Th("Alias", style=th_style),
            html.Th("Account #", style=th_style),
            html.Th("API Key", style=th_style),
            html.Th("Master", style={**th_style, "textAlign": "center"}),
            html.Th("Delete", style={**th_style, "textAlign": "center"}),
        ]),
    )

    accounts_table = html.Div(
        html.Table(
            children=[table_header, html.Tbody(table_rows)],
            className="app-table",
        ),
        className="app-table-container",
        style={"maxHeight": "500px"},
    )

    # Accounts table (no card wrapper)
    accounts_content = html.Div([
        html.Div(id="accounts-alert", children=[]),
        accounts_table if table_rows else html.P(
            "No accounts connected. Add one below.",
            style={"color": "var(--text-secondary)", "textAlign": "center", "padding": "2rem"},
        ),
    ], style={"marginBottom": "1.5rem"})

    # Add account card
    add_card = create_beautiful_card(
        title="Add Account",
        icon="mdi:account-plus",
        color_mode=color_mode,
        content=[
            dbc.Row(
                children=[
                    dbc.Col(
                        dmc.TextInput(
                            id="add-alias",
                            label="Alias",
                            placeholder="e.g. Joe's Account",
                            leftSection=DashIconify(icon="mdi:tag-outline", width=20),
                            styles=input_styles,
                        ),
                        md=4,
                    ),
                    dbc.Col(
                        dmc.TextInput(
                            id="add-account-number",
                            label="Account Number",
                            placeholder="e.g. VA23115648",
                            leftSection=DashIconify(icon="mdi:bank", width=20),
                            styles=input_styles,
                        ),
                        md=4,
                    ),
                    dbc.Col(
                        dmc.PasswordInput(
                            id="add-api-key",
                            label="API Key",
                            placeholder="e.g. 9i7X6Rw4uFEZKjLozEdxpKNY8TNU",
                            leftSection=DashIconify(icon="mdi:key-outline", width=20),
                            styles=input_styles,
                        ),
                        md=4,
                    ),
                ],
                style={"marginBottom": "1rem"},
            ),
            create_submit_button("➕ Add Account", "add-account-button", color_mode),
        ],
    )

    layout = html.Div(
        children=[
            build_page_title_row("💼 Accounts", color_mode),
            dbc.Container(
                children=[accounts_content, add_card],
                fluid=True,
                style={"maxWidth": "1200px"},
            ),
            build_page_info_accordion(
                "Accounts",
                "Manage connected Tradier brokerage accounts used for trade copying.",
                [
                    {"Connected Accounts Table": [
                        "Alias -- friendly name for the account",
                        "Account # -- Tradier brokerage account number",
                        "API Key -- masked Tradier API key for security",
                        "Master -- toggle switch to designate the master account (only one active at a time)",
                        "Delete -- remove an account with confirmation dialog",
                    ]},
                    {"Add Account Form": [
                        "Alias -- label for the new account",
                        "Account Number -- Tradier account number (e.g. VA23115648)",
                        "API Key -- Tradier API access token for order access",
                    ]},
                    {"How It Works": [
                        "The master account is the source of trades that get copied to all follower accounts",
                        "Follower accounts automatically mirror the master account's new orders",
                        "Each account requires its own Tradier API key with trading permissions",
                    ]},
                ],
                color_mode,
            ),
            html.Div(className="page-footer-spacer"),

            # Delete account confirmation modal
            dcc.Store(id="delete-account-pending", data=""),
            dmc.Modal(
                id="delete-account-modal",
                title="Confirm Delete Account",
                centered=True,
                styles={
                    "header": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "title": {"color": "var(--text-primary)", "fontWeight": 600},
                    "body": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "close": {"color": "var(--text-primary)"},
                    "overlay": {"backgroundColor": "rgba(0, 0, 0, 0.5)"},
                },
                children=[
                    html.P(id="delete-account-message", style={"marginBottom": "20px"}),
                    html.Div(
                        children=[
                            dmc.Button("✅ Confirm", id="delete-account-confirm", color="red", n_clicks=0, style={"marginRight": "10px"}),
                            dmc.Button("❌ Cancel", id="delete-account-cancel", color="gray", variant="outline", n_clicks=0),
                        ],
                        style={"display": "flex", "justifyContent": "flex-end"},
                    ),
                ],
            ),
        ]
    )

    return layout

# END
