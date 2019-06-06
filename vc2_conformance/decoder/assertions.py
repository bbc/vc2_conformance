"""
:py:mod:`vc2_conformance.decoder.assertions`: Assertions functions for conformance checks
=========================================================================================
"""

from vc2_conformance.tables import (
    ParseCodes,
    LEVEL_CONSTRAINTS,
    PictureCodingModes,
)

from vc2_conformance._symbol_re import WILDCARD, END_OF_SEQUENCE

from vc2_conformance._constraint_table import allowed_values_for

from vc2_conformance.decoder.io import tell

from vc2_conformance.decoder.exceptions import (
    ValueNotAllowedInLevel,
    NonConsecutivePictureNumbers,
    EarliestFieldHasOddPictureNumber,
)


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
    created/updated.
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


def assert_picture_number_incremented_as_expected(state):
    """
    Check that ``state["picture_number"]`` has been set to an appropriate value
    by (12.2) picture_header or (14.2) fragment_header.  It should be called
    immediately after the picture number has been read from the stream.
    
    This assertion will check that:
    
    * (12.2), (14.2) Picture numbers in a sequence must increment by 1 and wrap after
      2^32-1 back to zero, throwing :py:exc:`NonConsecutivePictureNumbers` if
      this is not the case.
    * (12.2), (14.2) When coded as fields, the first field in the sequence must
      have an even picture number, throwing
      :py:exc:`EarliestFieldHasOddPictureNumber` if this is not the case.
    
    This assertion also has the following side-effects:
    
    * Sets ``state["_last_picture_number"]`` to ``state["picture_number"]``
    * Sets ``state["_last_picture_number_offset"]`` to the current
      :py:func:`~vc2_conformance.decoder.io.tell`.
    * Increments ``state["_num_pictures_in_sequence"]``
    
    In the case of fragments (14.2), this assertion should be called only for
    the first fragment in a picture (with fragment_slice_count==0).
    """
    this_picture_header_offset = tell(state)
    
    # (12.2), (14.4) Picture numbers in a sequence must increment by 1 and wrap
    # after 2^32-1 back to zero
    if "_last_picture_number" in state:
        expected_picture_number = (state["_last_picture_number"] + 1) & 0xFFFFFFFF
        if state["picture_number"] != expected_picture_number:
            raise NonConsecutivePictureNumbers(
                state["_last_picture_number_offset"],
                state["_last_picture_number"],
                this_picture_header_offset,
                state["picture_number"],
            )
    state["_last_picture_number"] = state["picture_number"]
    state["_last_picture_number_offset"] = this_picture_header_offset
    
    # (12.2), (14.4) When coded as fields, the first field in the sequence must
    # have an even picture number.
    if state["_picture_coding_mode"] == PictureCodingModes.pictures_are_fields:
        early_field = state["_num_pictures_in_sequence"] % 2 == 0
        even_number = state["picture_number"] % 2 == 0
        if early_field and not even_number:
            raise EarliestFieldHasOddPictureNumber(state["picture_number"])
    state["_num_pictures_in_sequence"] += 1
