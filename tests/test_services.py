"""
Service Layer Unit Tests for Tradier Copy Bot

Tests all service modules with mocked DB and API calls.

Test Coverage:
    - settings_service: get/put settings
    - activity_service: get/delete logs
    - accounts_service: get/post/delete accounts, set master
    - orders_service: get/delete orders
    - positions_service: get/close positions
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==============================================================================
# SETTINGS SERVICE TESTS
# ==============================================================================

class TestSettingsService(unittest.TestCase):
    """Tests for settings_service -- 5 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestSettingsService completed in {elapsed:.2f} seconds")

    @patch("services.settings_service.connect_mongo")
    def test_get_settings_merges_defaults(self, mock_connect):
        """Should merge stored settings with defaults."""
        from services.settings_service import do_get_settings
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = {
            "type": "global", "use_automation": True
        }

        result = do_get_settings()
        self.assertTrue(result["use_automation"])
        # Defaults should fill in missing keys
        self.assertIn("poll_interval", result)
        self.assertIn("color_mode", result)

    @patch("services.settings_service.connect_mongo")
    def test_get_settings_uses_defaults_when_empty(self, mock_connect):
        """Should return defaults when no stored settings."""
        from services.settings_service import do_get_settings
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = None

        result = do_get_settings()
        self.assertFalse(result["use_automation"])
        self.assertEqual(result["poll_interval"], 2)

    @patch("services.settings_service.connect_mongo")
    def test_put_setting_returns_success(self, mock_connect):
        """Should return (True, message) on update."""
        from services.settings_service import do_put_setting
        mock_db = MagicMock()
        mock_connect.return_value = mock_db

        success, msg = do_put_setting("poll_interval", 5)
        self.assertTrue(success)
        self.assertIn("poll_interval", msg)

    @patch("services.settings_service.connect_mongo")
    def test_put_setting_calls_update_one(self, mock_connect):
        """Should call update_one with $set and upsert."""
        from services.settings_service import do_put_setting
        mock_db = MagicMock()
        mock_connect.return_value = mock_db

        do_put_setting("color_mode", "Light")

        mock_db.get_collection.return_value.update_one.assert_called_once()
        call_args = mock_db.get_collection.return_value.update_one.call_args
        # First two args are positional, upsert is keyword
        self.assertEqual(call_args[0][1], {"$set": {"color_mode": "Light"}})
        self.assertTrue(call_args[1]["upsert"])

    @patch("services.settings_service.connect_mongo")
    def test_global_aliases(self, mock_connect):
        """do_get_global_settings and do_put_global_setting should work."""
        from services.settings_service import do_get_global_settings, do_put_global_setting
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = None

        result = do_get_global_settings()
        self.assertIsInstance(result, dict)

        success, msg = do_put_global_setting("test_key", "test_value")
        self.assertTrue(success)


# ==============================================================================
# ACTIVITY SERVICE TESTS
# ==============================================================================

