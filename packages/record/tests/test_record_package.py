"""Smoke test: the package installs and imports. Replace with real tests as the stubs arrive."""

import importlib


def test_record_package_imports():
    assert importlib.import_module("record") is not None
