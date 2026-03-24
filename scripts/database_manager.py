"""
Database Manager Module for Tradier Copy Bot

This module provides MongoDB connection management, serialization utilities,
and logging functions for the copy bot system.

Key Functions:
    - serialize_for_mongo: Convert non-serializable Python objects for MongoDB
    - connect_mongo: Get MongoDB database connection from global pool
    - store_log_db: Store log entries in database
    - print_store: Print message and store in database logs
    - cleanup_old_data: Clean up old log entries and history
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import datetime as dt
import decimal
import logging
import os
import time
import traceback
import urllib
import uuid

from enum import Enum
from pymongo import MongoClient
import dotenv
import pytz

from constants import *


# Suppress MongoDB connection pool warnings
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("pymongo.topology").setLevel(logging.ERROR)

# ==============================================================================
# SERIALIZATION UTILITIES
# ==============================================================================

def serialize_for_mongo(doc={}):
    """
    Recursively converts non-serializable values into MongoDB-compatible types.

    Args:
        doc: The document/object to serialize

    Returns:
        A MongoDB-compatible version of the document
    """
    if hasattr(doc, '__dict__') and not isinstance(doc, (dict, list, set, tuple, str, int, float, bool, type(None))):
        return serialize_for_mongo(doc.__dict__)
    if isinstance(doc, dict):
        return {k: serialize_for_mongo(v) for k, v in doc.items()}
    elif isinstance(doc, (list, set, tuple)):
        return [serialize_for_mongo(v) for v in doc]
    elif isinstance(doc, uuid.UUID):
        return str(doc)
    elif isinstance(doc, Enum):
        return str(doc.value)
    elif isinstance(doc, decimal.Decimal):
        return float(doc)
    elif hasattr(doc, 'to_dict') and callable(getattr(doc, 'to_dict')):
        return serialize_for_mongo(doc.to_dict())
    return doc


# ==============================================================================
# DATABASE CONNECTION
# ==============================================================================

_mongo_connection_pool = None
_mongo_database_cache = {}


class MongoPoolWrapper:
    """Wrapper that prevents close() from killing the global pool."""

    def __init__(self, database):
        self._database = database
        self._client_wrapper = MongoClientWrapper(database.client)

    def __getattr__(self, name):
        return getattr(self._database, name)

    @property
    def client(self):
        return self._client_wrapper


class MongoClientWrapper:
    """Wrapper that ignores close() calls to preserve the global pool."""

    def __init__(self, client):
        self._client = client

    def __getattr__(self, name):
        if name == 'close':
            return self._ignore_close
        return getattr(self._client, name)

    def _ignore_close(self):
        pass


def get_mongo_pool():
    """Get or create the global MongoDB connection pool."""
    global _mongo_connection_pool
    if _mongo_connection_pool is None:
        _mongo_connection_pool = _create_mongo_client()
    return _mongo_connection_pool


def get_mongo_database(name=None):
    """Get database from connection pool (cached for efficiency)."""
    global _mongo_database_cache
    pool = get_mongo_pool()
    database_name = name or db_name

    if database_name not in _mongo_database_cache:
        raw_database = pool[database_name]
        _mongo_database_cache[database_name] = MongoPoolWrapper(raw_database)

    return _mongo_database_cache[database_name]


def _create_mongo_client():
    """Create MongoDB client with optimized connection pool settings."""
    if ".env" in os.listdir():
        dotenv.load_dotenv(".env")
    address = os.getenv("MONGO_ADDRESS")
    if not address:
        username = os.getenv("MONGO_USERNAME")
        password = os.getenv("MONGO_PASSWORD")
        cluster = os.getenv("MONGO_CLUSTER")
        port_env = os.getenv("MONGO_PORT")
        if username and password and cluster and port_env:
            username = urllib.parse.quote_plus(username)
            password = urllib.parse.quote_plus(password)
            address = f"mongodb+srv://{username}:{password}@{cluster}.{port_env}.mongodb.net?retryWrites=true&w=majority"
        else:
            address = "mongodb://localhost:27017"

    return MongoClient(
        address,
        maxPoolSize=50,
        minPoolSize=5,
        maxIdleTimeMS=300000,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=30000,
        retryWrites=True,
        retryReads=True,
    )


def connect_mongo(db_name_override=None):
    """
    Get MongoDB database connection from global connection pool.

    Args:
        db_name_override (str): Optional database name override

    Returns:
        MongoDB database connection from pool
    """
    try:
        return get_mongo_database(db_name_override)
    except Exception as e:
        print(f"Error getting MongoDB connection: {str(e)}")
        print(traceback.format_exc())
        global _mongo_connection_pool, _mongo_database_cache
        _mongo_connection_pool = None
        _mongo_database_cache = {}
        return get_mongo_database(db_name_override)


# ==============================================================================
# LOGGING UTILITIES
# ==============================================================================

def store_log_db(db, user, log):
    """
    Store a log entry in the database.

    Args:
        db: MongoDB database connection
        user (str): Username to associate with log
        log (str): Log message text

    Returns:
        dict: MongoDB update result
    """
    filters = {"username": user}
    new_log = {
        "datetime": dt.datetime.now(tz=market_timezone).strftime("%Y-%m-%d %X"),
        "log": log
    }
    updates = {
        "$push": {
            "logs": new_log
        }
    }
    db.get_collection("logs").update_one(filter=filters, update=updates, upsert=True)
    return updates


def print_store(db, user, log):
    """Print a message and store it in the database logs."""
    print(log)
    store_log_db(db, user, log)
    return db


# ==============================================================================
# DATABASE MAINTENANCE
# ==============================================================================

def cleanup_old_data(db=None, hours_limit=16, days_limit=90):
    """
    Clean up old log entries and historical data.

    Args:
        db: MongoDB database connection (connects if None)
        hours_limit (int): Hours to keep logs
        days_limit (int): Days to keep history
    """
    if db is None:
        db = connect_mongo()

    now = dt.datetime.now(tz=market_timezone)

    # Clean logs
    log_dicts = list(db.get_collection("logs").find({}))
    for log_dict in log_dicts:
        logs = log_dict.get("logs", [])
        kept_logs = []
        for log in logs:
            try:
                log_datetime = dt.datetime.strptime(log["datetime"], "%Y-%m-%d %X")
                log_datetime = market_timezone.localize(log_datetime)
                if log_datetime + dt.timedelta(hours=hours_limit) > now:
                    kept_logs.append(log)
            except (ValueError, KeyError):
                kept_logs.append(log)
        updates = {"$set": {"logs": kept_logs}}
        filters = {"username": log_dict.get("username")}
        db.get_collection("logs").update_one(filter=filters, update=updates)

    # Clean history
    history_dicts = list(db.get_collection("history").find({}))
    for history_dict in history_dicts:
        history = history_dict.get("history", [])
        kept_history = []
        for order in history:
            try:
                date_key = "transaction_date" if "transaction_date" in order else "create_date"
                history_datetime = dt.datetime.strptime(str(order.get(date_key, ""))[:19], "%Y-%m-%dT%H:%M:%S")
                history_datetime = market_timezone.localize(history_datetime)
                if history_datetime + dt.timedelta(days=days_limit) > now:
                    kept_history.append(order)
            except (ValueError, KeyError):
                kept_history.append(order)
        updates = {"$set": {"history": kept_history}}
        filters = {"_id": history_dict.get("_id")}
        db.get_collection("history").update_one(filter=filters, update=updates)

    return db

# END
