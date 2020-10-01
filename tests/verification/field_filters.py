"""
List field filters for AST nodes (for use with the ``filter_fields`` argument
of :py:meth:`NodeComparator.generic_compare`).
"""

import ast

from itertools import dropwhile

from verification.ast_utils import (
    name_to_str,
    argument_to_str,
    with_to_items,
)


def cascade(*filters):
    """
    Given a series of (comptaible) field filter functions, return a new
    function which applies each filter in turn.
    """

    def filter(lst):
        for f in filters:
            lst = f(lst)
        return lst

    return filter


def ignore_docstrings(body):
    """
    Filter for the 'body' field of :py:class:`ast.FunctionDef` which strips all
    leading strings (i.e. all docstrings).
    """
    return dropwhile(
        lambda e: isinstance(e, ast.Expr) and isinstance(e.value, ast.Str),
        body,
    )


def ignore_leading_arguments(*expected_arg_names):
    """
    Filter factory for filtering the 'args' field of :py:class:`ast.arguments`
    to remove an expected set of argument names from the start.
    """

    def filter(args):
        arg_names = tuple(map(argument_to_str, args))

        if arg_names[: len(expected_arg_names)] == expected_arg_names:
            return args[len(expected_arg_names) :]
        else:
            return args

    return filter


def ignore_leading_call_arguments(*expected_arg_names):
    """
    Filter factory for filtering the 'args' field of :py:class:`ast.Call` to
    remove leading arguments which consist of the provided list of variable
    names.
    """

    def filter(args):
        arg_names = tuple(map(name_to_str, args))

        if arg_names[: len(expected_arg_names)] == expected_arg_names:
            return args[len(expected_arg_names) :]
        else:
            return args

    return filter


def ignore_named_decorators(*ignored_decorator_names):
    """
    Filter factory for filtering any of the named decorators from the
    ``decorator_list`` field of :py:class:`ast.FunctionDef` nodes.
    """

    def filter(decorator_list):
        return [
            decorator
            for decorator in decorator_list
            if (
                name_to_str(decorator.func)
                if isinstance(decorator, ast.Call)
                else name_to_str(decorator)
            )
            not in ignored_decorator_names
        ]

    return filter


def ignore_calls_to(*ignored_function_names):
    """
    Filter factory for filtering of function expressions for any of the named
    functions from a list of statements.
    """

    def filter(nodes):
        return [
            node
            for node in nodes
            if (
                not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call))
                or name_to_str(node.value.func) not in ignored_function_names
            )
        ]

    return filter


def ignore_first_n(n):
    """
    Filter factory for a filter which removes the first 'n' entries from a
    list.
    """

    def filter(lst):
        return lst[n:]

    return filter


def unwrap_named_context_managers(*function_names):
    """
    Filter factory for replacing 'with' blocks with their body.

    For complete coverage, the following AST node types and fields must be
    filtered:

    * :py:class:`ast.Module`, 'body',
    * :py:class:`ast.FunctionDef`, 'body',
    * :py:class:`ast.If`, 'body', 'orelse'
    * :py:class:`ast.For`, 'body', 'orelse'
    * :py:class:`ast.While`, 'body', 'orelse'
    * :py:class:`ast.With`, 'body',
    * :py:class:`ast.ExceptHandler`, 'body'
    * Python 2.x only:
      * :py:class:`ast.TryFinally`, 'body', 'finalbody'
      * :py:class:`ast.TryExcept`, 'body', 'orelse'
    * Python 3.x only:
      * :py:class:`ast.Try`, 'body', 'orelse, 'finalbody'
      * :py:class:`ast.AsyncFunctionDef`, 'body',
      * :py:class:`ast.AsyncFor`, 'body', 'orelse'

    Given a list of AST nodes, substitutes any 'with' block whose
    'context_expr' is a function call whose name matches one of the provided
    names, for its body.

    For example, the filter returned by
    ``unwrap_named_context_managers(["foobar"])`` effectively
    transforms::

        a = 1
        with foobar(1, 2, 3) as baz:
            b = 2
            c = 3
        d = 4

    into::

        a = 1
        b = 2
        c = 3
        d = 4
    """

    def filter(body):
        nodes_to_unwrap = list(body)
        out = []

        while nodes_to_unwrap:
            node = nodes_to_unwrap.pop(0)
            if isinstance(node, ast.With):
                matches = True
                for context_expr, optional_vars in with_to_items(node):
                    if isinstance(context_expr, ast.Call):
                        if name_to_str(context_expr.func) not in function_names:
                            matches = False
                            break
                    else:
                        matches = False
                        break

                if matches:
                    for child in reversed(node.body):
                        nodes_to_unwrap.insert(0, child)
                else:
                    out.append(node)
            else:
                out.append(node)

        return out

    return filter
