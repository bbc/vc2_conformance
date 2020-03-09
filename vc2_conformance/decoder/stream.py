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

from vc2_data_tables import (
    PARSE_INFO_PREFIX,
    PARSE_INFO_HEADER_BYTES,
    ParseCodes,
    PROFILES,
    PictureCodingModes,
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
    LevelInvalidSequence,
    ParseCodeNotAllowedInProfile,
    OddNumberOfFieldsInSequence,
    SequenceContainsIncompleteFragmentedPicture,
    PictureInterleavedWithFragmentedPicture,
)

from vc2_conformance.symbol_re import Matcher

from vc2_conformance.picture_decoding import picture_decode

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
from vc2_conformance.decoder.picture_syntax import picture_parse
from vc2_conformance.decoder.fragment_syntax import fragment_parse


__all__ = [
    "parse_sequence",
    "output_picture",
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
    state["_generic_sequence_matcher"] = Matcher("sequence_header .* end_of_sequence")
    ## End not in spec
    
    state["_num_pictures_in_sequence"] = 0  ## Not in spec
    state["_fragment_slices_remaining"] = 0  ## Not in spec
    
    parse_info(state)
    while not is_end_of_sequence(state):
        if (is_seq_header(state)):
            state["video_parameters"] = sequence_header(state)
        elif (is_picture(state)):
            # Errata: fragments under-specified in spec
            #
            # (14.2) Picture data units may not be interleaved with in-progress
            # fragmented pictures.
            ## Begin not in spec
            if state["_fragment_slices_remaining"] != 0:
                raise PictureInterleavedWithFragmentedPicture(
                    state["_picture_initial_fragment_offset"],
                    tell(state),
                    state["fragment_slices_received"],
                    state["_fragment_slices_remaining"],
                )
            ## End not in spec
            
            picture_parse(state)
            picture_decode(state)
            output_picture(state, state["current_picture"], state["video_parameters"])
        elif (is_fragment(state)):
            fragment_parse(state)
            if state["fragmented_picture_done"]:
                picture_decode(state)
                output_picture(state, state["current_picture"], state["video_parameters"])
        elif (is_auxiliary_data(state)):
            auxiliary_data(state)
        elif (is_padding_data(state)):
            padding(state)
        parse_info(state)
    
    # (10.4.1) and (C.3) Check sequence structure allowed to end at this point
    ## Begin not in spec
    assert_parse_code_sequence_ended(state["_generic_sequence_matcher"], GenericInvalidSequence)
    if "_level_sequence_matcher" in state:
        assert_parse_code_sequence_ended(
            state["_level_sequence_matcher"],
            LevelInvalidSequence,
            state["level"],
        )
    ## End not in spec
    
    # Errata: fragments under-specified in spec
    #
    # (14.2) Ensure that any fragmented picture has been received completely by
    # the end of the stream.
    ## Begin not in spec
    if state["_fragment_slices_remaining"] != 0:
        raise SequenceContainsIncompleteFragmentedPicture(
            state["_picture_initial_fragment_offset"],
            state["fragment_slices_received"],
            state["_fragment_slices_remaining"],
        )
    ## End not in spec
    
    # (10.4.3) When pictures are fields, a sequence should contain a whole
    # number of frames
    ## Begin not in spec
    if state["_picture_coding_mode"] == PictureCodingModes.pictures_are_fields:
        if state["_num_pictures_in_sequence"] % 2 != 0:
            raise OddNumberOfFieldsInSequence(state["_num_pictures_in_sequence"])
    ## End not in spec
    
    # (10.3) Check for any unused data in the stream
    ## Begin not in spec
    if state["current_byte"] is not None:
        raise TrailingBytesAfterEndOfSequence()
    ## End not in spec


def output_picture(state, picture, video_parameters):
    """
    (10.4.999) Output a completely decoded picture.
    
    This function's existance is defined by the specification but its behaviour
    is left undefined. In this implementation,
    ``state["_output_picture_callback"]`` is called with the picture and video
    parameters as arguments.
    """
    if "_output_picture_callback" in state:
        state["_output_picture_callback"](picture, video_parameters)


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
    
    # (10.4.1) Check that the sequence starts with a sequence_header and ends
    # with and end_of_sequence.
    ## Begin not in spec
    assert_parse_code_in_sequence(
        state["parse_code"],
        state["_generic_sequence_matcher"],
        GenericInvalidSequence,
    )
    ## End not in spec
    
    # (C.3) Check that the sequence follows the pattern dictated by the current
    # level (NB: this matcher is populated later by parse_parameters (11.2.1)
    # when the level is read for the first time.
    ## Begin not in spec
    if "_level_sequence_matcher" in state:
        assert_parse_code_in_sequence(
            state["parse_code"],
            state["_level_sequence_matcher"],
            LevelInvalidSequence,
            state["level"],
        )
    ## End not in spec
    
    # (C.2.2) Ensure that only the profile-permitted parse codes are used
    ## Begin not in spec
    if "profile" in state:
        profile_params = PROFILES[state["profile"]]
        if state["parse_code"] not in profile_params.allowed_parse_codes:
            raise ParseCodeNotAllowedInProfile(state["parse_code"], state["profile"])
    ## End not in spec
    
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
            raise MissingNextParseOffset(state["parse_code"])
    
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
