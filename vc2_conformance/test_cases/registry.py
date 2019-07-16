"""
:py:mod:`vc2_conformance.test_cases.registry`: Test-caes registration logic
===========================================================================

This module contains the logic related to the registration of test cases
defined in the rest of the :py:mod:`vc2_conformance.test_cases` module.


Registering test cases
----------------------

Test cases should be registered using the :py:func:`test_case` decorator like
so::

    >>> from vc2_conformance.test_case.registry import test_case
    >>> from vc2_conformance.bitstream import Sequence
    
    >>> @test_case
    >>> def my_test_sequence():
    ...     return Sequence(...)

Test cases may also be parameterised (similar to test parameterisation in
Py.Test) to result in several similar cases being produced::

    >>> from vc2_conformance.tables import BaseVideoFormats
    
    >>> @test_case(parameters=("base_video_format", list(BaseVideoFormats)))
    >>> def check_base_video_format_support(base_video_format):
    ...     return Sequence(...)

Test cases which are designed to violate bitstream rules may be marked as
expected to fail. The xfail argument should be provided with the relevant
:py:mod:`vc2_conformance.decoder.exceptions` exception type. This will be
automatically checked by the vc2_conformance test suite::

    >>> from vc2_conformance.decoder import BadParseCode
    
    >>> @test_case(xfail=BadParseCode)
    >>> def test_case_with_invalid_parse_code():
    ...     return Sequence(...)

In cases where some (but not all) test parameterisations are expected to fail,
an :py:class:`XFail` object may be returned to indicate those cases which may
fail.

    >>> from vc2_conformance.decoder import NoQuantisationMatrixAvailable
    
    >>> @test_case(parameters=("dwt_depth", range(10)))
    >>> def conflicting_test_sequence(dwt_depth):
    ...     if dwt_depth > 4:
    ...         return XFail(Sequence(...), reason=NoQuantisationMatrixAvailable)
    ...     else:
    ...         return Sequence(...)

Finally, by returning None, test cases which should be skipped or ignored
(rather than XFailed) may be marked. For example, to skip over 'impossible'
parameter combinations.

    >>> @test_case(parameters=[
    ...     ("dwt_depth", range(4)),
    ...     ("dwt_depth_ho", range(4)),
    ... ])
    >>> def conflicting_test_sequence(dwt_depth):
    ...     if dwt_depth + dwt_depth_ho > 4:
    ...         return None
    ...     else:
    ...         return Sequence(...)
"""


from collections import namedtuple, OrderedDict

from contextlib import contextmanager

from functools import wraps, partial

from itertools import product, chain

import re


__all__ = [
    "XFail",
    "test_case_registry",
    "test_group",
    "test_case",
]


XFail = namedtuple("XFail", "sequence,error")
"""
To be returned by a test case function when a particular test is expected to
fail.

Parameters
==========
sequence : :py:class:`vc2_conformance.bitstream.Sequence`
    The test case itself.
error : :py:class:`Exception`
    The :py:mod:`vc2_conformance.decoder.exceptions` exception type which this
    test case is expected to violate.
"""


