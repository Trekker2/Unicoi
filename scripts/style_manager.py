"""
Style Manager Module for Tradier Copy Bot

This module provides centralized UI styling for the dashboard including
colors, typography, theme management, and reusable component factories.

Key Features:
    - Tradier Purple (#6f42c1) brand theming
    - Dark/Light mode support with consistent palettes
    - Mantine component style generators
    - Reusable card, button, and input factories
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import os

from dash import html
from dash_iconify import DashIconify
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from constants import *


# ==============================================================================
# BRAND COLORS - Tradier Purple Palette
# ==============================================================================

purple_hex = "#6f42c1"
purple_rgb = "rgba(111, 66, 193, 1)"
purple_rgb8 = "rgba(111, 66, 193, 0.8)"
purple_rgb6 = "rgba(111, 66, 193, 0.6)"
purple_rgb4 = "rgba(111, 66, 193, 0.4)"
purple_rgb2 = "rgba(111, 66, 193, 0.2)"

# Basic colors
black_hex = "#000000"
white_hex = "#FFFFFF"
light_hex = "#F5F5F0"

# ==============================================================================
# THEME COLORS - Dark/Light Mode Palettes
# ==============================================================================

dark_page_bg = "#2a2a2a"
dark_card_bg = "#1f1f1f"
dark_card_border = "#333333"
dark_table_container = "#1f1f1f"
dark_row_even = "#252525"
dark_row_odd = "#2e2e2e"
dark_footer_bg = "#1a1a1a"

light_page_bg = "#f5f5f5"
light_card_bg = "#f8f9fa"
light_card_border = "#dee2e6"
light_table_container = "#ffffff"
light_row_even = "#ffffff"
light_row_odd = "#f8f9fa"

dark_hex = dark_page_bg
charcoal_hex = dark_footer_bg

# Page background gradients (brand color tint - repeating bell curve)
def _blend_hex(fg, bg, alpha):
    """Blend fg color into bg at given alpha (0-1). Returns solid hex."""
    fg_r, fg_g, fg_b = int(fg[1:3], 16), int(fg[3:5], 16), int(fg[5:7], 16)
    bg_r, bg_g, bg_b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
    r = int(fg_r * alpha + bg_r * (1 - alpha))
    g = int(fg_g * alpha + bg_g * (1 - alpha))
    b = int(fg_b * alpha + bg_b * (1 - alpha))
    return f"#{r:02x}{g:02x}{b:02x}"


def _build_gradient(brand, bg, intensities):
    """Build a repeating bell-curve gradient from brand color blended into bg."""
    stops = [
        f"{bg} 0px",
        f"{_blend_hex(brand, bg, intensities[0])} 120px",
        f"{_blend_hex(brand, bg, intensities[1])} 250px",
        f"{_blend_hex(brand, bg, intensities[2])} 370px",
        f"{_blend_hex(brand, bg, intensities[3])} 500px",
        f"{_blend_hex(brand, bg, intensities[2])} 630px",
        f"{_blend_hex(brand, bg, intensities[1])} 750px",
        f"{_blend_hex(brand, bg, intensities[0])} 880px",
        f"{bg} 1000px",
    ]
    return f"repeating-linear-gradient(180deg, {', '.join(stops)})"


dark_page_gradient = _build_gradient(purple_hex, dark_page_bg, [0.015, 0.035, 0.055, 0.07])
light_page_gradient = _build_gradient(purple_hex, light_page_bg, [0.02, 0.045, 0.07, 0.09])


def get_horizontal_gradient(color_mode="Dark"):
    """Get horizontal gradient for navbar/footer — brand tint peaks at center."""
    if color_mode == "Dark":
        bg = dark_footer_bg
        peak = _blend_hex(purple_hex, bg, 0.15)
    else:
        bg = "#e9ecef"
        peak = _blend_hex(purple_hex, bg, 0.18)
    return f"linear-gradient(90deg, {bg} 0%, {peak} 50%, {bg} 100%)"


# ==============================================================================
# ACCENT COLORS
# ==============================================================================

ACCENT = purple_hex
SUCCESS = "#10b981"
WARNING = "#f59e0b"
DANGER = "#ef4444"

# ==============================================================================
# TYPOGRAPHY
# ==============================================================================

FONT_FAMILY_PRIMARY = "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"
FONT_INPUT = FONT_FAMILY_PRIMARY
FONT_LABEL = FONT_FAMILY_PRIMARY
FONT_DESCRIPTION = FONT_FAMILY_PRIMARY
FONT_DROPDOWN = FONT_FAMILY_PRIMARY
FONT_TABLE = FONT_FAMILY_PRIMARY

FONT_SIZE_INPUT = "0.9rem"
FONT_SIZE_LABEL = "0.85rem"
FONT_SIZE_DESCRIPTION = "0.85rem"
FONT_SIZE_DROPDOWN = "0.9rem"
FONT_SIZE_TABLE = "0.875rem"

FONT_WEIGHT_INPUT = "400"
FONT_WEIGHT_LABEL = "500"
FONT_WEIGHT_DROPDOWN = "400"

# ==============================================================================
# THEME FUNCTIONS
# ==============================================================================

def get_theme_colors(color_mode):
    """
    Get theme colors based on color mode.

    Args:
        color_mode: "Dark" or "Light"

    Returns:
        dict: Theme color dictionary
    """
    if color_mode == "Dark":
        return {
            "card_bg": dark_card_bg,
            "text_primary": "#ffffff",
            "text_secondary": "#a1a1aa",
            "border": "rgba(255,255,255,0.1)",
            "input_bg": "rgba(255,255,255,0.05)",
            "dropdown_bg": "#3a3a3a",
            "shadow": "0 4px 20px rgba(0,0,0,0.5)",
        }
    else:
        return {
            "card_bg": "#f8f9fa",
            "text_primary": "#1a1a1a",
            "text_secondary": "#666666",
            "border": "rgba(0,0,0,0.1)",
            "input_bg": "rgba(0,0,0,0.03)",
            "dropdown_bg": "#f8f9fa",
            "shadow": "0 4px 20px rgba(0,0,0,0.1)",
        }


def get_input_styles(color_mode):
    """Get styles for dmc.TextInput, dmc.NumberInput, dmc.PasswordInput."""
    theme = get_theme_colors(color_mode)
    focus_style = {
        "backgroundColor": f"{ACCENT}08",
        "borderColor": ACCENT,
        "boxShadow": f"0 0 0 2px {ACCENT}22",
    }
    return {
        "input": {
            "backgroundColor": theme["input_bg"],
            "border": f"1px solid {theme['border']}",
            "borderRadius": "8px",
            "color": theme["text_primary"],
            "fontFamily": FONT_INPUT,
            "fontSize": FONT_SIZE_INPUT,
            "&:focus": focus_style,
        },
        "label": {
            "color": theme["text_secondary"],
            "fontFamily": FONT_LABEL,
            "fontSize": FONT_SIZE_LABEL,
            "fontWeight": FONT_WEIGHT_LABEL,
            "marginBottom": "0.4rem",
        },
        "description": {
            "color": theme["text_secondary"],
            "fontFamily": FONT_DESCRIPTION,
            "fontSize": FONT_SIZE_DESCRIPTION,
        },
    }


def get_select_styles(color_mode):
    """Get styles for dmc.Select and dmc.MultiSelect."""
    theme = get_theme_colors(color_mode)
    focus_style = {
        "backgroundColor": f"{ACCENT}08",
        "borderColor": ACCENT,
        "boxShadow": f"0 0 0 2px {ACCENT}22",
    }
    return {
        "input": {
            "backgroundColor": theme["input_bg"],
            "border": f"1px solid {theme['border']}",
            "borderRadius": "8px",
            "color": theme["text_primary"],
            "fontFamily": FONT_INPUT,
            "fontSize": FONT_SIZE_INPUT,
            "&:focus": focus_style,
        },
        "label": {
            "color": theme["text_secondary"],
            "fontFamily": FONT_LABEL,
            "fontSize": FONT_SIZE_LABEL,
            "fontWeight": FONT_WEIGHT_LABEL,
            "marginBottom": "0.4rem",
        },
        "description": {
            "color": theme["text_secondary"],
            "fontFamily": FONT_DESCRIPTION,
            "fontSize": FONT_SIZE_DESCRIPTION,
        },
        "dropdown": {
            "backgroundColor": theme["dropdown_bg"],
            "border": f"1px solid {theme['border']}",
            "borderRadius": "8px",
            "maxHeight": "300px",
        },
        "option": {
            "backgroundColor": theme["dropdown_bg"],
            "color": theme["text_primary"],
            "fontFamily": FONT_DROPDOWN,
            "fontSize": FONT_SIZE_DROPDOWN,
            "padding": "10px",
            "&[data-combobox-selected]": {"backgroundColor": ACCENT, "color": "#ffffff"},
            "&[data-combobox-active]": {"backgroundColor": f"{ACCENT}33", "color": theme["text_primary"]},
        },
    }


def get_switch_styles(color_mode):
    """Get styles for dmc.Switch components."""
    theme = get_theme_colors(color_mode)
    return {
        "label": {
            "color": theme["text_secondary"],
            "fontSize": "0.85rem",
            "fontWeight": "500",
        },
        "description": {
            "color": theme["text_secondary"],
            "fontSize": "0.75rem",
        },
    }


def get_segmented_control_styles(color_mode):
    """Get styles for dmc.SegmentedControl. Colors handled by CSS vars."""
    return {
        "indicator": {"backgroundColor": purple_hex},
    }


def get_table_container_style(color_mode):
    """Get container style for wrapping tables."""
    theme = get_theme_colors(color_mode)
    bg_color = dark_table_container if color_mode == "Dark" else "#f0f2f5"
    return {
        "backgroundColor": bg_color,
        "borderRadius": "12px",
        "padding": "0",
        "boxShadow": theme["shadow"],
        "border": f"1px solid {theme['border']}",
    }


def get_dash_table_styles(color_mode):
    """Get styles for dash_table.DataTable component."""
    if color_mode == "Dark":
        data_bg = "#252525"
        data_bg_alt = "#2e2e2e"
        data_color = "#d1d4dc"
        border_color = "#3a3a3a"
    else:
        data_bg = "#ffffff"
        data_bg_alt = "#f8f9fa"
        data_color = "#131722"
        border_color = "#e0e3eb"

    return {
        "style_cell": {
            "textAlign": "center",
            "padding": "10px 12px",
            "fontFamily": FONT_TABLE,
            "fontSize": "13px",
            "minWidth": "90px",
            "whiteSpace": "nowrap",
        },
        "style_data": {
            "backgroundColor": data_bg,
            "color": data_color,
            "border": "none",
            "borderBottom": f"1px solid {border_color}",
        },
        "style_data_conditional": [
            {"if": {"row_index": "odd"}, "backgroundColor": data_bg_alt},
        ],
        "style_header": {
            "backgroundColor": purple_hex,
            "color": "white",
            "fontWeight": "600",
            "border": "none",
            "borderBottom": f"2px solid {purple_hex}",
        },
        "style_table": {
            "overflowX": "auto",
            "overflowY": "auto",
            "borderRadius": "8px",
        },
        "css": [
            {"selector": ".export", "rule": f"background-color: {purple_hex}; color: white; border: none; padding: 4px 10px; border-radius: 4px; font-size: 11px; cursor: pointer;"},
        ],
    }


# ==============================================================================
# COMPONENT STYLES
# ==============================================================================

hidden_style = {"display": "none"}
row_style = {"padding": "1%"}
alert_style = {"fontWeight": "bold", "textAlign": "center"}
login_page_style = {"background": f"linear-gradient(180deg, {purple_hex}08 0%, {dark_page_bg} 100%)"}


# ==============================================================================
# COMPONENT FACTORIES
# ==============================================================================

def create_submit_button(text, button_id, color_mode):
    """
    Create a styled submit button.

    Args:
        text: Button text
        button_id: ID for the button component
        color_mode: "Dark" or "Light"

    Returns:
        dbc.Button: Styled button component
    """
    return dbc.Button(
        children=text,
        id=button_id,
        style={
            "backgroundColor": purple_hex,
            "border": f"1px solid {purple_hex}",
            "color": "white",
            "fontWeight": "500",
            "padding": "8px 24px",
            "borderRadius": "8px",
        },
    )


def create_delete_button(button_id):
    """Create a styled red X delete button."""
    return dmc.Button(
        children="X",
        id=button_id,
        color="red",
        size="xs",
        style={"cursor": "pointer", "fontWeight": "bold"},
    )


def create_success_alert(message, title="Success", duration=5000):
    """Create a standardized success alert."""
    return dmc.Alert(
        children=message,
        title=title,
        color="green",
        variant="filled",
        withCloseButton=True,
        duration=duration,
        icon=DashIconify(icon="mdi:check-circle", width=24),
        radius="md",
        style={"borderRadius": "8px", "marginBottom": "1rem"},
    )


def create_error_alert(message, title="Error", duration=5000):
    """Create a standardized error alert."""
    return dmc.Alert(
        children=message,
        title=title,
        color="red",
        variant="filled",
        withCloseButton=True,
        duration=duration,
        icon=DashIconify(icon="mdi:alert-circle", width=24),
        radius="md",
        style={"borderRadius": "8px", "marginBottom": "1rem"},
    )


def create_beautiful_card(title, icon, content=None, color_mode="Dark", card_id=None):
    """
    Create a beautiful card with icon header.

    Args:
        title: Card title text
        icon: Iconify icon name
        content: List of Dash components for card body
        color_mode: "Dark" or "Light"
        card_id: Optional unique string ID

    Returns:
        html.Div: Styled card component
    """
    theme = get_theme_colors(color_mode)

    card_style = {
        "background": theme["card_bg"],
        "border": f"1px solid {theme['border']}",
        "borderRadius": "16px",
        "marginBottom": "1.5rem",
        "boxShadow": theme["shadow"],
    }

    icon_box_style = {
        "width": "45px",
        "height": "45px",
        "background": f"linear-gradient(135deg, {purple_rgb2}, {purple_hex}11)",
        "borderRadius": "12px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "marginRight": "1rem",
    }

    title_style = {
        "color": "var(--text-primary)",
        "fontSize": "1.1rem",
        "fontWeight": "600",
        "marginBottom": "0.2rem",
    }

    title_underline_style = {
        "height": "2px",
        "width": "30px",
        "background": purple_hex,
        "borderRadius": "1px",
    }

    header_style = {
        "padding": "1.25rem 1.5rem",
        "borderBottom": "1px solid var(--border-color)",
    }

    body_style = {"padding": "1.5rem"}

    icon_element = DashIconify(icon=icon, width=24, color=purple_hex)
    icon_box = html.Div(icon_element, style=icon_box_style)
    title_h5 = html.H5(title, style=title_style)
    title_underline = html.Div(style=title_underline_style)
    title_container = html.Div([title_h5, title_underline])

    header_row = html.Div(
        [icon_box, title_container],
        style={"display": "flex", "alignItems": "center"},
    )
    header = html.Div([header_row], style=header_style)
    body = html.Div(content, style=body_style)

    card_props = {"style": card_style}
    if card_id:
        card_props["id"] = card_id

    return html.Div([header, body], **card_props)


def get_settings_callback_styles(color_mode):
    """
    Get all styles needed by the color mode toggle callback.

    Args:
        color_mode: "Dark" or "Light"

    Returns:
        dict: Style dicts for cards, text, inputs, switches
    """
    theme = get_theme_colors(color_mode)
    return {
        "card_style": {
            "background": theme["card_bg"],
            "border": f"1px solid {theme['border']}",
            "borderRadius": "16px",
            "marginBottom": "1.5rem",
            "boxShadow": theme["shadow"],
        },
        "input_style": get_input_styles(color_mode),
        "switch_style": get_switch_styles(color_mode),
        "seg_style": get_segmented_control_styles(color_mode),
        "text_primary": theme["text_primary"],
        "text_secondary": theme["text_secondary"],
    }


def build_account_header(account_num, alias, account_number, is_master=False, color_mode="Dark"):
    """
    Create a styled account header for orders/positions pages.

    Args:
        account_num: Account index (1-indexed)
        alias: Account alias/name
        account_number: Tradier account number
        is_master: Whether this is the master account
        color_mode: "Dark" or "Light"

    Returns:
        html.Div: Styled account header component
    """
    theme = get_theme_colors(color_mode)

    container_style = {
        "backgroundColor": theme["card_bg"],
        "border": f"1px solid {theme['border']}",
        "borderRadius": "10px",
        "padding": "0.6rem 1rem",
        "display": "inline-flex",
        "alignItems": "center",
        "gap": "0.75rem",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
        "marginBottom": "1rem",
    }

    account_style = {
        "color": "var(--text-primary)",
        "fontSize": "1.1rem",
        "fontWeight": "600",
        "display": "flex",
        "alignItems": "center",
        "gap": "0.4rem",
    }

    separator_style = {
        "color": "var(--text-secondary)",
        "fontSize": "1.2rem",
        "opacity": "0.4",
    }

    detail_style = {
        "color": "var(--text-secondary)",
        "fontSize": "0.9rem",
        "fontWeight": "500",
        "display": "flex",
        "alignItems": "center",
        "gap": "0.3rem",
    }

    children = [
        html.Img(src="assets/img/tradier_login.png", height="24px", style={"borderRadius": "4px"}),
        html.Span(
            children=[
                DashIconify(icon="mdi:briefcase-account", width=20, color=purple_hex),
                f"Account {account_num}: {alias}",
            ],
            style=account_style,
        ),
        html.Span("·", style=separator_style),
        html.Span(
            children=[DashIconify(icon="mdi:identifier", width=16), account_number],
            style=detail_style,
        ),
    ]

    if is_master:
        children.extend([
            html.Span("·", style=separator_style),
            dmc.Badge("⭐ Master", color="grape", variant="filled", size="sm"),
        ])

    return html.Div(children=children, style=container_style)


def build_page_info_accordion(page_name, description, features, color_mode):
    """
    Build a collapsible info accordion for the bottom of pages.

    Args:
        page_name: Display name (e.g., "Accounts")
        description: Brief description of what the page does
        features: List of strings or {"Category": ["sub-item", ...]} dicts
        color_mode: "Dark" or "Light"

    Returns:
        dbc.Row: Centered info accordion row
    """
    # Uses CSS variables for dark/light responsiveness (no inline theme colors)

    content_children = []

    if description:
        content_children.append(
            dmc.Text(description, size="sm", c="dimmed", style={"marginBottom": "0.75rem"})
        )

    if features:
        feature_items = []
        for feature in features:
            if isinstance(feature, str):
                feature_items.append(
                    dmc.ListItem(
                        dmc.Text(feature, size="sm", c="dimmed"),
                        icon=DashIconify(icon="mdi:check-circle", width=16, style={"color": SUCCESS}),
                    )
                )
            elif isinstance(feature, dict):
                for category_name, sub_items in feature.items():
                    sub_list_items = [
                        dmc.ListItem(dmc.Text(sub, size="sm", c="dimmed"))
                        for sub in sub_items
                    ]
                    sub_list = dmc.List(
                        children=sub_list_items,
                        size="sm", spacing="xs", withPadding=True, listStyleType="disc",
                    )
                    feature_items.append(
                        dmc.ListItem(
                            children=[
                                html.Div([
                                    DashIconify(icon="mdi:check-circle", width=16, style={"color": SUCCESS, "marginRight": "8px", "verticalAlign": "middle"}),
                                    dmc.Text(category_name, size="sm", c="dimmed", fw=500, style={"display": "inline"}),
                                ], style={"display": "flex", "alignItems": "center"}),
                                sub_list,
                            ]
                        )
                    )

        content_children.append(
            dmc.List(children=feature_items, size="sm", spacing="xs", listStyleType="none")
        )

    accordion = dmc.Accordion(
        children=[
            dmc.AccordionItem(
                value="info",
                children=[
                    dmc.AccordionControl(
                        f"\u2139\ufe0f About {page_name}",
                        styles={
                            "control": {"&:hover": {"backgroundColor": "var(--hover-bg)"}},
                            "label": {"color": "var(--text-primary)", "fontWeight": 500},
                            "chevron": {"color": "var(--text-secondary)"},
                        },
                    ),
                    dmc.AccordionPanel(children=content_children),
                ],
            )
        ],
        variant="separated",
        radius="md",
        styles={
            "item": {
                "backgroundColor": "var(--card-bg)",
                "border": "1px solid var(--border-color)",
            },
            "panel": {"color": "var(--text-secondary)"},
        },
    )

    return dbc.Row(
        children=[
            dbc.Col(
                children=[accordion],
                width={"size": 10, "offset": 1},
            )
        ],
        style={"marginTop": "2rem", "marginBottom": "1rem"},
    )


def build_page_title_row(title, color_mode):
    """
    Build a standard page title row.

    Args:
        title: Page title text (can include emoji)
        color_mode: "Dark" or "Light"

    Returns:
        dbc.Row: Title row with centered title and underline
    """
    return dbc.Row(
        children=[
            dbc.Col(
                children=[
                    dmc.Title(
                        children=title,
                        ta="center",
                        order=1,
                        style={"color": "var(--text-primary)"},
                    ),
                    html.Hr(style={
                        "border": f"2px solid {purple_hex}",
                        "width": "60px",
                        "margin": "10px auto 20px auto",
                    }),
                ],
                width={"size": 10, "offset": 1},
                align="center",
            )
        ]
    )

# END
