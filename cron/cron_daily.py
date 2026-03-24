"""
Daily Cron Job for Tradier Copy Bot

Runs once per day to perform database maintenance, orphan cleanup,
and optional database backup.

Tasks:
    1. Clean up old logs (>16 hours, matching cleanup_old_data)
    2. Clean up old trade history (>90 days)
    3. Clean up orphaned trades (accounts that no longer exist)
    4. Clean up orphaned history (accounts that no longer exist)
    5. Clean up orphaned logs (users that no longer exist)
    6. Verify database indexes
    7. Database backup (export collection counts as health check)
    8. Restart Heroku dynos (cloud only)

Usage:
    python -m cron.cron_daily

Schedule via Heroku Scheduler to run daily at 05:00 UTC (1:00 AM ET).
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt
import os
import time
import traceback

from constants import db_name, required_dbs, utc_timezone, market_timezone
from scripts.database_manager import connect_mongo


# ==============================================================================
# MAINTENANCE TASKS
# ==============================================================================

def cleanup_old_logs(db, hours_limit=16):
    """
    Clean up log entries older than hours_limit.

    Uses the same retention window as the copy engine's cleanup_old_data().

    Args:
        db: MongoDB database connection
        hours_limit: Hours to keep log entries

    Returns:
        int: Number of log entries removed
    """
    now = dt.datetime.now(tz=market_timezone)
    total_removed = 0

    log_docs = list(db.get_collection("logs").find({}))
    for doc in log_docs:
        logs = doc.get("logs", [])
        kept = []
        for log in logs:
            try:
                log_dt = dt.datetime.strptime(log["datetime"], "%Y-%m-%d %X")
                log_dt = market_timezone.localize(log_dt)
                if log_dt + dt.timedelta(hours=hours_limit) > now:
                    kept.append(log)
                else:
                    total_removed += 1
            except (ValueError, KeyError):
                kept.append(log)

        if len(kept) != len(logs):
            db.get_collection("logs").update_one(
                {"_id": doc["_id"]},
                {"$set": {"logs": kept}},
            )

    return total_removed


def cleanup_old_history(db, days_limit=90):
    """
    Clean up trade history entries older than days_limit.

    Args:
        db: MongoDB database connection
        days_limit: Days to keep history

    Returns:
        int: Number of history entries removed
    """
    now = dt.datetime.now(tz=market_timezone)
    total_removed = 0

    history_docs = list(db.get_collection("history").find({}))
    for doc in history_docs:
        history = doc.get("history", [])
        kept = []
        for order in history:
            try:
                date_key = "transaction_date" if "transaction_date" in order else "create_date"
                order_dt = dt.datetime.strptime(str(order.get(date_key, ""))[:19], "%Y-%m-%dT%H:%M:%S")
                order_dt = market_timezone.localize(order_dt)
                if order_dt + dt.timedelta(days=days_limit) > now:
                    kept.append(order)
                else:
                    total_removed += 1
            except (ValueError, KeyError):
                kept.append(order)

        if len(kept) != len(history):
            db.get_collection("history").update_one(
                {"_id": doc["_id"]},
                {"$set": {"history": kept}},
            )

    return total_removed


def cleanup_orphaned_trades(db):
    """
    Remove trade documents for accounts that no longer exist.

    Args:
        db: MongoDB database connection

    Returns:
        int: Number of orphaned trade documents removed
    """
    account_numbers = set()
    for acct in db.get_collection("accounts").find({}):
        account_numbers.add(acct.get("account_number"))

    deleted = 0
    for trade_doc in db.get_collection("trades").find({}):
        if trade_doc.get("account_number") not in account_numbers:
            db.get_collection("trades").delete_one({"_id": trade_doc["_id"]})
            deleted += 1

    return deleted


def cleanup_orphaned_history(db):
    """
    Remove history documents for accounts that no longer exist.

    Args:
        db: MongoDB database connection

    Returns:
        int: Number of orphaned history documents removed
    """
    account_numbers = set()
    for acct in db.get_collection("accounts").find({}):
        account_numbers.add(acct.get("account_number"))

    deleted = 0
    for hist_doc in db.get_collection("history").find({}):
        if hist_doc.get("account_number") not in account_numbers:
            db.get_collection("history").delete_one({"_id": hist_doc["_id"]})
            deleted += 1

    return deleted


def cleanup_orphaned_logs(db):
    """
    Remove log documents for users that no longer exist.

    Args:
        db: MongoDB database connection

    Returns:
        int: Number of orphaned log documents removed
    """
    usernames = set()
    for user in db.get_collection("users").find({}):
        usernames.add(user.get("username"))

    deleted = 0
    for log_doc in db.get_collection("logs").find({}):
        if log_doc.get("username") not in usernames:
            db.get_collection("logs").delete_one({"_id": log_doc["_id"]})
            deleted += 1

    return deleted


def verify_indexes(db):
    """
    Create indexes on frequently queried fields.

    Args:
        db: MongoDB database connection

    Returns:
        int: Number of indexes created or verified
    """
    indexes = [
        ("accounts", "account_number"),
        ("accounts", "is_master"),
        ("trades", "account_number"),
        ("history", "account_number"),
        ("logs", "username"),
        ("settings", "type"),
        ("users", "username"),
    ]

    count = 0
    for coll_name, field in indexes:
        try:
            db.get_collection(coll_name).create_index(field)
            count += 1
        except Exception:
            pass

    return count


def database_health_check(db):
    """
    Log collection document counts as a basic health check.

    Args:
        db: MongoDB database connection

    Returns:
        dict: Collection name -> document count
    """
    counts = {}
    for coll_name in required_dbs:
        try:
            counts[coll_name] = db.get_collection(coll_name).count_documents({})
        except Exception:
            counts[coll_name] = -1

    return counts


def restart_heroku_dynos():
    """
    Restart Heroku dynos to prevent memory leaks (cloud only).

    Returns:
        bool: True if restart was attempted
    """
    app_name = os.getenv("HEROKU_APP_NAME")
    heroku_token = os.getenv("HEROKU_API_TOKEN") or os.getenv("HEROKU_TOKEN")

    if not app_name or not heroku_token:
        return False

    try:
        import requests
        response = requests.delete(
            f"https://api.heroku.com/apps/{app_name}/dynos",
            headers={
                "Authorization": f"Bearer {heroku_token}",
                "Accept": "application/vnd.heroku+json; version=3",
            },
        )
        return response.status_code in [200, 202]
    except Exception:
        return False


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Run all daily maintenance tasks."""
    start = time.time()
    print("=" * 60)
    print("DAILY CRON JOB - Tradier Copy Bot")
    print(f"Time: {dt.datetime.now(tz=utc_timezone).isoformat()}")
    print("=" * 60)

    db = connect_mongo()
    failed_tasks = []
    total_tasks = 8

    # 1. Clean up old logs
    print(f"\n[1/{total_tasks}] Cleaning up old logs (>16 hours)...")
    try:
        removed = cleanup_old_logs(db, hours_limit=16)
        print(f"    Removed: {removed} log entries")
    except Exception as e:
        print(f"    FAILED: {e}")
        failed_tasks.append("cleanup_old_logs")

    # 2. Clean up old trade history
    print(f"\n[2/{total_tasks}] Cleaning up old trade history (>90 days)...")
    try:
        removed = cleanup_old_history(db, days_limit=90)
        print(f"    Removed: {removed} history entries")
    except Exception as e:
        print(f"    FAILED: {e}")
        failed_tasks.append("cleanup_old_history")

    # 3. Clean up orphaned trades
    print(f"\n[3/{total_tasks}] Cleaning up orphaned trades...")
    try:
        removed = cleanup_orphaned_trades(db)
        print(f"    Removed: {removed} orphaned trade documents")
    except Exception as e:
        print(f"    FAILED: {e}")
        failed_tasks.append("cleanup_orphaned_trades")

    # 4. Clean up orphaned history
    print(f"\n[4/{total_tasks}] Cleaning up orphaned history...")
    try:
        removed = cleanup_orphaned_history(db)
        print(f"    Removed: {removed} orphaned history documents")
    except Exception as e:
        print(f"    FAILED: {e}")
        failed_tasks.append("cleanup_orphaned_history")

    # 5. Clean up orphaned logs
    print(f"\n[5/{total_tasks}] Cleaning up orphaned logs...")
    try:
        removed = cleanup_orphaned_logs(db)
        print(f"    Removed: {removed} orphaned log documents")
    except Exception as e:
        print(f"    FAILED: {e}")
        failed_tasks.append("cleanup_orphaned_logs")

    # 6. Verify indexes
    print(f"\n[6/{total_tasks}] Verifying database indexes...")
    try:
        count = verify_indexes(db)
        print(f"    Verified: {count} indexes")
    except Exception as e:
        print(f"    FAILED: {e}")
        failed_tasks.append("verify_indexes")

    # 7. Database health check
    print(f"\n[7/{total_tasks}] Database health check...")
    try:
        counts = database_health_check(db)
        for coll, count in counts.items():
            print(f"    {coll}: {count} documents")
    except Exception as e:
        print(f"    FAILED: {e}")
        failed_tasks.append("database_health_check")

    # 8. Restart Heroku dynos (cloud only)
    print(f"\n[8/{total_tasks}] Restarting Heroku dynos...")
    try:
        if os.getenv("DYNO") or os.getenv("HEROKU_APP_NAME"):
            restarted = restart_heroku_dynos()
            print(f"    {'Restart sent' if restarted else 'Restart failed'}")
        else:
            print("    Skipped (not running on Heroku)")
    except Exception as e:
        print(f"    FAILED: {e}")
        failed_tasks.append("restart_heroku_dynos")

    # Summary
    elapsed = time.time() - start
    print("\n" + "=" * 60)
    if failed_tasks:
        print(f"DAILY CRON COMPLETE — {len(failed_tasks)} task(s) failed: {failed_tasks}")
    else:
        print(f"DAILY CRON COMPLETE — all {total_tasks} tasks passed")
    print(f"Elapsed: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()

# END
