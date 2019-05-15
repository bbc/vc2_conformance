"""
:py:mod:`verification.compare`: Compare function implementations
================================================================

.. py:currentmodule:: verification.compare

This module provides a function, :py:func:`compare_functions`, which uses a
specified comparator (:py:mod:`verification.comparators`) to determine if a
given function matches the reference VC-2 pseudocode.

.. autofunction:: compare_functions

.. autofunction:: compare_sources

.. autoclass:: Difference
    :members:

.. autoexception:: ComparisonError
"""

from vc2_conformance._py2k_compat import unwrap

import ast

from tokenize import TokenError

from verification.get_full_source import get_full_source

from verification.amendment_comments import (
    undo_amendments,
    BadAmendmentCommentError,
    UnmatchedNotInSpecBlockError,
    UnclosedNotInSpecBlockError,
)

from verification.node_comparator import (
    NodeTypesDiffer,
    NodeFieldsDiffer,
    NodeFieldLengthsDiffer,
    NodeListFieldsDiffer,
)


def format_summary(comparison_error_or_difference):
    """
    Format a one-line summary of a :py:exc:`ComparisonError` or
    :py:class:`Difference` instance.
    """
    message = comparison_error_or_difference.message
    ref_row = comparison_error_or_difference.ref_row
    ref_col = comparison_error_or_difference.ref_col
    imp_row = comparison_error_or_difference.imp_row
    imp_col = comparison_error_or_difference.imp_col
    
    ref_func = comparison_error_or_difference.ref_func
    imp_func = comparison_error_or_difference.imp_func
    
    ref_filename = None
    if ref_func is not None:
        ref_filename, ref_lineno, ref_source = get_full_source(unwrap(ref_func))
        if ref_row is not None:
            ref_row += ref_lineno
    
    imp_filename = None
    if imp_func is not None:
        imp_filename, imp_lineno, imp_source = get_full_source(unwrap(imp_func))
        if imp_row is not None:
            imp_row += imp_lineno
    
    if ref_row is None and imp_row is None:
        return message
    else:
        return "{} (in {})".format(
            message,
            " and ".join(
                "{}, line {}{}{}".format(
                    source,
                    row,
                    " col {}".format(col) if col is not None else "",
                    " of {}".format(filename) if filename is not None else "",
                )
                for (source, row, col, filename) in [
                    ("reference code", ref_row, ref_col, ref_filename),
                    ("implementation code", imp_row, imp_col, imp_filename),
                ]
                if row is not None
            ),
        )


def format_detailed_summary(comparison_error_or_difference):
    """
    Format a detailed summary showing the original source.
    """
    out = []
    
    ref_func = comparison_error_or_difference.ref_func
    imp_func = comparison_error_or_difference.imp_func
    
    # Fall back on simple summary if functions not provided
    if ref_func is None or imp_func is None:
        return format_summary(comparison_error_or_difference)
    
    message = comparison_error_or_difference.message
    ref_row = comparison_error_or_difference.ref_row
    ref_col = comparison_error_or_difference.ref_col
    imp_row = comparison_error_or_difference.imp_row
    imp_col = comparison_error_or_difference.imp_col
    
    ref_filename, ref_first_lineno, ref_source_lines = get_full_source(unwrap(ref_func))
    imp_filename, imp_first_lineno, imp_source_lines = get_full_source(unwrap(imp_func))
    
    func_names = [ref_func.__name__]
    if ref_func.__name__ != imp_func.__name__:
        func_names.append(imp_func.__name__)
    
    out.append(message)
    
    for impl_name, filename, source_lines, row, col, first_lineno in [
            ("Reference", ref_filename, ref_source_lines, ref_row, ref_col, ref_first_lineno),
            ("Implementation", imp_filename, imp_source_lines, imp_row, imp_col, imp_first_lineno)]:
        if row is not None:
            out.append("")
            out.append("{} source:".format(impl_name))
            for r in range(row):
                out.append("    {}".format(source_lines[r]).rstrip())
            
            if col is not None:
                arrow_col = col
            else:
                # Extend arrow past indent if no column number given
                arrow_col = len(source_lines[row-1]) - len(source_lines[row-1].lstrip())
            out.append("----{}^".format("-"*arrow_col))
            
            out.append("{}:{}{}".format(
                filename,
                first_lineno + (row - 1),
                " (col {})".format(col) if col is not None else ""
            ))
    
    return "\n".join(out)


