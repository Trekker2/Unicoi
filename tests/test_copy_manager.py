"""
Copy Manager Unit Tests for Tradier Copy Bot

Tests the core copy engine logic: order reconstruction, copy cycle orchestration,
order detection, forwarding, cancellation sync, and stale handling.

Consolidated from test_copy_engine.py and test_copy_manager.py.

Test Coverage:
    - reconstruct_multileg_order: Multi-leg order reconstruction
    - reconstruct_single_order: Single-leg order reconstruction
    - Order data format validation (quantity as string, tag format)
    - get_master_account / get_follower_accounts: DB queries
    - get_new_master_orders: Order detection and deduplication
    - forward_order_to_follower: Stale checks, dedup, order posting
    - check_master_cancellations: Cancel sync from master to followers
    - check_master_modifications: Price/duration/quantity modification sync
    - _cancel_and_replace: Cancel + replace for quantity changes
    - run_copy_cycle: Full orchestration
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt
import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.copy_manager import (
    get_master_account, get_follower_accounts, get_new_master_orders,
    reconstruct_multileg_order, reconstruct_single_order,
    forward_order_to_follower, check_master_cancellations,
    check_master_modifications, _cancel_and_replace,
    run_copy_cycle,
)
from constants import DEFAULT_STALE_TIMEOUT, market_timezone, utc_timezone


# ==============================================================================
# TEST DATA
# ==============================================================================

MASTER_ACCOUNT = {
    "account_number": "VA111111",
    "api_key": "master-key",
    "alias": "Master",
    "is_master": True,
}

FOLLOWER_ACCOUNT = {
    "account_number": "VA222222",
    "api_key": "follower-key",
    "alias": "Follower1",
    "is_master": False,
}

SAMPLE_MULTILEG_ORDER = {
    "id": 12345,
    "class": "multileg",
    "symbol": "SPX",
    "duration": "day",
    "type": "credit",
    "status": "filled",
    "leg": [
        {
            "option_symbol": "SPX250319C05000000",
            "side": "sell_to_open",
            "quantity": 1,
        },
        {
            "option_symbol": "SPX250319C05050000",
            "side": "buy_to_open",
            "quantity": 1,
        },
    ],
}

SAMPLE_SINGLE_ORDER = {
    "id": 67890,
    "class": "equity",
    "symbol": "SPY",
    "duration": "day",
    "side": "buy",
    "quantity": 100,
    "type": "market",
    "status": "filled",
}

SAMPLE_OPTION_ORDER = {
    "id": 11111,
    "class": "option",
    "symbol": "SPY",
    "duration": "day",
    "side": "buy_to_open",
    "quantity": 5,
    "type": "limit",
    "price": 2.50,
    "option_symbol": "SPY250321C00500000",
    "status": "filled",
}

SAMPLE_ORDER = {
    "id": 99999,
    "class": "equity",
    "symbol": "SPY",
    "duration": "day",
    "side": "buy",
    "quantity": 10,
    "type": "market",
    "status": "filled",
    "create_date": dt.datetime.now(tz=utc_timezone).isoformat(),
}


# ==============================================================================
# TESTS
# ==============================================================================

class TestReconstructMultilegOrder(unittest.TestCase):
    """Test multi-leg order reconstruction -- 3 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestReconstructMultilegOrder completed in {elapsed:.2f} seconds")

    def test_basic_multileg(self):
        """Should produce correct indexed notation."""
        data = reconstruct_multileg_order(SAMPLE_MULTILEG_ORDER, multiplier=1)
        self.assertEqual(data["class"], "multileg")
        self.assertEqual(data["symbol"], "SPX")
        self.assertEqual(data["type"], "market")
        self.assertEqual(data["tag"], "follower-SPX-12345")
        self.assertEqual(data["option_symbol[0]"], "SPX250319C05000000")
        self.assertEqual(data["side[0]"], "sell_to_open")
        self.assertEqual(data["quantity[0]"], "1")
        self.assertEqual(data["option_symbol[1]"], "SPX250319C05050000")
        self.assertEqual(data["side[1]"], "buy_to_open")
        self.assertEqual(data["quantity[1]"], "1")

    def test_multileg_multiplier(self):
        """Multiplier should scale all leg quantities."""
        data = reconstruct_multileg_order(SAMPLE_MULTILEG_ORDER, multiplier=3)
        self.assertEqual(data["quantity[0]"], "3")
        self.assertEqual(data["quantity[1]"], "3")

    def test_multileg_has_duration(self):
        """Should preserve duration from master order."""
        data = reconstruct_multileg_order(SAMPLE_MULTILEG_ORDER)
        self.assertEqual(data["duration"], "day")


