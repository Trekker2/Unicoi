"""
Worker Module for Tradier Copy Bot

This module runs the main copy engine loop that monitors the master Tradier account
and copies orders to follower accounts.

Architecture:
    - Polls master account on configurable interval (default 2s)
    - Checks market hours via exchange_calendars NYSE
    - Respects global automation killswitch
    - Optional streaming mode for instant order detection
    - Stops after 50 consecutive errors

Usage:
    python main.py
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt
import time
import traceback

from constants import *
from helper import is_market_open
from scripts.copy_manager import run_copy_cycle
from scripts.database_manager import connect_mongo, cleanup_old_data
from scripts.stream_manager import TradierStreamManager


# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

def main():
    """Main copy engine loop."""
    recent_log_list = []
    log_min = 0
    loop_count = 0
    should_run = True
    error_count = 0
    stream_manager = None

    while should_run:
        try:
            # Connect to database
            db = connect_mongo()

            # Reset logger every minute
            now = dt.datetime.now(tz=market_timezone)
            if int(now.strftime("%M")) != log_min:
                log_min = int(now.strftime("%M"))
                recent_log_list = []

            loop_count += 1
            if loop_count == 1:
                print("Starting copy engine...")
                print("Cleaning up old data...")
                cleanup_old_data(db)

            # Check market hours (skip on local for testing)
            if is_cloud and not is_market_open(now):
                msg = f"Market closed at {now.strftime('%H:%M %Z')}"
                if msg not in recent_log_list:
                    print(msg)
                    recent_log_list.append(msg)
                time.sleep(30)
                continue

            # Get settings
            global_settings = db.get_collection("settings").find_one({"type": "global"}) or {}
            settings = {**get_default_settings(), **global_settings}
            poll_interval = settings.get("poll_interval", DEFAULT_POLL_INTERVAL)
            use_streaming = settings.get("use_streaming", False)

            # Start streaming if enabled and not already running
            if use_streaming and stream_manager is None:
                master = db.get_collection("accounts").find_one({"is_master": True})
                if master:
                    stream_manager = TradierStreamManager(
                        account_id=master.get("account_number"),
                        api_key=master.get("api_key"),
                        on_order_event=lambda event: None,
                    )
                    stream_manager.start()
                    poll_interval = 30  # Slower polling as fallback with streaming

            # Stop streaming if disabled
            if not use_streaming and stream_manager is not None:
                stream_manager.stop()
                stream_manager = None

            # Run copy cycle
            run_copy_cycle(db, recent_log_list)

            # Reset error count on success
            error_count = 0

        except Exception as e:
            tback = traceback.format_exc()
            if tback not in recent_log_list:
                print(tback)
                recent_log_list.append(tback)

            error_count += 1
            if error_count > MAX_ERRORS:
                print(f"Stopping due to error_count = {error_count}")
                should_run = False

        time.sleep(poll_interval)

    # Cleanup
    if stream_manager:
        stream_manager.stop()

    return should_run


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    main()

# END
