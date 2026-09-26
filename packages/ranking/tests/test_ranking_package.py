"""Smoke test: the package installs, imports and exports the contract functions."""

import importlib

CONTRACT_FUNCTION_NAMES = ["rank_providers", "trust_summary", "price_range"]


def test_ranking_package_exports_the_contract_functions():
    ranking = importlib.import_module("ranking")
    for function_name in CONTRACT_FUNCTION_NAMES:
        assert callable(getattr(ranking, function_name))