class TestActivityService(unittest.TestCase):
    """Tests for activity_service -- 4 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestActivityService completed in {elapsed:.2f} seconds")

    @patch("services.activity_service.connect_mongo")
    def test_get_logs_aggregates_by_username(self, mock_connect):
        """Should aggregate logs from all users and add username."""
        from services.activity_service import do_get_logs
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find.return_value = [
            {"username": "joe", "logs": [
                {"datetime": "2025-03-17 10:00:00", "log": "msg1"},
                {"datetime": "2025-03-17 10:01:00", "log": "msg2"},
            ]},
            {"username": "tyler", "logs": [
                {"datetime": "2025-03-17 10:02:00", "log": "msg3"},
            ]},
        ]

        result = do_get_logs()
        self.assertEqual(len(result), 3)
        # Should be sorted descending by datetime
        self.assertEqual(result[0]["datetime"], "2025-03-17 10:02:00")

    @patch("services.activity_service.connect_mongo")
    def test_get_logs_empty(self, mock_connect):
        """Should return empty list when no logs."""
        from services.activity_service import do_get_logs
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find.return_value = []

        result = do_get_logs()
        self.assertEqual(result, [])

    @patch("services.activity_service.connect_mongo")
    def test_delete_log_success(self, mock_connect):
        """Should return (True, message) when log found and deleted."""
        from services.activity_service import do_delete_log
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.update_one.return_value = MagicMock(modified_count=1)

        success, msg = do_delete_log("joe", "2025-03-17 10:00:00")
        self.assertTrue(success)

    @patch("services.activity_service.connect_mongo")
    def test_delete_log_not_found(self, mock_connect):
        """Should return (False, message) when log not found."""
        from services.activity_service import do_delete_log
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.update_one.return_value = MagicMock(modified_count=0)

        success, msg = do_delete_log("joe", "nonexistent")
        self.assertFalse(success)


# ==============================================================================
# ACCOUNTS SERVICE TESTS
# ==============================================================================

class TestAccountsService(unittest.TestCase):
    """Tests for accounts_service -- 8 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestAccountsService completed in {elapsed:.2f} seconds")

    @patch("services.accounts_service.connect_mongo")
    def test_get_accounts_sorts_master_first(self, mock_connect):
        """Should sort master account first."""
        from services.accounts_service import do_get_accounts
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find.return_value = [
            {"alias": "Follower", "is_master": False},
            {"alias": "Master", "is_master": True},
        ]

        result = do_get_accounts()
        self.assertEqual(result[0]["alias"], "Master")

    @patch("services.accounts_service.validate_account_trd")
    @patch("services.accounts_service.connect_mongo")
    def test_post_account_rejects_duplicate(self, mock_connect, mock_validate):
        """Should reject duplicate account numbers."""
        from services.accounts_service import do_post_account
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = {"account_number": "VA111111"}

        success, msg = do_post_account("Test", "VA111111", "key")
        self.assertFalse(success)
        self.assertIn("already exists", msg)

    @patch("services.accounts_service.validate_account_trd")
    @patch("services.accounts_service.connect_mongo")
    def test_post_account_rejects_bad_credentials(self, mock_connect, mock_validate):
        """Should reject invalid API credentials."""
        from services.accounts_service import do_post_account
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = None
        mock_validate.return_value = {"error": "Invalid token"}

        success, msg = do_post_account("Test", "VA333333", "bad-key")
        self.assertFalse(success)
        self.assertIn("Validation failed", msg)

    @patch("services.accounts_service.validate_account_trd")
    @patch("services.accounts_service.connect_mongo")
    def test_post_account_rejects_wrong_account(self, mock_connect, mock_validate):
        """Should reject when account_number not in API profile."""
        from services.accounts_service import do_post_account
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = None
        mock_validate.return_value = {
            "profile": {"account": {"account_number": "VA999999"}}
        }

        success, msg = do_post_account("Test", "VA333333", "key")
        self.assertFalse(success)
        self.assertIn("not found under this API key", msg)

    @patch("services.accounts_service.validate_account_trd")
    @patch("services.accounts_service.connect_mongo")
    def test_post_account_success(self, mock_connect, mock_validate):
        """Should insert account on valid credentials."""
        from services.accounts_service import do_post_account
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = None
        mock_validate.return_value = {
            "profile": {"account": [{"account_number": "VA333333"}]}
        }

        success, msg = do_post_account("Test", "VA333333", "good-key")
        self.assertTrue(success)
        mock_db.get_collection.return_value.insert_one.assert_called_once()

    @patch("services.accounts_service.connect_mongo")
    def test_delete_account_success(self, mock_connect):
        """Should delete account and clean up related data."""
        from services.accounts_service import do_delete_account
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.delete_one.return_value = MagicMock(deleted_count=1)

        success, msg = do_delete_account("VA111111")
        self.assertTrue(success)
        # Should also clean up trades and history
        self.assertEqual(mock_db.get_collection.return_value.delete_many.call_count, 2)

    @patch("services.accounts_service.connect_mongo")
    def test_delete_account_not_found(self, mock_connect):
        """Should return failure when account not found."""
        from services.accounts_service import do_delete_account
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.delete_one.return_value = MagicMock(deleted_count=0)

        success, msg = do_delete_account("VA000000")
        self.assertFalse(success)

    @patch("services.accounts_service.connect_mongo")
    def test_set_master_clears_all_then_sets(self, mock_connect):
        """Should clear all master flags then set the new one."""
        from services.accounts_service import do_set_master
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.update_one.return_value = MagicMock(modified_count=1)

        success, msg = do_set_master("VA111111")
        self.assertTrue(success)
        # Should call update_many to clear + update_one to set
        mock_db.get_collection.return_value.update_many.assert_called_once()
        mock_db.get_collection.return_value.update_one.assert_called_once()


