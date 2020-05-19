"""
Pytest configuration for verification test suite
"""

import pkgutil

import importlib

from verification.compare import Difference, format_detailed_summary


def pytest_assertrepr_compare(op, left, right):
    """
    Pytest Hook which shows a detailed message when assertions of the following
    form are used::

        assert compare_functions(f1, f2, Identical()) is True

    """
    if op == "is" and isinstance(left, Difference) and right is True:
        return [
            "{} and {} are equivalent".format(left.ref_func, left.imp_func),
            "",
        ] + format_detailed_summary(left).splitlines()


# Ensure all vc2_conformance submodules are loaded (and therefore all
# vc2_conformance.metadata annotations are populated)
for _module_loader, name, _ispkg in pkgutil.walk_packages(onerror=lambda err: None):
    if name.startswith("vc2_conformance."):
        importlib.import_module(name)
