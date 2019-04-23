"""
Transformed versions of the VC-2 pseudo code implementing the majority of the
VC-2 bitstream format, with the exception of slice data which is handled
separately.
"""

from collections import defaultdict

from vc2_conformance.bitstream.serdes import context_type

from vc2_conformance.tables import *

from vc2_conformance.state import State

from vc2_conformance.video_parameters import (
    set_source_defaults,
    set_coding_parameters,
    preset_frame_rate,
    preset_pixel_aspect_ratio,
    preset_signal_range,
    preset_color_primaries,
    preset_color_matrix,
    preset_transfer_function,
    preset_color_spec,
)

from vc2_conformance.parse_code_functions import (
    is_seq_header,
    is_end_of_sequence,
    is_auxiliary_data,
    is_padding_data,
    is_picture,
    is_ld_picture,
    is_hq_picture,
    is_fragment,
)

from vc2_conformance.bitstream.vc2.fixeddicts import *

from vc2_conformance.bitstream.vc2.slice_arrays import (
    transform_data,
    fragment_data,
)

__all__ = [
    "parse_sequence",
    
    "auxiliary_data",
    "padding",
    
    "parse_info",
    
    "sequence_header",
    "parse_parameters",
    "source_parameters",
    "frame_size",
    "color_diff_sampling_format",
    "scan_format",
    "frame_rate",
    "pixel_aspect_ratio",
    "clean_area",
    "signal_range",
    "color_spec",
    "color_primaries",
    "color_matrix",
    "transfer_function",
    
    "picture_parse",
    "picture_header",
    "wavelet_transform",
    
    "transform_parameters",
    "extended_transform_parameters",
    "slice_parameters",
    "quant_matrix",
    
    "fragment_parse",
    "fragment_header",
]


################################################################################
# (10) Stream decoding
################################################################################

@context_type(Sequence)
def parse_sequence(serdes):
    """
    (10.4.1) Parse a whole VC-2 sequence (i.e. file), discarding the contents.
    Given as a specification of the data structure, not an actually useful
    parsing loop.
    """
    state = State()
    
    serdes.declare_list("data_units")
    
    serdes.subcontext_enter("data_units")
    serdes.set_context_type(DataUnit)
    with serdes.subcontext("parse_info"):
        parse_info(serdes, state)
    while not is_end_of_sequence(state):
        if is_seq_header(state):
            with serdes.subcontext("sequence_header"):
                sequence_header(serdes, state)
        elif is_picture(state):
            with serdes.subcontext("picture_parse"):
                picture_parse(serdes, state)
        elif is_fragment(state):
            with serdes.subcontext("fragment_parse"):
                fragment_parse(serdes, state)
        elif is_auxiliary_data(state):
            with serdes.subcontext("auxiliary_data"):
                auxiliary_data(serdes, state)
        elif is_padding_data(state):  # Errata: listed as 'is_padding' in standard
            with serdes.subcontext("padding"):
                padding(serdes, state)
        serdes.subcontext_leave()
        
        serdes.subcontext_enter("data_units")
        serdes.set_context_type(DataUnit)
        with serdes.subcontext("parse_info"):
            parse_info(serdes, state)
    
    serdes.subcontext_leave()


@context_type(ParseInfo)
def parse_info(serdes, state):
    """(10.5.1) Read a parse_info header."""
    # Errata: Wording of spec requires this field to be aligned but the pseudo
    # code doesn't include a byte_align (and nor does the 'parse_sequence
    # function which calls it)
    serdes.byte_align("padding")
    
    serdes.uint_lit("parse_info_prefix", 4)
    state["parse_code"] = serdes.uint_lit("parse_code", 1)
    state["next_parse_offset"] = serdes.uint_lit("next_parse_offset", 4)
    state["previous_parse_offset"] = serdes.uint_lit("previous_parse_offset", 4)


@context_type(AuxiliaryData)
def auxiliary_data(serdes, state):
    """(10.4.4) Read an auxiliary data block."""
    serdes.byte_align("padding")
    serdes.bytes("bytes", state["next_parse_offset"] - PARSE_INFO_HEADER_BYTES)


@context_type(Padding)
def padding(serdes, state):
    """(10.4.5) Read a padding data block."""
    serdes.byte_align("padding")
    serdes.bytes("bytes", state["next_parse_offset"] - PARSE_INFO_HEADER_BYTES)


################################################################################
# (11) Sequence header parsing
################################################################################


