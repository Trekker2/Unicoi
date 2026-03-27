"""
Accounts Service for Tradier Copy Bot

Abstracts database and API calls for account management.

Key Functions:
    - do_get_accounts: Get all accounts
    - do_post_account: Add a new account
    - do_delete_account: Remove an account
    - do_set_master: Set master account (only one allowed)
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from scripts.database_manager import connect_mongo, serialize_for_mongo
from integrations.tradier_ import validate_account_trd


# ==============================================================================
# SERVICE FUNCTIONS
# ==============================================================================

def do_get_accounts():
    """Get all trading accounts from the database, master first."""
    db = connect_mongo()
    accounts = list(db.get_collection("accounts").find({}))
    accounts.sort(key=lambda a: (0 if a.get("is_master", False) else 1))
    return accounts


def do_post_account(alias, account_number, api_key, username=""):
    """
    Add a new trading account after validating credentials.

    Args:
        alias: Display name for the account
        account_number: Tradier account number
        api_key: Tradier API key
        username: App user who owns this account

    Returns:
        tuple: (success: bool, message: str)
    """
    db = connect_mongo()

    # Check duplicate
    existing = db.get_collection("accounts").find_one({"account_number": account_number})
    if existing:
        return False, f"Account {account_number} already exists"

    # Validate credentials — checks API key AND account number ownership
    validation = validate_account_trd(trd_account=account_number, trd_api=api_key)
    if "error" in validation:
        return False, f"Validation failed: {validation['error']}"

    # Verify the account number belongs to this API key
    profile = validation.get("profile", {})
    profile_account = profile.get("account", {})
    if isinstance(profile_account, dict):
        profile_accounts = [profile_account]
    elif isinstance(profile_account, list):
        profile_accounts = profile_account
    else:
        profile_accounts = []
    valid_numbers = [a.get("account_number", "") for a in profile_accounts]
    if account_number not in valid_numbers:
        return False, f"Account {account_number} not found under this API key"

    # Auto-set first account as master
    existing_count = db.get_collection("accounts").count_documents({})
    is_master = existing_count == 0

    # Insert account
    account = serialize_for_mongo({
        "alias": alias,
        "account_number": account_number,
        "api_key": api_key,
        "username": username,
        "is_master": is_master,
    })
    db.get_collection("accounts").insert_one(account)
    master_note = " (set as master)" if is_master else ""
    return True, f"Account {alias} ({account_number}) added successfully{master_note}"


def do_delete_account(account_number):
    """
    Delete an account by account number.

    Args:
        account_number: Tradier account number to delete

    Returns:
        tuple: (success: bool, message: str)
    """
    db = connect_mongo()
    result = db.get_collection("accounts").delete_one({"account_number": account_number})
    if result.deleted_count > 0:
        # Clean up related data
        db.get_collection("trades").delete_many({"account_number": account_number})
        db.get_collection("history").delete_many({"account_number": account_number})
        return True, f"Account {account_number} deleted"
    return False, f"Account {account_number} not found"


def do_set_master(account_number):
    """
    Set an account as the master (only one allowed).

    Args:
        account_number: Account number to set as master

    Returns:
        tuple: (success: bool, message: str)
    """
    db = connect_mongo()

    # Clear all master flags
    db.get_collection("accounts").update_many({}, {"$set": {"is_master": False}})

    # Set new master
    result = db.get_collection("accounts").update_one(
        {"account_number": account_number},
        {"$set": {"is_master": True}},
    )
    if result.modified_count > 0:
        return True, f"Account {account_number} set as master"
    return False, f"Account {account_number} not found"

# END
