"""
Database Manager Unit Tests for Tradier Copy Bot

Tests serialization, logging, and cleanup functions from database_manager.py.
Uses mocked MongoDB to avoid requiring a live database.

Test Coverage:
    - serialize_for_mongo: Type conversion for MongoDB storage
    - store_log_db: Log entry creation and DB upsert
    - cleanup_old_data: Old log and history pruning
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt
import decimal
import os
import sys
import time
import unittest
import uuid
from enum import Enum
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database_manager import serialize_for_mongo, store_log_db, cleanup_old_data


# ==============================================================================
# TESTS
# ==============================================================================

class TestSerializeForMongo(unittest.TestCase):
    """Tests for serialize_for_mongo() -- 10 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestSerializeForMongo completed in {elapsed:.2f} seconds")

    def test_dict_passthrough(self):
        """Plain dict should pass through."""
        data = {"key": "value", "num": 42}
        result = serialize_for_mongo(data)
        self.assertEqual(result, data)

    def test_nested_dict(self):
        """Nested dicts should be recursively serialized."""
        data = {"outer": {"inner": "value"}}
        result = serialize_for_mongo(data)
        self.assertEqual(result, {"outer": {"inner": "value"}})

    def test_list_passthrough(self):
        """Lists should be recursively serialized."""
        data = [1, 2, "three"]
        result = serialize_for_mongo(data)
        self.assertEqual(result, [1, 2, "three"])

    def test_uuid_to_string(self):
        """UUID should be converted to string."""
        test_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = serialize_for_mongo(test_uuid)
        self.assertEqual(result, "12345678-1234-5678-1234-567812345678")

    def test_enum_serialized_via_dict(self):
        """Enum has __dict__ so serialize_for_mongo converts it via __dict__ path.
        The Enum-specific check is unreachable for standard Enum instances."""
        class Color(Enum):
            RED = "red"
        result = serialize_for_mongo(Color.RED)
        # Enum.__dict__ produces a dict with internal attributes, not the value
        self.assertIsInstance(result, dict)

    def test_decimal_to_float(self):
        """Decimal should be converted to float."""
        result = serialize_for_mongo(decimal.Decimal("3.14"))
        self.assertIsInstance(result, float)
        self.assertAlmostEqual(result, 3.14)

    def test_object_with_dict(self):
        """Object with __dict__ should be serialized via its attributes."""
        class Obj:
            def __init__(self):
                self.name = "test"
                self.value = 42
        result = serialize_for_mongo(Obj())
        self.assertEqual(result, {"name": "test", "value": 42})

    def test_object_with_to_dict_and_slots(self):
        """Object with to_dict() and __slots__ (no __dict__) should use to_dict()."""
        class Obj:
            __slots__ = ()
            def to_dict(self):
                return {"key": "from_to_dict"}
        result = serialize_for_mongo(Obj())
        self.assertEqual(result, {"key": "from_to_dict"})

    def test_none_passthrough(self):
        """None should pass through unchanged."""
        self.assertIsNone(serialize_for_mongo(None))

    def test_empty_dict_default(self):
        """Default parameter (empty dict) should return empty dict."""
        result = serialize_for_mongo()
        self.assertEqual(result, {})


