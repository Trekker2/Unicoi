"""
Test Runner for Tradier Copy Bot

Default: runs unit tests + integration scenarios (safe, no API calls).
With --live: also runs live Tradier sandbox integration tests.

Usage:
    python -m tests.run_all_tests          # Unit + scenarios only
    python -m tests.run_all_tests --live   # Also runs live sandbox tests
"""

import argparse
import subprocess
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

UNIT_TEST_MODULES = [
    "tests.test_helper",
    "tests.test_constants",
    "tests.test_database_manager",
    "tests.test_copy_manager",
    "tests.test_services",
    "tests.test_cron_daily",
    "tests.test_tradier",  # Sandbox API connectivity (VA prefix accounts, no real money)
]

LIVE_TEST_RUNNER = "tests.live_test_runner"  # Phase-based sandbox tests (place/modify/cancel orders)


def main():
    parser = argparse.ArgumentParser(description="Run Tradier Copy Bot test suite")
    parser.add_argument("--live", action="store_true", help="Include live Tradier sandbox tests")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    failed = False

    # Step 1: Unit tests
    print("\n" + "=" * 60)
    print("UNIT TESTS")
    print("=" * 60)
    cmd = [sys.executable, "-m", "unittest"] + UNIT_TEST_MODULES + ["-v"]
    result = subprocess.run(cmd, cwd=root)
    if result.returncode != 0:
        failed = True

    # Step 2: Integration scenarios
    print("\n" + "=" * 60)
    print("INTEGRATION SCENARIOS")
    print("=" * 60)
    cmd = [sys.executable, "-m", "tests.scenario_runner", "--all"]
    result = subprocess.run(cmd, cwd=root)
    if result.returncode != 0:
        failed = True

    # Step 3: Live phase tests (only with --live)
    if args.live:
        print("\n" + "=" * 60)
        print("LIVE PHASE TESTS (sandbox)")
        print("=" * 60)
        cmd = [sys.executable, "-m", LIVE_TEST_RUNNER, "--required", "--force-automation"]
        result = subprocess.run(cmd, cwd=root)
        if result.returncode != 0:
            failed = True
    else:
        print(f"\nSkipping live phase tests (use --live to include)")

    # Summary
    print("\n" + "=" * 60)
    if failed:
        print("SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()

# END