class TestReconstructSingleOrder(unittest.TestCase):
    """Test single-leg order reconstruction -- 5 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestReconstructSingleOrder completed in {elapsed:.2f} seconds")

    def test_equity_order(self):
        """Should produce correct equity order data."""
        data = reconstruct_single_order(SAMPLE_SINGLE_ORDER, multiplier=1)
        self.assertEqual(data["class"], "equity")
        self.assertEqual(data["symbol"], "SPY")
        self.assertEqual(data["side"], "buy")
        self.assertEqual(data["quantity"], "100")
        self.assertEqual(data["type"], "market")
        self.assertEqual(data["tag"], "follower-SPY-67890")

    def test_equity_multiplier(self):
        """Multiplier should scale quantity."""
        data = reconstruct_single_order(SAMPLE_SINGLE_ORDER, multiplier=2)
        self.assertEqual(data["quantity"], "200")

    def test_option_order(self):
        """Should include option_symbol for option orders."""
        data = reconstruct_single_order(SAMPLE_OPTION_ORDER, multiplier=1)
        self.assertEqual(data["class"], "option")
        self.assertEqual(data["option_symbol"], "SPY250321C00500000")
        self.assertEqual(data["quantity"], "5")

    def test_limit_order_price(self):
        """Limit orders should include price."""
        data = reconstruct_single_order(SAMPLE_OPTION_ORDER)
        self.assertIn("price", data)
        self.assertEqual(data["price"], 2.50)

    def test_market_order_no_price(self):
        """Market orders should not include price."""
        data = reconstruct_single_order(SAMPLE_SINGLE_ORDER)
        self.assertNotIn("price", data)


class TestOrderFormatting(unittest.TestCase):
    """Test order data format requirements -- 3 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestOrderFormatting completed in {elapsed:.2f} seconds")

    def test_quantity_is_string(self):
        """Tradier requires quantity as string."""
        data = reconstruct_single_order(SAMPLE_SINGLE_ORDER)
        self.assertIsInstance(data["quantity"], str)

    def test_multileg_quantity_is_string(self):
        """Multi-leg quantities should be strings."""
        data = reconstruct_multileg_order(SAMPLE_MULTILEG_ORDER)
        self.assertIsInstance(data["quantity[0]"], str)
        self.assertIsInstance(data["quantity[1]"], str)

    def test_tag_format(self):
        """Tag should be follower-{id} format."""
        data = reconstruct_single_order(SAMPLE_SINGLE_ORDER)
        self.assertTrue(data["tag"].startswith("follower-"))


class TestGetMasterAccount(unittest.TestCase):
    """Tests for get_master_account() -- 2 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestGetMasterAccount completed in {elapsed:.2f} seconds")

    def test_returns_master_when_exists(self):
        """Should return the master account document."""
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = MASTER_ACCOUNT
        result = get_master_account(mock_db)
        self.assertEqual(result["account_number"], "VA111111")
        self.assertTrue(result["is_master"])

    def test_returns_none_when_no_master(self):
        """Should return None when no master account exists."""
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = None
        result = get_master_account(mock_db)
        self.assertIsNone(result)


class TestGetFollowerAccounts(unittest.TestCase):
    """Tests for get_follower_accounts() -- 2 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestGetFollowerAccounts completed in {elapsed:.2f} seconds")

    def test_returns_followers(self):
        """Should return list of non-master accounts."""
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find.return_value = [FOLLOWER_ACCOUNT]
        result = get_follower_accounts(mock_db)
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0].get("is_master"))

    def test_returns_empty_when_no_followers(self):
        """Should return empty list when no followers exist."""
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find.return_value = []
        result = get_follower_accounts(mock_db)
        self.assertEqual(result, [])


