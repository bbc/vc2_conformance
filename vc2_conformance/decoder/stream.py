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
)

from vc2_conformance.decoder.assertions import assert_in_enum

from vc2_conformance.decoder.io import (
    init_io,
    byte_align,
    read_uint_lit,
)


@ref_pseudocode
def parse_sequence(state):
    """
    (10.4.1) Parse a complete VC-2 sequence.
    
    This version of the function has been modified to accept a state dictionary
    as an argument since the spec 
    """
    parse_info(state)
    while(not is_end_of_sequence(state)):
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
    # Check for any unused data in the stream
    if state["current_byte"] is not None:
        raise TrailingBytesAfterEndOfSequence()
    ## End not in spec
    
    # Required to ensure comment line above is part of the function
    pass  ## Not in spec


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
    
    # Check that the previous parse_info's next_parse_offset was calculated
    # correctly
    ## Begin not in spec
    this_parse_info_offset = state["_file"].tell() - 1  # Will be about to read *next* byte
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
    
    # Capture and check the parse_info prefix
    ### read_uint_lit(state, 4)
    ## Begin not in spec
    prefix = read_uint_lit(state, 4)
    if prefix != PARSE_INFO_PREFIX:
        raise BadParseInfoPrefix(prefix)
    ## End not in spec
    
    # Check the parse_code is a supported value
    state["parse_code"] = read_uint_lit(state, 1)
    assert_in_enum(state["parse_code"], ParseCodes, BadParseCode) ## Not in spec
    
    # Check that the next_parse_offset holds a plausible value
    state["next_parse_offset"] = read_uint_lit(state, 4)
    ## Begin not in spec
    if state["parse_code"] == ParseCodes.end_of_sequence:
        # End of stream must have '0' as next offset
        if state["next_parse_offset"] != 0:
            raise NonZeroNextParseOffsetAtEndOfSequence(state["next_parse_offset"])
    elif not (is_picture(state) or is_fragment(state)):
        # Non-picture containing blocks *must* have a non-zero offset
        if state["next_parse_offset"] == 0:
            raise MissingNextParseOffset()
    
    # Offsets pointing inside this parse_info bock are always invalid
    if 1 <= state["next_parse_offset"] < PARSE_INFO_HEADER_BYTES:
        raise InvalidNextParseOffset(state["next_parse_offset"])
    ## End not in spec
    
    # Check that the previous parse offset was calculated correctly
    state["previous_parse_offset"] = read_uint_lit(state, 4)
    ## Begin not in spec
    if last_parse_info_offset is None:
        # This is the first parse_info encountered, must be zero
        if state["previous_parse_offset"] != 0:
            raise NonZeroPreviousParseOffsetAtStartOfSequence(state["previous_parse_offset"])
    else:
        true_previous_parse_offset = this_parse_info_offset - last_parse_info_offset
        if state["previous_parse_offset"] != true_previous_parse_offset:
            raise InconsistentPreviousParseOffset(
                last_parse_info_offset,
                state["previous_parse_offset"],
                true_parse_offset,
            )
    ## End not in spec
    
    state["_last_parse_info_offset"] = this_parse_info_offset  ## Not in spec
