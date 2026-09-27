"""Smoke test: the package installs, imports and exports the contract functions."""

import importlib

CONTRACT_FUNCTION_NAMES = ["build_record", "verify_record"]


def test_record_package_exports_the_contract_functions():
    record = importlib.import_module("record")
    for function_name in CONTRACT_FUNCTION_NAMES:
        assert callable(getattr(record, function_name))
