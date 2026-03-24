"""
Positions Service for Tradier Copy Bot

Abstracts API calls for position management.

Key Functions:
    - do_get_positions: Get live positions across all accounts
    - do_close_position: Close a position at market
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from scripts.database_manager import connect_mongo
from integrations.tradier_ import get_positions_trd, post_orders_trd


# ==============================================================================
# SERVICE FUNCTIONS
# ==============================================================================

def do_get_positions():
    """
    Get live positions from Tradier grouped by account.

    Returns:
        list: List of (account_dict, positions_list) tuples, one per account.
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
            positions = get_positions_trd(trd_account=act_nbr, trd_api=api_key)
            for position in positions:
                position["_account_alias"] = alias
                position["_account_number"] = act_nbr
        except Exception as e:
            positions = [{"_error": str(e), "_account_alias": alias, "_account_number": act_nbr}]

        result.append((account, positions))

    return result


def do_close_position(account_number, symbol, quantity, side="sell"):
    """
    Close a position by placing a market order.

    Args:
        account_number: Tradier account number
        symbol: Symbol to close
        quantity: Number of shares/contracts
        side: Closing side (sell, buy_to_cover, sell_to_close, buy_to_close)

    Returns:
        tuple: (success: bool, message: str)
    """
    db = connect_mongo()
    account = db.get_collection("accounts").find_one({"account_number": account_number})
    if not account:
        return False, f"Account {account_number} not found"

    # Determine order class
    order_class = "equity"
    if len(symbol) > 10:
        order_class = "option"

    data = {
        "class": order_class,
        "symbol": symbol,
        "side": side,
        "quantity": str(abs(int(quantity))),
        "type": "market",
        "duration": "day",
        "tag": "close-position",
    }

    result = post_orders_trd(
        data=data,
        trd_account=account_number,
        trd_api=account.get("api_key", ""),
    )

    if result == "Error":
        return False, f"Failed to close position {symbol}"
    return True, f"Close order placed for {symbol}"

# END
