"""
:py:mod:`vc2_conformance.stream`: (10) VC-2 Stream Syntax
=========================================================
"""

from vc2_conformance.metadata import ref_pseudocode

from vc2_conformance.state import State

from vc2_conformance.parse_code_functions import (
    is_seq_header,
    is_picture,
    is_fragment,
    is_auxiliary_data,
    is_padding_data,
    is_end_of_sequence,
)

from vc2_conformance.tables import (
    PARSE_INFO_PREFIX,
    PARSE_INFO_HEADER_BYTES,
    ParseCodes,
)

from vc2_conformance.decoder.exceptions import (
    TrailingBytesAfterEndOfSequence,
    BadParseInfoPrefix,
    BadParseCode,
    InconsistentNextParseOffset,
    MissingNextParseOffset,
    InvalidNextParseOffset,
    NonZeroNextParseOffsetAtEndOfSequence,
    InconsistentPreviousParseOffset,
    NonZeroPreviousParseOffsetAtStartOfSequence,
    GenericInvalidSequence,
)

from vc2_conformance._symbol_re import Matcher

from vc2_conformance.decoder.assertions import (
    assert_in_enum,
    assert_parse_code_in_sequence,
    assert_parse_code_sequence_ended,
)

from vc2_conformance.decoder.io import (
    init_io,
    tell,
    byte_align,
    read_uint_lit,
)

from vc2_conformance.decoder.sequence_header import sequence_header


__all__ = [
    "parse_sequence",
    "auxiliary_data",
    "padding",
    "parse_info",
]


def reset_state(state):
    """
    Reset a :py:class:`~vc2_conformance.state.State` dictionary to only include
    values retained between sequences in a VC-2 stream.
    """


@ref_pseudocode
def parse_sequence(state):
    """
    (10.4.1) Parse a complete VC-2 sequence.
    
    This version of the function has been modified to accept a state dictionary
    as an argument since the spec 
    """
    # (10.4.1) Check that the sequence starts with a sequence_header and ends
    # with and end_of_sequence.
    ## Begin not in spec
    valid_sequence_matcher = Matcher("sequence_header .* end_of_sequence")
    ## End not in spec
    
    parse_info(state)
    while not is_end_of_sequence(state):
        ## Begin not in spec
        assert_parse_code_in_sequence(state["parse_code"], valid_sequence_matcher, GenericInvalidSequence)
        ## End not in spec
        
        if (is_seq_header(state)):
            sequence_header(state)
        elif (is_picture(state)):
            picture_parse(state)
        elif (is_fragment(state)):
            fragment_parse(state)
        elif (is_auxiliary_data(state)):
            auxiliary_data(state)
        elif (is_padding_data(state)):
            padding(state)
        parse_info(state)
    
    ## Begin not in spec
    assert_parse_code_in_sequence(state["parse_code"], valid_sequence_matcher, GenericInvalidSequence)
    assert_parse_code_sequence_ended(valid_sequence_matcher, GenericInvalidSequence)
    ## End not in spec
    
    ## Begin not in spec
    # (10.3) Check for any unused data in the stream
    if state["current_byte"] is not None:
        raise TrailingBytesAfterEndOfSequence()
    ## End not in spec


@ref_pseudocode
def auxiliary_data(state):
    """(10.4.4)"""
    byte_align(state)
    for i in range(state["next_parse_offset"]-13):
        read_uint_lit(state, 1)


@ref_pseudocode
def padding(state):
    """(10.4.5)"""
    byte_align(state)
    for i in range(state["next_parse_offset"]-13):
        read_uint_lit(state, 1)


@ref_pseudocode
def parse_info(state):
    """(10.5.1)"""
    byte_align(state)
    
    # (10.5.1) Check that the previous parse_info's next_parse_offset was
    # calculated correctly
    ## Begin not in spec
    this_parse_info_offset = tell(state)[0]
    last_parse_info_offset = state.get("_last_parse_info_offset", None)
    
    if state.get("next_parse_offset"):
        true_parse_offset = this_parse_info_offset - last_parse_info_offset
        last_next_parse_offset = state["next_parse_offset"]
        if (last_next_parse_offset != 0 and last_next_parse_offset != true_parse_offset):
            raise InconsistentNextParseOffset(
                last_parse_info_offset,
                last_next_parse_offset,
                true_parse_offset,
            )
    ## End not in spec
    
    # (10.5.1) Capture and check the parse_info prefix
    ### read_uint_lit(state, 4)
    ## Begin not in spec
    prefix = read_uint_lit(state, 4)
    if prefix != PARSE_INFO_PREFIX:
        raise BadParseInfoPrefix(prefix)
    ## End not in spec
    
    # (10.5.1) Check the parse_code is a supported value
    state["parse_code"] = read_uint_lit(state, 1)
    assert_in_enum(state["parse_code"], ParseCodes, BadParseCode) ## Not in spec
    
    # (10.5.1) Check that the next_parse_offset holds a plausible value
    state["next_parse_offset"] = read_uint_lit(state, 4)
    ## Begin not in spec
    if state["parse_code"] == ParseCodes.end_of_sequence:
        # (10.5.1) End of stream must have '0' as next offset
        if state["next_parse_offset"] != 0:
            raise NonZeroNextParseOffsetAtEndOfSequence(state["next_parse_offset"])
    elif not (is_picture(state) or is_fragment(state)):
        # (10.5.1) Non-picture containing blocks *must* have a non-zero offset
        if state["next_parse_offset"] == 0:
            raise MissingNextParseOffset()
    
    # (10.5.1) Offsets pointing inside this parse_info bock are always invalid
    if 1 <= state["next_parse_offset"] < PARSE_INFO_HEADER_BYTES:
        raise InvalidNextParseOffset(state["next_parse_offset"])
    ## End not in spec
    
    # (10.5.1) Check that the previous parse offset was calculated correctly
    state["previous_parse_offset"] = read_uint_lit(state, 4)
    ## Begin not in spec
    if last_parse_info_offset is None:
        # (10.5.1) This is the first parse_info encountered, must be zero
        if state["previous_parse_offset"] != 0:
            raise NonZeroPreviousParseOffsetAtStartOfSequence(state["previous_parse_offset"])
    else:
        # (10.5.1) Previous offset must be present and calculated correctly otherwise
        true_previous_parse_offset = this_parse_info_offset - last_parse_info_offset
        if state["previous_parse_offset"] != true_previous_parse_offset:
            raise InconsistentPreviousParseOffset(
                last_parse_info_offset,
                state["previous_parse_offset"],
                true_parse_offset,
            )
    ## End not in spec
    
    state["_last_parse_info_offset"] = this_parse_info_offset  ## Not in spec
