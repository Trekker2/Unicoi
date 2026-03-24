"""
Constants Module for Tradier Copy Bot

This module contains all constant values, configuration variables, and enumerations
used throughout the Tradier Copy Bot application.

Key Sections:
    - Environment configuration
    - Database configuration
    - Timezone configuration
    - User authentication
    - Application configuration
    - Navbar configuration
    - Copy engine configuration
    - Order status classifications
    - Trading side classifications
    - Default settings
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import os

from flask_login import UserMixin
import dotenv
import pytz


# ==============================================================================
# ENVIRONMENT CONFIGURATION
# ==============================================================================

env = dotenv.load_dotenv(".env") if ".env" in os.listdir() else None
is_cloud = "twpot" not in os.getcwd()
is_local = "twpot" in os.getcwd()
port = 8080 if not is_cloud else None

REQUIRED_ENV_VARS = [
    "MONGO_ADDRESS",
    "FLASK_SECRET_KEY",
]

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

db_name = "copy-bot-system"

required_dbs = [
    "accounts",
    "history",
    "logs",
    "settings",
    "trades",
    "users",
]

# ==============================================================================
# TIMEZONE CONFIGURATION
# ==============================================================================

utc = "UTC"
utc_timezone = pytz.timezone(utc)
market_str = "US/Eastern"
market_timezone = pytz.timezone(market_str)

# ==============================================================================
# USER AUTHENTICATION
# ==============================================================================

login_system = "flask-login"
use_hashed_passwords = False
default_hasher = "bcrypt"
master_username = "joe"

public_routes = [
    '/login',
]

class User(UserMixin):
    """
    User class for Flask-Login authentication.

    Attributes:
        id (str): Unique user identifier (username)
        username (str): User's username for display and identification
    """
    def __init__(self, id, username):
        self.id = id
        self.username = username

# ==============================================================================
# APPLICATION CONFIGURATION
# ==============================================================================

app_title = "Copy Bot"
brand_color = "#6f42c1"
homepage = "accounts"
default_color_mode = "Dark"
show_beta_banner = False

# ==============================================================================
# NAVBAR CONFIGURATION
# ==============================================================================

NAVBAR_PAGES = [
    {"name": "Accounts", "id": "accounts", "href": "/accounts", "emoji": "💼"},
    {"name": "Activity", "id": "activity", "href": "/activity", "emoji": "📋"},
    {"name": "Orders", "id": "orders", "href": "/orders", "emoji": "📝"},
    {"name": "Positions", "id": "positions", "href": "/positions", "emoji": "🗂️"},
    {"name": "Settings", "id": "settings", "href": "/settings", "emoji": "⚙️"},
]

NAVBAR_PAGE_EMOJIS = {page["id"]: page["emoji"] for page in NAVBAR_PAGES}

# ==============================================================================
# COPY ENGINE CONFIGURATION
# ==============================================================================

DEFAULT_POLL_INTERVAL = 2
DEFAULT_STALE_TIMEOUT = 5
MAX_ERRORS = 50

# ==============================================================================
# ORDER STATUS CLASSIFICATIONS
# ==============================================================================

bad_statuses = [
    "expired", "canceled", "rejected", "error",
    "EXP", "CAN", "REJ",
]

open_statuses = [
    "open", "partially_filled", "pending",
    "OPN", "FPR", "ACK", "DON",
]

closed_statuses = [
    "filled", "expired", "canceled", "rejected", "error",
    "FLL", "FLP", "OUT", "EXP", "CAN", "REJ",
]

filled_statuses = ["filled", "Filled", "FLL"]

good_statuses = [
    "open", "partially_filled", "pending",
    "OPN", "FPR", "ACK", "DON",
    "filled", "FLL",
]

# ==============================================================================
# TRADING SIDE CLASSIFICATIONS
# ==============================================================================

long_sides = [
    "buy", "buy_to_open", "sell_to_close", "debit",
    "Buy", "BUY_TO_OPEN", "SELL_TO_CLOSE",
    "BUY", "BUYTOOPEN", "SELLTOCLOSE",
    "BuyToOpen", "SellToClose",
]

short_sides = [
    "sell", "sell_short", "buy_to_cover", "sell_to_open", "buy_to_close", "credit",
    "Sell", "SELL_SHORT", "BUY_TO_COVER", "SELL_TO_OPEN", "BUY_TO_CLOSE",
    "SELL", "SELLSHORT", "BUYTOCOVER", "SELLTOOPEN", "BUYTOCLOSE",
    "SellShort", "BuyToCover", "SellToOpen", "BuyToClose",
]

inverse_side_dict = {
    "buy": "sell", "Buy": "Sell", "BUY": "SELL",
    "sell": "buy", "Sell": "Buy", "SELL": "BUY",
    "sell_short": "buy_to_cover", "buy_to_cover": "sell_short",
    "buy_to_open": "sell_to_close", "sell_to_close": "buy_to_open",
    "sell_to_open": "buy_to_close", "buy_to_close": "sell_to_open",
    "debit": "credit", "credit": "debit",
}

# ==============================================================================
# VALUE CLASSIFICATIONS
# ==============================================================================

na = [None, "None", "none", False, "False", "false", "nan", "NaN", "Nan", "Null", "null", "", b""]

# ==============================================================================
# FOOTER CONFIGURATION
# ==============================================================================

FONT_SIZE_FOOTER = "0.8rem"

# ==============================================================================
# DEFAULT SETTINGS
# ==============================================================================

default_empty_string = ""
default_admin = False


def get_default_settings():
    """
    Get default settings for the copy bot system.

    Returns:
        dict: Dictionary of default settings
    """
    return {
        "use_automation": False,
        "poll_interval": DEFAULT_POLL_INTERVAL,
        "stale_timeout": DEFAULT_STALE_TIMEOUT,
        "color_mode": "Dark",
        "use_streaming": False,
        "multipliers": {},
    }

# END
