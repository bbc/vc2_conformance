"""
The :py:mod:`vc2_conformance.decoder.assertions` module contains functions
which perform checks which are used in multiple places within a bitstream and
have been factored-out to avoid repetition.
"""

from collections import OrderedDict

from vc2_data_tables import (
    ParseCodes,
    PictureCodingModes,
)

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.version_constraints import MINIMUM_MAJOR_VERSION

from vc2_conformance.symbol_re import WILDCARD, END_OF_SEQUENCE

from vc2_conformance.constraint_table import allowed_values_for

from vc2_conformance.decoder.exceptions import (
    ValueNotAllowedInLevel,
    NonConsecutivePictureNumbers,
    EarliestFieldHasOddPictureNumber,
    MajorVersionTooHigh,
)


def assert_in(value, collection, exception_type, *args):
    """
    Check to see if a value is a member of the provided collection using
    ``in``. If it is not, throws an exception of the given type with the value
    and collection passed as as arguments.
    """
    if value not in collection:
        raise exception_type(value, collection, *args)


def assert_in_enum(value, enum, exception_type):
    """
    Check to see if a value is a member of the provided assertion type. If it
    is not, throws an exception of the given type with the value as argument.
    """
    try:
        enum(value)
    except ValueError:
        raise exception_type(value)


def assert_parse_code_in_sequence(parse_code, matcher, exception_type, *args):
    """
    Check that the specified parse code's name matches the next value in the
    sequence defined by :py:class:`vc2_conformance.symbol_re.Matcher`.

    If it does not, ``exception_type`` will be raised with the following
    arguments:

    * The ``parse_code`` (as a :py:class:`~vc2_data_tables.ParseCodes`)
    * A list of parse codes (as a
      :py:class:`~vc2_data_tables.ParseCodes`) which would have been
      valid (or ``None`` if any parse code would be allowed.
    * A boolean which is True if it would have been valid to end the sequence
      at this point.
    * Any additional arguments passed to this function
    """
    parse_code = ParseCodes(parse_code)

    if not matcher.match_symbol(parse_code.name):
        expected_parse_codes = []
        expected_end = False
        for parse_code_name in matcher.valid_next_symbols():
            if parse_code_name == WILDCARD:
                expected_parse_codes = None
                break
            elif parse_code_name == END_OF_SEQUENCE:
                expected_end = True
            elif expected_parse_codes is not None:
                expected_parse_codes.append(getattr(ParseCodes, parse_code_name))

        raise exception_type(parse_code, expected_parse_codes, expected_end, *args)


def assert_parse_code_sequence_ended(matcher, exception_type, *args):
    """
    Check that the specified :py:class:`vc2_conformance.symbol_re.Matcher` has
    reached a valid end for the sequence of parse codes specified.

    If the matcher still expects more parse codes, ``exception_type`` will be
    raised with the following arguments:

    * The ``parse_code`` will be None
    * A list of parse codes (as a
      :py:class:`~vc2_data_tables.ParseCodes`) which would have been
      valid (or ``None`` if any parse code would be allowed.
    * A boolean which is True if it would have been valid to end the sequence
      at this point. (Always False, in this case)
    * Any additional arguments passed to this function
    """
    if not matcher.is_complete():
        expected_parse_codes = []
        for parse_code_name in matcher.valid_next_symbols():
            if parse_code_name == WILDCARD:
                expected_parse_codes = None
                break
            elif expected_parse_codes is not None:
                expected_parse_codes.append(getattr(ParseCodes, parse_code_name))

        raise exception_type(None, expected_parse_codes, False, *args)


def assert_level_constraint(state, key, value):
    """
    Check that the given key and value is allowed according to the
    :py:data:`vc2_conformance.level_constraints.LEVEL_CONSTRAINTS`. Throws a
    :py;exc:`vc2_conformance.decoder.exceptions.ValueNotAllowedInLevel`
    exception on failure.

    Takes the current :py:class:`~vc2_conformance.pseudocode.state.State` instance from
    which the current
    :py:attr:`~vc2_conformance.pseudocode.state.State._level_constrained_values` will be
    created/updated.
    """
    state.setdefault("_level_constrained_values", OrderedDict())

    allowed_values = allowed_values_for(
        LEVEL_CONSTRAINTS,
        key,
        state["_level_constrained_values"],
    )

    if value not in allowed_values:
        raise ValueNotAllowedInLevel(
            state["_level_constrained_values"], key, value, allowed_values
        )
    else:
        state["_level_constrained_values"][key] = value


