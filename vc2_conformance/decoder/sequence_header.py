"""
:py:mod:`vc2_conformance.sequence_header`: (11) Sequence Header
===============================================================
"""

from vc2_conformance.metadata import ref_pseudocode

from vc2_conformance.vc2_math import intlog2

from vc2_conformance.tables import Profiles, Levels

from vc2_conformance.video_parameters import (
    set_source_defaults,
)

from vc2_conformance.decoder.assertions import assert_in_enum

from vc2_conformance.decoder.exceptions import (
    SequenceHeaderChangedMidSequence,
    ProfileChanged,
    LevelChanged,
    BadProfile,
    BadLevel,
)

from vc2_conformance.decoder.io import (
    record_bitstream_start,
    record_bitstream_finish,
    tell,
    byte_align,
    read_bool,
    read_uint,
)


@ref_pseudocode
def sequence_header(state):
    """(11.1)"""
    byte_align(state)
    
    # Record this sequence_header as it appears in the bitstream
    ## Begin not in spec
    this_sequence_header_offset = tell(state)[0]
    record_bitstream_start(state)
    ## End not in spec
    
    parse_parameters(state)
    base_video_format = read_uint(state)
    video_parameters = source_parameters(state, base_video_format)
    picture_coding_mode = read_uint(state)
    set_coding_parameters(state, video_parameters, picture_coding_mode)
    
    # (11.1) Check that the this sequence_header is byte-for-byte identical
    # with the previous sequence_header in the sequence
    ## Begin not in spec
    this_sequence_header_bytes = record_bitstream_finish(state)
    if "_last_sequence_header_bytes" in state:
        if this_sequence_header_bytes != state["_last_sequence_header_bytes"]:
            raise SequenceHeaderChangedMidSequence(
                state["_last_sequence_header_offset"],
                state["_last_sequence_header_bytes"],
                this_sequence_header_offset,
                this_sequence_header_bytes,
            )
    state["_last_sequence_header_bytes"] = this_sequence_header_bytes
    state["_last_sequence_header_offset"] = this_sequence_header_offset
    ## End not in spec
    
    return video_parameters


@ref_pseudocode
def parse_parameters(state):
    """(11.2.1)"""
    this_parse_parameters_offset = tell(state)  ## Not in spec
    
    state["major_version"] = read_uint(state)
    state["minor_version"] = read_uint(state)
    
    state["profile"] = read_uint(state)
    # (C.2) Profile must be a supported value
    assert_in_enum(state["profile"], Profiles, BadProfile) ## Not in spec
    
    # (11.2.1) Ensure profile doesn't change (even between sequences)
    ## Begin not in spec
    if state.get("_last_profile", state["profile"]) != state["profile"]:
        raise ProfileChanged(
            state["_last_parse_parameters_offset"],
            state["_last_profile"],
            this_parse_parameters_offset,
            state["profile"],
        )
    ## End not in spec
    
    state["level"] = read_uint(state)
    
    # (C.3) Level must be a supported value
    assert_in_enum(state["level"], Levels, BadLevel) ## Not in spec
    
    # (11.2.1)  Ensure level doesn't change (even between sequences)
    ## Begin not in spec
    if state.get("_last_level", state["level"]) != state["level"]:
        raise LevelChanged(
            state["_last_parse_parameters_offset"],
            state["_last_level"],
            this_parse_parameters_offset,
            state["level"],
        )
    ## End not in spec
    
    ## Begin not in spec
    state["_last_parse_parameters_offset"] = this_parse_parameters_offset
    state["_last_profile"] = state["profile"]
    state["_last_level"] = state["level"]
    ## End not in spec
    
    # Included to ensure comment above is included
    pass  ## Not in spec


@ref_pseudocode
def source_parameters(state, base_video_format):
    """(11.4.1)"""
    video_parameters = set_source_defaults(base_video_format)
    frame_size(state, video_parameters)
    color_diff_sampling_format(state, video_parameters)
    scan_format(state, video_parameters)
    frame_rate(state, video_parameters)
    pixel_aspect_ratio(state, video_parameters)
    clean_area(state, video_parameters)
    signal_range(state, video_parameters)
    color_spec(state, video_parameters)
    return video_parameters


@ref_pseudocode
def frame_size(state, video_parameters):
    """(11.4.3)"""
    custom_dimensions_flag = read_bool(state)
    if(custom_dimensions_flag):
        video_parameters["frame_width"] = read_uint(state)
        video_parameters["frame_height"] = read_uint(state)


@ref_pseudocode
def color_diff_sampling_format(state, video_parameters):
    """(11.4.4)"""
    custom_color_diff_format_flag = read_bool(state)
    if(custom_color_diff_format_flag):
        video_parameters["color_diff_format_index"] = read_uint(state)


