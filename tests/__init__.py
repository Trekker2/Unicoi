"""
Tests Module for Tradier Copy Bot

Unit Tests (30%) — 137 tests:
    - test_helper: Utility functions (flatten, format_tag, hashing, market hours)
    - test_constants: Default settings, status classifications, side mappings
    - test_database_manager: Serialization, logging, cleanup
    - test_copy_manager: Order reconstruction, copy cycle, forwarding, cancel sync, modification sync
    - test_services: Settings, activity, accounts, orders, positions services
    - test_cron_daily: Daily maintenance (log cleanup, history cleanup, orphan removal, indexes)

Sandbox API Tests — 11 tests:
    - test_tradier: Tradier sandbox connectivity (auth, orders, balances, positions, streaming)
      Uses sandbox accounts (VA prefix), no real money. Included in default run.

Integration Scenarios (60%) — 13 scenarios:
    - 01: Single equity order copied to one follower
    - 02: Multi-leg SPX credit spread copied with 3x multiplier
    - 03: Duplicate order not forwarded twice (history dedup)
    - 04: Stale order not forwarded (10 min old > 5 min timeout)
    - 05: Automation disabled prevents all copies
    - 06: Canceled master order cancels matching follower order
    - 07: Order forwarded to 3 followers with 1x, 2x, 5x multipliers
    - 08: No master account returns failure gracefully
    - 09: Limit order preserves price field in reconstruction
    - 10: Expired and rejected orders filtered out
    - 11: Master modifies limit price — follower modified via PUT
    - 12: Master modifies quantity — follower cancel + replace
    - 13: Master modifies duration (day → gtc) — follower modified via PUT

Live Integration Tests (10%) — 6 phases (sandbox, --live flag):
    - Phase 0: Prerequisites — API connectivity, account access
    - Phase 1: Read-Only API — orders, positions, balances return valid data
    - Phase 2: Order Placement — post limit order far from market (won't fill)
    - Phase 3: Order Modification — modify limit price and duration via PUT
    - Phase 4: Order Cancellation — cancel test order, verify status change
    - Phase 5: Copy Pipeline — place on master, reconstruct, forward to follower
"""

# END