def assert_picture_number_incremented_as_expected(state, picture_number_offset):
    """
    Check that ``state["picture_number"]`` has been set to an appropriate value
    by (12.2) picture_header or (14.2) fragment_header.  It should be called
    after the picture number has been read from the stream into
    ``state["picture_number"]`` and with the
    :py:func:`~vc2_conformance.decoder.io.tell` value just after the value was
    read.

    This assertion will check that:

    * (12.2), (14.2) Picture numbers in a sequence must increment by 1 and wrap after
      2^32-1 back to zero, throwing :py:exc:`NonConsecutivePictureNumbers` if
      this is not the case.
    * (12.2), (14.2) When coded as fields, the first field in the sequence must
      have an even picture number, throwing
      :py:exc:`EarliestFieldHasOddPictureNumber` if this is not the case.

    This assertion also has the following side-effects:

    * Sets ``state["_last_picture_number"]`` to ``state["picture_number"]``
    * Sets ``state["_last_picture_number_offset"]`` to the value passed in the
      picture_number_offset argument.
    * Increments ``state["_num_pictures_in_sequence"]``

    In the case of fragments (14.2), this assertion should be called only for
    the first fragment in a picture (with fragment_slice_count==0).
    """
    # (12.2), (14.4) Picture numbers in a sequence must increment by 1 and wrap
    # after 2^32-1 back to zero
    if "_last_picture_number" in state:
        expected_picture_number = (state["_last_picture_number"] + 1) & 0xFFFFFFFF
        if state["picture_number"] != expected_picture_number:
            raise NonConsecutivePictureNumbers(
                state["_last_picture_number_offset"],
                state["_last_picture_number"],
                picture_number_offset,
                state["picture_number"],
            )
    state["_last_picture_number"] = state["picture_number"]
    state["_last_picture_number_offset"] = picture_number_offset

    # (12.2), (14.4) When coded as fields, the first field in the sequence must
    # have an even picture number.
    if state["picture_coding_mode"] == PictureCodingModes.pictures_are_fields:
        early_field = state["_num_pictures_in_sequence"] % 2 == 0
        even_number = state["picture_number"] % 2 == 0
        if early_field and not even_number:
            raise EarliestFieldHasOddPictureNumber(state["picture_number"])
    state["_num_pictures_in_sequence"] += 1


def log_version_lower_bound(state, minimum_major_version):
    """
    Records an instance where a value in the stream requires that
    major_version have a certain value. These will later be checked by
    :py:func:`assert_major_version_is_minimal`. Bounds are logged in
    ``state["_expected_major_version"]``

    Parameters
    ==========
    state : :py:class:`~vc2_conformance.pseudocode.state.State`
    minimum_major_version : int
        The minimum major version number allowed to support the feature being
        logged.
    """
    state["_expected_major_version"] = max(
        state.get("_expected_major_version", MINIMUM_MAJOR_VERSION),
        minimum_major_version,
    )


def assert_major_version_is_minimal(state):
    """
    Checks whether the major_version number supplied is the lowest possible
    major_version number for this stream (as required by (11.2.2)). Should be
    called once at the end of a stream.
    """
    major_version = state["major_version"]
    expected_major_version = state.get("_expected_major_version", MINIMUM_MAJOR_VERSION)

    # Errata: The following special case was missing from the spec
    #
    # (11.2.2) Special case for empty sequences of fragmented pictures: When an
    # encoder is configured to produce fragmented pictures in streams the
    # major_version needs to be set to '3' to allow fragmented picture data
    # units. In the case of an empty sequence, major_version may not have to be
    # '3' since no data units with a fragment parse code will be present. To
    # make the life of encoders developers easier in this special case, the
    # spec permits them to set major_version to '3' even when no fragmented
    # picture data units appear in the stream enabling them to use the same
    # sequence header for all sequences, regardless of length.
    if state["_num_pictures_in_sequence"] == 0 and major_version == 3:
        return

    if major_version > expected_major_version:
        raise MajorVersionTooHigh(major_version, expected_major_version)
