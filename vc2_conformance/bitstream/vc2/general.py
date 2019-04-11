"""
Token-emitting generators which define the majority of the VC-2 bitstream
format, with the exception of slice data which is handled separately.

Where possible the following code is a simple transformation of the pseudo-code
in the VC-2 specification.
"""

from collections import defaultdict

from vc2_conformance.bitstream.generator_io import (
    Token,
    TokenTypes,
    Return,
    context_type,
)

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
# Token aliases
################################################################################

# The following convenience aliases produce 'Token' instances equivalent to the
# various operations performed in the VC-2 spec.

def nest(generator, target):
    return Token(TokenTypes.nest, generator, target)

def byte_align(target):
    return Token(TokenTypes.byte_align, None, target)

def read_bool(target):
    return Token(TokenTypes.bool, None, target)

def read_uint_lit(num_bytes, target):
    return Token(TokenTypes.nbits, num_bytes*8, target)

def read_uint(target):
    return Token(TokenTypes.uint, None, target)


################################################################################
# (10) Stream decoding
################################################################################

@context_type(Sequence)
def parse_sequence():
    """
    (10.4.1) Parse a whole VC-2 sequence (i.e. file), discarding the contents.
    Given as a specification of the data structure, not an actually useful
    parsing loop.
    """
    state = State()
    
    yield Token(TokenTypes.declare_list, None, "data_units")
    
    yield Token(TokenTypes.nested_context_enter, None, "data_units")
    yield Token(TokenTypes.declare_context_type, DataUnit, None)
    yield nest(parse_info(state), "parse_info")
    while not is_end_of_sequence(state):
        if is_seq_header(state):
            yield nest(sequence_header(state), "sequence_header")
        elif is_picture(state):
            yield nest(picture_parse(state), "picture_parse")
        elif is_fragment(state):
            yield nest(fragment_parse(state), "fragment")
        elif is_auxiliary_data(state):
            yield nest(auxiliary_data(state), "auxiliary_data")
        elif is_padding_data(state):  # Errata: listed as 'is_padding' in standard
            yield nest(padding(state), "padding")
        yield Token(TokenTypes.nested_context_leave, None, None)
        
        yield Token(TokenTypes.nested_context_enter, None, "data_units")
        yield Token(TokenTypes.declare_context_type, DataUnit, None)
        yield nest(parse_info(state), "parse_info")
    
    yield Token(TokenTypes.nested_context_leave, None, None)


@context_type(ParseInfo)
def parse_info(state):
    """(10.5.1) Read a parse_info header."""
    # Errata: Wording of spec requires this field to be aligned but the pseudo
    # code doesn't include a byte_align (and nor does the 'parse_sequence
    # function which calls it)
    yield byte_align("padding")
    
    yield read_uint_lit(4, "parse_info_prefix")
    state["parse_code"] = (yield read_uint_lit(1, "parse_code"))
    state["next_parse_offset"] = (yield read_uint_lit(4, "next_parse_offset"))
    state["previous_parse_offset"] = (yield read_uint_lit(4, "previous_parse_offset"))


@context_type(AuxiliaryData)
def auxiliary_data(state):
    """(10.4.4) Read an auxiliary data block."""
    yield byte_align("padding")
    yield Token(TokenTypes.bytes, state["next_parse_offset"] - PARSE_INFO_HEADER_BYTES, "bytes")


@context_type(Padding)
def padding(state):
    """(10.4.5) Read a padding data block."""
    yield byte_align("padding")
    yield Token(TokenTypes.bytes, state["next_parse_offset"] - PARSE_INFO_HEADER_BYTES, "bytes")


################################################################################
# (11) Sequence header parsing
################################################################################


@context_type(SequenceHeader)
def sequence_header(state):
    """(11.1) Parse a sequence header returning a VideoParameters object."""
    yield byte_align("padding")
    
    yield nest(parse_parameters(state), "parse_parameters")
    
    base_video_format = (yield read_uint("base_video_format"))
    
    # For robustness against bad bitstreams, force unrecognised base formats to 'custom'
    try:
        BaseVideoFormats(base_video_format)
    except ValueError:
        base_video_format = BaseVideoFormats.custom_format
    
    video_parameters = (yield nest(
        source_parameters(state, base_video_format),
        "video_parameters",
    ))
    picture_coding_mode = (yield read_uint("picture_coding_mode"))
    set_coding_parameters(state, video_parameters, picture_coding_mode)
    
    raise Return(video_parameters)


