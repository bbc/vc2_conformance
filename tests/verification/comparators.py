"""
A series of :py:class:`validation.node_comparator.NodeComparator` based
comparators for checking the equivalence of VC-2 pseudocode functions from the
spec with their implementations in the :py:mod:`vc2_conformance` package.
"""

import ast

from verification.node_comparator import NodeComparator, NodesDiffer

from verification.ast_utils import name_to_str

from verification.field_filters import (
    cascade,
    ignore_named_decorators,
    ignore_leading_arguments,
    ignore_leading_call_arguments,
    ignore_docstrings,
    ignore_calls_to,
    ignore_first_n,
    unwrap_named_context_managers,
)


class Identical(NodeComparator):
    """
    Compares two function implementations only allowing differences in their
    docstrings and the presence of a
    :py:func:`vc2_conformance.metadata.ref_pseudocode` decorator on the second
    function.
    """
    
    
    def compare_FunctionDef(self, n1, n2):
        return self.generic_compare(n1, n2, filter_fields={
            "decorator_list": (None, ignore_named_decorators("ref_pseudocode")),
            "body": ignore_docstrings
        })


class SerdesChangesOnly(NodeComparator):
    """
    Compares two function implementations where the first as a VC-2 pseudocode
    definition and the second a function for use with the
    :py:mod:`vc2_conformance.bitstream.serdes` framework. The following
    differences are allowed:
    
    1. Differing docstrings. (Justification: has no effect on behaviour.)
    2. The addition of a :py:func:`vc2_conformance.metadata.ref_pseudocode`
       decorator to the second function. (Justification: has no effect on
       behaviour.)
    3. The addition of a :py:func:`vc2_conformance.bitstream.serdes.context_type`
       decorator to the second function. (Justification: has no effect on
       behaviour.)
    4. The addition of ``serdes`` as a first argument to the second function.
       (Justification: required for use of the serdes framework, has no effect
       on behaviour.)
    5. The wrapping of statements in ``with serdes.subcontext`` context managers
       in the second function will be ignored. (Justification: these context
       managers have no effect on behaviour but are required to set the serdes
       state.)
    6. The addition of the following methods calls in the second function
       (Justification: these method calls have no effect on behaviour but are
       required to set the serdes state):
       * :py:meth:`vc2_conformance.bitstream.serdes.Serdes.subcontext_enter`
       * :py:meth:`vc2_conformance.bitstream.serdes.Serdes.subcontext_leave`
       * :py:meth:`vc2_conformance.bitstream.serdes.Serdes.set_context_type`
       * :py:meth:`vc2_conformance.bitstream.serdes.Serdes.declare_list`
       * :py:meth:`vc2_conformance.bitstream.serdes.Serdes.computed_value`
    7. The substitution of an assignment to ``state.bits_left`` with a call to
       :py:meth:`vc2_conformance.bitstream.serdes.Serdes.bounded_block_begin`
       in the second function, taking the assigned value as argument.
       (Justification: this has the equivalent effect in the bitstream IO
       system).
    8. The following IO function substitutions in the second function are
       allowed with an additional first argument (for the target name).
       (Justification: these functions have the equivalent effect in the
       bitstream IO system).
       * ``read_bool`` -> ``serdes.bool``
       * ``read_nbits`` -> ``serdes.nbits``
       * ``read_uint_lit`` -> ``serdes.uint_lit``
       * ``read_uint`` -> ``serdes.uint``
       * ``read_sint`` -> ``serdes.sint``
       * ``byte_align`` -> ``serdes.byte_align``
       * ``flush_inputb`` -> ``serdes.bounded_block_end``
    9. Substitution of empty dictionary creation for creation of
       :py:class:`vc2_conformance.state.State` or
       :py:class:`vc2_conformance.video_parameters.VideoParameters` fixed dicts
       is allowed.
    """
    
    def compare_FunctionDef(self, n1, n2):
        return self.generic_compare(n1, n2, filter_fields={
            "body": (
                ignore_docstrings,  # Allowed change no. 1
                cascade(
                    ignore_docstrings,  # Allowed change no. 1
                    SerdesChangesOnly.common_body_filters,
                ),
            ),
            # Allowed change no. 2, 3
            "decorator_list": (None, ignore_named_decorators("ref_pseudocode", "context_type")),
        })
    
    def compare_arguments(self, n1, n2):
        return self.generic_compare(n1, n2, filter_fields={
            # Allowed change no. 4
            "args": (None, ignore_leading_arguments("serdes")),
        })
    
    # Filters to be applied to all lists of 'body' statements
    common_body_filters = cascade(
        # Allowed change no. 5
        unwrap_named_context_managers("serdes.subcontext"),
        # Allowed change no. 6
        ignore_calls_to(
            "serdes.subcontext_enter",
            "serdes.subcontext_leave",
            "serdes.set_context_type",
            "serdes.declare_list",
            "serdes.computed_value",
        ),
    )
    
    def compare_Assign_Expr(self, n1, n2):
        # Allowed change no. 7
        
        # n1 must assign to state['bits_left']
        if len(n1.targets) != 1 or name_to_str(n1.targets[0]) != "state['bits_left']":
            return self.generic_compare(n1, n2)
        
        # n2 must contain a 'Call' to bounded_block_begin
        if not isinstance(n2.value, ast.Call) or name_to_str(n2.value.func) != "serdes.bounded_block_begin":
            return self.generic_compare(n1, n2)
        
        # n2 must have exactly one positional argument
        if (len(n2.value.args) != 1 or
                n2.value.keywords != [] or
                # Python 2.x only
                getattr(n2.value, "starargs", None) is not None or
                getattr(n2.value, "kwargs", None) is not None):
            return self.generic_compare(n1, n2)
        
        # n2's positional argument must exactly match the value assigned to
        # state['bits_left'] in the n1
        return self.generic_compare(n1.value, n2.value.args[0])
    
    def compare_Call(self, n1, n2):
        # Allowed change no. 4 and 8
        
        # Test if the function name has changed in one of the expected ways
        allowed_name_changes = (
            ("read_bool", "serdes.bool"),
            ("read_nbits", "serdes.nbits"),
            ("read_uint_lit", "serdes.uint_lit"),
            ("read_uint", "serdes.uint"),
            ("read_sint", "serdes.sint"),
            ("byte_align", "serdes.byte_align"),
            ("flush_inputb", "serdes.bounded_block_end")
        )
        name1 = name_to_str(n1.func)
        name2 = name_to_str(n2.func)
        name_change_allowed = (name1, name2) in allowed_name_changes
        
        # Check the former function takes 'state' as its first argument
        n1_takes_state_as_first_arg =(
            len(n1.args) >= 1 and
            name_to_str(n1.args[0]) == "state"
        )
        
        if name_change_allowed and n1_takes_state_as_first_arg:
            # Test if the arguments match (asside from an extra first argument
            # which will be 'state' in n1 and a target name in n2)
            return self.generic_compare(
                n1, n2,
                ignore_fields=["func"],
                # Ignores 'state' (in ref version) and 'serdes' (in impl.
                # version)
                filter_fields={"args": ignore_first_n(1)},
            )
        else:
            return self.generic_compare(
                n1, n2,
                # Allowed change no. 4
                filter_fields={"args": (None, ignore_leading_call_arguments("serdes"))}
            )
    
    def compare_Module(self, n1, n2):
        return self.generic_compare(n1, n2, filter_fields={
            "body": (None, SerdesChangesOnly.common_body_filters),
        })
    
    def compare_With(self, n1, n2):
        return self.generic_compare(n1, n2, filter_fields={
            "body": (None, SerdesChangesOnly.common_body_filters),
        })
    
    def compare_If(self, n1, n2):
        return self.generic_compare(n1, n2, filter_fields={
            "body": (None, SerdesChangesOnly.common_body_filters),
            "orelse": (None, SerdesChangesOnly.common_body_filters),
        })
    
    def compare_For(self, n1, n2):
        return self.generic_compare(n1, n2, filter_fields={
            "body": (None, SerdesChangesOnly.common_body_filters),
            "orelse": (None, SerdesChangesOnly.common_body_filters),
        })
    
    def compare_While(self, n1, n2):
        return self.generic_compare(n1, n2, filter_fields={
            "body": (None, SerdesChangesOnly.common_body_filters),
            "orelse": (None, SerdesChangesOnly.common_body_filters),
        })
    
    def compare_Dict_Call(self, n1, n2):
        # Allowed change no. 9
        is_empty_dict = len(n1.keys) == 0 and len(n1.values) == 0
        is_empty_constructor = (
            len(n2.args) == 0 and
            len(n2.keywords) == 0 and
            # Python 2.x
            len(getattr(n2, "starargs", [])) == 0 and
            len(getattr(n2, "kwargs", [])) == 0
        )
        is_allowed_fixeddict = name_to_str(n2.func) in (
            "State",
            "VideoParameters",
        )
        
        if is_empty_dict and is_empty_constructor and is_allowed_fixeddict:
            return True
        else:
            return self.generic_compare(n1, n2)
