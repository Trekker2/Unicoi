"""
Tradier Copy Bot - Settings Page

Provides controls for the copy engine, per-account trade multipliers, and
display preferences. All setting changes are persisted to the database and
take effect immediately.

Page Layout:
    +------------------------------------------------------------------+
    |                        ⚙️ Settings                               |
    |------------------------------------------------------------------|
    |  [Copy Engine Control Card]                                      |
    |  +--------------------------------------------------------------+|
    |  | 🤖 Enable Automation          [on/off]  (master killswitch) ||
    |  | 📡 Use Streaming              [on/off]  (WebSocket mode)    ||
    |  | Poll Interval (sec)           [___5__]  (hidden if streaming)||
    |  | Stale Timeout (min)           [___2__]                       ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  [Per-Account Multipliers Card]                                  |
    |  +--------------------------------------------------------------+|
    |  | Bob's Account (VA442...)       [__1.00__]                    ||
    |  | Sue's Account (VA553...)       [__0.50__]                    ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  [Display Card]                                                  |
    |  +--------------------------------------------------------------+|
    |  | Color Mode    [🌙 Dark | ☀️ Light]                          ||
    |  +--------------------------------------------------------------+|
    |                                                                  |
    |  (Automation Confirmation Modal - hidden until triggered)        |
    +------------------------------------------------------------------+

Key Features:
    - Master killswitch for copy engine with confirmation modal
    - Streaming toggle (WebSocket vs polling mode)
    - Configurable poll interval and stale order timeout
    - Per-follower quantity multipliers (0-100x, 0.01 step)
    - Dark/Light color mode segmented control
    - Alert container for save feedback

Functions:
    - serve_settings(color_mode) : Build and return the full page layout
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from constants import *
from scripts.style_manager import *
from services.settings_service import do_get_settings
from services.accounts_service import do_get_accounts


# ==============================================================================
# PAGE LAYOUT
# ==============================================================================

def serve_settings(color_mode="Dark"):
    """
    Generate settings page layout.

    Args:
        color_mode: "Dark" or "Light"

    Returns:
        html.Div: Settings page layout
    """
    theme = get_theme_colors(color_mode)
    input_styles = get_input_styles(color_mode)
    switch_styles = get_switch_styles(color_mode)
    seg_styles = get_segmented_control_styles(color_mode)
    settings = do_get_settings()

    # Control card
    control_card = create_beautiful_card(
        title="Copy Engine Control",
        icon="mdi:tune",
        color_mode=color_mode,
        card_id={"type": "settings_card", "_id": "control"},
        content=[
            # Master killswitch with confirmation
            dmc.Switch(
                id="settings-use-automation",
                label="🤖 Enable Automation",
                description="Master killswitch for the copy engine",
                checked=settings.get("use_automation", False),
                color="grape",
                styles=switch_styles,
                style={"marginBottom": "1.5rem"},
            ),
            dcc.Store(id="automation-previous-value", data=settings.get("use_automation", False)),
            # Streaming mode
            dmc.Switch(
                id="settings-use-streaming",
                label="📡 Use Streaming",
                description="Use WebSocket streaming for instant order detection (polling becomes fallback)",
                checked=settings.get("use_streaming", False),
                color="grape",
                styles=switch_styles,
                style={"marginBottom": "1.5rem"},
            ),
            # Poll interval (hidden when streaming is enabled)
            html.Div(
                id="poll-interval-container",
                children=[
                    dmc.NumberInput(
                        id="settings-poll-interval",
                        label="Poll Interval (seconds)",
                        description="How often to check for new master orders",
                        value=settings.get("poll_interval", DEFAULT_POLL_INTERVAL),
                        min=1,
                        max=60,
                        leftSection=DashIconify(icon="mdi:timer-outline", width=20),
                        styles=input_styles,
                        style={"marginBottom": "1.5rem", "maxWidth": "300px"},
                    ),
                ],
                style={"display": "none" if settings.get("use_streaming", False) else "block"},
            ),
            # Stale timeout
            dmc.NumberInput(
                id="settings-stale-timeout",
                label="Stale Timeout (minutes)",
                description="Skip copying orders older than this",
                value=settings.get("stale_timeout", DEFAULT_STALE_TIMEOUT),
                min=1,
                max=60,
                leftSection=DashIconify(icon="mdi:clock-alert-outline", width=20),
                styles=input_styles,
                style={"maxWidth": "300px"},
            ),
        ],
    )

    # Multipliers card
    accounts = do_get_accounts()
    followers = [a for a in accounts if not a.get("is_master", False)]
    multipliers = settings.get("multipliers", {})

    multiplier_rows = []
    for follower in followers:
        act_nbr = follower.get("account_number", "")
        alias = follower.get("alias", act_nbr)
        mult = multipliers.get(act_nbr, 1)

        row = dbc.Row(
            children=[
                dbc.Col(
                    html.Span(
                        f"{alias} ({act_nbr})",
                        style={"color": "var(--text-primary)", "fontWeight": "500"},
                    ),
                    md=6,
                    style={"display": "flex", "alignItems": "center"},
                ),
                dbc.Col(
                    dmc.NumberInput(
                        id={"type": "settings-multiplier", "index": act_nbr},
                        value=mult,
                        min=0,
                        max=100,
                        step=0.01,
                        decimalScale=2,
                        styles=input_styles,
                    ),
                    md=6,
                ),
            ],
            style={"marginBottom": "1rem"},
        )
        multiplier_rows.append(row)

    multiplier_card = create_beautiful_card(
        title="Per-Account Multipliers",
        icon="mdi:multiplication",
        color_mode=color_mode,
        card_id={"type": "settings_card", "_id": "multipliers"},
        content=multiplier_rows if multiplier_rows else [
            html.P(
                "No follower accounts. Add accounts and set a master first.",
                style={"color": "var(--text-secondary)"},
            )
        ],
    )

    # Display card
    display_card = create_beautiful_card(
        title="Display",
        icon="mdi:palette",
        color_mode=color_mode,
        card_id={"type": "settings_card", "_id": "display"},
        content=[
            html.Div(
                children=[
                    html.Span(
                        "Color Mode",
                        style={"color": "var(--text-secondary)", "fontSize": "0.85rem", "marginBottom": "0.5rem", "display": "block"},
                    ),
                    dmc.SegmentedControl(
                        id="settings-color-mode",
                        data=[
                            {"value": "Dark", "label": "\U0001f319 Dark"},
                            {"value": "Light", "label": "\u2600\ufe0f Light"},
                        ],
                        value=settings.get("color_mode", "Dark"),
                        styles=seg_styles,
                    ),
                ]
            ),
        ],
    )

    # Settings alert
    settings_alert = html.Div(id="settings-alert", children=[])

    layout = html.Div(
        children=[
            build_page_title_row("⚙️ Settings", color_mode),
            dbc.Container(
                children=[settings_alert, control_card, multiplier_card, display_card],
                fluid=True,
                style={"maxWidth": "800px"},
            ),
            build_page_info_accordion(
                "Settings",
                "Configure the copy engine, per-account trade multipliers, and display preferences.",
                [
                    {"Copy Engine Control": [
                        "Enable Automation -- master killswitch to start or stop the copy engine (requires confirmation)",
                        "Use Streaming -- toggle WebSocket streaming for instant order detection vs polling fallback",
                        "Poll Interval (seconds) -- how often to check for new master orders (hidden when streaming is on)",
                        "Stale Timeout (minutes) -- skip copying orders older than this threshold",
                    ]},
                    {"Per-Account Multipliers": [
                        "Each follower account has a quantity multiplier (0 to 100x, 0.01 step)",
                        "Multiplier of 1.00 copies the exact master quantity; 0.50 copies half; 2.00 copies double",
                        "Only follower accounts are shown (the master account is excluded)",
                    ]},
                    {"Display": [
                        "Color Mode -- toggle between Dark and Light theme across the entire dashboard",
                    ]},
                ],
                color_mode,
            ),
            html.Div(className="page-footer-spacer"),

            # Automation confirmation modal
            dmc.Modal(
                id="automation-modal",
                title="Confirm Automation Change",
                centered=True,
                styles={
                    "header": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "title": {"color": "var(--text-primary)", "fontWeight": 600},
                    "body": {"backgroundColor": theme["card_bg"], "color": "var(--text-primary)"},
                    "close": {"color": "var(--text-primary)"},
                    "overlay": {"backgroundColor": "rgba(0, 0, 0, 0.5)"},
                },
                children=[
                    html.Div(id="automation-modal-message", style={"marginBottom": "20px", "fontSize": "0.95rem"}),
                    html.Div(
                        children=[
                            dmc.Button("✅ Confirm", id="automation-confirm", color="grape", n_clicks=0, style={"marginRight": "10px"}),
                            dmc.Button("❌ Cancel", id="automation-cancel", color="red", variant="outline", n_clicks=0),
                        ],
                        style={"display": "flex", "justifyContent": "flex-end"},
                    ),
                ],
            ),
        ]
    )

    return layout

# END
