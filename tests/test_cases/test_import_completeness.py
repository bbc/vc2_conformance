"""
Check that all of the testcase-containing submodules are explicitly imported.
"""

import pytest

import pkgutil

import importlib

import inspect

from vc2_conformance.test_cases import (
    ENCODER_TEST_CASE_GENERATOR_REGISTRY,
    DECODER_TEST_CASE_GENERATOR_REGISTRY,
)


@pytest.fixture(scope="module")
def ensure_all_test_cases_loaded():
    # Search for and load all vc2_conformance.test_cases submodules are loaded
    # (and therefore ensure they're registered with the Registry)
    for _module_loader, name, _ispkg in pkgutil.walk_packages(onerror=lambda err: None):
        if name.startswith("vc2_conformance.test_cases."):
            importlib.import_module(name)


@pytest.mark.parametrize(
    "registry,expected_parent",
    [
        (ENCODER_TEST_CASE_GENERATOR_REGISTRY, "encoder"),
        (DECODER_TEST_CASE_GENERATOR_REGISTRY, "decoder"),
    ],
)
def test_all_imports_present(ensure_all_test_cases_loaded, registry, expected_parent):
    for fn in registry.iter_registered_functions():
        module = inspect.getmodule(fn)
        module_path = module.__name__.split(".")

        # Check the test case is defined is in the expected submodule
        assert len(module_path) == 4
        parent_module_path = ["vc2_conformance", "test_cases", expected_parent]
        assert module_path[:3] == parent_module_path

        # Check the file it is in is imported
        parent_module = importlib.import_module(".".join(parent_module_path))
        parent_module_source = open(inspect.getsourcefile(parent_module)).read()

        # NB: The following check is fairly crude but should be good enough to
        # catch simple mistakes.
        assert module.__name__ in parent_module_source