@context_type(ParseParameters)
def parse_parameters(state):
    """(11.2.1)"""
    state["major_version"] = (yield read_uint("major_version"))
    state["minor_version"] = (yield read_uint("minor_version"))
    state["profile"] = (yield read_uint("profile"))
    state["level"] = (yield read_uint("level"))


@context_type(SourceParameters)
def source_parameters(state, base_video_format):
    """
    (11.4.1) Parse the video source parameters. Returns a VideoParameters
    object.
    """
    video_parameters = set_source_defaults(base_video_format)
    
    yield nest(frame_size(state, video_parameters), "frame_size")
    yield nest(color_diff_sampling_format(state, video_parameters), "color_diff_sampling_format")
    yield nest(scan_format(state, video_parameters), "scan_format")
    yield nest(frame_rate(state, video_parameters), "frame_rate")
    yield nest(pixel_aspect_ratio(state, video_parameters), "pixel_aspect_ratio")
    yield nest(clean_area(state, video_parameters), "clean_area")
    yield nest(signal_range(state, video_parameters), "signal_range")
    yield nest(color_spec(state, video_parameters), "color_spec")
    
    raise Return(video_parameters)

@context_type(FrameSize)
def frame_size(state, video_parameters):
    """(11.4.3) Override video parameter."""
    custom_dimensions_flag = (yield read_bool("custom_dimensions_flag"))
    if custom_dimensions_flag:
        video_parameters["frame_width"] = (yield read_uint("frame_width"))
        video_parameters["frame_height"] = (yield read_uint("frame_height"))

@context_type(ColorDiffSamplingFormat)
def color_diff_sampling_format(state, video_parameters):
    """(11.4.4) Override color sampling parameter."""
    custom_color_diff_format_flag = (yield read_bool("custom_color_diff_format_flag"))
    if custom_color_diff_format_flag:
        video_parameters["color_diff_format_index"] = (yield read_uint("color_diff_format_index"))

@context_type(ScanFormat)
def scan_format(state, video_parameters):
    """(11.4.5) Override source sampling parameter."""
    custom_scan_format_flag = (yield read_bool("custom_scan_format_flag"))
    if custom_scan_format_flag:
        video_parameters["source_sampling"] = (yield read_uint("source_sampling"))

@context_type(FrameRate)
def frame_rate(state, video_parameters):
    """(11.4.6) Override frame-rate parameter."""
    custom_frame_rate_flag = (yield read_bool("custom_frame_rate_flag"))
    
    if custom_frame_rate_flag:
        index = (yield read_uint("index"))
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            if index != 0:
                PresetFrameRates(index)
        except ValueError:
            index = PresetFrameRates.fps_24_over_1_001
        
        if index == 0:
            video_parameters["frame_rate_numer"] = (yield read_uint("frame_rate_numer"))
            video_parameters["frame_rate_denom"] = (yield read_uint("frame_rate_denom"))
        else:
            preset_frame_rate(video_parameters, index)

@context_type(PixelAspectRatio)
def pixel_aspect_ratio(state, video_parameters):  # Errata: called 'aspect_ratio' in spec
    """(11.4.7) Override pixel aspect ratio parameter."""
    custom_pixel_aspect_ratio_flag = (yield read_bool("custom_pixel_aspect_ratio_flag"))
    if custom_pixel_aspect_ratio_flag:
        index = (yield read_uint("index"))
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            if index != 0:
                PresetPixelAspectRatios(index)
        except ValueError:
            index = PresetPixelAspectRatios.ratio_1_1
        
        if index == 0:
            video_parameters["pixel_aspect_ratio_numer"] = (yield read_uint("pixel_aspect_ratio_numer"))
            video_parameters["pixel_aspect_ratio_denom"] = (yield read_uint("pixel_aspect_ratio_denom"))
        else:
            preset_pixel_aspect_ratio(video_parameters, index)

