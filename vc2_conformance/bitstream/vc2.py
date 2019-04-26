"""
VC-2-specific bitstream serialisation/deserialistion logic.

This module consists of a set of :py:class:`SerDes`-using (see
:py:module`serdes`) functions which follow the pseudo-code in the VC-2
specification as closely as possible. The following deviations from the
spec pseudo-code are allowed:

* Replacing ``read_*`` calls with :py:class:`SerDes` calls.
* Addition of :py:class:`SerDes` annotations.
* Removal of decoding functionality (retaining only the parts required for
  bitstream deserialisation.
"""

from collections import defaultdict

from vc2_conformance.metadata import ref_pseudocode

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
    is_ld_fragment,
    is_hq_fragment,
    is_fragment,
)

from vc2_conformance.math import intlog2

from vc2_conformance.slice_sizes import (
    subband_width,
    subband_height,
    slice_bytes,
    slice_left,
    slice_right,
    slice_top,
    slice_bottom,
)

from vc2_conformance.bitstream.vc2_fixeddicts import *

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
    
    "transform_data",
    "slice",
    "ld_slice",
    "hq_slice",
    "slice_band",
    "color_diff_slice_band",
    
    "transform_parameters",
    "extended_transform_parameters",
    "slice_parameters",
    "quant_matrix",
    
    "fragment_parse",
    "fragment_header",
    "fragment_data",
]


################################################################################
# (10) Stream decoding
################################################################################

@context_type(Sequence)
@ref_pseudocode(verbatim=False)
def parse_sequence(serdes):
    """
    (10.4.1) Parse a whole VC-2 sequence (i.e. file), discarding the contents.
    Given as a specification of the data structure, not an actually useful
    parsing loop.
    """
    state = State()
    
    # Not part of spec; initialise context dictionary.
    serdes.computed_value("_state", state)
    
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
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
def auxiliary_data(serdes, state):
    """(10.4.4) Read an auxiliary data block."""
    serdes.byte_align("padding")
    serdes.bytes("bytes", state["next_parse_offset"] - PARSE_INFO_HEADER_BYTES)


@context_type(Padding)
@ref_pseudocode(verbatim=False)
def padding(serdes, state):
    """(10.4.5) Read a padding data block."""
    serdes.byte_align("padding")
    serdes.bytes("bytes", state["next_parse_offset"] - PARSE_INFO_HEADER_BYTES)


################################################################################
# (11) Sequence header parsing
################################################################################


@context_type(SequenceHeader)
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
def parse_parameters(serdes, state):
    """(11.2.1)"""
    state["major_version"] = serdes.uint("major_version")
    state["minor_version"] = serdes.uint("minor_version")
    state["profile"] = serdes.uint("profile")
    state["level"] = serdes.uint("level")


@context_type(SourceParameters)
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
def frame_size(serdes, state, video_parameters):
    """(11.4.3) Override video parameter."""
    custom_dimensions_flag = serdes.bool("custom_dimensions_flag")
    if custom_dimensions_flag:
        video_parameters["frame_width"] = serdes.uint("frame_width")
        video_parameters["frame_height"] = serdes.uint("frame_height")

@context_type(ColorDiffSamplingFormat)
@ref_pseudocode(verbatim=False)
def color_diff_sampling_format(serdes, state, video_parameters):
    """(11.4.4) Override color sampling parameter."""
    custom_color_diff_format_flag = serdes.bool("custom_color_diff_format_flag")
    if custom_color_diff_format_flag:
        video_parameters["color_diff_format_index"] = serdes.uint("color_diff_format_index")

@context_type(ScanFormat)
@ref_pseudocode(verbatim=False)
def scan_format(serdes, state, video_parameters):
    """(11.4.5) Override source sampling parameter."""
    custom_scan_format_flag = serdes.bool("custom_scan_format_flag")
    if custom_scan_format_flag:
        video_parameters["source_sampling"] = serdes.uint("source_sampling")

@context_type(FrameRate)
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
def clean_area(serdes, state, video_parameters):
    """(11.4.8) Override clean area parameter."""
    custom_clean_area_flag = serdes.bool("custom_clean_area_flag")
    if custom_clean_area_flag:
        video_parameters["clean_width"] = serdes.uint("clean_width")
        video_parameters["clean_height"] = serdes.uint("clean_height")
        video_parameters["left_offset"] = serdes.uint("left_offset")
        video_parameters["top_offset"] = serdes.uint("top_offset")