class TestStoreLogDb(unittest.TestCase):
    """Tests for store_log_db() -- 4 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestStoreLogDb completed in {elapsed:.2f} seconds")

    def test_calls_update_one_with_push(self):
        """Should call update_one with $push for logs."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.get_collection.return_value = mock_collection

        store_log_db(mock_db, "joe", "Test log message")

        mock_db.get_collection.assert_called_with("logs")
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        self.assertEqual(call_args.kwargs["filter"], {"username": "joe"})
        self.assertIn("$push", call_args.kwargs["update"])
        self.assertTrue(call_args.kwargs["upsert"])

    def test_log_entry_has_datetime_and_log(self):
        """Pushed log entry should have datetime and log fields."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.get_collection.return_value = mock_collection

        store_log_db(mock_db, "joe", "Test message")

        call_args = mock_collection.update_one.call_args
        pushed = call_args.kwargs["update"]["$push"]["logs"]
        self.assertIn("datetime", pushed)
        self.assertEqual(pushed["log"], "Test message")

    def test_returns_update_dict(self):
        """Should return the update dictionary."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.get_collection.return_value = mock_collection

        result = store_log_db(mock_db, "joe", "msg")
        self.assertIn("$push", result)

    def test_datetime_format(self):
        """Datetime should be in YYYY-MM-DD HH:MM:SS format."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.get_collection.return_value = mock_collection

        store_log_db(mock_db, "joe", "msg")

        call_args = mock_collection.update_one.call_args
        pushed = call_args.kwargs["update"]["$push"]["logs"]
        dt_str = pushed["datetime"]
        # Should parse without error
        dt.datetime.strptime(dt_str, "%Y-%m-%d %X")


class TestCleanupOldData(unittest.TestCase):
    """Tests for cleanup_old_data() -- 4 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestCleanupOldData completed in {elapsed:.2f} seconds")

    def test_keeps_recent_logs(self):
        """Logs within hours_limit should be kept."""
        mock_db = MagicMock()
        mock_logs_coll = MagicMock()
        mock_history_coll = MagicMock()

        def get_coll(name):
            if name == "logs":
                return mock_logs_coll
            return mock_history_coll

        mock_db.get_collection = get_coll

        # Recent log (1 hour ago)
        recent_time = (dt.datetime.now() - dt.timedelta(hours=1)).strftime("%Y-%m-%d %X")
        mock_logs_coll.find.return_value = [
            {"username": "joe", "logs": [{"datetime": recent_time, "log": "recent"}]}
        ]
        mock_history_coll.find.return_value = []

        cleanup_old_data(db=mock_db, hours_limit=16, days_limit=90)

        call_args = mock_logs_coll.update_one.call_args
        kept_logs = call_args.kwargs["update"]["$set"]["logs"]
        self.assertEqual(len(kept_logs), 1)

    def test_removes_old_logs(self):
        """Logs older than hours_limit should be removed."""
        mock_db = MagicMock()
        mock_logs_coll = MagicMock()
        mock_history_coll = MagicMock()

        def get_coll(name):
            if name == "logs":
                return mock_logs_coll
            return mock_history_coll

        mock_db.get_collection = get_coll

        # Old log (20 hours ago)
        old_time = (dt.datetime.now() - dt.timedelta(hours=20)).strftime("%Y-%m-%d %X")
        mock_logs_coll.find.return_value = [
            {"username": "joe", "logs": [{"datetime": old_time, "log": "old"}]}
        ]
        mock_history_coll.find.return_value = []

        cleanup_old_data(db=mock_db, hours_limit=16, days_limit=90)

        call_args = mock_logs_coll.update_one.call_args
        kept_logs = call_args.kwargs["update"]["$set"]["logs"]
        self.assertEqual(len(kept_logs), 0)

    def test_returns_db(self):
        """Should return the database connection."""
        mock_db = MagicMock()
        mock_coll = MagicMock()
        mock_coll.find.return_value = []
        mock_db.get_collection.return_value = mock_coll

        result = cleanup_old_data(db=mock_db)
        self.assertEqual(result, mock_db)

    def test_keeps_malformed_logs(self):
        """Logs with unparseable datetime should be kept (not deleted)."""
        mock_db = MagicMock()
        mock_logs_coll = MagicMock()
        mock_history_coll = MagicMock()

        def get_coll(name):
            if name == "logs":
                return mock_logs_coll
            return mock_history_coll

        mock_db.get_collection = get_coll

        mock_logs_coll.find.return_value = [
            {"username": "joe", "logs": [{"datetime": "bad-format", "log": "malformed"}]}
        ]
        mock_history_coll.find.return_value = []

        cleanup_old_data(db=mock_db, hours_limit=16, days_limit=90)

        call_args = mock_logs_coll.update_one.call_args
        kept_logs = call_args.kwargs["update"]["$set"]["logs"]
        self.assertEqual(len(kept_logs), 1)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    unittest.main()

# END
