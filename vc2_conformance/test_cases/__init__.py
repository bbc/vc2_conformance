"""
:py:mod:`vc2_conformance.test_cases`: Test case generation routines for VC-2 codecs
===================================================================================

This module contains a collection of routines for generating test cases for
VC-2 encoders and decoders.
"""

# Import all of the test-case containing modules to ensure all test cases are
# registered with the registry.
from vc2_conformance.test_cases import cases_metadata

from vc2_conformance.test_cases.registry import test_case_registry, XFail