@context_type(CleanArea)
def clean_area(state, video_parameters):
    """(11.4.8) Override clean area parameter."""
    custom_clean_area_flag = (yield read_bool("custom_clean_area_flag"))
    if custom_clean_area_flag:
        video_parameters["clean_width"] = (yield read_uint("clean_width"))
        video_parameters["clean_height"] = (yield read_uint("clean_height"))
        video_parameters["left_offset"] = (yield read_uint("left_offset"))
        video_parameters["top_offset"] = (yield read_uint("top_offset"))

@context_type(SignalRange)
def signal_range(state, video_parameters):
    """(11.4.9) Override signal parameter."""
    custom_signal_range_flag = (yield read_bool("custom_signal_range_flag"))
    if custom_signal_range_flag:
        index = (yield read_uint("index"))
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            if index != 0:
                PresetSignalRanges(index)
        except ValueError:
            index = PresetSignalRanges.range_8_bit_full_range
        
        if index == 0:
            video_parameters["luma_offset"] = (yield read_uint("luma_offset"))
            video_parameters["luma_excursion"] = (yield read_uint("luma_excursion"))
            video_parameters["color_diff_offset"] = (yield read_uint("color_diff_offset"))
            video_parameters["color_diff_excursion"] = (yield read_uint("color_diff_excursion"))
        else:
            preset_signal_range(video_parameters, index)

@context_type(ColorSpec)
def color_spec(state, video_parameters):
    """(11.4.10.1) Override color specification parameter."""
    custom_color_spec_flag = (yield read_bool("custom_color_spec_flag"))
    if custom_color_spec_flag:
        index = (yield read_uint("index"))
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            PresetColorSpecs(index)
        except ValueError:
            index = PresetColorSpecs.sdtv_525
        
        preset_color_spec(video_parameters, index)
        if index == 0:
            yield nest(color_primaries(state, video_parameters), "color_primaries")
            yield nest(color_matrix(state, video_parameters), "color_matrix")
            yield nest(transfer_function(state, video_parameters), "transfer_function")

@context_type(ColorPrimaries)
def color_primaries(state, video_parameters):
    """(11.4.10.2) Override color primaries parameter."""
    custom_color_primaries_flag = (yield read_bool("custom_color_primaries_flag"))
    if custom_color_primaries_flag:
        index = (yield read_uint("index"))
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            PresetColorPrimaries(index)
        except ValueError:
            index = PresetColorPrimaries.hdtv
        
        preset_color_primaries(video_parameters, index)

@context_type(ColorMatrix)
def color_matrix(state, video_parameters):
    """(11.4.10.3) Override color matrix parameter."""
    custom_color_matrix_flag = (yield read_bool("custom_color_matrix_flag"))
    if custom_color_matrix_flag:
        index = (yield read_uint("index"))
        
        # Not part of spec but required to prevent crashes on malformed inputs
        # make an arbitrary choice
        try:
            PresetColorMatrices(index)
        except ValueError:
            index = PresetColorMatrices.hdtv
        
        preset_color_matrix(video_parameters, index)

@context_type(TransferFunction)
def transfer_function(state, video_parameters):
    """(11.4.10.4) Override color transfer function parameter."""
    custom_transfer_function_flag = (yield read_bool("custom_transfer_function_flag"))
    if custom_transfer_function_flag:
        index = (yield read_uint("index"))
        
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
def picture_parse(state):
    """(12.1)"""
    yield byte_align("padding1")
    yield nest(picture_header(state), "picture_header")
    yield byte_align("padding2")
    yield nest(wavelet_transform(state), "wavelet_transform")

@context_type(PictureHeader)
def picture_header(state):
    """(12.2)"""
    state["picture_number"] = (yield read_uint_lit(4, "picture_number"))

@context_type(WaveletTransform)
def wavelet_transform(state):
    """(12.3)"""
    yield nest(transform_parameters(state), "transform_parameters")
    yield byte_align("padding")
    yield Token(TokenTypes.use, transform_data(state), None)

