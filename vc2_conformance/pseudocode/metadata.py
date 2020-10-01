"""
The :py:mod:`vc2_conformance.pseudocode.metadata` module is used to record the
relationship between the functions in the :py:mod:`vc2_conformance` software
and the pseudocode functions in the VC-2 specification documents. This
information has two main uses:

1. To produce more helpful error messages which include cross-references to
   published specifications.
2. To enable automatic verification that the behaviour of this software exactly
   matches the published specifications (see :py:mod:`verification`).


Implementing pseudocode functions
---------------------------------

Functions in the codebase which implement a pseudocode function in the
specification must be labelled as such using the :py:func:`ref_pseudocode`
decorator::

    >>> from vc2_conformance.pseudocode.metadata import ref_pseudocode

    >>> @ref_pseudocode
    ... def parse_info(state):
    ...     '''(10.5.1) Read a parse_info header.'''
    ...     byte_align()
    ...     read_uint_lit(state, 4)
    ...     state["parse_code"] = read_uint_lit(state, 1)
    ...     state["next_parse_offset"] = read_uint_lit(state, 4)
    ...     state["previous_parse_offset"] = read_uint_lit(state, 4)

The :py:func:`ref_pseudocode` decorator will log the existence of the decorated
function, along with the reference to the spec at the start of its docstring.

By default, it is implied that a decorated function does *not* deviate from the
pseudocode -- a fact which is verified by the :py:mod:`verification` module in
the test suite. When a function does deviate (for example for use in
serialisation/deserialisation) or is not defined in the spec, the ``deviation``
argument should be provided. This is used by the :py:mod:`verification` logic
to determine how the function will be verified. See
:ref:`verification-deviation-types` for the allowed values. For example::

    >>> @ref_pseudocode(deviation="serdes")
    ... def parse_parameters(serdes, state):
    ...     '''(11.2.1)'''
    ...     state["major_version"] = serdes.uint("major_version")
    ...     state["minor_version"] = serdes.uint("minor_version")
    ...     state["profile"] = serdes.uint("profile")
    ...     state["level"] = serdes.uint("level")

.. autofunction:: ref_pseudocode


Accessing the metadata
----------------------

After all submodules of :py:mod:`vc2_conformance` have been loaded, the
:py:data:`pseudocode_derived_functions` list will be populated with
:py:class:`PseudocodeDerivedFunction` instances for every pseudocode derived
function annotated with :py:func:`ref_pseudocode`.

.. autoclass:: PseudocodeDerivedFunction
    :members:

.. autodata:: pseudocode_derived_functions
    :annotation: = [PseudocodeDerivedFunction, ...]


Pseudocode tracebacks
---------------------

The :py:func:`make_pseudocode_traceback` function may be used to convert a
Python traceback into a pseudocode function traceback.

.. autofunction:: make_pseudocode_traceback

"""

import re
import inspect

__all__ = [
    "DEFAULT_SPECIFICATION",
    "PseudocodeDerivedFunction",
    "pseudocode_derived_functions",
    "ref_pseudocode",
    "make_pseudocode_traceback",
]


DEFAULT_SPECIFICATION = "SMPTE ST 2042-1:2017"  # The main VC-2 specification
"""
If not otherwise specified, the specification section numbers refer to.
"""


