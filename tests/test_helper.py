"""
Helper Function Unit Tests for Tradier Copy Bot

Tests utility functions from helper.py including data manipulation,
security functions, and market schedule utilities.

Test Coverage:
    - flatten: Nested list flattening
    - format_tag: Tradier tag sanitization
    - hide_text: Text masking
    - hash_password / verify_password: Bcrypt password hashing
    - is_market_open: NYSE market hours check
    - get_current_username: Session username retrieval
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

from helper import flatten, format_tag, hide_text, hash_password, verify_password, is_market_open
import pytz


# ==============================================================================
# TESTS
# ==============================================================================

class TestFlatten(unittest.TestCase):
    """Tests for flatten() -- 7 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestFlatten completed in {elapsed:.2f} seconds")

    def test_flat_list(self):
        """Already-flat list should pass through unchanged."""
        self.assertEqual(list(flatten([1, 2, 3])), [1, 2, 3])

    def test_nested_list(self):
        """Single level of nesting."""
        self.assertEqual(list(flatten([1, [2, 3], 4])), [1, 2, 3, 4])

    def test_deeply_nested(self):
        """Multiple levels of nesting."""
        self.assertEqual(list(flatten([1, [2, [3, [4]]]])), [1, 2, 3, 4])

    def test_empty_list(self):
        """Empty list should return empty."""
        self.assertEqual(list(flatten([])), [])

    def test_empty_nested(self):
        """Nested empty lists should return empty."""
        self.assertEqual(list(flatten([[], [[]]])), [])

    def test_strings_not_flattened(self):
        """Strings should not be iterated as characters."""
        self.assertEqual(list(flatten(["abc", "def"])), ["abc", "def"])

    def test_mixed_types(self):
        """Mixed types in nested structure."""
        result = list(flatten([1, ["a", 2.5], [True, [None]]]))
        self.assertEqual(result, [1, "a", 2.5, True, None])


class TestFormatTag(unittest.TestCase):
    """Tests for format_tag() -- 6 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestFormatTag completed in {elapsed:.2f} seconds")

    def test_alphanumeric_passthrough(self):
        """Alphanumeric strings pass through unchanged."""
        self.assertEqual(format_tag("abc123"), "abc123")

    def test_spaces_replaced(self):
        """Spaces become dashes."""
        self.assertEqual(format_tag("hello world"), "hello-world")

    def test_special_chars_replaced(self):
        """Special characters become dashes."""
        self.assertEqual(format_tag("order#123!"), "order-123-")

    def test_max_length_255(self):
        """Output truncated to 255 characters."""
        long_str = "a" * 300
        self.assertEqual(len(format_tag(long_str)), 255)

    def test_empty_string(self):
        """Empty string returns empty."""
        self.assertEqual(format_tag(""), "")

    def test_all_special(self):
        """All special characters become dashes."""
        self.assertEqual(format_tag("!@#$%"), "-----")


class TestHideText(unittest.TestCase):
    """Tests for hide_text() -- 4 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestHideText completed in {elapsed:.2f} seconds")

    def test_hides_text(self):
        """All characters replaced with asterisks."""
        self.assertEqual(hide_text("secret"), "******")

    def test_preserves_length(self):
        """Output length matches input."""
        self.assertEqual(len(hide_text("abc")), 3)

    def test_empty_string(self):
        """Empty string returns empty."""
        self.assertEqual(hide_text(""), "")

    def test_default_empty(self):
        """Default parameter returns empty."""
        self.assertEqual(hide_text(), "")


class TestPasswordHashing(unittest.TestCase):
    """Tests for hash_password() and verify_password() -- 6 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestPasswordHashing completed in {elapsed:.2f} seconds")

    def test_hash_returns_string(self):
        """hash_password should return a string."""
        result = hash_password("test123")
        self.assertIsInstance(result, str)

    def test_hash_not_plaintext(self):
        """Hash should differ from input."""
        result = hash_password("test123")
        self.assertNotEqual(result, "test123")

    def test_hash_starts_with_bcrypt_prefix(self):
        """Bcrypt hashes start with $2b$."""
        result = hash_password("test123")
        self.assertTrue(result.startswith("$2b$"))

    def test_verify_correct_password(self):
        """Correct password should verify True."""
        hashed = hash_password("mypassword")
        self.assertTrue(verify_password("mypassword", hashed))

    def test_verify_wrong_password(self):
        """Wrong password should verify False."""
        hashed = hash_password("mypassword")
        self.assertFalse(verify_password("wrongpassword", hashed))

    def test_verify_accepts_string_hash(self):
        """verify_password should accept string hashes (not just bytes)."""
        hashed = hash_password("test")
        self.assertIsInstance(hashed, str)
        self.assertTrue(verify_password("test", hashed))


class TestIsMarketOpen(unittest.TestCase):
    """Tests for is_market_open() -- 6 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestIsMarketOpen completed in {elapsed:.2f} seconds")

    def test_market_open_during_trading_hours_utc(self):
        """Should return True when passed a UTC-aware time during market hours."""
        utc_tz = pytz.UTC
        # Monday 15:00 UTC = 10:00 AM ET (market open)
        market_time = utc_tz.localize(dt.datetime(2025, 3, 17, 15, 0, 0))
        self.assertTrue(is_market_open(market_time))

    def test_market_open_during_trading_hours_et(self):
        """Should return True when passed an ET-aware time during market hours."""
        et_tz = pytz.timezone("US/Eastern")
        # Monday 10:00 AM ET (market open)
        market_time = et_tz.localize(dt.datetime(2025, 3, 17, 10, 0, 0))
        self.assertTrue(is_market_open(market_time))

    def test_market_closed_weekend(self):
        """Should return False on Saturday."""
        utc_tz = pytz.UTC
        saturday = utc_tz.localize(dt.datetime(2025, 3, 15, 15, 0, 0))
        self.assertFalse(is_market_open(saturday))

    def test_market_closed_after_hours(self):
        """Should return False after market close (4 PM ET = 21:00 UTC)."""
        utc_tz = pytz.UTC
        after_close = utc_tz.localize(dt.datetime(2025, 3, 17, 22, 0, 0))
        self.assertFalse(is_market_open(after_close))

    def test_market_closed_after_hours_et(self):
        """Should return False when passed an ET-aware time after close."""
        et_tz = pytz.timezone("US/Eastern")
        # Monday 5:00 PM ET (after close)
        after_close = et_tz.localize(dt.datetime(2025, 3, 17, 17, 0, 0))
        self.assertFalse(is_market_open(after_close))

    def test_returns_bool(self):
        """Should always return a boolean."""
        result = is_market_open()
        self.assertIsInstance(result, bool)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    unittest.main()

# END