@context_type(TransformParameters)
def transform_parameters(state):
    """(12.4.1) Read transform parameters."""
    state["wavelet_index"] = (yield read_uint("wavelet_index"))
    state["dwt_depth"] = (yield read_uint("dwt_depth"))
    
    state["wavelet_index_ho"] = state["wavelet_index"]
    state["dwt_depth_ho"] = 0
    if state["major_version"] >= 3:
        yield nest(extended_transform_parameters(state), "extended_transform_parameters")
    
    yield nest(slice_parameters(state), "slice_parameters")
    yield nest(quant_matrix(state), "quant_matrix")

@context_type(ExtendedTransformParameters)
def extended_transform_parameters(state):
    """(12.4.4.1) Read horizontal only transform parameters."""
    asym_transform_index_flag = (yield read_bool("asym_transform_index_flag"))
    if asym_transform_index_flag:
        state["wavelet_index_ho"] = (yield read_uint("wavelet_index_ho"))
    
    asym_transform_flag = (yield read_bool("asym_transform_flag"))
    if asym_transform_flag:
        state["dwt_depth_ho"] = (yield read_uint("dwt_depth_ho"))

@context_type(SliceParameters)
def slice_parameters(state):
    """(12.4.5.2) Read slice parameters"""
    state["slices_x"] = (yield read_uint("slices_x"))
    state["slices_y"] = (yield read_uint("slices_y"))
    
    if is_ld_picture(state):
        state["slice_bytes_numerator"] = (yield read_uint("slice_bytes_numerator"))
        state["slice_bytes_denominator"] = (yield read_uint("slice_bytes_denominator"))
    if is_hq_picture(state):
        state["slice_prefix_bytes"] = (yield read_uint("slice_prefix_bytes"))
        state["slice_size_scaler"] = (yield read_uint("slice_size_scaler"))

@context_type(QuantMatrix)
def quant_matrix(state):
    """(12.4.5.3) Read quantisation matrix"""
    custom_quant_matrix = (yield read_bool("custom_quant_matrix"))
    if custom_quant_matrix:
        yield Token(TokenTypes.declare_list, None, "quant_matrix")
        
        state["quant_matrix"] = defaultdict(dict)
        if state["dwt_depth_ho"] == 0:
            state["quant_matrix"][0]["LL"] = (yield read_uint("quant_matrix"))
        else:
            state["quant_matrix"][0]["L"] = (yield read_uint("quant_matrix"))
            for level in range(1, state["dwt_depth_ho"] + 1):
                state["quant_matrix"][level]["H"] = (yield read_uint("quant_matrix"))
        
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            state["quant_matrix"][level]["HL"] = (yield read_uint("quant_matrix"))
            state["quant_matrix"][level]["LH"] = (yield read_uint("quant_matrix"))
            state["quant_matrix"][level]["HH"] = (yield read_uint("quant_matrix"))
    else:
        # Not required
        #set_quant_matrix(state)
        pass


################################################################################
# (14) Fragment syntax
################################################################################

@context_type(FragmentParse)
def fragment_parse(state):
    """(14.1)"""
    yield byte_align("padding1")
    yield nest(fragment_header(state), "fragment_header")
    if state["fragment_slice_count"] == 0:
        yield byte_align("padding2")
        yield nest(transform_parameters(state), "transform_parameters")
        
        # Not required (prepares structures used for decoding and termination detection)
        # initialize_fragment_state(state)
    else:
        yield byte_align("padding2")
        yield Token(TokenTypes.use, fragment_data(state), None)


@context_type(FragmentHeader)
def fragment_header(state):
    """14.2"""
    state["picture_number"] = (yield read_uint_lit(4, "picture_number"))
    state["fragment_data_length"] = (yield read_uint_lit(2, "fragment_data_length"))
    state["fragment_slice_count"] = (yield read_uint_lit(2, "fragment_slice_count"))
    if state["fragment_slice_count"] != 0:
        state["fragment_x_offset"] = (yield read_uint_lit(2, "fragment_x_offset"))
        state["fragment_y_offset"] = (yield read_uint_lit(2, "fragment_y_offset"))