@context_type(SignalRange)
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
def picture_parse(serdes, state):
    """(12.1)"""
    serdes.byte_align("padding1")
    with serdes.subcontext("picture_header"):
        picture_header(serdes, state)
    serdes.byte_align("padding2")
    with serdes.subcontext("wavelet_transform"):
        wavelet_transform(serdes, state)

@context_type(PictureHeader)
@ref_pseudocode(verbatim=False)
def picture_header(serdes, state):
    """(12.2)"""
    state["picture_number"] = serdes.uint_lit("picture_number", 4)

@context_type(WaveletTransform)
@ref_pseudocode(verbatim=False)
def wavelet_transform(serdes, state):
    """(12.3)"""
    with serdes.subcontext("transform_parameters"):
        transform_parameters(serdes, state)
    serdes.byte_align("padding")
    with serdes.subcontext("transform_data"):
        transform_data(serdes, state)

@context_type(TransformParameters)
@ref_pseudocode(verbatim=False)
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
@ref_pseudocode(verbatim=False)
def extended_transform_parameters(serdes, state):
    """(12.4.4.1) Read horizontal only transform parameters."""
    asym_transform_index_flag = serdes.bool("asym_transform_index_flag")
    if asym_transform_index_flag:
        state["wavelet_index_ho"] = serdes.uint("wavelet_index_ho")
    
    asym_transform_flag = serdes.bool("asym_transform_flag")
    if asym_transform_flag:
        state["dwt_depth_ho"] = serdes.uint("dwt_depth_ho")

@context_type(SliceParameters)
@ref_pseudocode(verbatim=False)
def slice_parameters(serdes, state):
    """(12.4.5.2) Read slice parameters"""
    state["slices_x"] = serdes.uint("slices_x")
    state["slices_y"] = serdes.uint("slices_y")
    
    # Errata: just uses 'is_ld_picture' and 'is_hq_picture', should check
    # fragment types too
    if is_ld_picture(state) or is_ld_fragment(state):
        state["slice_bytes_numerator"] = serdes.uint("slice_bytes_numerator")
        state["slice_bytes_denominator"] = serdes.uint("slice_bytes_denominator")
    if is_hq_picture(state) or is_hq_fragment(state):
        state["slice_prefix_bytes"] = serdes.uint("slice_prefix_bytes")
        state["slice_size_scaler"] = serdes.uint("slice_size_scaler")

@context_type(QuantMatrix)
@ref_pseudocode(verbatim=False)
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
# (13) Transform data syntax
################################################################################

@context_type(TransformData)
@ref_pseudocode(verbatim=False)
def transform_data(serdes, state):
    """(13.5.2)"""
    # Not required
    #state["y_transform"] = initialize_wavelet_data(state, Y)
    #state["c1_transform"] = initialize_wavelet_data(state, C1)
    #state["c2_transform"] = initialize_wavelet_data(state, C2)
    
    # Not in spec; initialise context dictionary
    serdes.computed_value("_state", state.copy())
    if is_ld_picture(state):
        serdes.declare_list("ld_slices")
    if is_hq_picture(state):
        serdes.declare_list("hq_slices")
    
    for sy in range(state["slices_y"]):
        for sx in range(state["slices_x"]):
            slice(serdes, state, sx, sy)
    
    # Not required
    #if using_dc_prediction(state):
    #    if state["dwt_depth_ho"] == 0:
    #        dc_prediction(state["y_transform"][0][LL])
    #        dc_prediction(state["c1_transform"][0][LL])
    #        dc_prediction(state["c2_transform"][0][LL])
    #    else:
    #        dc_prediction(state["y_transform"][0][L])
    #        dc_prediction(state["c1_transform"][0][L])
    #        dc_prediction(state["c2_transform"][0][L])

def slice(serdes, state, sx, sy):
    """(13.5.2)"""
    # Errata: just uses 'is_ld_picture' and 'is_hq_picture', should check
    # fragment types too
    if is_ld_picture(state) or is_ld_fragment(state):
        with serdes.subcontext("ld_slices"):
            ld_slice(serdes, state, sx, sy)
    elif is_hq_picture(state) or is_hq_fragment(state):
        with serdes.subcontext("hq_slices"):
            hq_slice(serdes, state, sx, sy)