@context_type(SequenceHeader)
def sequence_header(serdes, state):
    """(11.1) Parse a sequence header returning a VideoParameters object."""
    serdes.byte_align("padding")
    
    with serdes.subcontext("parse_parameters"):
        parse_parameters(serdes, state)
    
    base_video_format = serdes.uint("base_video_format")
    
    # For robustness against bad bitstreams, force unrecognised base formats to 'custom'
    try:
        BaseVideoFormats(base_video_format)
    except ValueError:
        base_video_format = BaseVideoFormats.custom_format
    
    with serdes.subcontext("video_parameters"):
        video_parameters = source_parameters(serdes, state, base_video_format)
    picture_coding_mode = serdes.uint("picture_coding_mode")
    set_coding_parameters(state, video_parameters, picture_coding_mode)
    
    return video_parameters


@context_type(ParseParameters)
def parse_parameters(serdes, state):
    """(11.2.1)"""
    state["major_version"] = serdes.uint("major_version")
    state["minor_version"] = serdes.uint("minor_version")
    state["profile"] = serdes.uint("profile")
    state["level"] = serdes.uint("level")


@context_type(SourceParameters)
def source_parameters(serdes, state, base_video_format):
    """
    (11.4.1) Parse the video source parameters. Returns a VideoParameters
    object.
    """
    video_parameters = set_source_defaults(base_video_format)
    
    with serdes.subcontext("frame_size"):
        frame_size(serdes, state, video_parameters)
    with serdes.subcontext("color_diff_sampling_format"):
        color_diff_sampling_format(serdes, state, video_parameters)
    with serdes.subcontext("scan_format"):
        scan_format(serdes, state, video_parameters)
    with serdes.subcontext("frame_rate"):
        frame_rate(serdes, state, video_parameters)
    with serdes.subcontext("pixel_aspect_ratio"):
        pixel_aspect_ratio(serdes, state, video_parameters)
    with serdes.subcontext("clean_area"):
        clean_area(serdes, state, video_parameters)
    with serdes.subcontext("signal_range"):
        signal_range(serdes, state, video_parameters)
    with serdes.subcontext("color_spec"):
        color_spec(serdes, state, video_parameters)
    
    return video_parameters

@context_type(FrameSize)
def frame_size(serdes, state, video_parameters):
    """(11.4.3) Override video parameter."""
    custom_dimensions_flag = serdes.bool("custom_dimensions_flag")
    if custom_dimensions_flag:
        video_parameters["frame_width"] = serdes.uint("frame_width")
        video_parameters["frame_height"] = serdes.uint("frame_height")

@context_type(ColorDiffSamplingFormat)
def color_diff_sampling_format(serdes, state, video_parameters):
    """(11.4.4) Override color sampling parameter."""
    custom_color_diff_format_flag = serdes.bool("custom_color_diff_format_flag")
    if custom_color_diff_format_flag:
        video_parameters["color_diff_format_index"] = serdes.uint("color_diff_format_index")

@context_type(ScanFormat)
def scan_format(serdes, state, video_parameters):
    """(11.4.5) Override source sampling parameter."""
    custom_scan_format_flag = serdes.bool("custom_scan_format_flag")
    if custom_scan_format_flag:
        video_parameters["source_sampling"] = serdes.uint("source_sampling")

@context_type(FrameRate)
def frame_rate(serdes, state, video_parameters):
    """(11.4.6) Override frame-rate parameter."""
    custom_frame_rate_flag = serdes.bool("custom_frame_rate_flag")
    
    if custom_frame_rate_flag:
        index = serdes.uint("index")
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            if index != 0:
                PresetFrameRates(index)
        except ValueError:
            index = PresetFrameRates.fps_24_over_1_001
        
        if index == 0:
            video_parameters["frame_rate_numer"] = serdes.uint("frame_rate_numer")
            video_parameters["frame_rate_denom"] = serdes.uint("frame_rate_denom")
        else:
            preset_frame_rate(video_parameters, index)

@context_type(PixelAspectRatio)
def pixel_aspect_ratio(serdes, state, video_parameters):  # Errata: called 'aspect_ratio' in spec
    """(11.4.7) Override pixel aspect ratio parameter."""
    custom_pixel_aspect_ratio_flag = serdes.bool("custom_pixel_aspect_ratio_flag")
    if custom_pixel_aspect_ratio_flag:
        index = serdes.uint("index")
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            if index != 0:
                PresetPixelAspectRatios(index)
        except ValueError:
            index = PresetPixelAspectRatios.ratio_1_1
        
        if index == 0:
            video_parameters["pixel_aspect_ratio_numer"] = serdes.uint("pixel_aspect_ratio_numer")
            video_parameters["pixel_aspect_ratio_denom"] = serdes.uint("pixel_aspect_ratio_denom")
        else:
            preset_pixel_aspect_ratio(video_parameters, index)