class TestGetNewMasterOrders(unittest.TestCase):
    """Tests for get_new_master_orders() -- 4 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestGetNewMasterOrders completed in {elapsed:.2f} seconds")

    @patch("scripts.copy_manager.get_orders_trd")
    def test_returns_new_orders(self, mock_get_orders):
        """Should return orders not in history or trades."""
        mock_get_orders.return_value = [SAMPLE_ORDER]
        mock_db = MagicMock()

        def find_one_side_effect(filter_dict):
            return None  # No history or trades

        mock_db.get_collection.return_value.find_one = find_one_side_effect
        result = get_new_master_orders(mock_db, MASTER_ACCOUNT)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 99999)

    @patch("scripts.copy_manager.get_orders_trd")
    def test_filters_bad_statuses(self, mock_get_orders):
        """Should exclude orders with bad statuses."""
        bad_order = {**SAMPLE_ORDER, "id": 11111, "status": "canceled"}
        mock_get_orders.return_value = [SAMPLE_ORDER, bad_order]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = None

        result = get_new_master_orders(mock_db, MASTER_ACCOUNT)
        ids = [o["id"] for o in result]
        self.assertIn(99999, ids)
        self.assertNotIn(11111, ids)

    @patch("scripts.copy_manager.get_orders_trd")
    def test_deduplicates_against_history(self, mock_get_orders):
        """Should exclude orders already in history."""
        mock_get_orders.return_value = [SAMPLE_ORDER]
        mock_db = MagicMock()

        call_count = [0]
        def find_one_side_effect(filter_dict=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # history collection
                return {"history": [{"id": 99999}]}
            return None  # trades collection

        mock_db.get_collection.return_value.find_one = find_one_side_effect
        result = get_new_master_orders(mock_db, MASTER_ACCOUNT)
        self.assertEqual(len(result), 0)

    @patch("scripts.copy_manager.get_orders_trd")
    def test_empty_when_no_orders(self, mock_get_orders):
        """Should return empty list when master has no orders."""
        mock_get_orders.return_value = []
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = None

        result = get_new_master_orders(mock_db, MASTER_ACCOUNT)
        self.assertEqual(result, [])


class TestForwardOrderToFollower(unittest.TestCase):
    """Tests for forward_order_to_follower() -- 4 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestForwardOrderToFollower completed in {elapsed:.2f} seconds")

    @patch("scripts.copy_manager.post_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_successful_forward(self, mock_print_store, mock_post):
        """Should post order and store in trades collection."""
        mock_post.return_value = {"order": {"id": 55555, "status": "pending"}}
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = None

        settings = {"stale_timeout": 5}
        order_data = {"class": "equity", "symbol": "SPY", "side": "buy", "quantity": "10", "type": "market"}

        result = forward_order_to_follower(
            mock_db, SAMPLE_ORDER, FOLLOWER_ACCOUNT, order_data, settings, []
        )
        self.assertIsNotNone(result)
        mock_post.assert_called_once()

    @patch("scripts.copy_manager.post_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_skips_stale_order(self, mock_print_store, mock_post):
        """Should skip orders older than stale timeout."""
        stale_order = {**SAMPLE_ORDER}
        stale_order["create_date"] = (dt.datetime.now(tz=utc_timezone) - dt.timedelta(minutes=10)).isoformat()

        mock_db = MagicMock()
        settings = {"stale_timeout": 5}

        result = forward_order_to_follower(
            mock_db, stale_order, FOLLOWER_ACCOUNT, {}, settings, []
        )
        self.assertIsNone(result)
        mock_post.assert_not_called()

    @patch("scripts.copy_manager.post_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_skips_duplicate(self, mock_print_store, mock_post):
        """Should skip if follower already has trade for this master order."""
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {
            "trades": [{"master_id": 99999}]
        }
        settings = {"stale_timeout": 5}

        result = forward_order_to_follower(
            mock_db, SAMPLE_ORDER, FOLLOWER_ACCOUNT, {}, settings, []
        )
        self.assertIsNone(result)
        mock_post.assert_not_called()

    @patch("scripts.copy_manager.post_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_returns_none_on_error(self, mock_print_store, mock_post):
        """Should return None when API returns error."""
        mock_post.return_value = "Error"
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = None
        settings = {"stale_timeout": 5}

        result = forward_order_to_follower(
            mock_db, SAMPLE_ORDER, FOLLOWER_ACCOUNT, {}, settings, []
        )
        self.assertIsNone(result)


class TestCheckMasterCancellations(unittest.TestCase):
    """Tests for check_master_cancellations() -- 3 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestCheckMasterCancellations completed in {elapsed:.2f} seconds")

    @patch("scripts.copy_manager.delete_orders_trd")
    def test_cancels_matching_follower_orders(self, mock_delete):
        """Should cancel follower orders when master order is canceled."""
        master_orders = [{"id": 99999, "status": "canceled"}]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {
            "trades": [{"master_id": 99999, "id": 55555, "status": "open"}]
        }

        check_master_cancellations(mock_db, master_orders, [FOLLOWER_ACCOUNT])
        mock_delete.assert_called_once()

    @patch("scripts.copy_manager.delete_orders_trd")
    def test_no_cancel_if_no_cancellations(self, mock_delete):
        """Should not cancel anything if master has no canceled orders."""
        master_orders = [{"id": 99999, "status": "filled"}]
        mock_db = MagicMock()

        check_master_cancellations(mock_db, master_orders, [FOLLOWER_ACCOUNT])
        mock_delete.assert_not_called()

    @patch("scripts.copy_manager.delete_orders_trd")
    def test_no_cancel_if_follower_already_filled(self, mock_delete):
        """Should not cancel follower order that's already filled."""
        master_orders = [{"id": 99999, "status": "canceled"}]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {
            "trades": [{"master_id": 99999, "id": 55555, "status": "filled"}]
        }

        check_master_cancellations(mock_db, master_orders, [FOLLOWER_ACCOUNT])
        mock_delete.assert_not_called()


class TestCheckMasterModifications(unittest.TestCase):
    """Tests for check_master_modifications() -- 7 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestCheckMasterModifications completed in {elapsed:.2f} seconds")

    def _make_open_trade(self, master_id=10001, child_id=55555, price=1.50, duration="day", quantity=10):
        """Helper to build an open follower trade with snapshots."""
        return {
            "id": child_id,
            "master_id": master_id,
            "status": "open",
            "master_snapshot": {
                "price": price, "stop": None, "duration": duration,
                "type": "limit", "quantity": quantity,
            },
            "copied_fields": {
                "price": price, "stop": None, "duration": duration,
                "type": "limit", "quantity": str(quantity),
            },
        }

    @patch("scripts.copy_manager.modify_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_modifies_price(self, mock_ps, mock_modify):
        """Should call modify_orders_trd when master price changes."""
        mock_modify.return_value = {"order": {"id": 55555, "status": "ok"}}
        master_orders = [{"id": 10001, "status": "open", "price": 1.75, "stop": None, "duration": "day", "type": "limit", "quantity": 10}]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {
            "trades": [self._make_open_trade(price=1.50)]
        }
        settings = {"multipliers": {"VA222222": 1}}

        check_master_modifications(mock_db, master_orders, [FOLLOWER_ACCOUNT], settings)
        mock_modify.assert_called_once()
        call_data = mock_modify.call_args[1]["data"]
        self.assertEqual(call_data["price"], 1.75)

    @patch("scripts.copy_manager.modify_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_modifies_duration(self, mock_ps, mock_modify):
        """Should call modify when master duration changes."""
        mock_modify.return_value = {"order": {"id": 55555, "status": "ok"}}
        master_orders = [{"id": 10001, "status": "open", "price": 1.50, "stop": None, "duration": "gtc", "type": "limit", "quantity": 10}]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {
            "trades": [self._make_open_trade(duration="day")]
        }
        settings = {"multipliers": {"VA222222": 1}}

        check_master_modifications(mock_db, master_orders, [FOLLOWER_ACCOUNT], settings)
        mock_modify.assert_called_once()
        self.assertEqual(mock_modify.call_args[1]["data"]["duration"], "gtc")

    @patch("scripts.copy_manager.post_orders_trd")
    @patch("scripts.copy_manager.delete_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_cancel_replace_on_quantity_change(self, mock_ps, mock_delete, mock_post):
        """Should cancel+replace when master quantity changes."""
        mock_post.return_value = {"order": {"id": 66666, "status": "pending"}}
        master_orders = [{"id": 10001, "status": "open", "class": "equity", "symbol": "AAPL",
                          "side": "buy", "price": 1.50, "stop": None, "duration": "day",
                          "type": "limit", "quantity": 20}]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {
            "trades": [self._make_open_trade(quantity=10)]
        }
        settings = {"multipliers": {"VA222222": 1}}

        check_master_modifications(mock_db, master_orders, [FOLLOWER_ACCOUNT], settings)
        mock_delete.assert_called_once()
        mock_post.assert_called_once()

    @patch("scripts.copy_manager.post_orders_trd")
    @patch("scripts.copy_manager.delete_orders_trd")
    @patch("scripts.copy_manager.modify_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_fallback_cancel_replace_on_modify_error(self, mock_ps, mock_modify, mock_delete, mock_post):
        """Should cancel+replace when modify returns Error."""
        mock_modify.return_value = "Error"
        mock_post.return_value = {"order": {"id": 66666, "status": "pending"}}
        master_orders = [{"id": 10001, "status": "open", "class": "equity", "symbol": "AAPL",
                          "side": "buy", "price": 1.75, "stop": None, "duration": "day",
                          "type": "limit", "quantity": 10}]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {
            "trades": [self._make_open_trade(price=1.50)]
        }
        settings = {"multipliers": {"VA222222": 1}}

        check_master_modifications(mock_db, master_orders, [FOLLOWER_ACCOUNT], settings)
        mock_modify.assert_called_once()
        mock_delete.assert_called_once()
        mock_post.assert_called_once()

    @patch("scripts.copy_manager.modify_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_skips_trades_without_snapshot(self, mock_ps, mock_modify):
        """Should skip legacy trades that have no master_snapshot."""
        master_orders = [{"id": 10001, "status": "open", "price": 1.75, "duration": "day", "type": "limit", "quantity": 10}]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {
            "trades": [{"id": 55555, "master_id": 10001, "status": "open"}]  # no master_snapshot
        }
        settings = {"multipliers": {"VA222222": 1}}

        check_master_modifications(mock_db, master_orders, [FOLLOWER_ACCOUNT], settings)
        mock_modify.assert_not_called()

    @patch("scripts.copy_manager.modify_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_skips_filled_follower_trades(self, mock_ps, mock_modify):
        """Should not modify trades that are already filled."""
        master_orders = [{"id": 10001, "status": "open", "price": 1.75, "duration": "day", "type": "limit", "quantity": 10}]
        trade = self._make_open_trade(price=1.50)
        trade["status"] = "filled"
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {"trades": [trade]}
        settings = {"multipliers": {"VA222222": 1}}

        check_master_modifications(mock_db, master_orders, [FOLLOWER_ACCOUNT], settings)
        mock_modify.assert_not_called()

    @patch("scripts.copy_manager.modify_orders_trd")
    @patch("scripts.copy_manager.print_store")
    def test_no_modify_when_fields_match(self, mock_ps, mock_modify):
        """Should not call modify when nothing has changed."""
        master_orders = [{"id": 10001, "status": "open", "price": 1.50, "stop": None, "duration": "day", "type": "limit", "quantity": 10}]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {
            "trades": [self._make_open_trade()]
        }
        settings = {"multipliers": {"VA222222": 1}}

        check_master_modifications(mock_db, master_orders, [FOLLOWER_ACCOUNT], settings)
        mock_modify.assert_not_called()


class TestRunCopyCycle(unittest.TestCase):
    """Tests for run_copy_cycle() -- 5 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestRunCopyCycle completed in {elapsed:.2f} seconds")

    @patch("scripts.copy_manager.update_trade_statuses")
    @patch("scripts.copy_manager.check_stale_orders")
    @patch("scripts.copy_manager.check_master_modifications")
    @patch("scripts.copy_manager.check_master_cancellations")
    @patch("scripts.copy_manager.get_orders_trd")
    @patch("scripts.copy_manager.get_new_master_orders")
    @patch("scripts.copy_manager.get_follower_accounts")
    @patch("scripts.copy_manager.get_master_account")
    def test_returns_false_when_no_master(self, mock_master, mock_followers, *_):
        """Should return False when no master account exists."""
        mock_master.return_value = None
        mock_db = MagicMock()

        result = run_copy_cycle(mock_db, [])
        self.assertFalse(result)

    @patch("scripts.copy_manager.update_trade_statuses")
    @patch("scripts.copy_manager.check_stale_orders")
    @patch("scripts.copy_manager.check_master_modifications")
    @patch("scripts.copy_manager.check_master_cancellations")
    @patch("scripts.copy_manager.get_orders_trd")
    @patch("scripts.copy_manager.get_new_master_orders")
    @patch("scripts.copy_manager.get_follower_accounts")
    @patch("scripts.copy_manager.get_master_account")
    def test_returns_true_when_no_followers(self, mock_master, mock_followers, *_):
        """Should return True (not error) when no followers exist."""
        mock_master.return_value = MASTER_ACCOUNT
        mock_followers.return_value = []
        mock_db = MagicMock()

        result = run_copy_cycle(mock_db, [])
        self.assertTrue(result)

    @patch("scripts.copy_manager.update_trade_statuses")
    @patch("scripts.copy_manager.check_stale_orders")
    @patch("scripts.copy_manager.check_master_modifications")
    @patch("scripts.copy_manager.check_master_cancellations")
    @patch("scripts.copy_manager.get_orders_trd")
    @patch("scripts.copy_manager.get_new_master_orders")
    @patch("scripts.copy_manager.get_follower_accounts")
    @patch("scripts.copy_manager.get_master_account")
    def test_returns_true_when_automation_disabled(self, mock_master, mock_followers, mock_new_orders, *_):
        """Should return True when automation is disabled."""
        mock_master.return_value = MASTER_ACCOUNT
        mock_followers.return_value = [FOLLOWER_ACCOUNT]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {"type": "global", "use_automation": False}

        result = run_copy_cycle(mock_db, [])
        self.assertTrue(result)
        mock_new_orders.assert_not_called()

    @patch("scripts.copy_manager.update_trade_statuses")
    @patch("scripts.copy_manager.check_stale_orders")
    @patch("scripts.copy_manager.check_master_modifications")
    @patch("scripts.copy_manager.check_master_cancellations")
    @patch("scripts.copy_manager.get_orders_trd")
    @patch("scripts.copy_manager.forward_order_to_follower")
    @patch("scripts.copy_manager.get_new_master_orders")
    @patch("scripts.copy_manager.get_follower_accounts")
    @patch("scripts.copy_manager.get_master_account")
    def test_forwards_new_orders(self, mock_master, mock_followers, mock_new_orders, mock_forward, *_):
        """Should forward detected new orders to followers."""
        mock_master.return_value = MASTER_ACCOUNT
        mock_followers.return_value = [FOLLOWER_ACCOUNT]
        mock_new_orders.return_value = [SAMPLE_ORDER]
        mock_db = MagicMock()
        mock_db.get_collection.return_value.find_one.return_value = {"type": "global", "use_automation": True}

        result = run_copy_cycle(mock_db, [])
        self.assertTrue(result)
        mock_forward.assert_called_once()

    @patch("scripts.copy_manager.update_trade_statuses")
    @patch("scripts.copy_manager.check_stale_orders")
    @patch("scripts.copy_manager.check_master_modifications")
    @patch("scripts.copy_manager.check_master_cancellations")
    @patch("scripts.copy_manager.get_orders_trd")
    @patch("scripts.copy_manager.get_new_master_orders")
    @patch("scripts.copy_manager.get_follower_accounts")
    @patch("scripts.copy_manager.get_master_account")
    def test_handles_exception_gracefully(self, mock_master, *_):
        """Should return False (not crash) on unexpected exception."""
        mock_master.side_effect = Exception("DB connection failed")
        mock_db = MagicMock()

        result = run_copy_cycle(mock_db, [])
        self.assertFalse(result)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    unittest.main()

# END
