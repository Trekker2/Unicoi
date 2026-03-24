"""
Main Application Module for Tradier Copy Bot

This module serves as the main entry point for the Copy Bot dashboard built with Dash.
It handles application initialization, authentication, database setup, and layout creation.

Key Features:
    - Tradier purple branded dashboard
    - Flask-Login authentication
    - Dark/Light mode via MantineProvider
    - MongoDB database initialization
    - Top navbar with 5 pages + logout
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt
import multiprocessing
import os
import time
import traceback

from dash import Dash, dcc, html
from flask_login import LoginManager, current_user
import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import secrets

from app_callbacks import register_app_callbacks
from constants import *
from helper import hash_password, verify_password
from pages import *
from scripts.database_manager import connect_mongo
from scripts.style_manager import *


# ==============================================================================
# APPLICATION CONFIGURATION
# ==============================================================================

os.environ['NUMEXPR_MAX_THREADS'] = str(multiprocessing.cpu_count())

# ==============================================================================
# DASH APPLICATION INITIALIZATION
# ==============================================================================

def create_dash_app():
    """Create and configure the main Dash application."""
    dash._dash_renderer._set_react_version('18.2.0')

    app = Dash(
        __name__,
        update_title="Updating...",
        suppress_callback_exceptions=True,
        meta_tags=[
            {'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}
        ],
        external_scripts=['assets/js/custom.js'],
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            dmc.styles.DATES,
            'assets/css/custom.css',
        ],
    )

    app.title = app_title
    app._favicon = "img/favicon.ico"
    app.server.config['SESSION_COOKIE_SECURE'] = True
    return app


# ==============================================================================
# AUTHENTICATION SETUP
# ==============================================================================

def ensure_secret_key(env_var="FLASK_SECRET_KEY"):
    """
    Get secret key from env, or generate and persist to .env on local.

    Args:
        env_var: Environment variable name

    Returns:
        str: Secret key value
    """
    key = os.getenv(env_var)
    if key:
        return key

    key = secrets.token_hex(32)
    if is_local and os.path.exists(".env"):
        with open(".env", "a") as f:
            f.write(f"\n# Auto-generated secret key\n{env_var}={key}\n")
        print(f"Generated {env_var} and saved to .env")
    elif is_local:
        with open(".env", "w") as f:
            f.write(f"# Auto-generated secret key\n{env_var}={key}\n")
        print(f"Generated {env_var} and created .env")
    return key


def setup_authentication(app):
    """Configure user authentication system based on login_system constant."""
    server = app.server
    server.config["SESSION_COOKIE_SECURE"] = True

    login_manager = LoginManager()
    login_manager.init_app(server)
    login_manager.login_view = "/login"

    @login_manager.user_loader
    def load_user(username):
        db = connect_mongo()
        try:
            user_dict = db.get_collection("users").find_one({"username": username}) or {}
            if user_dict:
                return User(
                    id=user_dict.get("username", ""),
                    username=user_dict.get("username", ""),
                )
        except Exception as e:
            print(f"Error (load_user): {traceback.format_exc()}")
        return None

    # Configure based on login_system constant
    if login_system == "dash-auth":
        import dash_auth
        import base64
        auth_secret = base64.b64encode(os.urandom(30)).decode("utf-8")

        def auth_func(username, password):
            db = connect_mongo()
            try:
                user_dict = db.get_collection("users").find_one({"username": username})
                if not user_dict:
                    return False
                stored_pw = user_dict.get("password", "")
                if use_hashed_passwords:
                    valid_auth = verify_password(password, stored_pw)
                else:
                    valid_auth = password == stored_pw
                if valid_auth:
                    user = User(
                        id=user_dict.get("username", ""),
                        username=user_dict.get("username", ""),
                    )
                    login_user(user)
                return valid_auth
            finally:
                db.client.close()

        auth = dash_auth.BasicAuth(
            app,
            auth_func=auth_func,
            public_routes=public_routes,
            secret_key=ensure_secret_key("DASH_SECRET_KEY"),
        )
    elif login_system == "flask-login":
        server.secret_key = ensure_secret_key("FLASK_SECRET_KEY")


# ==============================================================================
# DATABASE INITIALIZATION
# ==============================================================================

def initialize_database():
    """Initialize MongoDB database and create required collections."""
    db = connect_mongo()
    try:
        sub_dbs = db.list_collection_names()
        if not isinstance(sub_dbs, list):
            sub_dbs = []

        for item in required_dbs:
            if item not in sub_dbs:
                db.create_collection(item)
                print(f"Created {item} collection")

        # Create default users if empty
        users_collection = db.get_collection("users")
        if users_collection.count_documents({}) == 0:
            user_list = [
                {
                    "username": "tyler",
                    "password": "tyler",
                    "password_hash": hash_password("tyler"),
                    "admin": False,
                },
                {
                    "username": master_username,
                    "password": master_username,
                    "password_hash": hash_password(master_username),
                    "admin": True,
                },
            ]
            users_collection.insert_many(user_list)
            print(f"Created users collection with {len(user_list)} users")

        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False


# ==============================================================================
# LAYOUT GENERATION
# ==============================================================================

def create_navbar(username="", color_mode="Dark"):
    """
    Create top navigation bar items.

    Args:
        username: Current user's username
        color_mode: "Dark" or "Light"

    Returns:
        list: Navbar items
    """
    logged_in = username != ""
    navbar_items = []

    for page in NAVBAR_PAGES:
        navbar_items.append(
            dbc.NavItem(
                children=dbc.NavLink(
                    children=f"{page['emoji']} {page['name']}",
                    id={"type_": "links", "_id": page["id"]},
                    href=page["href"],
                ),
                id={"type_": "pages", "_id": page["id"]},
                style={"display": "block" if logged_in else "none"},
            )
        )

    # Logout button
    navbar_items.append(
        dbc.NavItem(
            children=html.A(
                dbc.Button(
                    children="Logout",
                    id="signout-button",
                    style={
                        "backgroundColor": "transparent",
                        "border": "1px solid white",
                        "color": "white",
                        "fontWeight": "500",
                        "padding": "6px 16px",
                        "borderRadius": "6px",
                    },
                ),
            ),
            style={"display": "block" if logged_in else "none"},
        )
    )
    return navbar_items


def create_footer(color_mode=default_color_mode):
    """
    Create standardized 3-column footer with brand theming.

    Args:
        color_mode (str): UI color mode (Light/Dark)

    Returns:
        html.Div: Footer component
    """
    current_year = dt.datetime.now(tz=market_timezone).year
    text_color = "white" if color_mode == "Dark" else "#333333"

    link_style = {
        "text-decoration": "none",
        "display": "flex",
        "align-items": "center",
        "margin-bottom": "8px",
        "font-size": "0.9rem",
    }
    link_style_last = {
        "text-decoration": "none",
        "display": "flex",
        "align-items": "center",
        "font-size": "0.9rem",
    }

    footer = html.Div(
        children=[
            html.Hr(
                className="brand-border-top",
                style={"margin": "0"},
            ),
            dbc.Container(
                children=[
                    dbc.Row(
                        children=[
                            # Column 1: About / Copyright
                            dbc.Col(
                                children=[
                                    html.H5(
                                        children="Copy Bot",
                                        style={
                                            "color": text_color,
                                            "font-weight": "bold",
                                            "margin-bottom": "15px",
                                        },
                                    ),
                                    html.P(
                                        children=(
                                            "An automated trade copier for Tradier brokerage accounts. "
                                            "Monitors a master account and replicates equity and option "
                                            "orders to follower accounts with configurable per-account "
                                            "multipliers, multi-leg spread support, and real-time WebSocket "
                                            "streaming. Includes modification sync, cancellation sync, "
                                            "stale order filtering, and full activity logging."
                                        ),
                                        style={
                                            "color": text_color,
                                            "font-size": "0.9rem",
                                            "margin-bottom": "10px",
                                            "line-height": "1.5",
                                        },
                                    ),
                                    html.P(
                                        children=f"(c) {current_year} All rights reserved.",
                                        style={
                                            "color": text_color,
                                            "font-size": "0.85rem",
                                            "margin-bottom": "5px",
                                        },
                                    ),
                                ],
                                md=4,
                                style={"margin-bottom": "20px"},
                            ),
                            # Column 2: Resources
                            dbc.Col(
                                children=[
                                    html.H5(
                                        children="Resources",
                                        style={
                                            "color": text_color,
                                            "font-weight": "bold",
                                            "margin-bottom": "15px",
                                        },
                                    ),
                                    html.Div(
                                        children=[
                                            html.A(
                                                children=[
                                                    DashIconify(icon="mdi:github", width=16, style={"margin-right": "5px"}),
                                                    "GitHub",
                                                ],
                                                href="https://github.com/Trekker2/Unicoi",
                                                target="_blank",
                                                className="brand-link",
                                                style=link_style,
                                            ),
                                            html.A(
                                                children=[
                                                    DashIconify(icon="mdi:cloud", width=16, style={"margin-right": "5px"}),
                                                    "Heroku",
                                                ],
                                                href="https://dashboard.heroku.com/apps/unicoi",
                                                target="_blank",
                                                className="brand-link",
                                                style=link_style,
                                            ),
                                            html.A(
                                                children=[
                                                    DashIconify(icon="mdi:database", width=16, style={"margin-right": "5px"}),
                                                    "MongoDB Atlas",
                                                ],
                                                href="https://www.mongodb.com/cloud/atlas",
                                                target="_blank",
                                                className="brand-link",
                                                style=link_style,
                                            ),
                                            html.A(
                                                children=[
                                                    DashIconify(icon="mdi:chart-line", width=16, style={"margin-right": "5px"}),
                                                    "Tradier Documentation",
                                                ],
                                                href="https://documentation.tradier.com",
                                                target="_blank",
                                                className="brand-link",
                                                style=link_style_last,
                                            ),
                                        ]
                                    ),
                                ],
                                md=4,
                                style={"margin-bottom": "20px"},
                            ),
                            # Column 3: Contact
                            dbc.Col(
                                children=[
                                    html.H5(
                                        children="Contact",
                                        style={
                                            "color": text_color,
                                            "font-weight": "bold",
                                            "margin-bottom": "15px",
                                        },
                                    ),
                                    html.P(
                                        children="Tyler Potts",
                                        style={
                                            "color": text_color,
                                            "font-weight": "bold",
                                            "margin-bottom": "10px",
                                            "font-size": "0.95rem",
                                        },
                                    ),
                                    html.P(
                                        children="Freelance Developer",
                                        style={
                                            "color": text_color,
                                            "font-size": "0.85rem",
                                            "margin-bottom": "15px",
                                            "font-style": "italic",
                                        },
                                    ),
                                    html.Div(
                                        children=[
                                            html.A(
                                                children=[
                                                    DashIconify(icon="mdi:email", width=16, style={"margin-right": "5px"}),
                                                    "twpotts11@gmail.com",
                                                ],
                                                href="mailto:twpotts11@gmail.com",
                                                className="brand-link",
                                                style=link_style,
                                            ),
                                            html.A(
                                                children=[
                                                    DashIconify(icon="mdi:briefcase", width=16, style={"margin-right": "5px"}),
                                                    "Upwork Profile",
                                                ],
                                                href="https://www.upwork.com/freelancers/robotraderguy",
                                                target="_blank",
                                                className="brand-link",
                                                style=link_style,
                                            ),
                                            html.A(
                                                children=[
                                                    DashIconify(icon="mdi:linkedin", width=16, style={"margin-right": "5px"}),
                                                    "LinkedIn",
                                                ],
                                                href="https://www.linkedin.com/in/tyler-potts-022b6573/",
                                                target="_blank",
                                                className="brand-link",
                                                style=link_style_last,
                                            ),
                                        ]
                                    ),
                                ],
                                md=4,
                                style={"margin-bottom": "20px"},
                            ),
                        ],
                        style={"padding": "30px 0 10px 0"},
                    ),
                    # Disclaimer
                    dbc.Row(
                        children=[
                            dbc.Col(
                                children=[
                                    html.Hr(
                                        className="brand-border-top",
                                        style={"margin": "0 0 10px 0"},
                                    ),
                                    html.P(
                                        children=(
                                            "\u26a0\ufe0f DISCLAIMER: Trading involves substantial risk and is not suitable "
                                            "for all investors. Past performance does not guarantee future results. "
                                            "The use of this software is at your own risk."
                                        ),
                                        style={
                                            "color": text_color,
                                            "font-size": "0.75rem",
                                            "text-align": "center",
                                            "margin": "0 0 10px 0",
                                            "font-style": "italic",
                                        },
                                    ),
                                ],
                                width=12,
                            )
                        ]
                    ),
                ],
                fluid=True,
                style={
                    "background": get_horizontal_gradient(color_mode),
                    "padding": "0 20px",
                },
            ),
        ]
    )

    return footer


def serve_layout():
    """Generate the main application layout."""
    try:
        username = ""
        if current_user.is_authenticated:
            username = current_user.username

        db = connect_mongo()
        try:
            # Get settings for color mode
            admin = False
            if username:
                settings = db.get_collection("settings").find_one({"type": "global"}) or {}
                color_mode = settings.get("color_mode", default_color_mode)
                user_dict = db.get_collection("users").find_one({"username": username}) or {}
                admin = user_dict.get("admin", False)
            else:
                color_mode = default_color_mode

            navbar_component = create_navbar(username, color_mode)

            # Mantine theme with Tradier purple
            mantine_theme = {
                "primaryColor": "grape",
                "colors": {
                    "grape": [
                        "#f3e8ff", "#e4ccff", "#c99aff", "#ae66ff",
                        "#9b3dff", "#8b2cf7", "#7c1eed", "#6f42c1",
                        "#5a32a3", "#4a2886",
                    ],
                },
            }

            if color_mode == "Dark":
                mantine_theme["components"] = {
                    "Combobox": {
                        "styles": {
                            "dropdown": {"backgroundColor": "#2e2e2e"},
                            "option": {"backgroundColor": "#2e2e2e", "color": "#ffffff"},
                        }
                    }
                }

            # Build layout
            top_navbar = dbc.NavbarSimple(
                id="navbar",
                children=navbar_component,
                brand=html.Div(
                    children=[
                        html.Img(src="assets/img/tradier_banner_white.png", height="36px"),
                        dmc.Badge(
                            id="username_display",
                            children=username,
                            variant="gradient",
                            gradient={"from": "#1e1e2f", "to": "#2d3561", "deg": 135},
                            size="lg",
                            leftSection=DashIconify(icon="mdi:account", width=14),
                            styles={"root": {"maxWidth": "none", "border": "1px solid rgba(255,255,255,0.2)"}, "label": {"overflow": "visible", "textOverflow": "unset"}},
                        ) if username else html.Span(
                            children=[
                                html.Span(id="username_display", style={"display": "none"}),
                                html.Span(app_title, style={"color": "white", "fontWeight": "600", "fontSize": "1.1rem"}),
                            ],
                        ),
                        dmc.Badge(
                            children="Admin",
                            color="blue",
                            variant="filled",
                            size="lg",
                            leftSection=DashIconify(icon="mdi:shield-account", width=14),
                        ) if username and admin else None,
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "row",
                        "gap": "12px",
                        "alignItems": "center",
                    },
                ),
                brand_href="#",
                color=purple_hex,
                dark=True,
                sticky=True,
                fixed="top",
                class_name="navbar-nav navbar-top",
                expand=True,
            )

            layout = dmc.MantineProvider(
                id="mantine-provider",
                forceColorScheme="dark" if color_mode == "Dark" else "light",
                theme=mantine_theme,
                children=[
                    html.Div(
                        id="main_page",
                        **{"data-bs-theme": "dark" if color_mode == "Dark" else "light"},
                        children=[
                            dcc.Location(id='url', refresh=True),
                            dcc.Location(id='url2', refresh=True),
                            dcc.Store(id='color-mode-store', data={'color_mode': color_mode}),
                            html.Div(id="logout-content", children=[]),
                            top_navbar,
                            html.Div(id='page-content', children=[], style={"minHeight": "100vh", "paddingTop": "70px"}),
                            html.Div(id="footer-content", children=create_footer(color_mode=color_mode)),
                        ],
                        style={
                            "background": dark_page_gradient if color_mode == "Dark" else light_page_gradient,
                            "backgroundColor": dark_hex if color_mode == "Dark" else light_hex,
                            "minHeight": "100vh",
                        },
                    )
                ],
            )

            return layout
        finally:
            pass

    except Exception as e:
        print(f"Error in serve_layout: {e}")
        print(traceback.format_exc())
        return html.Div([
            html.H1("Application Error"),
            html.P("Please contact support if this issue persists."),
        ])


# ==============================================================================
# APPLICATION INITIALIZATION
# ==============================================================================

def initialize_app():
    """Initialize and configure the complete Dash application."""
    app = create_dash_app()
    initialize_database()
    setup_authentication(app)
    app.layout = serve_layout
    register_app_callbacks(app)
    return app


# Create the application instance
app = initialize_app()
server = app.server

# ==============================================================================
# APPLICATION STARTUP
# ==============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, port=port)

# END