@ref_pseudocode
def scan_format(state, video_parameters):
    """(11.4.5)"""
    custom_scan_format_flag = read_bool(state)
    if(custom_scan_format_flag):
        video_parameters["source_sampling"] = read_uint(state)


@ref_pseudocode
def frame_rate(state, video_parameters):
    """(11.4.6)"""
    custom_frame_rate_flag = read_bool(state)
    if(custom_frame_rate_flag):
        index = read_uint(state)
        if(index == 0):
            video_parameters["frame_rate_numer"] = read_uint(state)
            video_parameters["frame_rate_denom"] = read_uint(state)
        else:
            preset_frame_rate(video_parameters, index)


@ref_pseudocode
def pixel_aspect_ratio(state, video_parameters):
    """(11.4.7)"""
    custom_pixel_aspect_ratio_flag = read_bool(state)
    if(custom_pixel_aspect_ratio_flag):
        index = read_uint(state)
        if(index == 0):
            video_parameters["pixel_aspect_ratio_numer"] = read_uint(state)
            video_parameters["pixel_aspect_ratio_denom"] = read_uint(state)
        else:
            preset_pixel_aspect_ratio(video_parameters, index)


@ref_pseudocode
def clean_area(state, video_parameters):
    """(11.4.8)"""
    custom_clean_area_flag = read_bool(state)
    if(custom_clean_area_flag):
        video_parameters["clean_width"] = read_uint(state)
        video_parameters["clean_height"] = read_uint(state)
        video_parameters["left_offset"] = read_uint(state)
        video_parameters["top_offset"] = read_uint(state)


@ref_pseudocode
def signal_range(state, video_parameters):
    """(11.4.9)"""
    custom_signal_range_flag = read_bool(state)
    if(custom_signal_range_flag):
        index = read_uint(state)
        if(index == 0):
            video_parameters["luma_offset"] = read_uint(state)
            video_parameters["luma_excursion"] = read_uint(state)
            video_parameters["color_diff_offset"] = read_uint(state)
            video_parameters["color_diff_excursion"] = read_uint(state)
        else:
            preset_signal_range(video_parameters, index)


@ref_pseudocode
def color_spec(state, video_parameters):
    """(11.4.10.1)"""
    custom_color_spec_flag = read_bool(state)
    if(custom_color_spec_flag):
        index = read_uint(state)
        preset_color_spec(video_parameters, index)
        if(index == 0):
            color_primaries(state, video_parameters)
            color_matrix(state, video_parameters)
            transfer_function(state, video_parameters)


@ref_pseudocode
def color_primaries(state, video_parameters):
    """(11.4.10.2)"""
    custom_color_primaries_flag = read_bool(state)
    if(custom_color_primaries_flag):
        index = read_uint(state)
        preset_color_primaries(video_parameters,index)


@ref_pseudocode
def color_matrix(state, video_parameters):
    """(11.4.10.3)"""
    custom_color_matrix_flag = read_bool(state)
    if(custom_color_matrix_flag):
        index = read_uint(state)
        preset_color_matrix(video_parameters, index)


@ref_pseudocode
def transfer_function(state, video_parameters):
    """(11.4.10.4)"""
    custom_transfer_function_flag = read_bool(state)
    if(custom_transfer_function_flag):
        index = read_uint(state)
        preset_transfer_function(video_parameters ,index)


@ref_pseudocode
def set_coding_parameters(state, video_parameters, picture_coding_mode):
    """(11.6.1)"""
    picture_dimensions(state, video_parameters, picture_coding_mode)
    video_depth(state, video_parameters)


@ref_pseudocode
def picture_dimensions(state, video_parameters, picture_coding_mode):
    """(11.6.2)"""
    state["luma_width"] = video_parameters["frame_width"]
    state["luma_height"] = video_parameters["frame_height"]
    state["color_diff_width"] = state["luma_width"]
    state["color_diff_height"] = state["luma_height"]
    color_diff_format_index = video_parameters["color_diff_format_index"]
    if (color_diff_format_index == 1):
        state["color_diff_width"] //= 2
    if (color_diff_format_index == 2):
        state["color_diff_width"] //= 2
        state["color_diff_height"] //= 2
    if (picture_coding_mode == 1):
        state["luma_height"] //= 2
        state["color_diff_height"] //= 2


@ref_pseudocode
def video_depth(state, video_parameters):
    """(11.6.3)"""
    state["luma_depth"] = intlog2(video_parameters["luma_excursion"]+1)
    state["color_diff_depth"] = intlog2(video_parameters["color_diff_excursion"]+1)
