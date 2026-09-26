"""Smoke test: the package installs and imports. Replace with real tests as the stubs arrive."""

import importlib


def test_lang_package_imports():
    assert importlib.import_module("lang") is not None
