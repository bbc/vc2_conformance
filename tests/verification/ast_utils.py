"""
Utility functions for working with AST nodes.
"""

import ast

try:
    # Python 3.x
    from ast import Constant
except ImportError:
    # Python 2.7: Create a class which will never match an isinstance check
    class Constant(object):
        pass


def name_to_str(attr_or_name):
    """
    Given a :py:class:`ast.Subscript`, :py:class:`ast.Attribute` or
    :py:class:`ast.Name`, made up entirely of simple constants, return a string
    containing the dot-separated name.
    """
    if (
        isinstance(attr_or_name, ast.Subscript)
        # As of Python 3.8, ast.Constant is used for constants here.
        and isinstance(attr_or_name.slice, Constant)
        and isinstance(attr_or_name.slice.value, (str, int, float))
    ):
        return "{}[{!r}]".format(
            name_to_str(attr_or_name.value),
            attr_or_name.slice.value,
        )
    elif (
        isinstance(attr_or_name, ast.Subscript)
        # Prior to Python 3.8, ast.Index is used for constants here
        and isinstance(attr_or_name.slice, ast.Index)
        and isinstance(attr_or_name.slice.value, (ast.Num, ast.Str))
    ):
        return "{}[{!r}]".format(
            name_to_str(attr_or_name.value),
            (
                attr_or_name.slice.value.s
                if isinstance(attr_or_name.slice.value, ast.Str)
                else attr_or_name.slice.value.n
            ),
        )
    elif isinstance(attr_or_name, ast.Attribute):
        return "{}.{}".format(
            name_to_str(attr_or_name.value),
            attr_or_name.attr,
        )
    elif isinstance(attr_or_name, ast.Name):
        return attr_or_name.id
    else:
        return repr(attr_or_name)


def argument_to_str(arg):
    """
    Given an entry from a :py:class:`ast.arguments` ``args`` field, return the
    string naming that argument.
    """
    # In Python 2.x: arguments field 'args' is a list of ast.Name
    # In Python 3.x: arguments field 'args' is a list of ast.arg
    return arg.id if isinstance(arg, ast.Name) else arg.arg


def with_to_items(with_node):
    """
    Given a :py:class:`ast.With` node, return a list containing a series of
    two-tuples (context_expr, optional_vars) associated with it.
    """
    if "items" in with_node._fields:
        # In Python 3.x, the 'items' field contains a list of ast.withitem
        # nodes which give the context_expr and optional_vars for the with
        # block.
        return [
            (withitem.context_expr, withitem.optional_vars)
            for withitem in with_node.items
        ]
    else:
        # In Python 2.x, context_expr and optional_vars are part of the With
        # AST node
        return [(with_node.context_expr, with_node.optional_vars)]
