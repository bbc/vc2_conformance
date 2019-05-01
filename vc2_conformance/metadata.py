"""
Metadata about the code and values in this library.

This metadata is used to help produce more helpful error messages and also as
part of the module's own test suite.


"""

import re
import sys
import inspect
import functools

from vc2_conformance._py2k_compat import unwrap

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
    "ReferencedValue",
    "value,section,document,verbatim,name,filename,lineno",
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
verbatim : bool
    True if the value referenced matches the specification verbaitm, False if
    the value is a derrivative from the specification.
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


def ref_value(value, section=None, document=None,
              verbatim=True, name="auto",
              filename="auto", lineno="auto"):
    """
    Record the fact that the provided Python value should be referenced back to
    the specified specification.
    
    Appends a :py:class:`ReferencedValue` to :py:data:`referenced_values`,
    automatically filling in the document, filename and line number if
    required.
    
    Parameters
    ==========
    value : any
        The Python value to be referenced.
    section : str or None
        A document reference (e.g. "1.34.2" or "Table 1.3").
        
        If None, the value being recorded must have a ``__doc__`` string which
        starts with the section number in perentheses, e.g. ``(1.34.2)``. If
        this number is of the form ``(SMPTE ST 2042-1:2017: 1.34.2)``, the
        first part (before the final colon) will be treated as the document
        name.
    document : str
        The name of the document being referenced. Defaults to the main VC-2
        specification.
    verbatim : bool
        True if the value referenced matches the specification verbaitm, False
        if the value is a derrivative from the specification.
    name : str, None or "auto"
        A meaningful identifier for this value.
        
        If "auto", uses the ``__name__`` attribute of the value. If no
        ``__name__`` attribute is present, falls back on whatever appears
        before the "=" on the line of code where ``ref_value`` was called.
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
    
    if name is "auto":
        # First try the __name__ attribute
        name = getattr(value, "__name__", None)
        
        if name is None:
            # Fall back on the name assigned in response to the call to
            # 'ref_value' (crudely extracted)
            for frame_summary in inspect.stack():
                code = "\n".join(frame_summary[4])
                if frame_summary[1] != __file__:
                    match = re.match(r"\s*([^\s]+)\s*=\s*((vc2_conformance\.)?metadata\.)?ref_value", code)
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
                if frame_summary[1] != __file__:
                    auto_filename = frame_summary[1]
                    auto_lineno = frame_summary[2]
    
    if filename == "auto":
        filename = auto_filename
    
    if lineno == "auto":
        lineno = auto_lineno
    
    referenced_values.append(ReferencedValue(
        value=value,
        section=section,
        document=document,
        verbatim=verbatim,
        name=name,
        filename=filename,
        lineno=lineno,
    ))
    
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
        
        @ref_pseudocode("10.5.1", verbatim=False)
        def parse_info(state):
            '''Some alternative implementation of parse info (10.5.1).'''
    
    
    .. info::
    
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
    results = list(filter(
        lambda e: e.name == name and (filename is None or e.filename == filename),
        referenced_values,
    ))
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
        (
            referenced_value.name
            if referenced_value.name is not None else
            ""
        ),
        (
            "{}: ".format(referenced_value.document)
            if referenced_value.document != DEFAULT_SPECIFICATION else
            ""
        ),
        referenced_value.section,
    ).strip()
