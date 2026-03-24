"""
Integration Scenario Runner for Tradier Copy Bot

Executes YAML-defined integration scenarios that test the full copy pipeline
with mocked broker backend. Each scenario specifies setup state, trigger events,
and expected outcomes.

Usage:
    python -m tests.scenario_runner --all
    python -m tests.scenario_runner --scenario "Single equity order copied to one follower"
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import argparse
import datetime as dt
import os
import sys
import time
import yaml
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import (
    get_default_settings, utc_timezone, market_timezone,
    bad_statuses, open_statuses,
)
from scripts.copy_manager import (
    run_copy_cycle, get_new_master_orders,
    reconstruct_single_order, reconstruct_multileg_order,
    forward_order_to_follower, check_master_cancellations,
)


# ==============================================================================
# SCENARIO EXECUTION
# ==============================================================================

class MockDB:
    """In-memory mock MongoDB for scenario testing."""

    def __init__(self):
        self.collections = {}

    def get_collection(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]


class MockCollection:
    """In-memory mock MongoDB collection."""

    def __init__(self, name):
        self.name = name
        self.docs = []

    def find(self, filter_dict=None, **kwargs):
        if not filter_dict:
            return list(self.docs)
        return [d for d in self.docs if all(
            d.get(k) == v if not isinstance(v, dict) else self._match_filter(d.get(k), v)
            for k, v in filter_dict.items()
        )]

    def find_one(self, filter_dict=None, *, filter=None, **kwargs):
        # pymongo uses both positional and 'filter=' keyword arg
        actual_filter = filter_dict or filter
        results = self.find(actual_filter)
        return results[0] if results else None

    def insert_one(self, doc):
        self.docs.append(doc)

    def update_one(self, filter=None, update=None, upsert=False, **kwargs):
        target = self.find_one(filter)
        if target is None and upsert:
            target = dict(filter) if filter else {}
            self.docs.append(target)
        if target and update:
            if "$set" in update:
                target.update(update["$set"])
            if "$push" in update:
                for key, value in update["$push"].items():
                    if key not in target:
                        target[key] = []
                    target[key].append(value)
            if "$pull" in update:
                for key, match in update["$pull"].items():
                    if key in target:
                        if isinstance(match, dict):
                            target[key] = [
                                item for item in target[key]
                                if not all(item.get(k) == v for k, v in match.items())
                            ]
                        else:
                            target[key] = [item for item in target[key] if item != match]
        return MagicMock(modified_count=1 if target else 0)

    def update_many(self, filter_dict=None, update=None):
        for doc in self.docs:
            if "$set" in update:
                doc.update(update["$set"])

    def delete_one(self, filter_dict):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not all(d.get(k) == v for k, v in filter_dict.items())]
        return MagicMock(deleted_count=before - len(self.docs))

    def delete_many(self, filter_dict):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not all(d.get(k) == v for k, v in filter_dict.items())]
        return MagicMock(deleted_count=before - len(self.docs))

    @staticmethod
    def _match_filter(value, filter_spec):
        if "$ne" in filter_spec:
            return value != filter_spec["$ne"]
        return value == filter_spec


def resolve_time(time_str):
    """Convert time placeholders to actual datetime strings."""
    now = dt.datetime.now(tz=utc_timezone)
    if time_str == "now":
        return now.isoformat()
    elif time_str == "10_minutes_ago":
        return (now - dt.timedelta(minutes=10)).isoformat()
    elif time_str == "1_hour_ago":
        return (now - dt.timedelta(hours=1)).isoformat()
    return time_str


def setup_db(db, setup):
    """Populate mock DB from scenario setup."""
    for account in setup.get("accounts", []):
        db.get_collection("accounts").insert_one(dict(account))

    settings = {**get_default_settings(), **setup.get("settings", {}), "type": "global"}
    db.get_collection("settings").insert_one(settings)

    for hist in setup.get("history", []):
        db.get_collection("history").insert_one(dict(hist))

    for trade in setup.get("trades", []):
        db.get_collection("trades").insert_one(dict(trade))


def run_scenario(scenario):
    """Execute a single scenario and return (passed, details)."""
    name = scenario["name"]
    setup = scenario["setup"]
    trigger = scenario["trigger"]
    expect = scenario["expect"]

    db = MockDB()
    setup_db(db, setup)

    # Resolve time placeholders in trigger orders
    master_orders = []
    for order in trigger.get("master_orders", []):
        order = dict(order)
        if "create_date" in order:
            order["create_date"] = resolve_time(order["create_date"])
        master_orders.append(order)

    # Track forwarded, canceled, and modified orders
    forwarded = []
    canceled = []
    modified = []

    def mock_post_orders(data=None, trd_account=None, trd_api=None):
        forwarded.append({"data": data, "account": trd_account})
        return {"order": {"id": 55555, "status": "pending"}}

    def mock_delete_orders(order_id=None, trd_account=None, trd_api=None):
        canceled.append({"order_id": order_id, "account": trd_account})
        return {"order": {"id": order_id, "status": "ok"}}

    def mock_modify_orders(order_id=None, data=None, trd_account=None, trd_api=None):
        modified.append({"order_id": order_id, "data": data, "account": trd_account})
        return {"order": {"id": order_id, "status": "ok"}}

    with patch("scripts.copy_manager.get_orders_trd", return_value=master_orders), \
         patch("scripts.copy_manager.post_orders_trd", side_effect=mock_post_orders), \
         patch("scripts.copy_manager.delete_orders_trd", side_effect=mock_delete_orders), \
         patch("scripts.copy_manager.modify_orders_trd", side_effect=mock_modify_orders):

        result = run_copy_cycle(db, [])

    # Validate expectations
    errors = []

    if "cycle_result" in expect:
        if result != expect["cycle_result"]:
            errors.append(f"cycle_result: expected {expect['cycle_result']}, got {result}")

    if "orders_forwarded" in expect:
        if len(forwarded) != expect["orders_forwarded"]:
            errors.append(f"orders_forwarded: expected {expect['orders_forwarded']}, got {len(forwarded)}")

    if "forwarded_to" in expect:
        actual_accounts = [f["account"] for f in forwarded]
        for acct in expect["forwarded_to"]:
            if acct not in actual_accounts:
                errors.append(f"forwarded_to: {acct} not in forwarded accounts {actual_accounts}")

    if "forwarded_data" in expect and forwarded:
        data = forwarded[0]["data"]
        for key, value in expect["forwarded_data"].items():
            if str(data.get(key)) != str(value):
                errors.append(f"forwarded_data[{key}]: expected {value}, got {data.get(key)}")

    if "quantities_by_account" in expect:
        for acct, expected_qty in expect["quantities_by_account"].items():
            matching = [f for f in forwarded if f["account"] == acct]
            if not matching:
                errors.append(f"quantities_by_account: no order forwarded to {acct}")
            else:
                actual_qty = matching[0]["data"].get("quantity")
                if actual_qty != expected_qty:
                    errors.append(f"quantities_by_account[{acct}]: expected {expected_qty}, got {actual_qty}")

    if "cancellations_sent" in expect:
        if len(canceled) != expect["cancellations_sent"]:
            errors.append(f"cancellations_sent: expected {expect['cancellations_sent']}, got {len(canceled)}")

    if "canceled_order_ids" in expect:
        actual_ids = [c["order_id"] for c in canceled]
        for oid in expect["canceled_order_ids"]:
            if oid not in actual_ids:
                errors.append(f"canceled_order_ids: {oid} not in {actual_ids}")

    if "modifications_sent" in expect:
        if len(modified) != expect["modifications_sent"]:
            errors.append(f"modifications_sent: expected {expect['modifications_sent']}, got {len(modified)}")

    if "modified_order_ids" in expect:
        actual_ids = [m["order_id"] for m in modified]
        for oid in expect["modified_order_ids"]:
            if oid not in actual_ids:
                errors.append(f"modified_order_ids: {oid} not in {actual_ids}")

    if "modified_data" in expect and modified:
        data = modified[0]["data"]
        for key, value in expect["modified_data"].items():
            if str(data.get(key)) != str(value):
                errors.append(f"modified_data[{key}]: expected {value}, got {data.get(key)}")

    if "forwarded_symbols" in expect:
        actual_symbols = [f["data"].get("symbol") for f in forwarded]
        if actual_symbols != expect["forwarded_symbols"]:
            errors.append(f"forwarded_symbols: expected {expect['forwarded_symbols']}, got {actual_symbols}")

    passed = len(errors) == 0
    return passed, errors


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Run integration scenarios")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--scenario", type=str, help="Run specific scenario by name")
    parser.add_argument("--file", type=str, default=None, help="YAML file to load")
    args = parser.parse_args()

    # Find scenario files
    scenarios_dir = os.path.join(os.path.dirname(__file__), "scenarios")
    if args.file:
        yaml_files = [args.file]
    else:
        yaml_files = [
            os.path.join(scenarios_dir, f)
            for f in os.listdir(scenarios_dir)
            if f.endswith(".yaml") or f.endswith(".yml")
        ]

    all_scenarios = []
    for yaml_file in yaml_files:
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)
        all_scenarios.extend(data.get("scenarios", []))

    if args.scenario:
        all_scenarios = [s for s in all_scenarios if s["name"] == args.scenario]

    if not all_scenarios:
        print("No scenarios found.")
        return

    # Run scenarios
    start = time.time()
    passed_count = 0
    failed_count = 0

    print(f"\nRunning {len(all_scenarios)} integration scenarios...")
    print("=" * 70)

    for scenario in all_scenarios:
        name = scenario["name"]
        passed, errors = run_scenario(scenario)
        if passed:
            print(f"  PASS  {name}")
            passed_count += 1
        else:
            print(f"  FAIL  {name}")
            for err in errors:
                print(f"        -> {err}")
            failed_count += 1

    elapsed = time.time() - start
    print("=" * 70)
    print(f"\n{passed_count} passed, {failed_count} failed in {elapsed:.2f}s")

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

# END
