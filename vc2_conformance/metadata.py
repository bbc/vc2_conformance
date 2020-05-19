"""
:py:mod:`vc2_conformance.metadata` Implementation metadata
==========================================================

This module is used to record the relationship between the code in the
:py:mod:`vc2_conformance` software and the VC-2 specification documents. This
metadata has two important uses:

1. To produce more helpful error messages which include cross-references to
   published specifications.
2. To enable automatic verification that the behaviour of this software exactly
   matches the published specifications (see :py:mod:`verification`).


Referencing the spec
--------------------

Functions in the codebase which implement a pseudocode function in the
specification may be labelled as such using a :py:func:`ref_pseudocode`
decorator::

    >>> from vc2_conformance.metadata import ref_pseudocode

    >>> @ref_pseudocode
    ... def parse_info(state):
    ...     '''(10.5.1) Read a parse_info header.'''
    ...     byte_align()
    ...     read_uint_lit(state, 4)
    ...     state["parse_code"] = read_uint_lit(state, 1)
    ...     state["next_parse_offset"] = read_uint_lit(state, 4)
    ...     state["previous_parse_offset"] = read_uint_lit(state, 4)

By default, the reference to the specification is extracted from the function's
docstring. The function is also assumed *not* to deviate from the pseudocode --
an assumption which is automatically verified by the test suite (see
:py:mod:`verification`). For functions which deviate from the specification in
some way, the ``deviation`` argument should be passed to the decorator (see
:py:class:`ReferencedValue`.

Constants in this codebase may be cross-referenced against the spec using
:py:func:`ref_value`. This takes the value being referenced along with the
specification reference as minimal arguments. For example::

    >>> from vc2_conformance.metadata import ref_value

    >>> PARSE_INFO_PREFIX = ref_value(0x42424344, "10.5.1")

:py:func:`ref_value` returns the argument passed to it unchanged but
automatically logs the name it was assigned to and the file and line number it
was assigned on.

As a convenience, :py:class:`enum.Enum` instances can also be annotated by the
:py:func:`ref_enum` decorator::

    >>> from enum import Enum
    >>> from vc2_conformance.metadata import ref_enum

    >>> @ref_enum
    ... class PictureCodingModes(IntEnum):
    ...     '''(11.5) Indices defined in the text. Names are not normative.'''
    ...     pictures_are_frames = 0
    ...     pictures_are_fields = 1


Accessing the metadata
----------------------

After all submodules of :py:mod:`vc2_conformance` have been loaded, the
:py:data:`referenced_values` list will be populated with
:py:class:`ReferencedValue` instances for everything annotated in the source.

Human-readable citations for :py:class:`ReferencedValue` instances can be
obtained from :py:func:`format_citation`.

The :py:func:`lookup_by_value` and :py:func:`lookup_by_name` convenience
functions may be used to search this list.

API
---

.. autoclass:: ReferencedValue

.. autodata:: referenced_values
    :annotation: = [...]

.. autodata:: DEFAULT_SPECIFICATION

.. autofunction:: ref_value

.. autofunction:: ref_pseudocode

.. autofunction:: ref_enum

.. autofunction:: lookup_by_value

.. autofunction:: lookup_by_name

.. autofunction:: format_citation
"""

import re
import sys
import inspect

from vc2_conformance.py2x_compat import unwrap

from collections import namedtuple

__all__ = [
    "DEFAULT_SPECIFICATION",
    "ReferencedValue",
    "referenced_values",
    "ref_value",
    "ref_pseudocode",
    "ref_enum",
    "lookup_by_value",
    "lookup_by_name",
    "format_citation",
]


DEFAULT_SPECIFICATION = "SMPTE ST 2042-1:2017"  # The main VC-2 specification
"""
If not otherwise specified, the specification section numbers refer to.
"""


ReferencedValue = namedtuple(
    "ReferencedValue", "value,section,document,deviation,name,filename,lineno",
)
"""
A value in this codebase, referenced back to a specification document.

Parameters
==========
value : any
    The Python value to be referenced.
section : str
    A document reference (e.g. "1.34.2" or "Table 1.3").
document : str
    The name of the document being referenced. Defaults to the main VC-2
    specification.
deviation : str or None
    Does the definition of this value deviate from the specification.

    If None, this value shoul match the contents of the specification exactly.
    If a string, it should indicate how it differs. Allowed values are:

    * ``"inferred_implementation"``: An implementation inferred from the
      specification where no explicit implementation is provided.
    * ``"alternative_implementation"``: An alternative implementation, e.g. for
      performance or correctness reasons.
    * ``"serdes"``: This implementation has been modified to perform
      seriallisation and deseriallisation using the
      :py:mod:`vc2.bitstream.serdes` library.

    Functions whose reported deviation is ``None`` or ``"serdes`` will be
    automatically checked against the specification by the testsuite (see
    :py:mod:`verification`).
name : str or None
    A meaningful identifier for this value.
filename : str, None or "auto"
    The filename of the Python source file within this codebase for the
    location where the value being referenced is defined.

    If "auto", the location will be determined automatically if possible,
    falling back on the location where 'ref_value' was called.

    If None, no value will be recorded.
lineno : int, None or "auto"
    The line number at which the definition of this value appears.

    If "auto", the location will be determined automatically if possible,
    falling back on the line where 'ref_value' was called.

    If None, no value will be recorded.
"""


referenced_values = []
r"""
The complete set of :py:class:`ReferencedValue`\ s in this code base, in no
particular order.
"""

# The filename of this module (not its .pyc file)
_metadata_module_filename = inspect.getsourcefile(sys.modules[__name__])