# ==============================================================================
# ORDERS SERVICE TESTS
# ==============================================================================

class TestOrdersService(unittest.TestCase):
    """Tests for orders_service -- 3 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestOrdersService completed in {elapsed:.2f} seconds")

    @patch("services.orders_service.get_orders_trd")
    @patch("services.orders_service.connect_mongo")
    def test_get_orders_injects_account_info(self, mock_connect, mock_get_orders):
        """Should inject _account_alias and _account_number into each order."""
        from services.orders_service import do_get_orders
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find.return_value = [
            {"alias": "Master", "account_number": "VA111", "api_key": "key", "is_master": True}
        ]
        mock_get_orders.return_value = [{"id": 123, "symbol": "SPY"}]

        result = do_get_orders()
        self.assertEqual(len(result), 1)
        account, orders = result[0]
        self.assertEqual(orders[0]["_account_alias"], "Master")
        self.assertEqual(orders[0]["_account_number"], "VA111")

    @patch("services.orders_service.delete_orders_trd")
    @patch("services.orders_service.connect_mongo")
    def test_delete_order_account_not_found(self, mock_connect, mock_delete):
        """Should return failure when account not found."""
        from services.orders_service import do_delete_order
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = None

        success, msg = do_delete_order("VA000000", "12345")
        self.assertFalse(success)

    @patch("services.orders_service.delete_orders_trd")
    @patch("services.orders_service.connect_mongo")
    def test_delete_order_success(self, mock_connect, mock_delete):
        """Should call delete_orders_trd and return success."""
        from services.orders_service import do_delete_order
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = {
            "account_number": "VA111111", "api_key": "key"
        }
        mock_delete.return_value = {"order": {"id": 12345, "status": "ok"}}

        success, msg = do_delete_order("VA111111", "12345")
        self.assertTrue(success)


# ==============================================================================
# POSITIONS SERVICE TESTS
# ==============================================================================

class TestPositionsService(unittest.TestCase):
    """Tests for positions_service -- 4 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestPositionsService completed in {elapsed:.2f} seconds")

    @patch("services.positions_service.get_positions_trd")
    @patch("services.positions_service.connect_mongo")
    def test_get_positions_injects_account_info(self, mock_connect, mock_get_pos):
        """Should inject account info into each position."""
        from services.positions_service import do_get_positions
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find.return_value = [
            {"alias": "Master", "account_number": "VA111", "api_key": "key", "is_master": True}
        ]
        mock_get_pos.return_value = [{"symbol": "SPY", "quantity": 100}]

        result = do_get_positions()
        _, positions = result[0]
        self.assertEqual(positions[0]["_account_alias"], "Master")

    @patch("services.positions_service.post_orders_trd")
    @patch("services.positions_service.connect_mongo")
    def test_close_position_equity(self, mock_connect, mock_post):
        """Should create equity close order for short symbol."""
        from services.positions_service import do_close_position
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = {
            "account_number": "VA111111", "api_key": "key"
        }
        mock_post.return_value = {"order": {"id": 55555}}

        success, msg = do_close_position("VA111111", "SPY", 100, "sell")
        self.assertTrue(success)
        call_data = mock_post.call_args[1]["data"]
        self.assertEqual(call_data["class"], "equity")

    @patch("services.positions_service.post_orders_trd")
    @patch("services.positions_service.connect_mongo")
    def test_close_position_option(self, mock_connect, mock_post):
        """Should detect option class for long symbols (>10 chars)."""
        from services.positions_service import do_close_position
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = {
            "account_number": "VA111111", "api_key": "key"
        }
        mock_post.return_value = {"order": {"id": 55555}}

        success, msg = do_close_position("VA111111", "SPY250321C00500000", 5, "sell_to_close")
        self.assertTrue(success)
        call_data = mock_post.call_args[1]["data"]
        self.assertEqual(call_data["class"], "option")

    @patch("services.positions_service.post_orders_trd")
    @patch("services.positions_service.connect_mongo")
    def test_close_position_api_error(self, mock_connect, mock_post):
        """Should return failure on API error."""
        from services.positions_service import do_close_position
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        mock_db.get_collection.return_value.find_one.return_value = {
            "account_number": "VA111111", "api_key": "key"
        }
        mock_post.return_value = "Error"

        success, msg = do_close_position("VA111111", "SPY", 100, "sell")
        self.assertFalse(success)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    unittest.main()

# END