class PseudocodeDerivedFunction(object):
    """
    A record of a pseudocode-derived function within this codebase.

    Parameters
    ==========
    function : function
        The Python function which was derived from a pseudocode function.
    deviation : str or None
        If this function deviates from the pseudocode in any way, indicates the
        nature of this deviation. None indicates that this function exactly
        matches the pseudocode.

        Automatic checks for pseudocode equivalence in the test suite (see
        :py:mod:`verification`) will use this value to determine how exactly
        this function must match the pseudocode for tests to pass. See
        :ref:`verification-deviation-types` for details of values this field
        may hold.
    document, section : str or None
        The name of the document and section defining this function. If None,
        will be extracted from the function docstring. Defaults to the main
        VC-2 specification. If not provided, and not found in the docstring, a
        :py:exc:`TypeError` will be thrown.

        When extracted from a docstring, a reference of one of the following
        forms must be used at the start of the docstring:

        * ``(1.2.3)``: Reference a section in the main VC-2 spec
        * ``(SMPTE ST 20402-2:2017: 1.2.3)``: Reference a section in another
          spec
    name : str or None
        The name of the pseudocode function this function implements. If None,
        the provided function's name will be used.
    """

    def __init__(
        self,
        function,
        deviation=None,
        document=None,
        section=None,
        name=None,
    ):
        # Auto-extract section/document
        if section is None or document is None:
            autodetected_document = None
            autodetected_section = None
            docstring = getattr(function, "__doc__", "")
            match = re.match(r"\s*\(([^\)]+)\)", docstring)
            if match:
                autodetected_document = DEFAULT_SPECIFICATION
                autodetected_section = match.group(1)

                # Also extract the document name, if present
                submatch = re.match(r"(.*)\s*:\s*([^:]+)$", autodetected_section)
                if submatch:
                    autodetected_document = submatch.group(1)
                    autodetected_section = submatch.group(2)

            if section is None:
                section = autodetected_section

            if document is None:
                document = autodetected_document

        if section is None or document is None:
            raise TypeError("No document or section reference could be found.")

        # Auto-extract function name
        if name is None:
            name = getattr(function, "__name__", None)

        self.function = function
        self.deviation = deviation
        self.document = document
        self.section = section
        self.name = name

    @property
    def citation(self):
        """
        A human-readable citation string for this pseudocode function.
        """
        return "{} ({}{})".format(
            self.name,
            (
                "{}: ".format(self.document)
                if self.document != DEFAULT_SPECIFICATION
                else ""
            ),
            self.section,
        )


pseudocode_derived_functions = []
r"""
The complete set of :py:class:`PseudocodeDerivedFunctions
<PseudocodeDerivedFunction>` in this code base, in no particular order.

.. warning::

    This array is only completely populated once every module of
    :py:mod:`vc2_conformance` has been loaded.
"""


def ref_pseudocode(*args, **kwargs):
    """
    Decorator for marking functions which are derived from the VC-2 pseudocode.

    Example usage::

        @ref_pseudocode
        def parse_info(state):
            ''''(10.5.1) Read a parse_info header.'''
            # ...

        @ref_pseudocode("10.5.1", deviation="alternative_implementation")
        def parse_info(state):
            '''Some alternative implementation of parse info.'''

    Parameters
    ==========
    deviation : str or None
        If this function deviates from the pseudocode in any way, indicates the
        nature of this deviation. None indicates that this function exactly
        matches the pseudocode.

        Automatic checks for pseudocode equivalence in the test suite (see
        :py:mod:`verification`) will use this value to determine how exactly
        this function must match the pseudocode for tests to pass. See
        :ref:`verification-deviation-types` for details of values this field
        may hold.
    document, section : str or None
        The name of the document and section defining this function. If None,
        will be extracted from the function docstring. Defaults to the main
        VC-2 specification. If not provided, and not found in the docstring, a
        :py:exc:`TypeError` will be thrown.

        When extracted from a docstring, a reference of one of the following
        forms must be used at the start of the docstring:

        * ``(1.2.3)``: Reference a section in the main VC-2 spec
        * ``(SMPTE ST 20402-2:2017: 1.2.3)``: Reference a section in another
          spec
    name : str or None
        The name of the pseudocode function this function implements. If None,
        the provided function's name will be used.
    """
    if len(args) >= 1 and callable(args[0]):
        pseudocode_derived_functions.append(PseudocodeDerivedFunction(*args, **kwargs))
        return args[0]
    else:

        def decorator(f):
            pseudocode_derived_functions.append(
                PseudocodeDerivedFunction(f, *args, **kwargs)
            )
            return f

        return decorator


def make_pseudocode_traceback(tb):
    """
    Given a :py:func:`traceback.extract_tb` generated traceback description,
    return a list of :py:class:`PseudocodeDerivedFunction` objects for the
    stack trace, most recently called last. Entries in the traceback which
    don't have a corresponding pseudocode-derived function are omitted.
    """
    calls = []

    for frame_summary in tb:
        filename = frame_summary[0]
        name = frame_summary[2]

        try:
            pseudocode_derived_function = next(
                iter(
                    filter(
                        lambda e: (
                            e.function.__name__ == name
                            and inspect.getsourcefile(e.function) == filename
                        ),
                        pseudocode_derived_functions,
                    )
                )
            )
            calls.append(pseudocode_derived_function)
        except StopIteration:
            # Not a pseudocode function, omit this from the traceback
            pass

    return calls
