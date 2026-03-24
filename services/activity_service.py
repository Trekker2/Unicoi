"""
Activity Service for Tradier Copy Bot

Abstracts database calls for activity log management.

Key Functions:
    - do_get_logs: Get all log entries
    - do_delete_log: Delete a specific log entry
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from scripts.database_manager import connect_mongo


# ==============================================================================
# SERVICE FUNCTIONS
# ==============================================================================

def do_get_logs():
    """
    Get all log entries, most recent first.

    Returns:
        list: List of log entry dicts with 'datetime' and 'log' keys
    """
    db = connect_mongo()
    log_docs = list(db.get_collection("logs").find({}))

    all_logs = []
    for doc in log_docs:
        username = doc.get("username", "system")
        for log in doc.get("logs", []):
            log["username"] = username
            all_logs.append(log)

    # Sort by datetime descending, master logs before follower logs at same timestamp
    def log_sort_key(x):
        dt_str = x.get("datetime", "")
        log_text = x.get("log", "")
        # Master logs get priority (0) over follower logs (1) at the same timestamp
        role_order = 0 if "Master:" in log_text or "Master " in log_text else 1
        return (dt_str, role_order)
    all_logs.sort(key=log_sort_key, reverse=True)
    return all_logs


def do_delete_log(username, log_datetime):
    """
    Delete a specific log entry.

    Args:
        username: Username associated with the log
        log_datetime: Datetime string of the log to delete

    Returns:
        tuple: (success: bool, message: str)
    """
    db = connect_mongo()
    result = db.get_collection("logs").update_one(
        {"username": username},
        {"$pull": {"logs": {"datetime": log_datetime}}},
    )
    if result.modified_count > 0:
        return True, "Log entry deleted"
    return False, "Log entry not found"

# END