def ref_value(
    value,
    section=None,
    document=None,
    deviation=None,
    name="auto",
    filename="auto",
    lineno="auto",
):
    """
    Record the fact that the provided Python value should be referenced back to
    the specified specification.

    Appends a :py:class:`ReferencedValue` to :py:data:`referenced_values`,
    automatically filling in the document, filename and line number if
    required.

    Parameters
    ==========
    value : any
    section : str or None
        If None, the value being recorded must have a ``__doc__`` string which
        starts with the section number in perentheses, e.g. ``(1.34.2)``. If
        this number is of the form ``(SMPTE ST 2042-1:2017: 1.34.2)``, the
        first part (before the final colon) will be treated as the document
        name.
    document : str
        Defaults to the main VC-2 specification if None and not specified in
        the value's ``__doc__`` string.
    deviation : str or None
    name : str, None or "auto"
        If "auto", uses the ``__name__`` attribute of the value. If no
        ``__name__`` attribute is present, falls back on whatever appears
        before the "=" on the line of code where ``ref_value`` was called.
    filename : str, None or "auto"
        If "auto", the location will be determined automatically if possible,
        falling back on the location where 'ref_value' was called.

        If None, no value will be recorded.
    lineno : int, None or "auto"
        If "auto", the location will be determined automatically if possible,
        falling back on the line where 'ref_value' was called.

        If None, no value will be recorded.

    Returns
    =======
    Returns the 'value' argument (untouched).
    """
    default_document = DEFAULT_SPECIFICATION

    if section is None:
        docstring = getattr(value, "__doc__", "")
        match = re.match(r"\s*\(([^\)]+)\)", docstring)
        if match:
            section = match.group(1)

            # Also extract the document name, if present
            submatch = re.match(r"(.*)\s*:\s*([^:]+)$", section)
            if submatch:
                default_document = submatch.group(1)
                section = submatch.group(2)
        else:
            raise TypeError("'section' argument omitted and not found in docstring.")

    if document is None:
        document = default_document

    if name == "auto":
        # First try the __name__ attribute
        name = getattr(value, "__name__", None)

        if name is None:
            # Fall back on the name assigned in response to the call to
            # 'ref_value' (crudely extracted)
            for frame_summary in inspect.stack():
                code = "\n".join(frame_summary[4])
                if frame_summary[1] != _metadata_module_filename:
                    match = re.match(
                        r"\s*([^\s]+)\s*=\s*((vc2_conformance\.)?metadata\.)?ref_value",
                        code,
                    )
                    if match:
                        name = match.group(1)
                    break

    if filename == "auto" or lineno == "auto":
        try:
            # First, try using introspection to determine the value's origin
            auto_filename = inspect.getsourcefile(unwrap(value))
            auto_lineno = inspect.getsourcelines(unwrap(value))[1]
        except (TypeError, IOError):
            auto_filename = None
            auto_lineno = None

        if auto_filename is None or auto_lineno is None:
            # Introspection hasn't worked, search up the stack to find the
            # callsite of 'ref_value'.
            auto_filename = None
            auto_lineno = None
            for frame_summary in reversed(list(inspect.stack())):
                if frame_summary[1] != _metadata_module_filename:
                    auto_filename = frame_summary[1]
                    auto_lineno = frame_summary[2]

    if filename == "auto":
        filename = auto_filename

    if lineno == "auto":
        lineno = auto_lineno

    referenced_values.append(
        ReferencedValue(
            value=value,
            section=section,
            document=document,
            deviation=deviation,
            name=name,
            filename=filename,
            lineno=lineno,
        )
    )

    return value


def ref_pseudocode(*args, **kwargs):
    """
    Decorator for marking instances where VC-2 pseudocode has been transformed
    into Python code.

    Takes the same parameters as :py:func:`ref_value`.

    Example usage::

        @ref_pseudocode
        def parse_info(state):
            ''''(10.5.1) Read a parse_info header.'''
            # ...

        @ref_pseudocode("10.5.1", deviation="alternative_implementation")
        def parse_info(state):
            '''Some alternative implementation of parse info.'''


    .. note::

        This decorator is syntactic sugar for passing such functions manually
        to :py:func:`ref_value`. It returns the original function, not a
        wrapper, and so incurrs no runtime penalty.
    """
    if len(args) >= 1 and callable(args[0]):
        ref_value(*args, **kwargs)
        return args[0]
    else:

        def decorator(f):
            ref_value(f, *args, **kwargs)
            return f

        return decorator


def ref_enum(*args, **kwargs):
    """
    Decorator for marking instances of VC-2 value enumerations.
    """
    return ref_pseudocode(*args, **kwargs)


def lookup_by_value(value):
    """
    Search :py:data:`referenced_values` for entries whose values match that
    value given. If no or multiple matching entries exist, a
    :py:exc:`ValueError` is thrown.
    """
    results = list(filter(lambda e: e.value == value, referenced_values))
    if len(results) != 1:
        raise ValueError(value)
    else:
        return results[0]


def lookup_by_name(name, filename=None):
    """
    Search :py:data:`referenced_values` for entries whose names (and optionally
    filename) match the provided value.
    """
    results = list(
        filter(
            lambda e: e.name == name and (filename is None or e.filename == filename),
            referenced_values,
        )
    )
    if len(results) != 1:
        raise ValueError(name)
    else:
        return results[0]


def format_citation(referenced_value):
    """
    Produce a human-readable citation string for the specified
    :py:class:`ReferencedValue`.
    """
    return "{} ({}{})".format(
        (referenced_value.name if referenced_value.name is not None else ""),
        (
            "{}: ".format(referenced_value.document)
            if referenced_value.document != DEFAULT_SPECIFICATION
            else ""
        ),
        referenced_value.section,
    ).strip()
