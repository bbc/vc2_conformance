"""
:py:mod:`vc2_conformance.decoder.assertions`: Assertions functions for conformance checks
=========================================================================================
"""


def assert_in_enum(value, enum, exception_type):
    """
    Check to see if a value is a member of the provided assertion type. If it
    is not, throws an exception of the given type with the value as argument.
    """
    try:
        enum(value)
    except ValueError:
        raise exception_type(value)
