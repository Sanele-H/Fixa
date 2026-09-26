"""Smoke test: the package installs and imports. Replace with real tests as the stubs arrive."""

import importlib


def test_ranking_package_imports():
    assert importlib.import_module("ranking") is not None