def force_xfail(func, error):
    """
    Function wrapper which wraps the original function's output in
    :py:class:`XFail` except when the original function has already returned
    :py:class:`XFail` or None.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        out = func(*args, **kwargs)
        if out is None or isinstance(out, XFail):
            return out
        else:
            return XFail(out, error)
    
    return wrapper


def expand_parameters(parameter_spec):
    """
    Expand a parameter set specification into a list of kwargs dictionaries.
    
    Input and output examples:
    
    * ``("param", [1, 2, 3])``
        * ``{"param": 1}``
        * ``{"param": 2}``
        * ``{"param": 3}``
    * ``("param_a, param_b", [(1, "one"), (2, "two"), (3, "three")])``
        * ``{"param_a": 1, "param_b": "one"}``
        * ``{"param_a": 2, "param_b": "two"}``
        * ``{"param_a": 3, "param_b": "three"}``
    * ``[("param_a", [1, 2, 3]), ("param_b", ["a", "b"])]``
        * ``{"param_a": 1, "param_b": "a"}``
        * ``{"param_a": 1, "param_b": "b"}``
        * ``{"param_a": 2, "param_b": "a"}``
        * ``{"param_a": 2, "param_b": "b"}``
        * ``{"param_a": 3, "param_b": "a"}``
        * ``{"param_a": 3, "param_b": "b"}``
    * ``[("param_a", [1, 2, 3]), ("param_b, param_c", [("a", True), ("b", False)])]``
        * ``{"param_a": 1, "param_b": "a", "param_c": True}``
        * ``{"param_a": 1, "param_b": "b", "param_c": False}``
        * ``{"param_a": 2, "param_b": "a", "param_c": True}``
        * ``{"param_a": 2, "param_b": "b", "param_c": False}``
        * ``{"param_a": 3, "param_b": "a", "param_c": True}``
        * ``{"param_a": 3, "param_b": "b", "param_c": False}``
    """
    # Cast to list of (param_names, values) pairs
    if len(parameter_spec) == 2 and isinstance(parameter_spec[0], str):
        parameter_spec = [parameter_spec]
    
    # Normalise all param_names strings into lists of names (and all value lists
    # into lists of tuples of values, in the case where param_names has only
    # one entry)
    uniform_parameter_specs = []
    for param_names, values in parameter_spec:
        if "," in param_names:
            param_names = re.split(r"\s*,\s*", param_names.strip(", "))
        else:
            param_names = [param_names]
            values = [(v, ) for v in values]
        uniform_parameter_specs.append((param_names, values))
    
    # Expand all cases
    out = []
    for values in product(*(values for (names, values) in uniform_parameter_specs)):
        kwargs = OrderedDict()
        for name, value in zip(
            chain(*(n for (n, v) in uniform_parameter_specs)),
            chain(*values),
        ):
            kwargs[name] = value
        out.append(kwargs)
    
    return out


class TestCaseRegistry(object):
    """
    A registry of test cases.
    
    This class is intended to be used as a singleton like so::
    
        >>> # In this module
        >>> test_case_registry = TestCaseRegistry()
        >>> test_group = test_case_registry.test_group
        >>> test_case = test_case_registry.test_case
        
        >>> # In a test-case defining module
        >>> from vc2_conformance.test_cases.registry import test_group, test_case
        >>> from vc2_conformance.tables import ParseCodes
        >>> from vc2_conformance.bitstream import Sequence, DataUnit, ParseInfo
        >>> with test_group("minimal_sequences"):
        ...     @test_case(xfail="Missing sequence header")
        ...     def empty_sequence():
        ...         return Sequence(data_units=[
        ...             DataUnit(parse_info=ParseInfo(
        ...                 parse_code=ParseCodes.end_of_sequence
        ...             ))
        ...         )])
    """
    
    def __init__(self):
        # The test case returning functions for each case registered so far.
        #
        # {name: function() -> Sequence, ...}
        self.test_cases = OrderedDict()
        
        # The current stack of nested group names
        self._group_stack = []
    
    @contextmanager
    def test_group(self, name):
        """
        A context manager which prefixes all test cases defined inside it with
        the provided name. For consistency, group names should be restricted to
        valid Python identifiers.
        """
        self._group_stack.append(name)
        try:
            yield
        finally:
            self._group_stack.pop()
    
    def test_case(self, func=None, **kwargs):
        """
        A decorator which registers the decorated function as a test caes in
        this registry.
        
        Parameters
        ==========
        xfail : None or :py:exc:`vc2_conformance.decoder.ConformanceError`
            If a :py:exc:`vc2_conformance.decoder.ConformanceError`, this test
            case (including any parameterizations) will be marked as expected
            to fail with the conformance checking decoder throwing the provided
            exception type.
            
            For tests which are expected to pass, This argument should be
            absent or set to None. For parameterized test cases, individual
            cases may return :py:class:`XFail` to indicate that particular case
            is expected to fail.
        parameters : see :py:func:`expand_parameters`
            If given, should specify a set of keyword parameters 
        """
        def wrap(func):
            xfail = kwargs.pop("xfail", None)
            parameters = kwargs.pop("parameters", None)
            if kwargs:
                raise TypeError("test_case got unexpected keyword argument(s): {}".format(
                    ", ".join(map(repr, kwargs.keys()))
                ))
            
            name = ":".join(self._group_stack + [func.__name__])
            
            if xfail is not None:
                func = force_xfail(func, xfail)
            
            if parameters is None:
                assert name not in self.test_cases
                self.test_cases[name] = func
            else:
                for parameters in expand_parameters(parameters):
                    this_name = "{}[{}]".format(
                        name,
                        ", ".join(
                            "{}={!r}".format(key, value)
                            for key, value in parameters.items()
                        )
                    )
                    assert this_name not in self.test_cases
                    self.test_cases[this_name] = wraps(func)(partial(func, **parameters))
            
            return func
        
        # Support use as both @test_case and @test_case(foo, bar)
        if func is None:
            return wrap
        else:
            return wrap(func)


test_case_registry = TestCaseRegistry()
"""
The singleton :py:class:`TestCaseRegistry` instance used to register all of the
test cases in this module.
"""

test_group = test_case_registry.test_group
test_case = test_case_registry.test_case
