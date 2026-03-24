"""
Helper Functions Module for Tradier Copy Bot

This module provides utility functions used throughout the application including
session management, data manipulation, security, and market schedule utilities.

Key Functions:
    - get_current_username: Get username from Flask-Login session
    - flatten: Flatten nested lists
    - hide_text: Mask sensitive text with asterisks
    - format_tag: Sanitize tag strings for Tradier API
    - hash_password: Hash password with bcrypt
    - verify_password: Verify password against hash
    - is_market_open: Check if NYSE market is currently open
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt

from flask_login import current_user
import bcrypt
import exchange_calendars as xcals
import pytz

from constants import *


# ==============================================================================
# SESSION UTILITIES
# ==============================================================================

def get_current_username(username=None):
    """
    Get username from current session or use provided override.

    Args:
        username: Optional username override for testing

    Returns:
        str: Current authenticated username, or empty string
    """
    if username:
        return username
    if login_system == "flask-login":
        return current_user.username if current_user.is_authenticated else ""
    return ""


# ==============================================================================
# DATA STRUCTURE UTILITIES
# ==============================================================================

def flatten(lst):
    """Recursively flatten a nested list."""
    for x in lst:
        if isinstance(x, list):
            for x in flatten(x):
                yield x
        else:
            yield x


def format_tag(s):
    """
    Sanitize a string for use as a Tradier order tag.
    Replaces non-alphanumeric characters with dashes, max 255 chars.
    """
    result = ''
    for char in s:
        if char.isalnum():
            result += char
        else:
            result += '-'
    return result[:255]


# ==============================================================================
# SECURITY UTILITIES
# ==============================================================================

def hide_text(text=""):
    """Mask text by replacing all characters with asterisks."""
    return '*' * len(text)


def hash_password(password):
    """
    Hash a password for secure storage using bcrypt.

    Args:
        password (str): Plain text password to hash

    Returns:
        str: Hashed password with salt
    """
    password_bytes = str(password).encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(password, hashed):
    """
    Verify a password against its hashed version.

    Args:
        password (str): Plain text password to verify
        hashed (str): Hashed password to compare against

    Returns:
        bool: True if password matches
    """
    password_bytes = str(password).encode('utf-8')
    if isinstance(hashed, str):
        hashed = hashed.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed)


# ==============================================================================
# MARKET SCHEDULE UTILITIES
# ==============================================================================

_nyse_calendar = xcals.get_calendar("XNYS")


def is_market_open(check_time=None):
    """
    Check if NYSE market is open at the given time.

    Args:
        check_time: datetime object (timezone-aware). Defaults to now.

    Returns:
        bool: True if market is open
    """
    if check_time is None:
        check_time = dt.datetime.now(tz=market_timezone)
    try:
        # exchange_calendars treats naive times as UTC, so convert aware times to UTC first
        if check_time.tzinfo is not None:
            check_time = check_time.astimezone(pytz.UTC)
        naive_time = check_time.replace(tzinfo=None)
        return _nyse_calendar.is_open_on_minute(naive_time)
    except Exception:
        return False

# END
