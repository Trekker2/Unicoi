"""
Tradier API Integration Tests for Tradier Copy Bot

Tests against sandbox accounts to verify API connectivity and response parsing.
NEVER places real money orders - only uses sandbox accounts (VA prefix).

Test Coverage:
    - Authentication (sandbox detection)
    - Get orders (response parsing, single-vs-list)
    - Get balances
    - Get positions
    - Validate account (user profile)
    - Streaming session creation
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.tradier_ import (
    get_auth_trd,
    get_orders_trd,
    get_balances_trd,
    get_positions_trd,
    validate_account_trd,
    create_streaming_session,
)


# ==============================================================================
# TEST CONFIGURATION
# ==============================================================================

SANDBOX_ACCOUNT = "VA23115648"
SANDBOX_API_KEY = "9i7X6Rw4uFEZKjLozEdxpKNY8TNU"

SANDBOX_ACCOUNT_2 = "VA180221"
SANDBOX_API_KEY_2 = "UGVFD3KK4ZKHGIouYSH5jRyivuDV"


# ==============================================================================
# TESTS
# ==============================================================================

class TestTradierAuth(unittest.TestCase):
    """Test Tradier authentication."""

    def test_sandbox_detection(self):
        """VA prefix should route to sandbox."""
        auth = get_auth_trd(trd_account=SANDBOX_ACCOUNT, trd_api=SANDBOX_API_KEY)
        self.assertIn("sandbox", auth["base"])
        self.assertEqual(auth["account"], SANDBOX_ACCOUNT)

    def test_real_detection(self):
        """Non-VA prefix should route to real API."""
        auth = get_auth_trd(trd_account="6YA19689", trd_api="fake-key")
        self.assertNotIn("sandbox", auth["base"])

    def test_headers(self):
        """Auth headers should contain Bearer token."""
        auth = get_auth_trd(trd_account=SANDBOX_ACCOUNT, trd_api=SANDBOX_API_KEY)
        self.assertIn("Authorization", auth["headers"])
        self.assertTrue(auth["headers"]["Authorization"].startswith("Bearer"))


class TestTradierOrders(unittest.TestCase):
    """Test order retrieval."""

    def test_get_orders_returns_list(self):
        """get_orders_trd should return a list."""
        orders = get_orders_trd(trd_account=SANDBOX_ACCOUNT, trd_api=SANDBOX_API_KEY)
        self.assertIsInstance(orders, list)

    def test_get_orders_second_account(self):
        """Should work with second sandbox account."""
        orders = get_orders_trd(trd_account=SANDBOX_ACCOUNT_2, trd_api=SANDBOX_API_KEY_2)
        self.assertIsInstance(orders, list)


class TestTradierBalances(unittest.TestCase):
    """Test balance retrieval."""

    def test_get_balances_returns_dict(self):
        """get_balances_trd should return a dict with balance fields."""
        balances = get_balances_trd(trd_account=SANDBOX_ACCOUNT, trd_api=SANDBOX_API_KEY)
        self.assertIsInstance(balances, dict)

    def test_balances_has_equity(self):
        """Balances should include total_equity or equivalent."""
        balances = get_balances_trd(trd_account=SANDBOX_ACCOUNT, trd_api=SANDBOX_API_KEY)
        has_equity = "total_equity" in balances or "equity" in balances
        self.assertTrue(has_equity, f"No equity field found in: {list(balances.keys())}")


class TestTradierPositions(unittest.TestCase):
    """Test position retrieval."""

    def test_get_positions_returns_list(self):
        """get_positions_trd should return a list."""
        positions = get_positions_trd(trd_account=SANDBOX_ACCOUNT, trd_api=SANDBOX_API_KEY)
        self.assertIsInstance(positions, list)


class TestTradierValidation(unittest.TestCase):
    """Test account validation."""

    def test_validate_good_account(self):
        """Valid credentials should return profile data."""
        result = validate_account_trd(trd_account=SANDBOX_ACCOUNT, trd_api=SANDBOX_API_KEY)
        self.assertIsInstance(result, dict)
        self.assertNotIn("error", result)

    def test_validate_bad_account(self):
        """Invalid credentials should return error."""
        result = validate_account_trd(trd_account="VA00000000", trd_api="bad-key")
        self.assertIn("error", result)


class TestTradierStreaming(unittest.TestCase):
    """Test streaming session creation."""

    def test_create_session(self):
        """Should return a session ID string."""
        session_id = create_streaming_session(trd_api=SANDBOX_API_KEY)
        self.assertIsInstance(session_id, str)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    unittest.main()

# END
