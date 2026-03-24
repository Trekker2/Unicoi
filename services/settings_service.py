"""
Settings Service for Tradier Copy Bot

Abstracts database calls for settings management.

Key Functions:
    - do_get_settings: Get global settings
    - do_put_setting: Update a single setting
    - do_get_global_settings: Get merged global settings with defaults
    - do_put_global_setting: Update a global setting
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from constants import get_default_settings
from scripts.database_manager import connect_mongo


# ==============================================================================
# SERVICE FUNCTIONS
# ==============================================================================

def do_get_settings():
    """
    Get global settings merged with defaults.

    Returns:
        dict: Complete settings dictionary
    """
    db = connect_mongo()
    stored = db.get_collection("settings").find_one({"type": "global"}) or {}
    defaults = get_default_settings()
    return {**defaults, **stored}


def do_put_setting(key, value):
    """
    Update a single global setting.

    Args:
        key: Setting key name
        value: New value

    Returns:
        tuple: (success: bool, message: str)
    """
    db = connect_mongo()
    db.get_collection("settings").update_one(
        {"type": "global"},
        {"$set": {key: value}},
        upsert=True,
    )
    return True, f"Setting '{key}' updated"


def do_get_global_settings():
    """Get global settings (alias for do_get_settings)."""
    return do_get_settings()


def do_put_global_setting(key, value):
    """Update a global setting (alias for do_put_setting)."""
    return do_put_setting(key, value)

# END