@context_type(LDSlice)
@ref_pseudocode(verbatim=False)
def ld_slice(serdes, state, sx, sy):
    """(13.5.3.1)"""
    slice_bits_left = 8*slice_bytes(state, sx, sy)
    
    qindex = serdes.nbits("qindex", 7)
    slice_bits_left -= 7
    
    # Not required
    #slice_quantizers(state, qindex)
    
    length_bits = intlog2((8 * slice_bytes(state, sx, sy)) - 7)
    slice_y_length = serdes.nbits("slice_y_length", length_bits)
    slice_bits_left -= length_bits
    
    # Not in spec; here to ensure robustness in the presence of invalid
    # bitstreams
    if slice_y_length > slice_bits_left:
        slice_y_length = slice_bits_left
    
    # Not in spec; initialise context dictionary
    serdes.computed_value("_sx", sx)
    serdes.computed_value("_sy", sy)
    serdes.declare_list("y_transform")
    serdes.declare_list("c_transform")
    
    serdes.bounded_block_begin(slice_y_length)
    #state.bits_left = slice_y_length
    
    if state["dwt_depth_ho"] == 0:
        # Errata: standard says 'luma_slice_band(state, 0, "LL", sx, sy)'
        slice_band(serdes, state, "y_transform", 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                slice_band(serdes, state, "y_transform", level, orient, sx, sy)
    else:
        # Errata: standard says 'luma_slice_band(state, 0, "L", sx, sy)'
        slice_band(serdes, state, "y_transform", 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            slice_band(serdes, state, "y_transform", level, "H", sx, sy)
        for level in range(state["dwt_depth_ho"] + 1, 
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                slice_band(serdes, state, "y_transform", level, orient, sx, sy)
    
    serdes.bounded_block_end("y_block_padding")
    #flush_inputb(state)
    
    slice_bits_left -= slice_y_length
    
    serdes.bounded_block_begin(slice_bits_left)
    #state.bits_left = slice_bits_left
    
    # Errata: The standard shows only 2D transform slices being read
    if state["dwt_depth_ho"] == 0:
        color_diff_slice_band(serdes, state, 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(serdes, state, level, orient, sx, sy)
    else:
        color_diff_slice_band(serdes, state, 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            color_diff_slice_band(serdes, state, level, "H", sx, sy)
        for level in range(state["dwt_depth_ho"] + 1, 
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(serdes, state, level, orient, sx, sy)
    
    serdes.bounded_block_end("c_block_padding")
    #flush_inputb(state)


@context_type(HQSlice)
@ref_pseudocode(verbatim=False)
def hq_slice(serdes, state, sx, sy):
    """(13.5.4)"""
    serdes.bytes("prefix_bytes", state["slice_prefix_bytes"])
    
    qindex = serdes.nbits("qindex", 8)
    
    # Not required
    #slice_quantizers(state, qindex)
    
    # Not in spec; initialise context dictionary
    serdes.computed_value("_sx", sx)
    serdes.computed_value("_sy", sy)
    serdes.declare_list("y_transform")
    serdes.declare_list("c1_transform")
    serdes.declare_list("c2_transform")
    
    for component in ["y", "c1", "c2"]:
        length = state["slice_size_scaler"] * serdes.nbits("slice_{}_length".format(component), 8)
        
        serdes.bounded_block_begin(8*length)
        #state.bits_left = 8*length
        
        transform = "{}_transform".format(component)
        if state["dwt_depth_ho"] == 0:
            slice_band(serdes, state, transform, 0, "LL", sx, sy)
            for level in range(1, state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(serdes, state, transform, level, orient, sx, sy)
        else:
            slice_band(serdes, state, transform, 0, "L", sx, sy)
            for level in range(1, state["dwt_depth_ho"] + 1):
                slice_band(serdes, state, transform, level, "H", sx, sy)
            for level in range(state["dwt_depth_ho"] + 1,
                               state["dwt_depth_ho"] + state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(serdes, state, transform, level, orient, sx, sy)
        
        serdes.bounded_block_end("{}_block_padding".format(component))
        #flush_inputb(state)

@ref_pseudocode(verbatim=False)
def slice_band(serdes, state, transform, level, orient, sx, sy):
    """(13.5.6.3) Read and dequantize a subband in a slice."""
    # These values evaulated in the loop definition in the spec, moving them
    # here saves a lot of computation
    #
    # Errata: 'Y' is always used in the spec but should respect whatever
    # transform is specified.
    comp = "Y" if transform.startswith("y") else "C1"
    y1 = slice_top(state, sy, comp, level)
    y2 = slice_bottom(state, sy, comp, level)
    x1 = slice_left(state, sx, comp, level)
    x2 = slice_right(state, sx, comp, level)
    
    for y in range(y1, y2):
        for x in range(x1, x2):
            val = serdes.sint(transform)
            
            # Not required
            #qi = state.quantizer[level][orient]
            #transform[level][orient][y][x] = inverse_quant(val, qi)

@ref_pseudocode(verbatim=False)
def color_diff_slice_band(serdes, state, level, orient, sx, sy):
    """(13.5.6.4) Read and dequantize interleaved color difference subbands in a slice."""
    # These values evaulated in the loop definition in the spec, moving them
    # here saves a lot of computation
    y1 = slice_top(state, sy, "C1", level)
    y2 = slice_bottom(state, sy, "C1", level)
    x1 = slice_left(state, sx, "C1", level)
    x2 = slice_right(state, sx, "C1", level)
    
    # Not required
    #qi = state.quantizer[level][orient]
    for y in range(y1, y2):
        for x in range(x1, x2):
            # Not required
            #qi = state.quantizer[level][orient]
            
            val = serdes.sint("c_transform")
            # Not required
            #state.c1_transform[level][orient][y][x] = inverse_quant(val, qi)
            
            val = serdes.sint("c_transform")
            # Not required
            #state.c2_transform[level][orient][y][x] = inverse_quant(val, qi)

################################################################################
# (14) Fragment syntax
################################################################################

@context_type(FragmentParse)
@ref_pseudocode(verbatim=False)
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
        with serdes.subcontext("fragment_data"):
            fragment_data(serdes, state)


@context_type(FragmentHeader)
@ref_pseudocode(verbatim=False)
def fragment_header(serdes, state):
    """(14.2)"""
    state["picture_number"] = serdes.uint_lit("picture_number", 4)
    state["fragment_data_length"] = serdes.uint_lit("fragment_data_length", 2)
    state["fragment_slice_count"] = serdes.uint_lit("fragment_slice_count", 2)
    if state["fragment_slice_count"] != 0:
        state["fragment_x_offset"] = serdes.uint_lit("fragment_x_offset", 2)
        state["fragment_y_offset"] = serdes.uint_lit("fragment_y_offset", 2)


@context_type(FragmentData)
@ref_pseudocode(verbatim=False)
def fragment_data(serdes, state):
    """(14.4) Unpack and dequantize transform data from a fragment."""
    # Not in spec; initialise context dictionary
    serdes.computed_value("_state", state.copy())
    if is_ld_fragment(state):
        serdes.declare_list("ld_slices")
    if is_hq_fragment(state):
        serdes.declare_list("hq_slices")
    
    # Errata: In the spec this loop goes from 0 to fragment_slice_count
    # inclusive but should be fragment_slice_count *exclusive* (as below)
    for s in range(state["fragment_slice_count"]):
        state["slice_x"] = (
            ((state["fragment_y_offset"] * state["slices_x"]) +
             state["fragment_x_offset"] + s) % state["slices_x"]
        )
        state["slice_y"] = (
            ((state["fragment_y_offset"] * state["slices_x"]) +
             state["fragment_x_offset"] + s) // state["slices_x"]
        )
        slice(serdes, state, state["slice_x"], state["slice_y"])
        
        # Not required
        #state["fragment_slices_received"] += 1
        #
        #if state["fragment_slices_received"] == (state["slice_x"] * state["slice_y"]):
        #    state["fragmented_picture_done"] = True
        #    if using_dc_prediction(state):
        #        if state["dwt_depth_ho"] == 0:
        #            dc_prediction(state["y_transform"][0][LL])
        #            dc_prediction(state["c1_transform"][0][LL])
        #            dc_prediction(state["c2_transform"][0][LL])
        #        else:
        #            dc_prediction(state["y_transform"][0][L])
        #            dc_prediction(state["c1_transform"][0][L])
        #            dc_prediction(state["c2_transform"][0][L])
