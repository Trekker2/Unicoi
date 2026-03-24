"""
Cron Daily Unit Tests for Tradier Copy Bot

Tests all daily maintenance tasks with mocked MongoDB.

Test Coverage:
    - cleanup_old_logs: Log retention enforcement
    - cleanup_old_history: Trade history retention
    - cleanup_orphaned_trades: Remove trades for deleted accounts
    - cleanup_orphaned_history: Remove history for deleted accounts
    - cleanup_orphaned_logs: Remove logs for deleted users
    - verify_indexes: Index creation
    - database_health_check: Collection document counts
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt
import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cron.cron_daily import (
    cleanup_old_logs, cleanup_old_history,
    cleanup_orphaned_trades, cleanup_orphaned_history, cleanup_orphaned_logs,
    verify_indexes, database_health_check,
)
from constants import market_timezone


# ==============================================================================
# HELPERS
# ==============================================================================

def _make_mock_db(collections):
    """Build a mock DB where get_collection returns per-name mocks."""
    db = MagicMock()
    coll_mocks = {}
    for name, docs in collections.items():
        mock_coll = MagicMock()
        mock_coll.find.return_value = list(docs)
        mock_coll.count_documents.return_value = len(docs)
        coll_mocks[name] = mock_coll

    def get_coll(name):
        if name not in coll_mocks:
            coll_mocks[name] = MagicMock()
            coll_mocks[name].find.return_value = []
            coll_mocks[name].count_documents.return_value = 0
        return coll_mocks[name]

    db.get_collection = get_coll
    db._coll_mocks = coll_mocks
    return db


# ==============================================================================
# TESTS
# ==============================================================================

class TestCleanupOldLogs(unittest.TestCase):
    """Tests for cleanup_old_logs() -- 3 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestCleanupOldLogs completed in {elapsed:.2f} seconds")

    def test_removes_old_keeps_recent(self):
        """Should remove logs older than hours_limit and keep recent ones."""
        recent = (dt.datetime.now() - dt.timedelta(hours=1)).strftime("%Y-%m-%d %X")
        old = (dt.datetime.now() - dt.timedelta(hours=20)).strftime("%Y-%m-%d %X")
        db = _make_mock_db({"logs": [
            {"_id": "1", "username": "joe", "logs": [
                {"datetime": recent, "log": "recent"},
                {"datetime": old, "log": "old"},
            ]}
        ]})

        removed = cleanup_old_logs(db, hours_limit=16)
        self.assertEqual(removed, 1)
        call_args = db._coll_mocks["logs"].update_one.call_args
        # update_one called with positional args: (filter, update)
        update_arg = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("update", {})
        kept = update_arg["$set"]["logs"]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["log"], "recent")

    def test_keeps_malformed_datetime(self):
        """Should keep logs with unparseable datetime."""
        db = _make_mock_db({"logs": [
            {"_id": "1", "username": "joe", "logs": [
                {"datetime": "bad-format", "log": "malformed"},
            ]}
        ]})

        removed = cleanup_old_logs(db, hours_limit=16)
        self.assertEqual(removed, 0)

    def test_empty_logs(self):
        """Should handle empty log collection."""
        db = _make_mock_db({"logs": []})
        removed = cleanup_old_logs(db, hours_limit=16)
        self.assertEqual(removed, 0)


