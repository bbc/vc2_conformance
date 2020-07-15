r"""
The :py:mod:`vc2_conformance.bitstream.vc2` module contains a set of
:py:class:`.SerDes`-using (see :py:mod:`~vc2_conformance.bitstream.serdes`)
functions which follow the pseudo-code in the VC-2 specification as closely as
possible. All pseudocode functions are re-exported by the
:py:mod:`vc2_conformance.bitstream` module.

See the table in :ref:`bitstream-fixeddicts` which relates these functions to
their matching :py:mod:`fixeddicts <vc2_conformance.fixeddict>`.

In this module, all functions are derived from the pseudocode by:

* Replacing ``read_*`` calls with :py:class:`.SerDes` calls.
* Adding :py:class:`.SerDes` annotations.
* Removing of decoding functionality (retaining only the code required for
  bitstream deserialisation).

Consistency with the VC-2 pseudocode is checked by the test suite (see
:py:mod:`verification`).
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_conformance.bitstream.serdes import context_type

from vc2_data_tables import (
    BaseVideoFormats,
    PresetFrameRates,
    PresetPixelAspectRatios,
    PresetSignalRanges,
    PresetColorSpecs,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    PARSE_INFO_HEADER_BYTES,
)

from vc2_conformance.pseudocode.state import reset_state

from vc2_conformance.pseudocode.video_parameters import (
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

from vc2_conformance.pseudocode.parse_code_functions import (
    is_seq_header,
    is_end_of_sequence,
    is_auxiliary_data,
    is_padding_data,
    is_picture,
    is_ld,
    is_hq,
    is_fragment,
)

from vc2_conformance.pseudocode.vc2_math import intlog2

from vc2_conformance.pseudocode.slice_sizes import (
    slice_bytes,
    slice_left,
    slice_right,
    slice_top,
    slice_bottom,
)

from vc2_conformance.bitstream.vc2_fixeddicts import (
    ParseInfo,
    SequenceHeader,
    ParseParameters,
    SourceParameters,
    FrameSize,
    ColorDiffSamplingFormat,
    ScanFormat,
    FrameRate,
    PixelAspectRatio,
    CleanArea,
    SignalRange,
    ColorSpec,
    ColorPrimaries,
    ColorMatrix,
    TransferFunction,
    AuxiliaryData,
    Padding,
    TransformParameters,
    ExtendedTransformParameters,
    SliceParameters,
    QuantMatrix,
    PictureHeader,
    TransformData,
    WaveletTransform,
    PictureParse,
    LDSlice,
    HQSlice,
    FragmentHeader,
    FragmentData,
    FragmentParse,
    DataUnit,
    Sequence,
    Stream,
)

__all__ = [
    "parse_stream",
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


@context_type(Stream)
@ref_pseudocode(deviation="serdes")
def parse_stream(serdes, state):
    """
    (10.3) Parse a VC-2 whole stream containing multiple concatenated
    sequences, discarding the contents.

    Populates a :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Stream`
    :py:mod:`~vc2_conformance.fixeddict`.
    """
    serdes.declare_list("sequences")

    # Here the logic for deciding when a sequence is 'over' is complicated by
    # the fact that the pseudocode uses an EOF signal to determine this. In the
    # Serialisation case, this obviously isn't suitable so we instead wait for
    # the 'sequences' list to run out of entries.
    #
    ### while not is_end_of_stream(state):
    ## Begin not in spec
    while (
        # Deserialisation case: stream is ended by an end-of-stream (NB
        # BitstreamWriter.is_end_of_stream always returns True)
        not serdes.io.is_end_of_stream()
        # Serialisation case: stream is ended by running out of sequences to
        # serialise...
        or not serdes.is_target_complete("sequences")
    ):
        ## End not in spec
        with serdes.subcontext("sequences"):
            parse_sequence(serdes, state)


@context_type(Sequence)
@ref_pseudocode(deviation="serdes")
def parse_sequence(serdes, state):
    """
    (10.4.1) Parse a VC-2 sequence, discarding the contents.

    Populates a :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Sequence`
    :py:mod:`~vc2_conformance.fixeddict`.  Provides a copy of the
    :py:class:`~vc2_conformance.pseudocode.state.State` in ``"_state"``.
    """
    reset_state(state)

    serdes.computed_value("_state", state)

    serdes.declare_list("data_units")

    serdes.subcontext_enter("data_units")
    serdes.set_context_type(DataUnit)
    with serdes.subcontext("parse_info"):
        parse_info(serdes, state)
    while not is_end_of_sequence(state):
        if is_seq_header(state):
            with serdes.subcontext("sequence_header"):
                state["video_parameters"] = sequence_header(serdes, state)
        elif is_picture(state):
            with serdes.subcontext("picture_parse"):
                picture_parse(serdes, state)
            # No need to perform the IDWT
            ### picture_decode(state)
        elif is_fragment(state):
            with serdes.subcontext("fragment_parse"):
                fragment_parse(serdes, state)
            # No need to perform the IDWT
            ### if state["fragmented_picture_done"]:
            ###     picture_decode(state)
        elif is_auxiliary_data(state):
            with serdes.subcontext("auxiliary_data"):
                auxiliary_data(serdes, state)
        elif is_padding_data(state):
            with serdes.subcontext("padding"):
                padding(serdes, state)
        serdes.subcontext_leave()

        serdes.subcontext_enter("data_units")
        serdes.set_context_type(DataUnit)
        with serdes.subcontext("parse_info"):
            parse_info(serdes, state)

    serdes.subcontext_leave()


@context_type(ParseInfo)
@ref_pseudocode(deviation="serdes")
def parse_info(serdes, state):
    """(10.5.1) Read a parse_info header."""
    serdes.byte_align("padding")

    ## Begin not in spec
    serdes.computed_value("_offset", serdes.io.tell()[0])
    ## End not in spec

    serdes.uint_lit("parse_info_prefix", 4)
    state["parse_code"] = serdes.uint_lit("parse_code", 1)
    state["next_parse_offset"] = serdes.uint_lit("next_parse_offset", 4)
    state["previous_parse_offset"] = serdes.uint_lit("previous_parse_offset", 4)


@context_type(AuxiliaryData)
@ref_pseudocode(deviation="serdes")
def auxiliary_data(serdes, state):
    """(10.4.4) Read an auxiliary data block."""
    ### for i in range(1, state["next_parse_offset"]-12):
    ###     read_uint_lit(state, 1)
    ## Begin not in spec
    serdes.bytes("bytes", state["next_parse_offset"] - PARSE_INFO_HEADER_BYTES)
    ## End not in spec


@context_type(Padding)
@ref_pseudocode(deviation="serdes")
def padding(serdes, state):
    """(10.4.5) Read a padding data block."""
    ### for i in range(1, state["next_parse_offset"]-12):
    ###     read_uint_lit(state, 1)
    ## Begin not in spec
    serdes.bytes("bytes", state["next_parse_offset"] - PARSE_INFO_HEADER_BYTES)
    ## End not in spec


################################################################################
# (11) Sequence header parsing
################################################################################


@context_type(SequenceHeader)
@ref_pseudocode(deviation="serdes")
def sequence_header(serdes, state):
    """(11.1) Parse a sequence header returning a VideoParameters object."""
    with serdes.subcontext("parse_parameters"):
        parse_parameters(serdes, state)

    base_video_format = serdes.uint("base_video_format")

    # For robustness against bad bitstreams, force unrecognised base formats to 'custom'
    ## Begin not in spec
    try:
        BaseVideoFormats(base_video_format)
    except ValueError:
        base_video_format = BaseVideoFormats.custom_format
    ## End not in spec

    with serdes.subcontext("video_parameters"):
        video_parameters = source_parameters(serdes, state, base_video_format)
    state["picture_coding_mode"] = serdes.uint("picture_coding_mode")
    set_coding_parameters(state, video_parameters)

    return video_parameters


@context_type(ParseParameters)
@ref_pseudocode(deviation="serdes")
def parse_parameters(serdes, state):
    """(11.2.1)"""
    state["major_version"] = serdes.uint("major_version")
    state["minor_version"] = serdes.uint("minor_version")
    state["profile"] = serdes.uint("profile")
    state["level"] = serdes.uint("level")


@context_type(SourceParameters)
@ref_pseudocode(deviation="serdes")
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
@ref_pseudocode(deviation="serdes")
def frame_size(serdes, state, video_parameters):
    """(11.4.3) Override video parameter."""
    custom_dimensions_flag = serdes.bool("custom_dimensions_flag")
    if custom_dimensions_flag:
        video_parameters["frame_width"] = serdes.uint("frame_width")
        video_parameters["frame_height"] = serdes.uint("frame_height")


@context_type(ColorDiffSamplingFormat)
@ref_pseudocode(deviation="serdes")
def color_diff_sampling_format(serdes, state, video_parameters):
    """(11.4.4) Override color sampling parameter."""
    custom_color_diff_format_flag = serdes.bool("custom_color_diff_format_flag")
    if custom_color_diff_format_flag:
        video_parameters["color_diff_format_index"] = serdes.uint(
            "color_diff_format_index"
        )


@context_type(ScanFormat)
@ref_pseudocode(deviation="serdes")
def scan_format(serdes, state, video_parameters):
    """(11.4.5) Override source sampling parameter."""
    custom_scan_format_flag = serdes.bool("custom_scan_format_flag")
    if custom_scan_format_flag:
        video_parameters["source_sampling"] = serdes.uint("source_sampling")


@context_type(FrameRate)
@ref_pseudocode(deviation="serdes")
def frame_rate(serdes, state, video_parameters):
    """(11.4.6) Override frame-rate parameter."""
    custom_frame_rate_flag = serdes.bool("custom_frame_rate_flag")

    if custom_frame_rate_flag:
        index = serdes.uint("index")

        # Required to prevent crashes on malformed inputs make an arbitrary
        # choice
        ## Begin not in spec
        try:
            if index != 0:
                PresetFrameRates(index)
        except ValueError:
            index = PresetFrameRates.fps_24_over_1_001
        ## End not in spec

        if index == 0:
            video_parameters["frame_rate_numer"] = serdes.uint("frame_rate_numer")
            video_parameters["frame_rate_denom"] = serdes.uint("frame_rate_denom")
        else:
            preset_frame_rate(video_parameters, index)


@context_type(PixelAspectRatio)
@ref_pseudocode(deviation="serdes")
def pixel_aspect_ratio(serdes, state, video_parameters):
    """(11.4.7) Override pixel aspect ratio parameter."""
    custom_pixel_aspect_ratio_flag = serdes.bool("custom_pixel_aspect_ratio_flag")
    if custom_pixel_aspect_ratio_flag:
        index = serdes.uint("index")

        # Required to prevent crashes on malformed inputs make an arbitrary
        # choice
        ## Begin not in spec
        try:
            if index != 0:
                PresetPixelAspectRatios(index)
        except ValueError:
            index = PresetPixelAspectRatios.ratio_1_1
        ## End not in spec

        if index == 0:
            video_parameters["pixel_aspect_ratio_numer"] = serdes.uint(
                "pixel_aspect_ratio_numer"
            )
            video_parameters["pixel_aspect_ratio_denom"] = serdes.uint(
                "pixel_aspect_ratio_denom"
            )
        else:
            preset_pixel_aspect_ratio(video_parameters, index)


@context_type(CleanArea)
@ref_pseudocode(deviation="serdes")
def clean_area(serdes, state, video_parameters):
    """(11.4.8) Override clean area parameter."""
    custom_clean_area_flag = serdes.bool("custom_clean_area_flag")
    if custom_clean_area_flag:
        video_parameters["clean_width"] = serdes.uint("clean_width")
        video_parameters["clean_height"] = serdes.uint("clean_height")
        video_parameters["left_offset"] = serdes.uint("left_offset")
        video_parameters["top_offset"] = serdes.uint("top_offset")


@context_type(SignalRange)
@ref_pseudocode(deviation="serdes")
def signal_range(serdes, state, video_parameters):
    """(11.4.9) Override signal parameter."""
    custom_signal_range_flag = serdes.bool("custom_signal_range_flag")
    if custom_signal_range_flag:
        index = serdes.uint("index")

        # Required to prevent crashes on malformed inputs make an arbitrary
        # choice
        ## Begin not in spec
        try:
            if index != 0:
                PresetSignalRanges(index)
        except ValueError:
            index = PresetSignalRanges.video_8bit_full_range
        ## End not in spec

        if index == 0:
            video_parameters["luma_offset"] = serdes.uint("luma_offset")
            video_parameters["luma_excursion"] = serdes.uint("luma_excursion")
            video_parameters["color_diff_offset"] = serdes.uint("color_diff_offset")
            video_parameters["color_diff_excursion"] = serdes.uint(
                "color_diff_excursion"
            )
        else:
            preset_signal_range(video_parameters, index)


@context_type(ColorSpec)
@ref_pseudocode(deviation="serdes")
def color_spec(serdes, state, video_parameters):
    """(11.4.10.1) Override color specification parameter."""
    custom_color_spec_flag = serdes.bool("custom_color_spec_flag")
    if custom_color_spec_flag:
        index = serdes.uint("index")

        # Required to prevent crashes on malformed inputs make an arbitrary
        # choice
        ## Begin not in spec
        try:
            PresetColorSpecs(index)
        except ValueError:
            index = PresetColorSpecs.sdtv_525
        ## End not in spec

        preset_color_spec(video_parameters, index)
        if index == 0:
            with serdes.subcontext("color_primaries"):
                color_primaries(serdes, state, video_parameters)
            with serdes.subcontext("color_matrix"):
                color_matrix(serdes, state, video_parameters)
            with serdes.subcontext("transfer_function"):
                transfer_function(serdes, state, video_parameters)


@context_type(ColorPrimaries)
@ref_pseudocode(deviation="serdes")
def color_primaries(serdes, state, video_parameters):
    """(11.4.10.2) Override color primaries parameter."""
    custom_color_primaries_flag = serdes.bool("custom_color_primaries_flag")
    if custom_color_primaries_flag:
        index = serdes.uint("index")

        # Required to prevent crashes on malformed inputs make an arbitrary
        # choice
        ## Begin not in spec
        try:
            PresetColorPrimaries(index)
        except ValueError:
            index = PresetColorPrimaries.hdtv
        ## End not in spec

        preset_color_primaries(video_parameters, index)


@context_type(ColorMatrix)
@ref_pseudocode(deviation="serdes")
def color_matrix(serdes, state, video_parameters):
    """(11.4.10.3) Override color matrix parameter."""
    custom_color_matrix_flag = serdes.bool("custom_color_matrix_flag")
    if custom_color_matrix_flag:
        index = serdes.uint("index")

        # Required to prevent crashes on malformed inputs make an arbitrary
        # choice
        ## Begin not in spec
        try:
            PresetColorMatrices(index)
        except ValueError:
            index = PresetColorMatrices.hdtv
        ## End not in spec

        preset_color_matrix(video_parameters, index)


@context_type(TransferFunction)
@ref_pseudocode(deviation="serdes")
def transfer_function(serdes, state, video_parameters):
    """(11.4.10.4) Override color transfer function parameter."""
    custom_transfer_function_flag = serdes.bool("custom_transfer_function_flag")
    if custom_transfer_function_flag:
        index = serdes.uint("index")

        # Required to prevent crashes on malformed inputs make an arbitrary
        # choice
        ## Begin not in spec
        try:
            PresetTransferFunctions(index)
        except ValueError:
            index = PresetTransferFunctions.tv_gamma
        ## End not in spec

        preset_transfer_function(video_parameters, index)


################################################################################
# (12) Picture syntax
################################################################################


@context_type(PictureParse)
@ref_pseudocode(deviation="serdes")
def picture_parse(serdes, state):
    """(12.1)"""
    serdes.byte_align("padding1")
    with serdes.subcontext("picture_header"):
        picture_header(serdes, state)
    serdes.byte_align("padding2")
    with serdes.subcontext("wavelet_transform"):
        wavelet_transform(serdes, state)


@context_type(PictureHeader)
@ref_pseudocode(deviation="serdes")
def picture_header(serdes, state):
    """(12.2)"""
    state["picture_number"] = serdes.uint_lit("picture_number", 4)


@context_type(WaveletTransform)
@ref_pseudocode(deviation="serdes")
def wavelet_transform(serdes, state):
    """(12.3)"""
    with serdes.subcontext("transform_parameters"):
        transform_parameters(serdes, state)
    serdes.byte_align("padding")
    with serdes.subcontext("transform_data"):
        transform_data(serdes, state)


@context_type(TransformParameters)
@ref_pseudocode(deviation="serdes")
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
@ref_pseudocode(deviation="serdes")
def extended_transform_parameters(serdes, state):
    """(12.4.4.1) Read horizontal only transform parameters."""
    asym_transform_index_flag = serdes.bool("asym_transform_index_flag")
    if asym_transform_index_flag:
        state["wavelet_index_ho"] = serdes.uint("wavelet_index_ho")

    asym_transform_flag = serdes.bool("asym_transform_flag")
    if asym_transform_flag:
        state["dwt_depth_ho"] = serdes.uint("dwt_depth_ho")


@context_type(SliceParameters)
@ref_pseudocode(deviation="serdes")
def slice_parameters(serdes, state):
    """(12.4.5.2) Read slice parameters"""
    state["slices_x"] = serdes.uint("slices_x")
    state["slices_y"] = serdes.uint("slices_y")

    if is_ld(state):
        state["slice_bytes_numerator"] = serdes.uint("slice_bytes_numerator")
        state["slice_bytes_denominator"] = serdes.uint("slice_bytes_denominator")
    if is_hq(state):
        state["slice_prefix_bytes"] = serdes.uint("slice_prefix_bytes")
        state["slice_size_scaler"] = serdes.uint("slice_size_scaler")


@context_type(QuantMatrix)
@ref_pseudocode(deviation="serdes")
def quant_matrix(serdes, state):
    """(12.4.5.3) Read quantisation matrix"""
    custom_quant_matrix = serdes.bool("custom_quant_matrix")
    if custom_quant_matrix:
        serdes.declare_list("quant_matrix")

        # NB: For historical reasons, we use a dict not an array in this
        # implementation.
        ### state["quant_matrix"] = new_array(state["dwt_depth_ho"] + state["dwt_depth"] + 1)
        state["quant_matrix"] = {}  ## Not in spec
        if state["dwt_depth_ho"] == 0:
            state["quant_matrix"][0] = {}
            state["quant_matrix"][0]["LL"] = serdes.uint("quant_matrix")
        else:
            state["quant_matrix"][0] = {}
            state["quant_matrix"][0]["L"] = serdes.uint("quant_matrix")
            for level in range(1, state["dwt_depth_ho"] + 1):
                state["quant_matrix"][level] = {}
                state["quant_matrix"][level]["H"] = serdes.uint("quant_matrix")

        for level in range(
            state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1
        ):
            state["quant_matrix"][level] = {}
            state["quant_matrix"][level]["HL"] = serdes.uint("quant_matrix")
            state["quant_matrix"][level]["LH"] = serdes.uint("quant_matrix")
            state["quant_matrix"][level]["HH"] = serdes.uint("quant_matrix")
    else:
        # Not required for bitstream decoding
        ### set_quant_matrix(state)
        pass  ## Not in spec


################################################################################
# (13) Transform data syntax
################################################################################


@context_type(TransformData)
@ref_pseudocode(deviation="serdes")
def transform_data(serdes, state):
    """(13.5.2)"""
    # Not required for bitstream decoding
    ### state["y_transform"] = initialize_wavelet_data(state, "Y")
    ### state["c1_transform"] = initialize_wavelet_data(state, "C1")
    ### state["c2_transform"] = initialize_wavelet_data(state, "C2")

    # Initialise context dictionary
    ## Begin not in spec
    serdes.computed_value("_state", state.copy())
    if is_ld(state):
        serdes.declare_list("ld_slices")
    if is_hq(state):
        serdes.declare_list("hq_slices")
    ## End not in spec

    for sy in range(state["slices_y"]):
        for sx in range(state["slices_x"]):
            slice(serdes, state, sx, sy)

    # Not required for bitstream decoding
    ### if using_dc_prediction(state):
    ###     if state["dwt_depth_ho"] == 0:
    ###         dc_prediction(state["y_transform"][0]["LL"])
    ###         dc_prediction(state["c1_transform"][0]["LL"])
    ###         dc_prediction(state["c2_transform"][0]["LL"])
    ###     else:
    ###         dc_prediction(state["y_transform"][0]["L"])
    ###         dc_prediction(state["c1_transform"][0]["L"])
    ###         dc_prediction(state["c2_transform"][0]["L"])

    # Following line included to ensure the above comment is considered part of
    # this function
    pass  ## Not in spec


@ref_pseudocode(deviation="serdes")
def slice(serdes, state, sx, sy):
    """(13.5.2)"""
    if is_ld(state):
        with serdes.subcontext("ld_slices"):
            ld_slice(serdes, state, sx, sy)
    elif is_hq(state):
        with serdes.subcontext("hq_slices"):
            hq_slice(serdes, state, sx, sy)


@context_type(LDSlice)
@ref_pseudocode(deviation="serdes")
def ld_slice(serdes, state, sx, sy):
    """(13.5.3.1)"""
    slice_bits_left = 8 * slice_bytes(state, sx, sy)

    qindex = serdes.nbits("qindex", 7)  # noqa: F841
    slice_bits_left -= 7

    # Not required for bitstream unpacking
    ### slice_quantizers(state, qindex)

    length_bits = intlog2((8 * slice_bytes(state, sx, sy)) - 7)
    slice_y_length = serdes.nbits("slice_y_length", length_bits)
    slice_bits_left -= length_bits

    # Ensure robustness in the presence of invalid bitstreams
    ## Begin not in spec
    if slice_y_length > slice_bits_left:
        slice_y_length = slice_bits_left
    ## End not in spec

    # Initialise context dictionary
    serdes.computed_value("_sx", sx)
    serdes.computed_value("_sy", sy)
    serdes.declare_list("y_transform")
    serdes.declare_list("c_transform")

    serdes.bounded_block_begin(slice_y_length)

    if state["dwt_depth_ho"] == 0:
        slice_band(serdes, state, "y_transform", 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                slice_band(serdes, state, "y_transform", level, orient, sx, sy)
    else:
        slice_band(serdes, state, "y_transform", 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            slice_band(serdes, state, "y_transform", level, "H", sx, sy)
        for level in range(
            state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1
        ):
            for orient in ["HL", "LH", "HH"]:
                slice_band(serdes, state, "y_transform", level, orient, sx, sy)

    serdes.bounded_block_end("y_block_padding")

    slice_bits_left -= slice_y_length

    serdes.bounded_block_begin(slice_bits_left)

    if state["dwt_depth_ho"] == 0:
        color_diff_slice_band(serdes, state, 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(serdes, state, level, orient, sx, sy)
    else:
        color_diff_slice_band(serdes, state, 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            color_diff_slice_band(serdes, state, level, "H", sx, sy)
        for level in range(
            state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1
        ):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(serdes, state, level, orient, sx, sy)

    serdes.bounded_block_end("c_block_padding")


@context_type(HQSlice)
@ref_pseudocode(deviation="serdes")
def hq_slice(serdes, state, sx, sy):
    """(13.5.4)"""
    serdes.bytes("prefix_bytes", state["slice_prefix_bytes"])

    qindex = serdes.uint_lit("qindex", 1)  # noqa: F841

    # Not required for bitstream unpacking
    ### slice_quantizers(state, qindex)

    # Initialise context dictionary
    serdes.computed_value("_sx", sx)
    serdes.computed_value("_sy", sy)
    serdes.declare_list("y_transform")
    serdes.declare_list("c1_transform")
    serdes.declare_list("c2_transform")

    for transform in ["y_transform", "c1_transform", "c2_transform"]:
        component = transform.split("_")[0]  ## Not in spec
        length = state["slice_size_scaler"] * serdes.uint_lit(
            "slice_{}_length".format(component), 1
        )

        serdes.bounded_block_begin(8 * length)

        if state["dwt_depth_ho"] == 0:
            slice_band(serdes, state, transform, 0, "LL", sx, sy)
            for level in range(1, state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(serdes, state, transform, level, orient, sx, sy)
        else:
            slice_band(serdes, state, transform, 0, "L", sx, sy)
            for level in range(1, state["dwt_depth_ho"] + 1):
                slice_band(serdes, state, transform, level, "H", sx, sy)
            for level in range(
                state["dwt_depth_ho"] + 1,
                state["dwt_depth_ho"] + state["dwt_depth"] + 1,
            ):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(serdes, state, transform, level, orient, sx, sy)

        serdes.bounded_block_end("{}_block_padding".format(component))


@ref_pseudocode(deviation="serdes")
def slice_band(serdes, state, transform, level, orient, sx, sy):
    """(13.5.6.3) Read and dequantize a subband in a slice."""
    if transform == "y_transform":
        comp = "Y"
    elif transform == "c1_transform":
        comp = "C1"
    elif transform == "c2_transform":
        comp = "C2"

    # Not required for bitstream unpacking
    ### qi = state["quantizer"][level][orient]

    # These values evaulated in the loop definition in the spec, moving them
    # here saves a lot of computation
    ## Begin not in spec
    y1 = slice_top(state, sy, comp, level)
    y2 = slice_bottom(state, sy, comp, level)
    x1 = slice_left(state, sx, comp, level)
    x2 = slice_right(state, sx, comp, level)
    ## End not in spec

    ### for y in range(slice_top(state, sy,comp,level), slice_bottom(state, sy,comp,level)):
    ###     for x in range(slice_left(state, sx,comp,level), slice_right(state, sx,comp,level)):
    for y in range(y1, y2):  ## Not in spec
        for x in range(x1, x2):  ## Not in spec
            val = serdes.sint(transform)  # noqa: F841

            # Not required for bitstream unpacking
            ### state[transform][level][orient][y][x] = inverse_quant(val, qi)

    # Following line included to ensure the trailing comment above is
    # considered part of this function
    pass  ## Not in spec


@ref_pseudocode(deviation="serdes")
def color_diff_slice_band(serdes, state, level, orient, sx, sy):
    """(13.5.6.4) Read and dequantize interleaved color difference subbands in a slice."""
    # Not required for bitstream unpacking
    ### qi = state["quantizer"][level][orient]

    # These values evaulated in the loop definition in the spec, moving them
    # here saves a lot of computation
    ## Begin not in spec
    y1 = slice_top(state, sy, "C1", level)
    y2 = slice_bottom(state, sy, "C1", level)
    x1 = slice_left(state, sx, "C1", level)
    x2 = slice_right(state, sx, "C1", level)
    ## End not in spec

    ### for y in range(slice_top(state,sy,"C1",level), slice_bottom(state,sy,"C1",level)):
    ###     for x in range(slice_left(state,sx,"C1",level), slice_right(state,sx,"C1",level)):
    for y in range(y1, y2):  ## Not in spec
        for x in range(x1, x2):  ## Not in spec
            val = serdes.sint("c_transform")  # noqa: F841
            ### state["c1_transform"][level][orient][y][x] = inverse_quant(val, qi)

            val = serdes.sint("c_transform")  # noqa: F841
            ### state["c2_transform"][level][orient][y][x] = inverse_quant(val, qi)

    # Following line included to ensure the trailing comment above is
    # considered part of this function
    pass  ## Not in spec


################################################################################
# (14) Fragment syntax
################################################################################


@context_type(FragmentParse)
@ref_pseudocode(deviation="serdes")
def fragment_parse(serdes, state):
    """(14.1)"""
    with serdes.subcontext("fragment_header"):
        fragment_header(serdes, state)
    if state["fragment_slice_count"] == 0:
        with serdes.subcontext("transform_parameters"):
            transform_parameters(serdes, state)

        # Not required (prepares structures used for decoding and termination
        # detection)
        ### initialize_fragment_state(state)
    else:
        with serdes.subcontext("fragment_data"):
            fragment_data(serdes, state)


@context_type(FragmentHeader)
@ref_pseudocode(deviation="serdes")
def fragment_header(serdes, state):
    """(14.2)"""
    state["picture_number"] = serdes.uint_lit("picture_number", 4)
    state["fragment_data_length"] = serdes.uint_lit("fragment_data_length", 2)
    state["fragment_slice_count"] = serdes.uint_lit("fragment_slice_count", 2)
    if state["fragment_slice_count"] != 0:
        state["fragment_x_offset"] = serdes.uint_lit("fragment_x_offset", 2)
        state["fragment_y_offset"] = serdes.uint_lit("fragment_y_offset", 2)


@context_type(FragmentData)
@ref_pseudocode(deviation="serdes")
def fragment_data(serdes, state):
    """(14.4) Unpack and dequantize transform data from a fragment."""
    # Initialise context dictionary
    ## Begin not in spec
    serdes.computed_value("_state", state.copy())
    if is_ld(state):
        serdes.declare_list("ld_slices")
    if is_hq(state):
        serdes.declare_list("hq_slices")
    ## End not in spec

    for s in range(state["fragment_slice_count"]):
        slice_x = (
            (state["fragment_y_offset"] * state["slices_x"])
            + state["fragment_x_offset"]
            + s
        ) % state["slices_x"]
        slice_y = (
            (state["fragment_y_offset"] * state["slices_x"])
            + state["fragment_x_offset"]
            + s
        ) // state["slices_x"]
        slice(serdes, state, slice_x, slice_y)

        # Not required for bitstream unpacking
        ### state["fragment_slices_received"] += 1
        ###
        ### if state["fragment_slices_received"] == (state["slices_x"] * state["slices_y"]):
        ###     state["fragmented_picture_done"] = True
        ###     if using_dc_prediction(state):
        ###         if state["dwt_depth_ho"] == 0:
        ###             dc_prediction(state["y_transform"][0]["LL"])
        ###             dc_prediction(state["c1_transform"][0]["LL"])
        ###             dc_prediction(state["c2_transform"][0]["LL"])
        ###         else:
        ###             dc_prediction(state["y_transform"][0]["L"])
        ###             dc_prediction(state["c1_transform"][0]["L"])
        ###             dc_prediction(state["c2_transform"][0]["L"])

    # Following line included to ensure the trailing comment above is
    # considered part of this function
    pass  ## Not in spec
