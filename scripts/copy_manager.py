"""
Copy Manager Module for Tradier Copy Bot

This module contains the core copy trading logic that monitors a master account
and replicates orders to follower accounts with configurable multipliers.

Key Functions:
    - get_master_account: Query DB for master account
    - get_follower_accounts: Query DB for all non-master accounts
    - get_new_master_orders: Poll master for unhandled orders
    - reconstruct_multileg_order: Build multi-leg order data from master order
    - reconstruct_single_order: Build single-leg order data from master order
    - forward_order_to_follower: Copy an order to a follower account
    - check_master_cancellations: Detect and sync cancellations
    - check_master_modifications: Detect and sync price/duration/quantity changes
    - check_stale_orders: Cancel orders older than timeout
    - update_trade_statuses: Poll and update open trade statuses
    - run_copy_cycle: Orchestrate one full copy cycle

Notes:
    - Multi-leg orders use indexed notation for Tradier API
    - Deduplication via history + trades collections
    - Stale timeout prevents copying old orders
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt
import json
import math
import traceback

from constants import *
from integrations.tradier_ import *
from scripts.database_manager import *


# ==============================================================================
# ACCOUNT QUERIES
# ==============================================================================

def get_master_account(db):
    """
    Get the master account from the database.

    Returns:
        dict: Master account document, or None
    """
    return db.get_collection("accounts").find_one({"is_master": True})


def get_follower_accounts(db):
    """
    Get all follower (non-master) accounts from the database.

    Returns:
        list: List of follower account documents
    """
    return list(db.get_collection("accounts").find({"is_master": {"$ne": True}}))


# ==============================================================================
# ORDER DETECTION
# ==============================================================================

def get_new_master_orders(db, master_account):
    """
    Poll master account for new unhandled orders.

    Filters out bad statuses and deduplicates against history and trades.

    Args:
        db: MongoDB database connection
        master_account: Master account document

    Returns:
        list: List of new order dictionaries
    """
    master_orders = get_orders_trd(
        trd_account=master_account.get("account_number"),
        trd_api=master_account.get("api_key"),
    )

    # Filter bad statuses
    master_orders = [o for o in master_orders if o.get("status") not in bad_statuses]

    # Get handled order IDs from history
    master_id = master_account.get("account_number")
    master_history = db.get_collection("history").find_one({"account_number": master_id})
    if not master_history:
        master_history = {}
    history_ids = [item.get("id") for item in master_history.get("history", [])]

    # Get handled order IDs from trades
    master_trades = db.get_collection("trades").find_one({"account_number": master_id})
    if not master_trades:
        master_trades = {}
    trade_ids = [item.get("id") for item in master_trades.get("trades", [])]

    handled_ids = history_ids + trade_ids
    new_orders = [o for o in master_orders if o.get("id") not in handled_ids]

    return new_orders


# ==============================================================================
# ORDER RECONSTRUCTION
# ==============================================================================

def reconstruct_multileg_order(master_order, multiplier=1):
    """
    Reconstruct a multi-leg order from a master order for forwarding.

    Uses Tradier's indexed notation for multi-leg orders:
    option_symbol[0], side[0], quantity[0], etc.

    Args:
        master_order: Master order dictionary with 'leg' key
        multiplier: Quantity multiplier for follower

    Returns:
        dict: Form-encoded order data for Tradier API
    """
    data = {
        "class": "multileg",
        "symbol": master_order.get("symbol", ""),
        "type": "market",
        "duration": master_order.get("duration", "day"),
        "tag": f"follower-{master_order.get('symbol', '')}-{master_order.get('id', 0)}",
    }

    legs = master_order.get("leg", [])
    for i, leg in enumerate(legs):
        data[f"option_symbol[{i}]"] = leg.get("option_symbol", leg.get("symbol", ""))
        data[f"side[{i}]"] = leg.get("side", "")
        raw_qty = int(leg.get("quantity", 0)) * multiplier
        data[f"quantity[{i}]"] = str(max(MIN_FOLLOWER_QTY, math.floor(raw_qty)))

    return data


def reconstruct_single_order(master_order, multiplier=1):
    """
    Reconstruct a single-leg (equity/option) order from a master order.

    Args:
        master_order: Master order dictionary
        multiplier: Quantity multiplier for follower

    Returns:
        dict: Form-encoded order data for Tradier API
    """
    order_class = master_order.get("class", "equity")
    raw_qty = int(master_order.get("quantity", 0)) * multiplier
    quantity = max(MIN_FOLLOWER_QTY, math.floor(raw_qty))
    order_type = master_order.get("type", "market")

    data = {
        "class": order_class,
        "symbol": master_order.get("symbol", ""),
        "duration": master_order.get("duration", "day"),
        "side": master_order.get("side", "buy"),
        "quantity": str(quantity),
        "type": order_type,
        "tag": f"follower-{master_order.get('symbol', '')}-{master_order.get('id', 0)}",
    }

    if "limit" in order_type:
        data["price"] = master_order.get("price", 0)
    if "stop" in order_type:
        data["stop"] = master_order.get("stop", 0)

    option_symbol = master_order.get("option_symbol", "")
    if option_symbol:
        data["option_symbol"] = option_symbol

    return data


# ==============================================================================
# ORDER FORWARDING
# ==============================================================================

def forward_order_to_follower(db, master_order, follower, order_data, settings, recent_log_list):
    """
    Forward an order to a single follower account.

    Checks automation, dedup, stale timeout, then posts order.

    Args:
        db: MongoDB database connection
        master_order: Original master order dict
        follower: Follower account document
        order_data: Reconstructed order data for Tradier
        settings: Global settings dict
        recent_log_list: List of recent log messages for dedup

    Returns:
        dict or None: Order response, or None if skipped
    """
    act_nbr = follower.get("account_number", "")
    alias = follower.get("alias", act_nbr)
    order_id = master_order.get("id", 0)
    now = dt.datetime.now(tz=market_timezone)

    # Check stale timeout
    create_date_str = master_order.get("create_date", "")
    if create_date_str:
        try:
            create_date = dt.datetime.fromisoformat(str(create_date_str).replace("Z", "+00:00"))
            if create_date.tzinfo is None:
                create_date = utc_timezone.localize(create_date)
            create_date = create_date.astimezone(market_timezone)
            stale_timeout = settings.get("stale_timeout", DEFAULT_STALE_TIMEOUT)
            minutes_since = (now - create_date).total_seconds() / 60
            if minutes_since > stale_timeout:
                msg = f"Warning: Follower '{alias}': skipping order {order_id}, {minutes_since:.1f} min old > {stale_timeout} min timeout"
                if msg not in recent_log_list:
                    print_store(db, master_username, msg)
                    recent_log_list.append(msg)
                return None
        except (ValueError, TypeError):
            pass

    # Check dedup - already copied?
    follower_filters = {"account_number": act_nbr}
    account_trades = db.get_collection("trades").find_one(filter=follower_filters)
    if not account_trades:
        account_trades = {}
    for trade in account_trades.get("trades", []):
        if trade.get("master_id") == order_id:
            msg = f"Info: Follower '{alias}': already has order for master order {order_id}"
            if msg not in recent_log_list:
                print_store(db, master_username, msg)
                recent_log_list.append(msg)
            return None

    # Post order
    result = post_orders_trd(
        data=order_data,
        trd_account=act_nbr,
        trd_api=follower.get("api_key", ""),
    )

    if isinstance(result, dict):
        result_order = result.get("order", result)
        result_id = result_order.get("id", "?")
        result_status = result_order.get("status", "?")
        print_store(db, master_username,
            f"Info: Follower '{alias}': order placed — id={result_id}, status={result_status}, "
            f"master_order={order_id}")
    else:
        print_store(db, master_username,
            f"Error: Follower '{alias}': order failed for master order {order_id}, result={result}")

    if result == "Error":
        return None

    # Store in trades with snapshot for modification tracking
    if isinstance(result, dict):
        if "order" in result:
            result = result["order"]
        result["master_id"] = order_id

        # Store what was sent to the follower broker
        copied_fields = {
            "price": order_data.get("price"),
            "stop": order_data.get("stop"),
            "duration": order_data.get("duration"),
            "type": order_data.get("type"),
            "quantity": order_data.get("quantity"),
        }
        if order_data.get("class") == "multileg":
            leg_quantities = {}
            i = 0
            while f"quantity[{i}]" in order_data:
                leg_quantities[str(i)] = order_data[f"quantity[{i}]"]
                i += 1
            copied_fields["leg_quantities"] = leg_quantities

        # Store master's state at copy time for drift detection
        master_snapshot = {
            "price": master_order.get("price"),
            "stop": master_order.get("stop"),
            "duration": master_order.get("duration"),
            "type": master_order.get("type"),
            "quantity": master_order.get("quantity"),
        }
        if master_order.get("leg"):
            master_snapshot["leg_quantities"] = [
                leg.get("quantity") for leg in master_order.get("leg", [])
            ]

        result["copied_fields"] = copied_fields
        result["master_snapshot"] = master_snapshot

        updates = {"$push": {"trades": result}}
        db.get_collection("trades").update_one(filter=follower_filters, update=updates, upsert=True)
        print_store(db, master_username, f"Info: Follower '{alias}': trade stored for master order {order_id}")

    return result


# ==============================================================================
# CANCELLATION SYNC
# ==============================================================================

def check_master_cancellations(db, master_orders, followers):
    """
    Detect canceled master orders and cancel matching follower orders.

    Args:
        db: MongoDB database connection
        master_orders: Pre-fetched list of current master orders
        followers: List of follower account documents
    """
    canceled_ids = [o.get("id") for o in master_orders if o.get("status") == "canceled"]
    if not canceled_ids:
        return

    for follower in followers:
        act_nbr = follower.get("account_number", "")
        alias = follower.get("alias", act_nbr)
        follower_filters = {"account_number": act_nbr}

        account_trades = db.get_collection("trades").find_one(filter=follower_filters)
        if not account_trades:
            continue

        for trade in account_trades.get("trades", []):
            if not trade:
                continue
            master_id = trade.get("master_id", 0)
            child_id = trade.get("id", 0)

            if master_id in canceled_ids and trade.get("status") in open_statuses:
                print_store(db, master_username,
                    f"Info: Follower '{alias}': canceling order {child_id} (master {master_id} was canceled)")
                delete_orders_trd(
                    order_id=child_id,
                    trd_account=act_nbr,
                    trd_api=follower.get("api_key", ""),
                )


# ==============================================================================
# MODIFICATION SYNC
# ==============================================================================

MODIFIABLE_FIELDS = ["price", "stop", "duration", "type"]


def check_master_modifications(db, master_orders, followers, settings):
    """
    Detect modified master orders and sync changes to follower orders.

    For modifiable fields (price, stop, duration, type): uses PUT to modify.
    For quantity changes: cancels and replaces the follower order.

    Args:
        db: MongoDB database connection
        master_orders: Pre-fetched list of current master orders
        followers: List of follower account documents
        settings: Global settings dict (for multipliers)
    """
    master_orders_by_id = {o.get("id"): o for o in master_orders}

    for follower in followers:
        act_nbr = follower.get("account_number", "")
        alias = follower.get("alias", act_nbr)
        follower_filters = {"account_number": act_nbr}

        account_trades = db.get_collection("trades").find_one(filter=follower_filters)
        if not account_trades:
            continue

        for i, trade in enumerate(account_trades.get("trades", [])):
            if not trade:
                continue
            master_id = trade.get("master_id", 0)
            if master_id == 0:
                continue
            if trade.get("status") not in open_statuses:
                continue

            master_snapshot = trade.get("master_snapshot")
            if not master_snapshot:
                continue  # Legacy trade without snapshot

            current_master = master_orders_by_id.get(master_id)
            if not current_master:
                continue  # Master order no longer visible
            if current_master.get("status") not in open_statuses:
                continue  # Master order is no longer open

            # Check modifiable fields (price, stop, duration, type)
            modify_data = {}
            for field in MODIFIABLE_FIELDS:
                current_val = current_master.get(field)
                snapshot_val = master_snapshot.get(field)
                if current_val != snapshot_val and current_val is not None:
                    modify_data[field] = current_val

            # Check quantity (requires cancel+replace)
            quantity_changed = False
            current_qty = current_master.get("quantity")
            snapshot_qty = master_snapshot.get("quantity")
            if str(current_qty) != str(snapshot_qty) and current_qty is not None:
                quantity_changed = True

            # Check multi-leg quantities
            if not quantity_changed and current_master.get("leg"):
                current_leg_qtys = [leg.get("quantity") for leg in current_master.get("leg", [])]
                snapshot_leg_qtys = master_snapshot.get("leg_quantities", [])
                if current_leg_qtys != snapshot_leg_qtys:
                    quantity_changed = True

            if not modify_data and not quantity_changed:
                continue

            child_id = trade.get("id", 0)

            if quantity_changed:
                # Quantity changed — must cancel + replace
                print_store(db, master_username,
                    f"Info: Follower '{alias}': cancel+replace order {child_id} "
                    f"(master {master_id} quantity changed)")
                _cancel_and_replace(db, trade, current_master, follower, settings, i, follower_filters)
            else:
                # Only modifiable fields changed — try PUT
                print_store(db, master_username,
                    f"Info: Follower '{alias}': modifying order {child_id} "
                    f"(master {master_id} changed {list(modify_data.keys())})")

                result = modify_orders_trd(
                    order_id=child_id,
                    data=modify_data,
                    trd_account=act_nbr,
                    trd_api=follower.get("api_key", ""),
                )

                if result == "Error":
                    # Fallback: cancel + replace
                    print_store(db, master_username,
                        f"Warning: Follower '{alias}': modify failed, falling back to cancel+replace")
                    _cancel_and_replace(db, trade, current_master, follower, settings, i, follower_filters)
                else:
                    # Update stored snapshots
                    new_snapshot = dict(master_snapshot)
                    for field in MODIFIABLE_FIELDS:
                        new_snapshot[field] = current_master.get(field)
                    new_copied = dict(trade.get("copied_fields", {}))
                    new_copied.update(modify_data)

                    db.get_collection("trades").update_one(
                        filter=follower_filters,
                        update={"$set": {
                            f"trades.{i}.master_snapshot": new_snapshot,
                            f"trades.{i}.copied_fields": new_copied,
                        }},
                    )


def _cancel_and_replace(db, trade, current_master, follower, settings, trade_index, follower_filters):
    """
    Cancel a follower order and replace it with a new one based on current master state.

    Args:
        db: MongoDB database connection
        trade: The follower's trade dict being replaced
        current_master: Current state of the master order
        follower: Follower account document
        settings: Global settings dict
        trade_index: Index of the trade in the trades array
        follower_filters: MongoDB filter for the follower's trades doc
    """
    act_nbr = follower.get("account_number", "")
    alias = follower.get("alias", act_nbr)
    child_id = trade.get("id", 0)
    master_id = trade.get("master_id", 0)

    # Cancel the existing order
    cancel_result = delete_orders_trd(
        order_id=child_id,
        trd_account=act_nbr,
        trd_api=follower.get("api_key", ""),
    )
    print_store(db, master_username, f"Info: Follower '{alias}': canceled order {child_id} for replacement")

    # Reconstruct from current master state
    multiplier = float(settings.get("multipliers", {}).get(act_nbr, 1))
    legs = current_master.get("leg", [])
    if legs:
        order_data = reconstruct_multileg_order(current_master, multiplier)
    else:
        order_data = reconstruct_single_order(current_master, multiplier)

    # Post new order
    result = post_orders_trd(
        data=order_data,
        trd_account=act_nbr,
        trd_api=follower.get("api_key", ""),
    )

    if result == "Error":
        print_store(db, master_username, f"Error: Follower '{alias}': replacement order failed for master {master_id}")
        # Remove the old trade since it was canceled
        db.get_collection("trades").update_one(
            filter=follower_filters,
            update={"$pull": {"trades": {"id": child_id}}},
        )
        return

    # Store the new trade
    if isinstance(result, dict):
        if "order" in result:
            result = result["order"]
        result["master_id"] = master_id

        # Build fresh snapshots
        copied_fields = {
            "price": order_data.get("price"),
            "stop": order_data.get("stop"),
            "duration": order_data.get("duration"),
            "type": order_data.get("type"),
            "quantity": order_data.get("quantity"),
        }
        if order_data.get("class") == "multileg":
            leg_quantities = {}
            idx = 0
            while f"quantity[{idx}]" in order_data:
                leg_quantities[str(idx)] = order_data[f"quantity[{idx}]"]
                idx += 1
            copied_fields["leg_quantities"] = leg_quantities

        master_snapshot = {
            "price": current_master.get("price"),
            "stop": current_master.get("stop"),
            "duration": current_master.get("duration"),
            "type": current_master.get("type"),
            "quantity": current_master.get("quantity"),
        }
        if current_master.get("leg"):
            master_snapshot["leg_quantities"] = [
                leg.get("quantity") for leg in current_master.get("leg", [])
            ]

        result["copied_fields"] = copied_fields
        result["master_snapshot"] = master_snapshot

        # Remove old trade, add new one
        db.get_collection("trades").update_one(
            filter=follower_filters,
            update={"$pull": {"trades": {"id": child_id}}},
        )
        db.get_collection("trades").update_one(
            filter=follower_filters,
            update={"$push": {"trades": result}},
            upsert=True,
        )
        print_store(db, master_username,
            f"Info: Follower '{alias}': replacement order stored for master {master_id}")


# ==============================================================================
# STALE ORDER MANAGEMENT
# ==============================================================================

def check_stale_orders(db, all_accounts, stale_timeout):
    """
    Find and cancel open orders older than the stale timeout.

    Args:
        db: MongoDB database connection
        all_accounts: List of all account documents
        stale_timeout: Timeout in minutes
    """
    now = dt.datetime.now(tz=market_timezone)

    for account in all_accounts:
        act_nbr = account.get("account_number", "")
        alias = account.get("alias", act_nbr)

        orders = get_orders_trd(
            trd_account=act_nbr,
            trd_api=account.get("api_key", ""),
        )

        for order in orders:
            if order.get("status") not in open_statuses:
                continue
            create_date_str = order.get("create_date", "")
            if not create_date_str:
                continue
            try:
                create_date = dt.datetime.fromisoformat(str(create_date_str).replace("Z", "+00:00"))
                if create_date.tzinfo is None:
                    create_date = utc_timezone.localize(create_date)
                create_date = create_date.astimezone(market_timezone)
                minutes_since = (now - create_date).total_seconds() / 60
                if minutes_since > stale_timeout:
                    print(f"Follower '{alias}': canceling stale order {order.get('id')} ({minutes_since:.1f} min old)")
                    delete_orders_trd(
                        order_id=order.get("id"),
                        trd_account=act_nbr,
                        trd_api=account.get("api_key", ""),
                    )
            except (ValueError, TypeError):
                continue


# ==============================================================================
# TRADE STATUS UPDATES
# ==============================================================================

def update_trade_statuses(db):
    """
    Poll order statuses for all open trades and move completed ones to history.

    Args:
        db: MongoDB database connection
    """
    accounts = list(db.get_collection("accounts").find({}))

    for account in accounts:
        act_nbr = account.get("account_number", "")
        alias = account.get("alias", act_nbr)
        filters = {"account_number": act_nbr}

        account_trades = db.get_collection("trades").find_one(filter=filters)
        if not account_trades:
            continue

        trades = account_trades.get("trades", [])
        for i, trade in enumerate(trades):
            if not trade:
                continue
            order_id = trade.get("id", 0)
            if order_id == 0:
                continue

            current_status = trade.get("status", "")
            if current_status in closed_statuses:
                # Move to history
                db.get_collection("history").update_one(
                    filter=filters,
                    update={"$push": {"history": trade}},
                    upsert=True,
                )
                db.get_collection("trades").update_one(
                    filter=filters,
                    update={"$pull": {"trades": trade}},
                )
                print(f"Follower '{alias}': trade {order_id} moved to history (status: {current_status})")
                continue

            # Poll for updated status
            orders = get_orders_trd(
                trd_account=act_nbr,
                trd_api=account.get("api_key", ""),
            )

            matching = [o for o in orders if o.get("id") == order_id]
            if matching:
                updated_order = matching[0]
                new_status = updated_order.get("status", "")
                if new_status != current_status:
                    updated_trade = {**trade, **updated_order}
                    updated_trade["master_id"] = trade.get("master_id", 0)
                    db.get_collection("trades").update_one(
                        filter=filters,
                        update={"$set": {f"trades.{i}": updated_trade}},
                    )

                    if new_status in closed_statuses:
                        db.get_collection("history").update_one(
                            filter=filters,
                            update={"$push": {"history": updated_trade}},
                            upsert=True,
                        )
                        db.get_collection("trades").update_one(
                            filter=filters,
                            update={"$pull": {"trades": {"id": order_id}}},
                        )
                        print(f"Follower '{alias}': trade {order_id} completed (status: {new_status})")


# ==============================================================================
# MAIN COPY CYCLE
# ==============================================================================

def run_copy_cycle(db, recent_log_list):
    """
    Orchestrate one full copy cycle.

    1. Get master account and followers
    2. Detect new master orders
    3. Reconstruct and forward to followers
    4. Check cancellations
    5. Update trade statuses

    Args:
        db: MongoDB database connection
        recent_log_list: List of recent log messages for dedup

    Returns:
        bool: True if cycle completed successfully
    """
    try:
        # Get master account
        master = get_master_account(db)
        if not master:
            msg = "No master account configured"
            if msg not in recent_log_list:
                print(msg)
                recent_log_list.append(msg)
            return False

        # Get followers
        followers = get_follower_accounts(db)
        if not followers:
            msg = "No follower accounts configured"
            if msg not in recent_log_list:
                print(msg)
                recent_log_list.append(msg)
            return True

        # Get global settings
        global_settings = db.get_collection("settings").find_one({"type": "global"}) or {}
        settings = {**get_default_settings(), **global_settings}

        # Check automation killswitch
        if not settings.get("use_automation", False):
            msg = "Automation is disabled"
            if msg not in recent_log_list:
                print(msg)
                recent_log_list.append(msg)
            return True

        # Detect new orders
        new_orders = get_new_master_orders(db, master)
        if not new_orders:
            msg = f"No new orders in master account"
            if msg not in recent_log_list:
                print(msg)
                recent_log_list.append(msg)
        else:
            master_id = master.get("account_number")
            master_filters = {"account_number": master_id}

            for order in new_orders:
                order_id = order.get("id", 0)
                ticker = order.get("symbol", "")
                side = order.get("side", "")
                qty = order.get("quantity", 0)
                order_type = order.get("type", "market")
                legs = order.get("leg", [])
                print_store(db, master_username,
                    f"Info: Master: new order detected — {side.upper()} {qty} {ticker} "
                    f"({order_type}), id={order_id}, copying to {len(followers)} follower(s)")

                # Store in master history
                db.get_collection("history").update_one(
                    filter=master_filters,
                    update={"$push": {"history": order}},
                    upsert=True,
                )

                # Forward to each follower
                for follower in followers:
                    act_nbr = follower.get("account_number", "")
                    alias = follower.get("alias", act_nbr)
                    multiplier = float(settings.get("multipliers", {}).get(act_nbr, 1))
                    master_qty = int(order.get("quantity", 0))
                    follower_qty = max(MIN_FOLLOWER_QTY, math.floor(master_qty * multiplier))
                    print(f"Follower '{alias}': master_qty={master_qty} x multiplier={multiplier} = {master_qty * multiplier} -> floor={follower_qty}")

                    if legs:
                        order_data = reconstruct_multileg_order(order, multiplier)
                    else:
                        order_data = reconstruct_single_order(order, multiplier)

                    forward_order_to_follower(db, order, follower, order_data, settings, recent_log_list)

        # Fetch master orders once for cancellation + modification checks
        master_orders_live = get_orders_trd(
            trd_account=master.get("account_number"),
            trd_api=master.get("api_key"),
        )

        # Check for cancellations
        check_master_cancellations(db, master_orders_live, followers)

        # Check for modifications (price, duration, quantity changes)
        check_master_modifications(db, master_orders_live, followers, settings)

        # Auto-cancel stale open orders
        stale_timeout = settings.get("stale_timeout", DEFAULT_STALE_TIMEOUT)
        all_accounts = [master] + followers
        check_stale_orders(db, all_accounts, stale_timeout)

        # Update trade statuses
        update_trade_statuses(db)

        return True

    except Exception as e:
        print(f"Error in run_copy_cycle: {e}")
        print(traceback.format_exc())
        return False

# END
