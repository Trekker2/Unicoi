"""
Pages Module Initialization for Tradier Copy Bot

This module serves as the central import point for all page modules.

Available Pages:
    - 💼 Accounts: Master/follower account management
    - 📋 Activity: System activity logs
    - 🔐 Login: User authentication
    - 📝 Orders: Live order management
    - 🗂️ Positions: Current position monitoring
    - ⚙️ Settings: Automation and display settings
"""

from pages.accounts import *
from pages.activity import *
from pages.login import *
from pages.orders import *
from pages.positions import *
from pages.settings import *


__all__ = [
    'serve_accounts',
    'serve_activity',
    'serve_login',
    'serve_orders',
    'update_orders',
    'serve_positions',
    'update_positions',
    'serve_settings',
]

# END