class ComparisonError(Exception):
    """
    An error occurred while attempting to compare two function implementations.
    
    Use :py:class:`str` to turn into a human-readable description (including
    source code snippets).
    
    Parameters
    ----------
    message : str
    ref_row, ref_col : int or None
        The position in the reference code where the error ocurred. May be None
        if not related to the reference code.
    imp_row, imp_col : int or None
        The position in the implementation code where the error ocurred. May be
        None if not related to the implementation code.
    ref_func, imp_func : FunctionType or None
        The Python function objects being compared.
    """
    
    def __init__(self, message,
                 ref_row=None, ref_col=None,
                 imp_row=None, imp_col=None,
                 ref_func=None, imp_func=None):
        self.message = message
        self.ref_row = ref_row
        self.ref_col = ref_col
        self.imp_row = imp_row
        self.imp_col = imp_col
        self.ref_func = ref_func
        self.imp_func = imp_func
        
        super(ComparisonError, self).__init__()
    
    def __str__(self):
        return format_detailed_summary(self)


class Difference(object):
    """
    A description of the difference between a reference function and its
    implementation.
    
    Use :py:class:`str` to turn into a human-readable description (including
    source code snippets).
    
    Parameters
    ----------
    message : str
    ref_row, ref_col : int or None
        The position in the reference code where the difference ocurred. May be
        None if not related to the reference code.
    imp_row, imp_col : int or None
        The position in the implementation code where the difference ocurred.
        May be None if not related to the implementation code.
    ref_func, imp_func : FunctionType or None
        The Python function objects being compared.
    """
    
    def __init__(self, message,
                 ref_row=None, ref_col=None,
                 imp_row=None, imp_col=None,
                 ref_func=None, imp_func=None):
        self.message = message
        self.ref_row = ref_row
        self.ref_col = ref_col
        self.imp_row = imp_row
        self.imp_col = imp_col
        self.ref_func = ref_func
        self.imp_func = imp_func
    
    def __repr__(self):
        return "<{} {}>".format(
            type(self).__name__,
            format_summary(self),
        )
    
    def __str__(self):
        return format_detailed_summary(self)
    
    def __bool__(self):  # Py 3.x
        return False
    
    def __nonzero__(self):  # Py 2.x
        return False


