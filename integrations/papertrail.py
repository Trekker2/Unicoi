"""
Papertrail Module - Log Search via SolarWinds Observability API

This module provides functions for querying logs via the SolarWinds Observability API.
It enables programmatic access to application logs for debugging and monitoring.

Environment Variables:
    PT_API_TOKEN: SolarWinds Observability API token for log search
                  Get from: SolarWinds Observability > Settings > API Tokens

Key Functions:
    - search_logs: Search logs by query string within a time range
    - get_logs: Get all logs within a time range
    - search_logs_hours_ago: Search logs from the last N hours
    - search_logs_days_ago: Search logs from the last N days

API Documentation:
    https://documentation.solarwinds.com/en/success_center/observability/content/intro/logs/
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

# Standard Library Imports
from datetime import datetime, timedelta, timezone
import os

import requests


# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================

papertrail_url = "https://api.na-01.cloud.solarwinds.com"
logs_url = f"{papertrail_url}/v1/logs"

# ==============================================================================
# API AUTHENTICATION
# ==============================================================================

def get_headers(api_token = None):
    """
    Generate authentication headers for Papertrail API requests.

    Args:
        api_token (str): Papertrail API token. If None, reads from PT_API_TOKEN env var.

    Returns:
        dict: HTTP headers for API requests

    Example:
        >>> headers = get_headers()
        >>> headers = get_headers("your-api-token")
    """
    if api_token is None:
        api_token = os.environ.get("PT_API_TOKEN", "")

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_token}"
    }
    return headers

# ==============================================================================
# LOG SEARCH FUNCTIONS
# ==============================================================================

def search_logs(query, start_time = None, end_time = None, page_size = 100, api_token = None):
    """
    Search logs by query string within a time range.

    Args:
        query (str): Search query string (e.g., "stale", "ERROR", "kalshi")
        start_time (str): ISO format start time (e.g., "2025-12-12T14:00:00Z")
        end_time (str): ISO format end time (e.g., "2025-12-12T22:00:00Z")
        page_size (int): Number of results per page (max 10000)
        api_token (str): Papertrail API token. If None, reads from PT_API_TOKEN env var.

    Returns:
        list: List of log entries matching the query

    Example:
        >>> logs = search_logs("ERROR", "2026-03-19T00:00:00Z", "2026-03-19T12:00:00Z")
        >>> for log in logs:
        ...     print(f"{log['time']} - {log['message']}")
    """
    headers = get_headers(api_token)

    params = {
        "filter": query,
        "pageSize": page_size
    }

    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    response = requests.get(logs_url, headers = headers, params = params)

    if response.status_code == 200:
        data = response.json()
        return data.get("logs", [])
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []

def get_logs(start_time = None, end_time = None, page_size = 100, api_token = None):
    """
    Get all logs within a time range (no filter).

    Args:
        start_time (str): ISO format start time
        end_time (str): ISO format end time
        page_size (int): Number of results per page
        api_token (str): Papertrail API token

    Returns:
        list: List of log entries

    Example:
        >>> logs = get_logs("2026-03-19T14:00:00Z", "2026-03-19T15:00:00Z")
    """
    headers = get_headers(api_token)

    params = {"pageSize": page_size}

    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    response = requests.get(logs_url, headers = headers, params = params)

    if response.status_code == 200:
        data = response.json()
        return data.get("logs", [])
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []

def search_logs_hours_ago(query, hours = 1, page_size = 100, api_token = None):
    """
    Search logs from the last N hours.

    Args:
        query (str): Search query string
        hours (int): Number of hours to look back
        page_size (int): Number of results per page
        api_token (str): Papertrail API token

    Returns:
        list: List of log entries matching the query

    Example:
        >>> logs = search_logs_hours_ago("ERROR", hours=2)
    """
    end_time = datetime.now(timezone.utc).replace(tzinfo = None)
    start_time = end_time - timedelta(hours = hours)

    return search_logs(
        query = query,
        start_time = start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_time = end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        page_size = page_size,
        api_token = api_token
    )

def search_logs_days_ago(query, days = 1, page_size = 100, api_token = None):
    """
    Search logs from N days ago (1 hour window).

    Args:
        query (str): Search query string
        days (int): Number of days to look back
        page_size (int): Number of results per page
        api_token (str): Papertrail API token

    Returns:
        list: List of log entries matching the query

    Example:
        >>> logs = search_logs_days_ago("kalshi", days=7)
    """
    end_time = datetime.now(timezone.utc).replace(tzinfo = None)
    start_time = end_time - timedelta(days = days)

    return search_logs(
        query = query,
        start_time = start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_time = (start_time + timedelta(hours = 1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        page_size = page_size,
        api_token = api_token
    )

def print_logs(logs, max_message_length = 120):
    """
    Pretty print log entries.

    Args:
        logs (list): List of log entries from search
        max_message_length (int): Truncate messages longer than this

    Example:
        >>> logs = search_logs("stale", ...)
        >>> print_logs(logs)
    """
    for log in logs:
        time = log.get("time", "")
        message = log.get("message", "")
        if len(message) > max_message_length:
            message = message[:max_message_length] + "..."
        print(f"{time} - {message}")

# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def search_stale(start_time, end_time, api_token = None):
    """Search for stale data warnings."""
    return search_logs("Stale", start_time, end_time, api_token = api_token)

def search_warnings(start_time, end_time, api_token = None):
    """Search for WARNING messages."""
    return search_logs("WARNING", start_time, end_time, api_token = api_token)

def search_errors(start_time, end_time, api_token = None):
    """Search for Error messages."""
    return search_logs("Error", start_time, end_time, api_token = api_token)

def search_ticker(ticker, start_time, end_time, api_token = None):
    """Search for logs related to a specific ticker."""
    return search_logs(ticker, start_time, end_time, api_token = api_token)

def search_user(username, start_time, end_time, api_token = None):
    """Search for logs related to a specific user."""
    return search_logs(username, start_time, end_time, api_token = api_token)

# ==============================================================================
# TEST FUNCTIONS
# ==============================================================================

def test_live_search():
    """
    Test live log search functionality.
    Searches recent logs for any activity.
    """
    import sys
    sys.stdout.reconfigure(encoding = "utf-8", errors = "replace")

    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("TEST: Live Log Search")
    print("=" * 60)

    token = os.environ.get("PT_API_TOKEN", "")
    if not token:
        print("ERROR: PT_API_TOKEN not set in environment")
        return False

    print(f"Token found: {token[:8]}...")

    logs = search_logs_hours_ago("", hours = 1, page_size = 10)
    print(f"Logs found in last hour: {len(logs)}")

    if logs:
        print("\nSample logs:")
        for log in logs[:5]:
            time = log.get("time", "")
            msg = log.get("message", "")[:80]
            print(f"  {time} - {msg}")
        return True

    return False

def test_historical_search():
    """
    Test historical log search.
    Searches logs from a week ago.
    """
    import sys
    sys.stdout.reconfigure(encoding = "utf-8", errors = "replace")

    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("TEST: Historical Log Search")
    print("=" * 60)

    token = os.environ.get("PT_API_TOKEN", "")
    if not token:
        print("ERROR: PT_API_TOKEN not set in environment")
        return False

    print(f"Token found: {token[:8]}...")

    logs = search_logs_days_ago("", days = 7, page_size = 10)
    end_time = datetime.now(timezone.utc).replace(tzinfo = None)
    start_time = end_time - timedelta(days = 7)
    print(f"Logs found from {start_time.strftime('%Y-%m-%d')}: {len(logs)}")

    if logs:
        print("\nSample logs:")
        for log in logs[:3]:
            time = log.get("time", "")
            msg = log.get("message", "")[:80]
            print(f"  {time} - {msg}")
        return True

    print("No historical logs found (may be outside retention window)")
    return False

def test_all():
    """Run all tests."""
    import sys
    sys.stdout.reconfigure(encoding = "utf-8", errors = "replace")

    from dotenv import load_dotenv
    load_dotenv()

    print("\n" + "=" * 60)
    print("PAPERTRAIL MODULE TESTS")
    print("=" * 60 + "\n")

    results = {}

    results["live_search"] = test_live_search()
    print()

    results["historical_search"] = test_historical_search()
    print()

    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    return all(results.values())

if __name__ == "__main__":
    test_all()

# END
