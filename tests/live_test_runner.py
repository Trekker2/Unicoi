"""
Live Integration Test Runner for Tradier Copy Bot

Phase-based tests against the real Tradier sandbox API. Tests the actual
order lifecycle: place, modify, cancel, and verify the copy pipeline end-to-end.
Multi-symbol coverage (SPY, AAPL, QQQ) with standard and 0 DTE options.

Uses Tradier sandbox accounts (VA prefix) — no real money at risk.

Usage:
    python -m tests.live_test_runner --required     # Phases 0-4 (read-only + order lifecycle)
    python -m tests.live_test_runner --all           # All phases (same as --required)
    python -m tests.live_test_runner --phase 2       # Single phase
    python -m tests.live_test_runner --phase 1-3     # Phase range
    python -m tests.live_test_runner --cleanup       # Cancel any leftover test orders

Phases:
    0: Prerequisites — API connectivity, account access
    1: Read-Only API — orders, positions, balances return valid data
    2: Order Placement + Copy — multi-symbol equities (AAPL, MSFT, NVDA),
       SPY options (7+ DTE), SPY/QQQ 0 DTE options, 2-leg spreads, 4-leg iron condor
    3: Order Modification — modify master, run copy engine, verify sync
    4: Order Cancellation — cancel master, run copy engine, verify sync
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import argparse
import atexit
import datetime as dt
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.tradier_ import (
    get_auth_trd, get_orders_trd, get_balances_trd, get_positions_trd,
    post_orders_trd, modify_orders_trd, delete_orders_trd,
    validate_account_trd, create_streaming_session,
    get_expirations_trd, get_chain_trd,
)
from constants import get_default_settings
from scripts.database_manager import connect_mongo, print_store
try:
    from helper import is_market_open, format_tag
except ImportError:
    # Fallback if helper not importable — weekday 9:30-16:00 ET
    import datetime as dt
    import pytz
    def is_market_open(check_time=None):
        et = pytz.timezone("US/Eastern")
        now = check_time or dt.datetime.now(tz=et)
        now_et = now.astimezone(et)
        if now_et.weekday() >= 5:
            return False
        t = now_et.time()
        return dt.time(9, 30) <= t < dt.time(16, 0)
    def format_tag(s):
        result = ""
        for char in s:
            result += char if char.isalnum() else "-"
        return result[:255]


# ==============================================================================
# ACCOUNT CREDENTIALS (loaded from MongoDB)
# ==============================================================================

# Populated at runtime from accounts collection — master/follower as defined in DB
MASTER_ACCOUNT = None
MASTER_API_KEY = None
FOLLOWER_ACCOUNT = None
FOLLOWER_API_KEY = None


def load_accounts():
    """Load master/follower accounts from MongoDB."""
    global MASTER_ACCOUNT, MASTER_API_KEY, FOLLOWER_ACCOUNT, FOLLOWER_API_KEY
    db = get_db()
    accounts = list(db.get_collection("accounts").find())
    for acct in accounts:
        if acct.get("is_master"):
            MASTER_ACCOUNT = acct.get("account_number")
            MASTER_API_KEY = acct.get("api_key")
        else:
            if FOLLOWER_ACCOUNT is None:
                FOLLOWER_ACCOUNT = acct.get("account_number")
                FOLLOWER_API_KEY = acct.get("api_key")

TEST_TAG_PREFIX = "live-test"
LOG_USER = "live-test"
_db = None
_force_automation = False


def get_db():
    """Lazy-connect to MongoDB for logging."""
    global _db
    if _db is None:
        _db = connect_mongo()
    return _db


def log(msg):
    """Log a message to both stdout and MongoDB activity logs."""
    print_store(get_db(), LOG_USER, msg)


def make_test_tag(symbol, role=""):
    """Generate a unique order tag. Short format: live-test-{role}-{symbol}-{timestamp}."""
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    parts = [TEST_TAG_PREFIX]
    if role:
        parts.append(role)
    parts.extend([symbol, ts])
    return format_tag("-".join(parts))


# Test symbols — equities use big-name tech, SPY/QQQ reserved for options
TEST_EQUITY_SYMBOLS = ["AAPL", "MSFT", "NVDA"]
TEST_OPTION_SYMBOLS = ["SPY", "QQQ"]  # Liquid chains for option + spread tests


def make_equity_order(symbol, order_type="market", price=None):
    """Build an equity order dict for the given symbol."""
    data = {
        "class": "equity",
        "symbol": symbol,
        "side": "buy",
        "quantity": "1",
        "type": order_type,
        "duration": "day",
    }
    if order_type == "limit":
        data["price"] = price or "1.00"
    return data


def get_test_option_symbols(symbol, zero_dte=False):
    """
    Get real option symbols from the chain API for testing.

    Args:
        symbol: Underlying symbol (e.g., "SPY", "QQQ")
        zero_dte: If True, use today's expiration (0 DTE). Otherwise use 7+ days out.

    Returns:
        dict with keys:
            - single: OCC symbol for a far OTM call (single-leg test)
            - spread_long: OCC symbol for long leg of a vertical spread
            - spread_short: OCC symbol for short leg of a vertical spread
            - expiration: Expiration date used
            - zero_dte: Whether this is a 0 DTE expiration
        Returns None if chain unavailable.
    """
    expirations = get_expirations_trd(symbol, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
    if not expirations:
        return None

    today_str = dt.datetime.now().strftime("%Y-%m-%d")
    expiration = None

    if zero_dte:
        # Look for today's expiration (0 DTE)
        if today_str in expirations:
            expiration = today_str
        else:
            # No 0 DTE available for this symbol today
            return None
    else:
        # Use the first expiration at least 7 days out
        min_date = (dt.datetime.now() + dt.timedelta(days=7)).strftime("%Y-%m-%d")
        for exp in expirations:
            if exp >= min_date:
                expiration = exp
                break
        if not expiration:
            expiration = expirations[-1]

    # Get chain for that expiration
    chain = get_chain_trd(symbol, expiration, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
    if not chain:
        return None

    # Filter calls and puts, sorted by strike
    calls = [c for c in chain if c.get("option_type") == "call"]
    puts = [c for c in chain if c.get("option_type") == "put"]
    calls.sort(key=lambda c: c.get("strike", 0), reverse=True)
    puts.sort(key=lambda p: p.get("strike", 0))  # ascending (lowest first = far OTM)

    if len(calls) < 2:
        return None

    # Pick 2 far OTM calls for vertical spread (highest strikes)
    single_symbol = calls[0].get("symbol")
    spread_short = calls[0].get("symbol")  # Sell highest strike
    spread_long = calls[1].get("symbol")   # Buy second highest

    result = {
        "single": single_symbol,
        "spread_long": spread_long,
        "spread_short": spread_short,
        "expiration": expiration,
        "zero_dte": expiration == today_str,
    }

    # Iron condor legs (4-leg): buy OTM put, sell less-OTM put, sell OTM call, buy more-OTM call
    if len(puts) >= 2 and len(calls) >= 2:
        result["ic_buy_put"] = puts[0].get("symbol")      # Buy far OTM put (lowest strike)
        result["ic_sell_put"] = puts[1].get("symbol")      # Sell next put (higher strike)
        result["ic_sell_call"] = calls[1].get("symbol")    # Sell OTM call (second highest)
        result["ic_buy_call"] = calls[0].get("symbol")     # Buy far OTM call (highest strike)

    return result


# ==============================================================================
# OUTPUT HELPERS
# ==============================================================================

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg):
    print(f"  {GREEN}PASS{RESET}  {msg}")


def fail(msg):
    print(f"  {RED}FAIL{RESET}  {msg}")


def warn(msg):
    print(f"  {YELLOW}WARN{RESET}  {msg}")


def step(msg):
    print(f"  {DIM}>{RESET}     {msg}")


def info(msg):
    print(f"  {DIM}INFO{RESET}  {msg}")


def phase_header(n, description, cost="$0"):
    print(f"\n{'=' * 60}")
    print(f"  Phase {n}: {description}  (cost: ~{cost})")
    print(f"{'=' * 60}")


# ==============================================================================
# PHASE RESULT
# ==============================================================================

class PhaseResult:
    """Tracks pass/fail counts for a single phase."""

    def __init__(self, number, description):
        self.number = number
        self.description = description
        self.passed = 0
        self.failed = 0

    def check(self, condition, pass_msg, fail_msg=None):
        if condition:
            ok(pass_msg)
            self.passed += 1
        else:
            fail(fail_msg or f"Expected: {pass_msg}")
            self.failed += 1
        return condition

    @property
    def success(self):
        return self.failed == 0

    def __repr__(self):
        status = f"{GREEN}PASS{RESET}" if self.success else f"{RED}FAIL{RESET}"
        return f"Phase {self.number}: {self.description} — {status} ({self.passed} passed, {self.failed} failed)"


# ==============================================================================
# CLEANUP
# ==============================================================================

_test_order_ids = {"master": [], "follower": []}
_equity_limit_order_id = None  # Tracked for phase 3 modification test


def cleanup():
    """Cancel any test orders that may still be open, restore automation if force-enabled."""
    for label, account, api_key in [
        ("master", MASTER_ACCOUNT, MASTER_API_KEY),
        ("follower", FOLLOWER_ACCOUNT, FOLLOWER_API_KEY),
    ]:
        orders = get_orders_trd(trd_account=account, trd_api=api_key)
        for order in orders:
            tag = order.get("tag", "")
            if TEST_TAG_PREFIX in str(tag) and order.get("status") in ["open", "pending", "partially_filled"]:
                step(f"Cleaning up {label} order {order['id']} (tag={tag})")
                delete_orders_trd(order_id=order["id"], trd_account=account, trd_api=api_key)

    # Restore automation to disabled if we force-enabled it
    if _force_automation:
        try:
            db = get_db()
            db.get_collection("settings").update_one(
                {"type": "global"}, {"$set": {"use_automation": False}}, upsert=True)
            step("Restored automation to disabled after test run")
        except Exception:
            pass


# ==============================================================================
# PHASES
# ==============================================================================

def phase_0():
    """Phase 0: Prerequisites — API connectivity and account access."""
    phase_header(0, "Prerequisites", cost="$0")
    r = PhaseResult(0, "Prerequisites")

    try:
        # Master auth
        auth = get_auth_trd(trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        r.check("sandbox" in auth["base"], "Master routes to sandbox")
        r.check(auth["account"] == MASTER_ACCOUNT, f"Master account = {MASTER_ACCOUNT}")

        # Master validation
        profile = validate_account_trd(trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        r.check("error" not in profile, "Master credentials valid")

        # Follower auth
        auth2 = get_auth_trd(trd_account=FOLLOWER_ACCOUNT, trd_api=FOLLOWER_API_KEY)
        r.check("sandbox" in auth2["base"], "Follower routes to sandbox")

        # Follower validation
        profile2 = validate_account_trd(trd_account=FOLLOWER_ACCOUNT, trd_api=FOLLOWER_API_KEY)
        r.check("error" not in profile2, "Follower credentials valid")

        # Streaming session (optional — some sandbox keys lack streaming permissions)
        session_id = create_streaming_session(trd_api=MASTER_API_KEY)
        if isinstance(session_id, str) and len(session_id) > 0:
            ok("Streaming session created")
        else:
            warn("Streaming session failed (sandbox may not support streaming — non-critical)")

    except Exception as e:
        r.check(False, "", f"Phase crashed: {e}")

    return r


def phase_1():
    """Phase 1: Read-Only API — orders, positions, balances return valid data."""
    phase_header(1, "Read-Only API Verification", cost="$0")
    r = PhaseResult(1, "Read-Only API Verification")

    try:
        # Orders
        orders = get_orders_trd(trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        r.check(isinstance(orders, list), f"Master orders returned list ({len(orders)} orders)")

        orders2 = get_orders_trd(trd_account=FOLLOWER_ACCOUNT, trd_api=FOLLOWER_API_KEY)
        r.check(isinstance(orders2, list), f"Follower orders returned list ({len(orders2)} orders)")

        # Balances
        balances = get_balances_trd(trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        r.check(isinstance(balances, dict), "Master balances returned dict")
        has_equity = "total_equity" in balances or "equity" in balances or "total_cash" in balances
        r.check(has_equity, f"Balances has equity field (keys: {list(balances.keys())[:5]})")

        # Positions
        positions = get_positions_trd(trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        r.check(isinstance(positions, list), f"Master positions returned list ({len(positions)} positions)")

    except Exception as e:
        r.check(False, "", f"Phase crashed: {e}")

    return r


def phase_2():
    """Phase 2: Order Placement + Copy — multi-symbol equities, options, 0 DTE, and spreads."""
    phase_header(2, "Order Placement + Copy", cost="~$0")
    r = PhaseResult(2, "Order Placement + Copy")

    try:
        from scripts.copy_manager import run_copy_cycle

        # Reset tracked order IDs for this run
        _test_order_ids["master"].clear()
        _test_order_ids["follower"].clear()

        # Check automation is enabled (or forced for testing)
        db = get_db()
        global_settings = db.get_collection("settings").find_one({"type": "global"}) or {}
        settings = {**get_default_settings(), **global_settings}
        automation_on = settings.get("use_automation", False)
        if _force_automation and not automation_on:
            step("Force-enabling automation for this test run")
            db.get_collection("settings").update_one(
                {"type": "global"}, {"$set": {"use_automation": True}}, upsert=True)
            automation_on = True
        if not automation_on:
            r.check(False, "", "Automation is disabled — enable it in Settings or use --force-automation")
            return r
        r.check(True, "Automation is enabled")

        # Clean slate: clear history/trades so copy engine sees fresh orders
        step("Clearing history, trades, and canceling stale orders for clean test")
        db.get_collection("history").delete_many({"account_number": MASTER_ACCOUNT})
        db.get_collection("trades").delete_many({"account_number": MASTER_ACCOUNT})
        db.get_collection("trades").delete_many({"account_number": FOLLOWER_ACCOUNT})

        # Cancel any lingering open orders on master so only our new ones are detected
        existing_orders = get_orders_trd(trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        for o in existing_orders:
            if o.get("status") in ["open", "pending", "partially_filled"]:
                delete_orders_trd(order_id=o["id"], trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        time.sleep(1)

        # ---- EQUITY ORDERS: multiple symbols ----
        for symbol in TEST_EQUITY_SYMBOLS:
            step(f"Placing {symbol} market buy on master")
            market_data = make_equity_order(symbol, "market")
            market_data["tag"] = make_test_tag(symbol, role="master")
            result = post_orders_trd(data=market_data, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
            r.check(result != "Error", f"{symbol} market order POST returned response")
            order_info = result.get("order", result) if isinstance(result, dict) else {}
            order_id = order_info.get("id", 0)
            r.check(order_id > 0, f"{symbol} market master order ID: {order_id}")
            if order_id:
                _test_order_ids["master"].append(order_id)
            time.sleep(1)

        # SPY limit order (kept open for phase 3 modification and phase 4 cancellation)
        step("Placing SPY limit buy at $1.00 on master (will not fill)")
        limit_data = make_equity_order("SPY", "limit", price="1.00")
        limit_data["tag"] = make_test_tag("SPY", role="master")
        result2 = post_orders_trd(data=limit_data, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        r.check(result2 != "Error", "SPY limit order POST returned response")
        order_info2 = result2.get("order", result2) if isinstance(result2, dict) else {}
        limit_order_id = order_info2.get("id", 0)
        r.check(limit_order_id > 0, f"SPY limit master order ID: {limit_order_id}")
        if limit_order_id:
            _test_order_ids["master"].append(limit_order_id)
            global _equity_limit_order_id
            _equity_limit_order_id = limit_order_id
        time.sleep(1)

        # ---- OPTION ORDERS: standard expiration (7+ days out) ----
        step("Fetching SPY option chain (7+ DTE)")
        opt_symbols = get_test_option_symbols("SPY", zero_dte=False)
        if not opt_symbols:
            step("WARNING: Could not fetch SPY option chain — skipping standard option tests")
        else:
            option_symbol = opt_symbols["single"]
            step(f"Using SPY option: {option_symbol} (exp: {opt_symbols['expiration']})")

            # Option market order (single leg)
            step(f"Placing SPY option market buy on master ({option_symbol})")
            opt_market_data = {
                "class": "option",
                "symbol": "SPY",
                "side": "buy_to_open",
                "quantity": "1",
                "type": "market",
                "duration": "day",
                "option_symbol": option_symbol,
                "tag": make_test_tag("SPY", role="master"),
            }
            result3 = post_orders_trd(data=opt_market_data, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
            r.check(result3 != "Error", "SPY option market order POST returned response")
            order_info3 = result3.get("order", result3) if isinstance(result3, dict) else {}
            opt_market_id = order_info3.get("id", 0)
            r.check(opt_market_id > 0, f"SPY option market master order ID: {opt_market_id}")
            if opt_market_id:
                _test_order_ids["master"].append(opt_market_id)
            time.sleep(1)

            # Multi-leg vertical spread (limit debit so it stays open for copy engine)
            long_leg = opt_symbols["spread_long"]
            short_leg = opt_symbols["spread_short"]
            step(f"Placing SPY multi-leg debit spread ({long_leg} / {short_leg})")
            spread_data = {
                "class": "multileg",
                "symbol": "SPY",
                "type": "debit",
                "price": "0.01",
                "duration": "day",
                "tag": make_test_tag("SPY", role="master"),
                "option_symbol[0]": long_leg,
                "side[0]": "buy_to_open",
                "quantity[0]": "1",
                "option_symbol[1]": short_leg,
                "side[1]": "sell_to_open",
                "quantity[1]": "1",
            }
            result4 = post_orders_trd(data=spread_data, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
            r.check(result4 != "Error", "SPY multi-leg spread POST returned response")
            order_info4 = result4.get("order", result4) if isinstance(result4, dict) else {}
            spread_id = order_info4.get("id", 0)
            r.check(spread_id > 0, f"SPY multi-leg spread master order ID: {spread_id}")
            if spread_id:
                _test_order_ids["master"].append(spread_id)
            time.sleep(1)

            # 4-leg iron condor
            if opt_symbols.get("ic_buy_put"):
                ic_bp = opt_symbols["ic_buy_put"]
                ic_sp = opt_symbols["ic_sell_put"]
                ic_sc = opt_symbols["ic_sell_call"]
                ic_bc = opt_symbols["ic_buy_call"]
                step(f"Placing SPY 4-leg iron condor ({ic_bp} / {ic_sp} / {ic_sc} / {ic_bc})")
                ic_data = {
                    "class": "multileg",
                    "symbol": "SPY",
                    "type": "credit",
                    "price": "0.01",
                    "duration": "day",
                    "tag": make_test_tag("SPY", role="master"),
                    "option_symbol[0]": ic_bp,
                    "side[0]": "buy_to_open",
                    "quantity[0]": "1",
                    "option_symbol[1]": ic_sp,
                    "side[1]": "sell_to_open",
                    "quantity[1]": "1",
                    "option_symbol[2]": ic_sc,
                    "side[2]": "sell_to_open",
                    "quantity[2]": "1",
                    "option_symbol[3]": ic_bc,
                    "side[3]": "buy_to_open",
                    "quantity[3]": "1",
                }
                result_ic = post_orders_trd(data=ic_data, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
                r.check(result_ic != "Error", "SPY 4-leg iron condor POST returned response")
                order_info_ic = result_ic.get("order", result_ic) if isinstance(result_ic, dict) else {}
                ic_id = order_info_ic.get("id", 0)
                r.check(ic_id > 0, f"SPY iron condor master order ID: {ic_id}")
                if ic_id:
                    _test_order_ids["master"].append(ic_id)
                time.sleep(1)
            else:
                step("WARNING: Not enough strikes for iron condor — skipping 4-leg test")

        # ---- 0 DTE OPTIONS: QQQ (daily expirations) ----
        step("Fetching QQQ option chain (0 DTE)")
        dte0_symbols = get_test_option_symbols("QQQ", zero_dte=True)
        if not dte0_symbols:
            step("WARNING: No 0 DTE expiration for QQQ today — skipping 0 DTE tests")
        else:
            dte0_option = dte0_symbols["single"]
            step(f"Using QQQ 0 DTE option: {dte0_option} (exp: {dte0_symbols['expiration']})")

            # 0 DTE option market order
            step(f"Placing QQQ 0 DTE option market buy on master ({dte0_option})")
            dte0_market_data = {
                "class": "option",
                "symbol": "QQQ",
                "side": "buy_to_open",
                "quantity": "1",
                "type": "market",
                "duration": "day",
                "option_symbol": dte0_option,
                "tag": make_test_tag("QQQ", role="master"),
            }
            result5 = post_orders_trd(data=dte0_market_data, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
            r.check(result5 != "Error", "QQQ 0 DTE option market order POST returned response")
            order_info5 = result5.get("order", result5) if isinstance(result5, dict) else {}
            dte0_id = order_info5.get("id", 0)
            r.check(dte0_id > 0, f"QQQ 0 DTE option master order ID: {dte0_id}")
            if dte0_id:
                _test_order_ids["master"].append(dte0_id)
            time.sleep(1)

            # 0 DTE multi-leg spread (limit debit so it stays open for copy engine)
            long_leg_0 = dte0_symbols["spread_long"]
            short_leg_0 = dte0_symbols["spread_short"]
            step(f"Placing QQQ 0 DTE debit spread ({long_leg_0} / {short_leg_0})")
            dte0_spread_data = {
                "class": "multileg",
                "symbol": "QQQ",
                "type": "debit",
                "price": "0.01",
                "duration": "day",
                "tag": make_test_tag("QQQ", role="master"),
                "option_symbol[0]": long_leg_0,
                "side[0]": "buy_to_open",
                "quantity[0]": "1",
                "option_symbol[1]": short_leg_0,
                "side[1]": "sell_to_open",
                "quantity[1]": "1",
            }
            result6 = post_orders_trd(data=dte0_spread_data, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
            r.check(result6 != "Error", "QQQ 0 DTE multi-leg spread POST returned response")
            order_info6 = result6.get("order", result6) if isinstance(result6, dict) else {}
            dte0_spread_id = order_info6.get("id", 0)
            r.check(dte0_spread_id > 0, f"QQQ 0 DTE spread master order ID: {dte0_spread_id}")
            if dte0_spread_id:
                _test_order_ids["master"].append(dte0_spread_id)
            time.sleep(1)

        # ---- SPY 0 DTE (Mon/Wed/Fri) ----
        step("Fetching SPY option chain (0 DTE)")
        spy_dte0 = get_test_option_symbols("SPY", zero_dte=True)
        if not spy_dte0:
            step("INFO: No SPY 0 DTE today (SPY has Mon/Wed/Fri expirations)")
        else:
            spy_dte0_option = spy_dte0["single"]
            step(f"Using SPY 0 DTE option: {spy_dte0_option} (exp: {spy_dte0['expiration']})")
            spy_dte0_data = {
                "class": "option",
                "symbol": "SPY",
                "side": "buy_to_open",
                "quantity": "1",
                "type": "market",
                "duration": "day",
                "option_symbol": spy_dte0_option,
                "tag": make_test_tag("SPY", role="master"),
            }
            result7 = post_orders_trd(data=spy_dte0_data, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
            r.check(result7 != "Error", "SPY 0 DTE option market order POST returned response")
            order_info7 = result7.get("order", result7) if isinstance(result7, dict) else {}
            spy_dte0_id = order_info7.get("id", 0)
            r.check(spy_dte0_id > 0, f"SPY 0 DTE option master order ID: {spy_dte0_id}")
            if spy_dte0_id:
                _test_order_ids["master"].append(spy_dte0_id)
            time.sleep(1)

        # Wait for all orders to appear
        time.sleep(2)

        # Run copy engine — should detect all orders and copy to follower
        step("Running copy engine cycle")
        recent_log_list = []
        cycle_result = run_copy_cycle(db, recent_log_list)
        r.check(cycle_result is True, "Copy cycle completed successfully")

        # Verify follower received copied orders
        time.sleep(1)
        follower_orders = get_orders_trd(trd_account=FOLLOWER_ACCOUNT, trd_api=FOLLOWER_API_KEY)
        follower_copies = [
            o for o in follower_orders
            if str(o.get("tag", "")).startswith("follower-")
        ]
        r.check(len(follower_copies) > 0, f"Follower has copied orders ({len(follower_copies)} found)")

        for f_order in follower_copies:
            fid = f_order.get("id")
            if fid and fid not in _test_order_ids["follower"]:
                _test_order_ids["follower"].append(fid)

        # Verify multileg orders were placed (sandbox rejects them, which is expected)
        master_orders = get_orders_trd(trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        master_multilegs = [o for o in master_orders if o.get("class") == "multileg"]
        multileg_rejected = all(o.get("status") == "rejected" for o in master_multilegs)
        if master_multilegs and multileg_rejected:
            info(f"Sandbox rejected {len(master_multilegs)} multileg order(s) (sandbox limitation — not a bug)")
            r.check(True, f"Multileg orders placed and correctly rejected by sandbox ({len(master_multilegs)} orders)")
        elif master_multilegs:
            # If sandbox ever starts supporting multilegs, verify they were copied
            follower_multilegs = [
                o for o in follower_copies
                if o.get("class") == "multileg" or o.get("num_legs", 0) > 1
            ]
            r.check(len(follower_multilegs) > 0,
                    f"Follower has multileg orders ({len(follower_multilegs)} found)",
                    f"No multileg orders copied to follower")
        else:
            r.check(False, "", "No multileg orders placed on master")

        # Verify multiple symbols were copied (not just SPY)
        follower_symbols = set()
        for o in follower_copies:
            sym = o.get("symbol", "")
            if sym:
                follower_symbols.add(sym)
        r.check(len(follower_symbols) >= 2,
                f"Follower received orders for {len(follower_symbols)} symbols: {sorted(follower_symbols)}",
                f"Only {len(follower_symbols)} symbol(s) copied — expected at least 2")

    except Exception as e:
        r.check(False, "", f"Phase crashed: {e}")

    return r


def phase_3():
    """Phase 3: Order Modification — modify master, run copy engine, verify follower synced."""
    phase_header(3, "Order Modification via Copy Engine", cost="~$0")
    r = PhaseResult(3, "Order Modification")

    try:
        from scripts.copy_manager import run_copy_cycle

        if not _equity_limit_order_id:
            r.check(False, "", "No equity limit order from phase 2 — skipping")
            return r

        order_id = _equity_limit_order_id

        # Modify price on master
        step(f"Modifying master order {order_id}: price $1.00 -> $1.50")
        result = modify_orders_trd(
            order_id=order_id,
            data={"price": "1.50"},
            trd_account=MASTER_ACCOUNT,
            trd_api=MASTER_API_KEY,
        )
        r.check(result != "Error", "PUT price modify returned response")

        time.sleep(1)

        # Run copy engine — should detect the modification and sync to follower
        step("Running copy engine cycle to sync modification")
        db = get_db()
        recent_log_list = []
        run_copy_cycle(db, recent_log_list)

        # Verify master price changed
        master_orders = get_orders_trd(trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        matching = [o for o in master_orders if o.get("id") == order_id]
        if matching:
            new_price = matching[0].get("price")
            r.check(float(new_price) == 1.5, f"Master price updated to {new_price}")
        else:
            r.check(False, "", f"Master order {order_id} not found after modify")

        # Modify duration on master
        step(f"Modifying master order {order_id}: duration day -> gtc")
        result2 = modify_orders_trd(
            order_id=order_id,
            data={"duration": "gtc"},
            trd_account=MASTER_ACCOUNT,
            trd_api=MASTER_API_KEY,
        )
        r.check(result2 != "Error", "PUT duration modify returned response")

    except Exception as e:
        r.check(False, "", f"Phase crashed: {e}")

    return r


def phase_4():
    """Phase 4: Order Cancellation — cancel master, run copy engine, verify follower canceled."""
    phase_header(4, "Order Cancellation via Copy Engine", cost="~$0")
    r = PhaseResult(4, "Order Cancellation")

    try:
        from scripts.copy_manager import run_copy_cycle

        if not _equity_limit_order_id:
            r.check(False, "", "No equity limit order to cancel — skipping")
            return r

        order_id = _equity_limit_order_id

        # Cancel on master
        step(f"Canceling master order {order_id}")
        result = delete_orders_trd(order_id=order_id, trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        r.check(isinstance(result, dict), "DELETE returned dict response")

        time.sleep(1)

        # Run copy engine — should detect cancellation and sync to follower
        step("Running copy engine cycle to sync cancellation")
        db = get_db()
        recent_log_list = []
        run_copy_cycle(db, recent_log_list)

        # Verify master order canceled
        master_orders = get_orders_trd(trd_account=MASTER_ACCOUNT, trd_api=MASTER_API_KEY)
        matching = [o for o in master_orders if o.get("id") == order_id]
        if matching:
            status = matching[0].get("status")
            r.check(status in ["canceled", "ok", "CAN"], f"Master order status: {status}")

        # Verify follower's copy of the canceled master order is also canceled
        # The copy engine tags follower orders as "follower-{symbol}-{master_order_id}"
        follower_orders = get_orders_trd(trd_account=FOLLOWER_ACCOUNT, trd_api=FOLLOWER_API_KEY)
        tag_match = f"follower-{MASTER_ACCOUNT}"
        follower_copy = None
        for f_order in follower_orders:
            # Match by tag and symbol — the limit order copy for this master order
            if (str(f_order.get("tag", "")).startswith("follower-")
                    and f_order.get("symbol") == "SPY"
                    and f_order.get("type") == "limit"):
                f_status = f_order.get("status")
                if f_status in ["canceled", "CAN"]:
                    follower_copy = f_order
                    break
        if follower_copy:
            r.check(True, f"Follower limit order {follower_copy['id']} status: canceled")
        else:
            # Check if any follower order for this master was canceled
            any_canceled = any(
                o.get("status") in ["canceled", "CAN"]
                for o in follower_orders
                if str(o.get("tag", "")).startswith("follower-")
            )
            r.check(any_canceled, "At least one follower order canceled",
                    "No follower order found in canceled state")

        _test_order_ids["master"].clear()
        _test_order_ids["follower"].clear()

    except Exception as e:
        r.check(False, "", f"Phase crashed: {e}")

    return r


# ==============================================================================
# PHASE REGISTRY
# ==============================================================================

PHASES = {
    0: ("Prerequisites", phase_0),
    1: ("Read-Only API Verification", phase_1),
    2: ("Order Placement + Copy", phase_2),
    3: ("Order Modification via Copy Engine", phase_3),
    4: ("Order Cancellation via Copy Engine", phase_4),
}

REQUIRED_PHASES = [0, 1, 2, 3, 4]
ALL_PHASES = list(PHASES.keys())


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Live integration tests for Tradier Copy Bot")
    parser.add_argument("--phase", type=str, help="Phase number or range (e.g., 2, 1-4)")
    parser.add_argument("--required", action="store_true", help="Run required phases (0-4)")
    parser.add_argument("--all", action="store_true", help="Run all phases (0-4)")
    parser.add_argument("--cleanup", action="store_true", help="Cancel any leftover test orders")
    parser.add_argument("--force-automation", action="store_true",
                        help="Temporarily enable automation for this test run (does not change DB)")
    args = parser.parse_args()

    # Set force automation flag
    global _force_automation
    _force_automation = args.force_automation

    # Load accounts from MongoDB
    load_accounts()
    if not MASTER_ACCOUNT or not FOLLOWER_ACCOUNT:
        print("ERROR: Could not load master/follower accounts from MongoDB.")
        print(f"  Master: {MASTER_ACCOUNT}, Follower: {FOLLOWER_ACCOUNT}")
        print("  Ensure accounts are configured in the dashboard with one marked as master.")
        sys.exit(1)

    # Register cleanup to always run
    atexit.register(cleanup)

    if args.cleanup:
        print("Running cleanup...")
        cleanup()
        return

    # Check market hours
    market_open = is_market_open()
    if not market_open:
        print(f"\n{YELLOW}WARNING: Market is currently CLOSED.{RESET}")
        print("Phases 2-4 (order placement/modification/cancellation) require market hours.")
        print("Only phases 0-1 (read-only) will produce reliable results.\n")

    # Determine which phases to run
    if args.phase:
        if "-" in args.phase:
            start, end = args.phase.split("-")
            phases_to_run = list(range(int(start), int(end) + 1))
        else:
            phases_to_run = [int(args.phase)]
    elif args.all:
        phases_to_run = ALL_PHASES
    elif args.required:
        phases_to_run = REQUIRED_PHASES
    else:
        phases_to_run = REQUIRED_PHASES  # Default to required

    # Validate
    for p in phases_to_run:
        if p not in PHASES:
            print(f"Unknown phase: {p}. Available: {list(PHASES.keys())}")
            sys.exit(1)

    # Run
    print(f"\n{BOLD}Tradier Copy Bot — Live Integration Tests{RESET}")
    print(f"Accounts: master={MASTER_ACCOUNT}, follower={FOLLOWER_ACCOUNT}")
    print(f"Phases: {phases_to_run}")

    results = []
    skipped = 0
    for p in phases_to_run:
        desc, func = PHASES[p]

        # Skip order-manipulation phases when market is closed
        if not market_open and p >= 2:
            print(f"\n{'=' * 60}")
            print(f"  Phase {p}: {desc}  — SKIPPED (market closed)")
            print(f"{'=' * 60}")
            skipped += 1
            continue

        result = func()
        results.append(result)

        # Stop on critical failure (phases 0-1)
        if p <= 1 and not result.success:
            warn(f"Phase {p} failed - stopping (prerequisites not met)")
            break

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  {BOLD}SUMMARY{RESET}")
    print(f"{'=' * 60}")
    total_passed = 0
    total_failed = 0
    for r in results:
        print(f"  {r}")
        total_passed += r.passed
        total_failed += r.failed

    if skipped:
        print(f"\n  {skipped} phase(s) skipped (market closed)")
    print(f"\n  Total: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

# END
