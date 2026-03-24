"""
Tradier API Integration Module for Tradier Copy Bot

This module provides all Tradier API functions including authentication,
order management, account queries, and streaming session support.

Key Functions:
    - get_auth_trd: Build auth headers (sandbox vs real auto-detection)
    - get_orders_trd: Get all orders for an account
    - get_balances_trd: Get account balances
    - get_positions_trd: Get account positions
    - post_orders_trd: Place orders (supports multi-leg form-encoded)
    - modify_orders_trd: Modify open order (price, stop, duration, type)
    - delete_orders_trd: Cancel an order
    - validate_account_trd: Validate account credentials via user profile
    - get_expirations_trd: Get option expiration dates for a symbol
    - get_chain_trd: Get option chain for a symbol at specific expiration
    - create_streaming_session: Create account event streaming session
    - get_streaming_url: Get WebSocket URL for streaming

Notes:
    - VA prefix accounts use sandbox, others use real API
    - Orders are posted as form-encoded data (NOT JSON)
    - Multi-leg orders use indexed notation: option_symbol[0], side[0], quantity[0]
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import json
import os

import requests

from constants import *


# ==============================================================================
# AUTHENTICATION
# ==============================================================================

def get_auth_trd(trd_account=None, trd_api=None):
    """
    Build Tradier authentication headers with auto sandbox/real detection.

    VA-prefixed accounts use sandbox API, others use real API.

    Args:
        trd_account: Tradier account number
        trd_api: Tradier API key

    Returns:
        dict: Auth config with 'account', 'base', 'headers' keys
    """
    real = True
    if trd_account and "VA" in trd_account:
        real = False

    if real:
        trd_base = 'https://api.tradier.com/v1'
        trd_mode = "REAL"
    else:
        trd_base = 'https://sandbox.tradier.com/v1'
        trd_mode = "SIM"

    if not trd_account:
        trd_account = os.getenv(f"TRD_ACCOUNT_{trd_mode}")
    if not trd_api:
        trd_api = os.getenv(f"TRD_API_{trd_mode}")

    trd_headers = {
        'Authorization': f'Bearer {trd_api}',
        'Accept': 'application/json',
    }

    return {
        'account': trd_account,
        'base': trd_base,
        'headers': trd_headers,
    }


# ==============================================================================
# ACCOUNT QUERIES
# ==============================================================================

def get_orders_trd(trd_account=None, trd_api=None):
    """
    Get all orders for an account, including tags.

    Args:
        trd_account: Tradier account number
        trd_api: Tradier API key

    Returns:
        list: List of order dictionaries
    """
    trd_auth = get_auth_trd(trd_account, trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]
    trd_account = trd_auth["account"]

    url = f'{trd_base}/accounts/{trd_account}/orders?includeTags=true'
    response = requests.get(url, headers=trd_headers)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
        if "orders" in content:
            content = content["orders"]
            if "order" in content:
                content = content["order"]
                if not isinstance(content, list):
                    content = [content]
    else:
        print(f"Error: get_orders_trd, trd_account = {trd_account}")
        content = []

    if content in na:
        content = []
    return content


def get_balances_trd(trd_account=None, trd_api=None):
    """
    Get account balances.

    Args:
        trd_account: Tradier account number
        trd_api: Tradier API key

    Returns:
        dict: Balances dictionary
    """
    trd_auth = get_auth_trd(trd_account, trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]
    trd_account = trd_auth["account"]

    url = f'{trd_base}/accounts/{trd_account}/balances'
    response = requests.get(url, headers=trd_headers)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
        if "balances" in content:
            content = content["balances"]
    else:
        print(f"Error: get_balances_trd, trd_account = {trd_account}")
        content = {}

    return content


def get_positions_trd(trd_account=None, trd_api=None):
    """
    Get account positions.

    Args:
        trd_account: Tradier account number
        trd_api: Tradier API key

    Returns:
        list: List of position dictionaries
    """
    trd_auth = get_auth_trd(trd_account, trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]
    trd_account = trd_auth["account"]

    url = f'{trd_base}/accounts/{trd_account}/positions'
    response = requests.get(url, headers=trd_headers)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
        if "positions" in content:
            content = content["positions"]
            if "position" in content:
                content = content["position"]
                if not isinstance(content, list):
                    content = [content]
    else:
        print(f"Error: get_positions_trd, trd_account = {trd_account}")
        content = []

    if content in na:
        content = []
    return content


# ==============================================================================
# ORDER MANAGEMENT
# ==============================================================================

def post_orders_trd(data=None, trd_account=None, trd_api=None):
    """
    Place an order. Supports single and multi-leg orders.

    Data is sent as form-encoded (NOT JSON) per Tradier API requirements.
    Multi-leg orders use indexed notation: option_symbol[0], side[0], quantity[0].

    Args:
        data: Order data dictionary
        trd_account: Tradier account number
        trd_api: Tradier API key

    Returns:
        dict or str: Order response or "Error"
    """
    trd_auth = get_auth_trd(trd_account, trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]
    trd_account = trd_auth["account"]

    url = f'{trd_base}/accounts/{trd_account}/orders'
    response = requests.post(url, headers=trd_headers, data=data)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
    else:
        detail = response.text[:300] if response.text else "No response body"
        print(f"Error: post_orders_trd, trd_account = {trd_account}, status = {response.status_code}, detail = {detail}")
        return "Error"
    return content


def modify_orders_trd(order_id, data=None, trd_account=None, trd_api=None):
    """
    Modify an open order. Supports changing price, stop, duration, and type.
    Quantity cannot be modified via PUT — requires cancel + replace.

    Data is sent as form-encoded per Tradier API requirements.

    Args:
        order_id: Order ID to modify
        data: Dict of fields to modify (e.g., {"price": 1.75, "duration": "gtc"})
        trd_account: Tradier account number
        trd_api: Tradier API key

    Returns:
        dict or str: Modified order response or "Error"
    """
    trd_auth = get_auth_trd(trd_account, trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]
    trd_account = trd_auth["account"]

    url = f'{trd_base}/accounts/{trd_account}/orders/{order_id}'
    response = requests.put(url, headers=trd_headers, data=data)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
    else:
        detail = response.text[:300] if response.text else "No response body"
        print(f"Error: modify_orders_trd, order_id = {order_id}, trd_account = {trd_account}, status = {response.status_code}, detail = {detail}")
        return "Error"
    return content


def delete_orders_trd(order_id, trd_account=None, trd_api=None):
    """
    Cancel an order by ID.

    Args:
        order_id: Order ID to cancel
        trd_account: Tradier account number
        trd_api: Tradier API key

    Returns:
        dict: Cancellation response
    """
    trd_auth = get_auth_trd(trd_account, trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]
    trd_account = trd_auth["account"]

    url = f'{trd_base}/accounts/{trd_account}/orders/{order_id}'
    response = requests.delete(url, headers=trd_headers)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
    else:
        print(f"Error: delete_orders_trd, order_id = {order_id}, trd_account = {trd_account}")
        content = response.content
        print(content)
    return content


# ==============================================================================
# ACCOUNT VALIDATION
# ==============================================================================

def validate_account_trd(trd_account=None, trd_api=None):
    """
    Validate account credentials by fetching user profile.

    Args:
        trd_account: Tradier account number
        trd_api: Tradier API key

    Returns:
        dict: User profile data, or error dict
    """
    trd_auth = get_auth_trd(trd_account, trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]

    url = f'{trd_base}/user/profile'
    response = requests.get(url, headers=trd_headers)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
        return content
    else:
        try:
            body = json.loads(response.content)
            detail = body.get("fault", {}).get("faultstring", str(body))
        except Exception:
            detail = response.text[:200] if response.text else "No response body"
        print(f"Error: validate_account_trd, trd_account = {trd_account}, status = {response.status_code}, detail = {detail}")
        return {"error": f"HTTP {response.status_code}: {detail}"}


# ==============================================================================
# OPTIONS MARKET DATA
# ==============================================================================

def get_expirations_trd(symbol, trd_account=None, trd_api=None):
    """
    Get available option expiration dates for a symbol.

    Args:
        symbol: Underlying symbol (e.g., "SPY")
        trd_account: Tradier account number (for sandbox detection)
        trd_api: Tradier API key

    Returns:
        list: List of expiration date strings (e.g., ["2026-04-17", "2026-05-15"])
    """
    trd_auth = get_auth_trd(trd_account, trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]

    url = f"{trd_base}/markets/options/expirations?symbol={symbol}"
    response = requests.get(url, headers=trd_headers)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
        dates = content.get("expirations", {}).get("date", [])
        if not isinstance(dates, list):
            dates = [dates]
        return dates
    else:
        print(f"Error (get_expirations_trd): symbol={symbol}, status={response.status_code}")
        return []


def get_chain_trd(symbol, expiration, trd_account=None, trd_api=None):
    """
    Get the option chain for a symbol at a specific expiration.

    Args:
        symbol: Underlying symbol (e.g., "SPY")
        expiration: Expiration date string (e.g., "2026-04-17")
        trd_account: Tradier account number (for sandbox detection)
        trd_api: Tradier API key

    Returns:
        list: List of option contract dicts with symbol, strike, option_type, bid, ask, etc.
    """
    trd_auth = get_auth_trd(trd_account, trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]

    url = f"{trd_base}/markets/options/chains?symbol={symbol}&expiration={expiration}&greeks=false"
    response = requests.get(url, headers=trd_headers)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
        options = content.get("options", {}).get("option", [])
        if not isinstance(options, list):
            options = [options]
        return options
    else:
        print(f"Error (get_chain_trd): symbol={symbol}, expiration={expiration}, status={response.status_code}")
        return []


# ==============================================================================
# STREAMING
# ==============================================================================

def create_streaming_session(trd_api=None):
    """
    Create an account event streaming session.

    Args:
        trd_api: Tradier API key

    Returns:
        str: Session ID for WebSocket connection
    """
    trd_auth = get_auth_trd(trd_api=trd_api)
    trd_base = trd_auth["base"]
    trd_headers = trd_auth["headers"]

    url = f'{trd_base}/accounts/events/session'
    response = requests.post(url, headers=trd_headers)

    if response.status_code in [200, 201]:
        content = json.loads(response.content)
        if "stream" in content:
            return content["stream"].get("sessionid", "")
        return content.get("sessionid", "")
    else:
        print(f"Error: create_streaming_session")
        return ""


def get_streaming_url():
    """Get the WebSocket URL for Tradier account event streaming."""
    return "wss://ws.tradier.com/v1/accounts/events"

# END
