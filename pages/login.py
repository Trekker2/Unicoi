"""
Tradier Copy Bot - Login Page

Provides the authentication gateway with a centered login card styled
in Tradier purple branding. Supports dark/light color modes with a
gradient background.

Page Layout:
    +------------------------------------------------------------------+
    |                         🔐 Login                                 |
    |           (gradient background, vertically centered)             |
    |                                                                  |
    |                    +------------------------+                    |
    |                    |      Copy Bot          |                    |
    |                    |  Tradier Trade Copier  |                    |
    |                    |                        |                    |
    |                    |  👤 Username [_______] |                    |
    |                    |  🔒 Password [_______] |                    |
    |                    |                        |                    |
    |                    |  [🔓 Sign In         ] |                    |
    |                    |  (alert area)          |                    |
    |                    +------------------------+                    |
    |                                                                  |
    +------------------------------------------------------------------+

Key Features:
    - Centered card layout with rounded corners and shadow
    - Purple-branded title and sign-in button
    - Username text input with account icon
    - Password input with lock icon (masked)
    - Alert container for login error messages
    - Gradient background adapts to dark/light mode

Functions:
    - serve_login(color_mode) : Build and return the login page layout
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from constants import *
from scripts.style_manager import *


# ==============================================================================
# PAGE LAYOUT
# ==============================================================================

def serve_login(color_mode="Dark"):
    """
    Generate login page layout.

    Args:
        color_mode: "Dark" or "Light"

    Returns:
        html.Div: Login page layout
    """
    theme = get_theme_colors(color_mode)
    input_styles = get_input_styles(color_mode)

    card_style = {
        "background": theme["card_bg"],
        "border": f"1px solid {theme['border']}",
        "borderRadius": "20px",
        "padding": "0",
        "maxWidth": "480px",
        "width": "100%",
        "margin": "0 auto",
        "boxShadow": "0 8px 40px rgba(0,0,0,0.4)",
        "overflow": "hidden",
    }

    # Card header with icon + title
    card_header = html.Div(
        children=[
            DashIconify(icon="mdi:login", width=28, color=purple_hex),
            html.Span("Login", style={"fontSize": "1.3rem", "fontWeight": "600", "color": "var(--text-primary)"}),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "0.75rem",
            "padding": "1.25rem 2rem",
            "borderBottom": f"1px solid {theme['border']}",
        },
    )

    # Logo section inside card
    logo_section = html.Div(
        children=[
            html.Img(
                src="assets/img/tradier_login.png",
                style={"height": "120px", "display": "block", "margin": "0 auto"},
            ),
        ],
        style={
            "padding": "2rem 2rem 1rem 2rem",
            "textAlign": "center",
            "background": f"linear-gradient(180deg, {purple_hex}15 0%, transparent 100%)",
        },
    )

    # Form section
    form_section = html.Div(
        children=[
            dmc.TextInput(
                id="login-username",
                label="Username",
                placeholder="Enter username",
                leftSection=DashIconify(icon="mdi:account", width=20),
                styles=input_styles,
                style={"marginBottom": "1rem"},
            ),
            dmc.PasswordInput(
                id="login-password",
                label="Password",
                placeholder="Enter password",
                leftSection=DashIconify(icon="mdi:lock-outline", width=20),
                styles=input_styles,
                style={"marginBottom": "1.5rem"},
            ),
            dbc.Button(
                children="🔓 Sign In",
                id="login-button",
                n_clicks=0,
                style={
                    "backgroundColor": purple_hex,
                    "border": "none",
                    "width": "100%",
                    "padding": "12px",
                    "borderRadius": "10px",
                    "fontWeight": "600",
                    "color": "white",
                    "fontSize": "1rem",
                },
            ),
            html.Div(id="login-alert", children=[], style={"marginTop": "1rem"}),
        ],
        style={"padding": "1rem 2rem 2rem 2rem"},
    )

    layout = html.Div(
        children=[
            html.Div(
                children=[
                    html.Div(
                        children=[card_header, logo_section, form_section],
                        style=card_style,
                    ),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "center",
                    "minHeight": "80vh",
                    "padding": "2rem",
                },
            ),
        ],
        style={
            "background": f"linear-gradient(180deg, {purple_hex}08 0%, {dark_page_bg if color_mode == 'Dark' else light_hex} 100%)",
            "minHeight": "100vh",
        },
    )

    return layout

# END