@context_type(CleanArea)
def clean_area(serdes, state, video_parameters):
    """(11.4.8) Override clean area parameter."""
    custom_clean_area_flag = serdes.bool("custom_clean_area_flag")
    if custom_clean_area_flag:
        video_parameters["clean_width"] = serdes.uint("clean_width")
        video_parameters["clean_height"] = serdes.uint("clean_height")
        video_parameters["left_offset"] = serdes.uint("left_offset")
        video_parameters["top_offset"] = serdes.uint("top_offset")

@context_type(SignalRange)
def signal_range(serdes, state, video_parameters):
    """(11.4.9) Override signal parameter."""
    custom_signal_range_flag = serdes.bool("custom_signal_range_flag")
    if custom_signal_range_flag:
        index = serdes.uint("index")
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            if index != 0:
                PresetSignalRanges(index)
        except ValueError:
            index = PresetSignalRanges.range_8_bit_full_range
        
        if index == 0:
            video_parameters["luma_offset"] = serdes.uint("luma_offset")
            video_parameters["luma_excursion"] = serdes.uint("luma_excursion")
            video_parameters["color_diff_offset"] = serdes.uint("color_diff_offset")
            video_parameters["color_diff_excursion"] = serdes.uint("color_diff_excursion")
        else:
            preset_signal_range(video_parameters, index)

@context_type(ColorSpec)
def color_spec(serdes, state, video_parameters):
    """(11.4.10.1) Override color specification parameter."""
    custom_color_spec_flag = serdes.bool("custom_color_spec_flag")
    if custom_color_spec_flag:
        index = serdes.uint("index")
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            PresetColorSpecs(index)
        except ValueError:
            index = PresetColorSpecs.sdtv_525
        
        preset_color_spec(video_parameters, index)
        if index == 0:
            with serdes.subcontext("color_primaries"):
                color_primaries(serdes, state, video_parameters)
            with serdes.subcontext("color_matrix"):
                color_matrix(serdes, state, video_parameters)
            with serdes.subcontext("transfer_function"):
                transfer_function(serdes, state, video_parameters)

@context_type(ColorPrimaries)
def color_primaries(serdes, state, video_parameters):
    """(11.4.10.2) Override color primaries parameter."""
    custom_color_primaries_flag = serdes.bool("custom_color_primaries_flag")
    if custom_color_primaries_flag:
        index = serdes.uint("index")
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            PresetColorPrimaries(index)
        except ValueError:
            index = PresetColorPrimaries.hdtv
        
        preset_color_primaries(video_parameters, index)

@context_type(ColorMatrix)
def color_matrix(serdes, state, video_parameters):
    """(11.4.10.3) Override color matrix parameter."""
    custom_color_matrix_flag = serdes.bool("custom_color_matrix_flag")
    if custom_color_matrix_flag:
        index = serdes.uint("index")
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            PresetColorMatrices(index)
        except ValueError:
            index = PresetColorMatrices.hdtv
        
        preset_color_matrix(video_parameters, index)

@context_type(TransferFunction)
def transfer_function(serdes, state, video_parameters):
    """(11.4.10.4) Override color transfer function parameter."""
    custom_transfer_function_flag = serdes.bool("custom_transfer_function_flag")
    if custom_transfer_function_flag:
        index = serdes.uint("index")
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            PresetTransferFunctions(index)
        except ValueError:
            index = PresetTransferFunctions.tv_gamma
        
        preset_transfer_function(video_parameters, index)


################################################################################
# (12) Picture syntax
################################################################################

@context_type(PictureParse)
def picture_parse(serdes, state):
    """(12.1)"""
    serdes.byte_align("padding1")
    with serdes.subcontext("picture_header"):
        picture_header(serdes, state)
    serdes.byte_align("padding2")
    with serdes.subcontext("wavelet_transform"):
        wavelet_transform(serdes, state)

@context_type(PictureHeader)
def picture_header(serdes, state):
    """(12.2)"""
    state["picture_number"] = serdes.uint_lit("picture_number", 4)

