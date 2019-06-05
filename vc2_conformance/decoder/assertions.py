"""
:py:mod:`vc2_conformance.decoder.assertions`: Assertions functions for conformance checks
=========================================================================================
"""

from vc2_conformance.tables import ParseCodes, LEVEL_CONSTRAINTS

from vc2_conformance._symbol_re import WILDCARD, END_OF_SEQUENCE

from vc2_conformance._constraint_table import allowed_values_for

from vc2_conformance.decoder.exceptions import ValueNotAllowedInLevel


def assert_in(value, collection, exception_type):
    """
    Check to see if a value is a member of the provided collection using
    ``in``. If it is not, throws an exception of the given type with the value
    and collections passed as as arguments.
    """
    if value not in collection:
        raise exception_type(value, collection)


def assert_in_enum(value, enum, exception_type):
    """
    Check to see if a value is a member of the provided assertion type. If it
    is not, throws an exception of the given type with the value as argument.
    """
    try:
        enum(value)
    except ValueError:
        raise exception_type(value)


def assert_parse_code_in_sequence(parse_code, matcher, exception_type):
    """
    Check that the specified parse code's name matches the next value in the
    sequence defined by :py:class:`vc2_conformance._symbol_re.Matcher`.
    
    If it does not, ``exception_type`` will be raised with the following
    arguments:
    
    * The ``parse_code`` (as a :py:class:`~vc2_conformance.tables.ParseCodes`)
    * A list of parse codes (as a
      :py:class:`~vc2_conformance.tables.ParseCodes`) which would have been
      valid (or ``None`` if any parse code would be allowed.
    * A boolean which is True if it would have been valid to end the sequence
      at this point.
    """
    parse_code = ParseCodes(parse_code)
    
    if not matcher.match_symbol(parse_code.name):
        expected_parse_codes = []
        expected_end = False
        for parse_code_name in matcher.valid_next_symbols():
            if parse_code_name == WILDCARD:
                expected_parse_codes = None
            elif parse_code_name == END_OF_SEQUENCE:
                expected_end = True
            elif expected_parse_codes is not None:
                expected_parse_codes.append(getattr(ParseCodes, parse_code_name))
        
        raise exception_type(
            parse_code,
            expected_parse_codes,
            expected_end,
        )


def assert_parse_code_sequence_ended(matcher, exception_type):
    """
    Check that the specified :py:class:`vc2_conformance._symbol_re.Matcher` has
    reached a valid end for the sequence of parse codes specified.
    
    If the matcher still expects more parse codes, ``exception_type`` will be
    raised with the following arguments:
    
    * The ``parse_code`` will be None
    * A list of parse codes (as a
      :py:class:`~vc2_conformance.tables.ParseCodes`) which would have been
      valid (or ``None`` if any parse code would be allowed.
    * A boolean which is True if it would have been valid to end the sequence
      at this point. (Always False, in this case)
    """
    if not matcher.is_complete():
        expected_parse_codes = []
        for parse_code_name in matcher.valid_next_symbols():
            if parse_code_name == WILDCARD:
                expected_parse_codes = None
            elif expected_parse_codes is not None:
                expected_parse_codes.append(getattr(ParseCodes, parse_code_name))
        
        raise exception_type(None, expected_parse_codes, False)


def assert_level_constraint(state, key, value):
    """
    Check that the given key and value is allowed according to the
    :py:data:`vc2_conformance.tables.LEVEL_CONSTRAINTS`. Throws a
    :py;exc:`vc2_conformance.decoder.exceptions.ValueNotAllowedInLevel`
    exception on failure.
    
    Takes the current :py:class:`~vc2_conformance.state.State` instance from
    which the current
    :py:attr:`~vc2_conformance.state.State._level_constrained_values` will be
    checked and updated (and created if it does not exist).
    """
    state.setdefault("_level_constrained_values", {})
    
    allowed_values = allowed_values_for(
        LEVEL_CONSTRAINTS,
        key,
        state["_level_constrained_values"],
    )
    
    if value not in allowed_values:
        raise ValueNotAllowedInLevel(state["_level_constrained_values"], key, value, allowed_values)
    else:
        state["_level_constrained_values"][key] = value
    
