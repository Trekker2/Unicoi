"""
Orders Service for Tradier Copy Bot

Abstracts API calls for order management.

Key Functions:
    - do_get_orders: Get live orders across all accounts
    - do_delete_order: Cancel an order
    - get_display_price: Resolve the price to show in the Orders table
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from scripts.database_manager import connect_mongo
from integrations.tradier_ import get_orders_trd, delete_orders_trd


# ==============================================================================
# HELPERS
# ==============================================================================

def get_display_price(order):
    """
    Resolve the price to show in the Orders table for a given order.

    Returns (value, is_fill):
        value   -- the price to display, or "" when no usable price exists
        is_fill -- True when the displayed value is a realized fill price
                   (average or last partial), False when it is the limit
                   price shown while the order is still open / canceled /
                   rejected. The Orders page uses this flag to render limit
                   prices in muted italic so the reader can tell at a glance
                   whether the cell is a fill or a still-pending limit.
    """
    avg = order.get("avg_fill_price")
    if avg:
        return avg, True
    last = order.get("last_fill_price")
    if last:
        return last, True
    limit = order.get("price")
    if limit:
        return limit, False
    return "", False


# ==============================================================================
# SERVICE FUNCTIONS
# ==============================================================================

def do_get_orders():
    """
    Get live orders from Tradier grouped by account.

    Returns:
        list: List of (account_dict, orders_list) tuples, one per account.
              Each account_dict has alias, account_number, is_master.
              Each order has _account_alias and _account_number injected.
    """
    db = connect_mongo()
    accounts = list(db.get_collection("accounts").find({}))
    accounts.sort(key=lambda a: (0 if a.get("is_master", False) else 1))
    result = []

    for account in accounts:
        act_nbr = account.get("account_number", "")
        alias = account.get("alias", act_nbr)
        api_key = account.get("api_key", "")

        try:
            orders = get_orders_trd(trd_account=act_nbr, trd_api=api_key)
            for order in orders:
                order["_account_alias"] = alias
                order["_account_number"] = act_nbr
        except Exception as e:
            orders = [{"_error": str(e), "_account_alias": alias, "_account_number": act_nbr}]

        result.append((account, orders))

    return result


def do_delete_order(account_number, order_id):
    """
    Cancel an order.

    Args:
        account_number: Tradier account number
        order_id: Order ID to cancel

    Returns:
        tuple: (success: bool, message: str)
    """
    db = connect_mongo()
    account = db.get_collection("accounts").find_one({"account_number": account_number})
    if not account:
        return False, f"Account {account_number} not found"

    result = delete_orders_trd(
        order_id=order_id,
        trd_account=account_number,
        trd_api=account.get("api_key", ""),
    )

    if isinstance(result, dict) and "order" in result:
        return True, f"Order {order_id} canceled"
    return True, f"Cancel request sent for order {order_id}"

# END