class TestCleanupOldHistory(unittest.TestCase):
    """Tests for cleanup_old_history() -- 3 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestCleanupOldHistory completed in {elapsed:.2f} seconds")

    def test_removes_old_history(self):
        """Should remove history entries older than days_limit."""
        recent = (dt.datetime.now() - dt.timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S")
        old = (dt.datetime.now() - dt.timedelta(days=100)).strftime("%Y-%m-%dT%H:%M:%S")
        db = _make_mock_db({"history": [
            {"_id": "1", "account_number": "VA111", "history": [
                {"create_date": recent, "id": 1},
                {"create_date": old, "id": 2},
            ]}
        ]})

        removed = cleanup_old_history(db, days_limit=90)
        self.assertEqual(removed, 1)

    def test_uses_transaction_date_if_present(self):
        """Should prefer transaction_date over create_date."""
        recent = (dt.datetime.now() - dt.timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S")
        db = _make_mock_db({"history": [
            {"_id": "1", "account_number": "VA111", "history": [
                {"transaction_date": recent, "create_date": "1970-01-01T00:00:00", "id": 1},
            ]}
        ]})

        removed = cleanup_old_history(db, days_limit=90)
        self.assertEqual(removed, 0)

    def test_empty_history(self):
        """Should handle empty history collection."""
        db = _make_mock_db({"history": []})
        removed = cleanup_old_history(db, days_limit=90)
        self.assertEqual(removed, 0)


class TestCleanupOrphanedTrades(unittest.TestCase):
    """Tests for cleanup_orphaned_trades() -- 2 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestCleanupOrphanedTrades completed in {elapsed:.2f} seconds")

    def test_deletes_orphaned(self):
        """Should delete trades for accounts that don't exist."""
        db = _make_mock_db({
            "accounts": [{"account_number": "VA111"}],
            "trades": [
                {"_id": "t1", "account_number": "VA111"},
                {"_id": "t2", "account_number": "VA999"},
            ],
        })
        deleted = cleanup_orphaned_trades(db)
        self.assertEqual(deleted, 1)
        db._coll_mocks["trades"].delete_one.assert_called_once()

    def test_keeps_valid(self):
        """Should keep trades for existing accounts."""
        db = _make_mock_db({
            "accounts": [{"account_number": "VA111"}],
            "trades": [{"_id": "t1", "account_number": "VA111"}],
        })
        deleted = cleanup_orphaned_trades(db)
        self.assertEqual(deleted, 0)


class TestCleanupOrphanedHistory(unittest.TestCase):
    """Tests for cleanup_orphaned_history() -- 2 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestCleanupOrphanedHistory completed in {elapsed:.2f} seconds")

    def test_deletes_orphaned(self):
        """Should delete history for accounts that don't exist."""
        db = _make_mock_db({
            "accounts": [{"account_number": "VA111"}],
            "history": [
                {"_id": "h1", "account_number": "VA111"},
                {"_id": "h2", "account_number": "VA999"},
            ],
        })
        deleted = cleanup_orphaned_history(db)
        self.assertEqual(deleted, 1)

    def test_keeps_valid(self):
        """Should keep history for existing accounts."""
        db = _make_mock_db({
            "accounts": [{"account_number": "VA111"}],
            "history": [{"_id": "h1", "account_number": "VA111"}],
        })
        deleted = cleanup_orphaned_history(db)
        self.assertEqual(deleted, 0)


class TestCleanupOrphanedLogs(unittest.TestCase):
    """Tests for cleanup_orphaned_logs() -- 2 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestCleanupOrphanedLogs completed in {elapsed:.2f} seconds")

    def test_deletes_orphaned(self):
        """Should delete logs for users that don't exist."""
        db = _make_mock_db({
            "users": [{"username": "joe"}],
            "logs": [
                {"_id": "l1", "username": "joe"},
                {"_id": "l2", "username": "deleteduser"},
            ],
        })
        deleted = cleanup_orphaned_logs(db)
        self.assertEqual(deleted, 1)

    def test_keeps_valid(self):
        """Should keep logs for existing users."""
        db = _make_mock_db({
            "users": [{"username": "joe"}],
            "logs": [{"_id": "l1", "username": "joe"}],
        })
        deleted = cleanup_orphaned_logs(db)
        self.assertEqual(deleted, 0)


class TestVerifyIndexes(unittest.TestCase):
    """Tests for verify_indexes() -- 1 test."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestVerifyIndexes completed in {elapsed:.2f} seconds")

    def test_creates_indexes(self):
        """Should create indexes on all expected collections."""
        db = MagicMock()
        count = verify_indexes(db)
        self.assertEqual(count, 7)
        self.assertEqual(db.get_collection.return_value.create_index.call_count, 7)


class TestDatabaseHealthCheck(unittest.TestCase):
    """Tests for database_health_check() -- 2 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestDatabaseHealthCheck completed in {elapsed:.2f} seconds")

    def test_returns_counts(self):
        """Should return document count per collection."""
        db = MagicMock()
        db.get_collection.return_value.count_documents.return_value = 5
        counts = database_health_check(db)
        self.assertIsInstance(counts, dict)
        for coll in ["accounts", "history", "logs", "settings", "trades", "users"]:
            self.assertIn(coll, counts)
            self.assertEqual(counts[coll], 5)

    def test_handles_error(self):
        """Should return -1 for collections that error."""
        db = MagicMock()
        db.get_collection.return_value.count_documents.side_effect = Exception("timeout")
        counts = database_health_check(db)
        for count in counts.values():
            self.assertEqual(count, -1)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    unittest.main()

# END