def compare_sources(ref_source, imp_source, comparator):
    """
    Compare two Python sources, one containing a reference VC-2 pseudocode
    function and the other containing an implementation.
    
    Parameters
    ==========
    ref_source : str
        The reference VC-2 pseudocode implementation of a function.
    imp_source : str
        The implementation of the same function used in
        :py:mod:`vc2_conformance`. Will be pre-processed using
        :py:func:`verification.amendment_comments.undo_amendments` prior to
        comparison.
    comparator : :py:class:`verification.node_comparator.NodeComparator`
        The comparator to use to test for equivalence.
    
    Returns
    =======
    True or :py:class:`Difference`
        True is returned if the implementations are equal (according to the
        supplied comparator). Otherwise a :py:class:`Difference` is returned
        enumerating the differences.
    
    Raises
    =======
    :py:exc:`ComparisonError`
    """
    try:
        imp_source, implementation_indent_offsets = undo_amendments(imp_source)
    except TokenError as e:
        raise ComparisonError(e.args[0], imp_row=e.args[1][0], imp_col=e.args[1][1])
    except BadAmendmentCommentError as e:
        raise ComparisonError(
            "Unrecognised amendment comment {!r}".format(e.comment),
            imp_row=e.row,
            imp_col=e.col,
        )
    except UnmatchedNotInSpecBlockError as e:
        raise ComparisonError(
            "No matching '## Begin not in spec'",
            imp_row=e.row,
        )
    except UnclosedNotInSpecBlockError as e:
        raise ComparisonError(
            "'## Begin not in spec' block not closed",
            imp_row=e.row,
        )
    
    try:
        ref_ast = ast.parse(ref_source)
    except SyntaxError as e:
        raise ComparisonError(e.msg, ref_row=e.lineno, ref_col=e.offset)
    
    try:
        imp_ast = ast.parse(imp_source)
    except SyntaxError as e:
        raise ComparisonError(
            e.msg,
            imp_row=e.lineno,
            imp_col=e.offset + implementation_indent_offsets.get(e.lineno, 0),
        )
    
    match = comparator.compare(ref_ast, imp_ast)
    if match is True:
        return match
    
    message = str(match)
    ref_row = None
    ref_col = None
    imp_row = None
    imp_col = None
    if isinstance(match, NodeTypesDiffer):
        message = "Mismatched {} vs. {}".format(
            type(match.n1).__name__,
            type(match.n2).__name__,
        )
        ref_row, ref_col = match.n1_row_col
        imp_row, imp_col = match.n2_row_col
    elif isinstance(match, NodeFieldsDiffer):
        message = "Different {} values".format(match.field)
        ref_row, ref_col = match.n1_row_col
        imp_row, imp_col = match.n2_row_col
    elif isinstance(match, NodeFieldLengthsDiffer):
        if len(match.v1) > len(match.v2):
            num = len(match.v1) - len(match.v2)
            message = "{} extra value{} in reference's {}".format(
                num,
                "s" if num != 1 else "",
                match.field,
            )
        else:
            num = len(match.v2) - len(match.v1)
            message = "{} extra value{} in implementation's {}".format(
                num,
                "s" if num != 1 else "",
                match.field,
            )
        ref_row, ref_col = match.n1_row_col
        imp_row, imp_col = match.n2_row_col
    elif isinstance(match, NodeListFieldsDiffer):
        message = "Different {} at index {} ({!r} and {!r})".format(
            match.field,
            match.index,
            match.v1[match.index],
            match.v2[match.index],
        )
        ref_row, ref_col = match.n1_row_col
        imp_row, imp_col = match.n2_row_col
    
    return Difference(
        message=message,
        ref_row=ref_row,
        ref_col=ref_col,
        imp_row=imp_row,
        imp_col=(
            imp_col + implementation_indent_offsets.get(imp_row, 0)
            if imp_row is not None and imp_col is not None else
            imp_col
        ),
    )


def compare_functions(ref_func, imp_func, comparator):
    """
    Compare two Python functions where one is a reference implementation and
    the other an implementation used in :py:mod:`vc2_conformance`.
    
    Parameters
    ==========
    ref_func : :py:class:`FunctionType`
        The reference VC-2 implementation of a function.
    imp_func : :py:class:`FunctionType`
        The implementation of the same function used in
        :py:mod:`vc2_conformance`. Will be pre-processed using
        :py:func:`verification.amendment_comments.undo_amendments` prior to
        comparison.
    comparator : :py:class:`verification.node_comparator.NodeComparator`
        The comparator to use to test for equivalence.
    
    Returns
    =======
    True or :py:class:`Difference`
        True is returned if the implementations are equal (according to the
        supplied comparator). Otherwise a :py:class:`Difference` is returned
        enumerating the differences.
    
    Raises
    =======
    :py:exc:`ComparisonError`
    """
    ref_source = "".join(get_full_source(unwrap(ref_func))[2])
    imp_source = "".join(get_full_source(unwrap(imp_func))[2])
    
    try:
        match = compare_sources(ref_source, imp_source, comparator)
        if match is not True:
            match.ref_func = ref_func
            match.imp_func = imp_func
        return match
    except ComparisonError as e:
        e.ref_func = ref_func
        e.imp_func = imp_func
        raise e
