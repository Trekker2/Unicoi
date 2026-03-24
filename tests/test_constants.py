"""
Constants Unit Tests for Tradier Copy Bot

Tests default settings, status classifications, side classifications,
and configuration values from constants.py.

Test Coverage:
    - get_default_settings: Default values and structure
    - Status classifications: Completeness and no overlap
    - Side classifications: Long/short/inverse correctness
    - Value classifications: na list completeness
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import (
    get_default_settings, DEFAULT_POLL_INTERVAL, DEFAULT_STALE_TIMEOUT, MAX_ERRORS,
    bad_statuses, open_statuses, closed_statuses, filled_statuses, good_statuses,
    long_sides, short_sides, inverse_side_dict, na,
    required_dbs, NAVBAR_PAGES, NAVBAR_PAGE_EMOJIS,
    User, db_name, brand_color, homepage, app_title,
)


# ==============================================================================
# TESTS
# ==============================================================================

class TestDefaultSettings(unittest.TestCase):
    """Tests for get_default_settings() -- 8 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()
        cls.defaults = get_default_settings()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestDefaultSettings completed in {elapsed:.2f} seconds")

    def test_returns_dict(self):
        """Should return a dictionary."""
        self.assertIsInstance(self.defaults, dict)

    def test_automation_off_by_default(self):
        """Automation should be disabled by default (safety)."""
        self.assertFalse(self.defaults["use_automation"])

    def test_default_poll_interval(self):
        """Poll interval should match constant."""
        self.assertEqual(self.defaults["poll_interval"], DEFAULT_POLL_INTERVAL)
        self.assertEqual(self.defaults["poll_interval"], 2)

    def test_default_stale_timeout(self):
        """Stale timeout should match constant."""
        self.assertEqual(self.defaults["stale_timeout"], DEFAULT_STALE_TIMEOUT)
        self.assertEqual(self.defaults["stale_timeout"], 5)

    def test_default_color_mode(self):
        """Color mode should default to Dark."""
        self.assertEqual(self.defaults["color_mode"], "Dark")

    def test_streaming_off_by_default(self):
        """Streaming should be disabled by default."""
        self.assertFalse(self.defaults["use_streaming"])

    def test_multipliers_empty_by_default(self):
        """Multipliers should be an empty dict by default."""
        self.assertEqual(self.defaults["multipliers"], {})

    def test_has_all_required_keys(self):
        """Should contain all expected setting keys."""
        expected = {"use_automation", "poll_interval", "stale_timeout", "color_mode", "use_streaming", "multipliers"}
        self.assertEqual(set(self.defaults.keys()), expected)


class TestStatusClassifications(unittest.TestCase):
    """Tests for order status classification lists -- 8 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestStatusClassifications completed in {elapsed:.2f} seconds")

    def test_bad_statuses_not_empty(self):
        """Bad statuses list should not be empty."""
        self.assertTrue(len(bad_statuses) > 0)

    def test_bad_statuses_include_common(self):
        """Bad statuses should include expired, canceled, rejected."""
        for status in ["expired", "canceled", "rejected", "error"]:
            self.assertIn(status, bad_statuses)

    def test_open_statuses_include_common(self):
        """Open statuses should include open, pending."""
        for status in ["open", "pending"]:
            self.assertIn(status, open_statuses)

    def test_filled_in_closed(self):
        """Filled should be in closed statuses."""
        self.assertIn("filled", closed_statuses)

    def test_filled_statuses_variants(self):
        """Filled statuses should include case variants."""
        self.assertIn("filled", filled_statuses)
        self.assertIn("Filled", filled_statuses)
        self.assertIn("FLL", filled_statuses)

    def test_good_statuses_include_open_and_filled(self):
        """Good statuses should include open statuses and filled."""
        self.assertIn("open", good_statuses)
        self.assertIn("filled", good_statuses)

    def test_bad_and_open_no_overlap(self):
        """Bad and open statuses should not overlap."""
        overlap = set(bad_statuses) & set(open_statuses)
        self.assertEqual(overlap, set(), f"Overlapping statuses: {overlap}")

    def test_max_errors_positive(self):
        """MAX_ERRORS should be a positive integer."""
        self.assertGreater(MAX_ERRORS, 0)
        self.assertEqual(MAX_ERRORS, 50)


class TestSideClassifications(unittest.TestCase):
    """Tests for trading side classification lists -- 6 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestSideClassifications completed in {elapsed:.2f} seconds")

    def test_buy_is_long(self):
        """'buy' should be in long sides."""
        self.assertIn("buy", long_sides)

    def test_sell_is_short(self):
        """'sell' should be in short sides."""
        self.assertIn("sell", short_sides)

    def test_buy_to_open_is_long(self):
        """'buy_to_open' (option entry long) should be in long sides."""
        self.assertIn("buy_to_open", long_sides)

    def test_sell_to_open_is_short(self):
        """'sell_to_open' (option entry short) should be in short sides."""
        self.assertIn("sell_to_open", short_sides)

    def test_long_and_short_no_overlap(self):
        """Long and short sides should not overlap."""
        overlap = set(long_sides) & set(short_sides)
        self.assertEqual(overlap, set(), f"Overlapping sides: {overlap}")

    def test_inverse_side_dict_symmetry(self):
        """Inverse dict should be symmetrical (A->B implies B->A)."""
        for side, inverse in inverse_side_dict.items():
            if inverse in inverse_side_dict:
                self.assertEqual(
                    inverse_side_dict[inverse], side,
                    f"Asymmetry: {side}->{inverse} but {inverse}->{inverse_side_dict.get(inverse)}"
                )


class TestNaValues(unittest.TestCase):
    """Tests for na (null/falsy value) list -- 3 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestNaValues completed in {elapsed:.2f} seconds")

    def test_none_in_na(self):
        """None should be in na list."""
        self.assertIn(None, na)

    def test_empty_string_in_na(self):
        """Empty string should be in na list."""
        self.assertIn("", na)

    def test_false_in_na(self):
        """False should be in na list."""
        self.assertIn(False, na)


class TestAppConfig(unittest.TestCase):
    """Tests for application configuration constants -- 5 tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        elapsed = time.time() - cls.test_start_time
        print(f"\nTestAppConfig completed in {elapsed:.2f} seconds")

    def test_db_name(self):
        """Database name should be set."""
        self.assertEqual(db_name, "copy-bot-system")

    def test_required_dbs_has_core_collections(self):
        """Required DBs should include core collections."""
        for coll in ["accounts", "settings", "trades", "history", "logs", "users"]:
            self.assertIn(coll, required_dbs)

    def test_navbar_pages_count(self):
        """Should have 5 navbar pages."""
        self.assertEqual(len(NAVBAR_PAGES), 5)

    def test_navbar_page_emojis_match(self):
        """NAVBAR_PAGE_EMOJIS should have one entry per page."""
        self.assertEqual(len(NAVBAR_PAGE_EMOJIS), len(NAVBAR_PAGES))

    def test_user_class_has_username(self):
        """User class should store username."""
        user = User(id="test", username="testuser")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.id, "test")


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    unittest.main()

# END