@context_type(WaveletTransform)
def wavelet_transform(serdes, state):
    """(12.3)"""
    with serdes.subcontext("transform_parameters"):
        transform_parameters(serdes, state)
    serdes.byte_align("padding")
    transform_data(serdes, state)

@context_type(TransformParameters)
def transform_parameters(serdes, state):
    """(12.4.1) Read transform parameters."""
    state["wavelet_index"] = serdes.uint("wavelet_index")
    state["dwt_depth"] = serdes.uint("dwt_depth")
    
    state["wavelet_index_ho"] = state["wavelet_index"]
    state["dwt_depth_ho"] = 0
    if state["major_version"] >= 3:
        with serdes.subcontext("extended_transform_parameters"):
            extended_transform_parameters(serdes, state)
    
    with serdes.subcontext("slice_parameters"):
        slice_parameters(serdes, state)
    with serdes.subcontext("quant_matrix"):
        quant_matrix(serdes, state)

@context_type(ExtendedTransformParameters)
def extended_transform_parameters(serdes, state):
    """(12.4.4.1) Read horizontal only transform parameters."""
    asym_transform_index_flag = serdes.bool("asym_transform_index_flag")
    if asym_transform_index_flag:
        state["wavelet_index_ho"] = serdes.uint("wavelet_index_ho")
    
    asym_transform_flag = serdes.bool("asym_transform_flag")
    if asym_transform_flag:
        state["dwt_depth_ho"] = serdes.uint("dwt_depth_ho")

@context_type(SliceParameters)
def slice_parameters(serdes, state):
    """(12.4.5.2) Read slice parameters"""
    state["slices_x"] = serdes.uint("slices_x")
    state["slices_y"] = serdes.uint("slices_y")
    
    if is_ld_picture(state):
        state["slice_bytes_numerator"] = serdes.uint("slice_bytes_numerator")
        state["slice_bytes_denominator"] = serdes.uint("slice_bytes_denominator")
    if is_hq_picture(state):
        state["slice_prefix_bytes"] = serdes.uint("slice_prefix_bytes")
        state["slice_size_scaler"] = serdes.uint("slice_size_scaler")

@context_type(QuantMatrix)
def quant_matrix(serdes, state):
    """(12.4.5.3) Read quantisation matrix"""
    custom_quant_matrix = serdes.bool("custom_quant_matrix")
    if custom_quant_matrix:
        serdes.declare_list("quant_matrix")
        
        state["quant_matrix"] = defaultdict(dict)
        if state["dwt_depth_ho"] == 0:
            state["quant_matrix"][0]["LL"] = serdes.uint("quant_matrix")
        else:
            state["quant_matrix"][0]["L"] = serdes.uint("quant_matrix")
            for level in range(1, state["dwt_depth_ho"] + 1):
                state["quant_matrix"][level]["H"] = serdes.uint("quant_matrix")
        
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            state["quant_matrix"][level]["HL"] = serdes.uint("quant_matrix")
            state["quant_matrix"][level]["LH"] = serdes.uint("quant_matrix")
            state["quant_matrix"][level]["HH"] = serdes.uint("quant_matrix")
    else:
        # Not required
        #set_quant_matrix(state)
        pass


################################################################################
# (14) Fragment syntax
################################################################################

@context_type(FragmentParse)
def fragment_parse(serdes, state):
    """(14.1)"""
    serdes.byte_align("padding1")
    with serdes.subcontext("fragment_header"):
        fragment_header(serdes, state)
    if state["fragment_slice_count"] == 0:
        serdes.byte_align("padding2")
        with serdes.subcontext("transform_parameters"):
            transform_parameters(serdes, state)
        
        # Not required (prepares structures used for decoding and termination detection)
        # initialize_fragment_state(state)
    else:
        serdes.byte_align("padding2")
        fragment_data(serdes, state)


@context_type(FragmentHeader)
def fragment_header(serdes, state):
    """14.2"""
    state["picture_number"] = serdes.uint_lit("picture_number", 4)
    state["fragment_data_length"] = serdes.uint_lit("fragment_data_length", 2)
    state["fragment_slice_count"] = serdes.uint_lit("fragment_slice_count", 2)
    if state["fragment_slice_count"] != 0:
        state["fragment_x_offset"] = serdes.uint_lit("fragment_x_offset", 2)
        state["fragment_y_offset"] = serdes.uint_lit("fragment_y_offset", 2)
