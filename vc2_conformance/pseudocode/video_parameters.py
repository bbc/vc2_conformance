"""
Video parameter computation functions (11)

The functions in this module make up the purely functional (i.e. non
bitstream-reading) logic for computing video parameters. This predominantly
consists of preset-loading and component dimension calculation routines.

For functions below which take a 'state' argument, this should be a
dictionary-like object (e.g.
:py:class:`~vc2_conformance.pseudocode.state.State`) with the following
entries:

* ``"frame_width"``
* ``"frame_height"``
* ``"luma_width"``
* ``"luma_height"``
* ``"color_diff_width"``
* ``"color_diff_height"``
* ``"luma_depth"``
* ``"color_diff_depth"``
* ``"picture_coding_mode"``
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_conformance.fixeddict import fixeddict, Entry

from vc2_data_tables import (
    PictureCodingModes,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    BASE_VIDEO_FORMAT_PARAMETERS,
    PRESET_FRAME_RATES,
    PRESET_PIXEL_ASPECT_RATIOS,
    PRESET_SIGNAL_RANGES,
    PRESET_COLOR_SPECS,
)

from vc2_conformance.pseudocode.vc2_math import intlog2

__all__ = [
    "VideoParameters",
    "set_source_defaults",
    "set_coding_parameters",
    "picture_dimensions",
    "video_depth",
    "preset_frame_rate",
    "preset_pixel_aspect_ratio",
    "preset_signal_range",
    "preset_color_primaries",
    "preset_color_matrix",
    "preset_transfer_function",
    "preset_color_spec",
]


VideoParameters = fixeddict(
    "VideoParameters",
    # (11.4.3) frame_size
    Entry("frame_width", help_type="int", help="Set by (11.4.3) frame_size"),
    Entry("frame_height", help_type="int", help="Set by (11.4.3) frame_size"),
    # (11.4.4) color_diff_sampling_format
    Entry(
        "color_diff_format_index",
        enum=ColorDifferenceSamplingFormats,
        help_type=":py:class:`~vc2_data_tables.ColorDifferenceSamplingFormats`",
        help="Set by (11.4.4) color_diff_sampling_format",
    ),
    # (11.4.5) scan_format
    Entry(
        "source_sampling",
        enum=SourceSamplingModes,
        help_type=":py:class:`~vc2_data_tables.SourceSamplingModes`",
        help="Set by (11.4.5) scan_format",
    ),
    # (11.4.5)
    Entry(
        "top_field_first",
        help_type="bool",
        help="Set by (11.4.5) set_source_defaults",
    ),
    # (11.4.6) frame_rate
    Entry("frame_rate_numer", help_type="int", help="Set by (11.4.6) frame_rate"),
    Entry("frame_rate_denom", help_type="int", help="Set by (11.4.6) frame_rate"),
    # (11.4.7) aspect_ratio
    Entry(
        "pixel_aspect_ratio_numer", help_type="int", help="Set by (11.4.7) aspect_ratio"
    ),
    Entry(
        "pixel_aspect_ratio_denom", help_type="int", help="Set by (11.4.7) aspect_ratio"
    ),
    # (11.4.8) clean_area
    Entry("clean_width", help_type="int", help="Set by (11.4.8) clean_area"),
    Entry("clean_height", help_type="int", help="Set by (11.4.8) clean_area"),
    Entry("left_offset", help_type="int", help="Set by (11.4.8) clean_area"),
    Entry("top_offset", help_type="int", help="Set by (11.4.8) clean_area"),
    # (11.4.9) signal_range
    Entry("luma_offset", help_type="int", help="Set by (11.4.9) signal_range"),
    Entry("luma_excursion", help_type="int", help="Set by (11.4.9) signal_range"),
    Entry("color_diff_offset", help_type="int", help="Set by (11.4.9) signal_range"),
    Entry("color_diff_excursion", help_type="int", help="Set by (11.4.9) signal_range"),
    # (11.4.10.2) color_primaries
    Entry(
        "color_primaries_index",
        enum=PresetColorPrimaries,
        help_type=":py:class:`~vc2_data_tables.PresetColorPrimaries`",
        help="Set by (11.4.10.2) color_primaries",
    ),
    # (11.4.10.3) color_matrix
    Entry(
        "color_matrix_index",
        enum=PresetColorMatrices,
        help_type=":py:class:`~vc2_data_tables.PresetColorMatrices`",
        help="Set by (11.4.10.3) color_matrix",
    ),
    # (11.4.10.4) transfer_function
    Entry(
        "transfer_function_index",
        enum=PresetTransferFunctions,
        help_type=":py:class:`~vc2_data_tables.PresetTransferFunctions`",
        help="Set by (11.4.10.4) transfer_function",
    ),
    help="""
        (11.4) Video parameters struct.
    """,
)


@ref_pseudocode(deviation="inferred_implementation")
def set_source_defaults(base_video_format):
    """
    (11.4.2) Create a :py:class:`VideoParameters` object with the parameters
    specified in a base video format.
    """
    base = BASE_VIDEO_FORMAT_PARAMETERS[base_video_format]
    preset_frame_rates = PRESET_FRAME_RATES[base.frame_rate_index]
    preset_pixel_aspect_ratios = PRESET_PIXEL_ASPECT_RATIOS[
        base.pixel_aspect_ratio_index
    ]
    preset_signal_ranges = PRESET_SIGNAL_RANGES[base.signal_range_index]
    preset_color_spec = PRESET_COLOR_SPECS[base.color_spec_index]
    return VideoParameters(
        frame_width=base.frame_width,
        frame_height=base.frame_height,
        color_diff_format_index=base.color_diff_format_index,
        source_sampling=base.source_sampling,
        top_field_first=base.top_field_first,
        frame_rate_numer=preset_frame_rates.numerator,
        frame_rate_denom=preset_frame_rates.denominator,
        pixel_aspect_ratio_numer=preset_pixel_aspect_ratios.numerator,
        pixel_aspect_ratio_denom=preset_pixel_aspect_ratios.denominator,
        clean_width=base.clean_width,
        clean_height=base.clean_height,
        left_offset=base.left_offset,
        top_offset=base.top_offset,
        luma_offset=preset_signal_ranges.luma_offset,
        luma_excursion=preset_signal_ranges.luma_excursion,
        color_diff_offset=preset_signal_ranges.color_diff_offset,
        color_diff_excursion=preset_signal_ranges.color_diff_excursion,
        color_primaries_index=preset_color_spec.color_primaries_index,
        color_matrix_index=preset_color_spec.color_matrix_index,
        transfer_function_index=preset_color_spec.transfer_function_index,
    )


@ref_pseudocode
def set_coding_parameters(state, video_parameters):
    """(11.6.1) Set picture coding mode parameter."""
    picture_dimensions(state, video_parameters)
    video_depth(state, video_parameters)


@ref_pseudocode
def picture_dimensions(state, video_parameters):
    """(11.6.2) Compute the picture component dimensions in global state."""
    state["luma_width"] = video_parameters["frame_width"]
    state["luma_height"] = video_parameters["frame_height"]
    state["color_diff_width"] = state["luma_width"]
    state["color_diff_height"] = state["luma_height"]

    if (
        video_parameters["color_diff_format_index"]
        == ColorDifferenceSamplingFormats.color_4_2_2
    ):
        state["color_diff_width"] //= 2
    if (
        video_parameters["color_diff_format_index"]
        == ColorDifferenceSamplingFormats.color_4_2_0
    ):
        state["color_diff_width"] //= 2
        state["color_diff_height"] //= 2

    if state["picture_coding_mode"] == PictureCodingModes.pictures_are_fields:
        state["luma_height"] //= 2
        state["color_diff_height"] //= 2


@ref_pseudocode
def video_depth(state, video_parameters):
    """(11.6.3) Compute the bits-per-sample for the decoded video."""
    state["luma_depth"] = intlog2(video_parameters["luma_excursion"] + 1)
    state["color_diff_depth"] = intlog2(video_parameters["color_diff_excursion"] + 1)


@ref_pseudocode(deviation="inferred_implementation")
def preset_frame_rate(video_parameters, index):
    """(11.4.6) Set frame rate from preset."""
    preset = PRESET_FRAME_RATES[index]
    video_parameters["frame_rate_numer"] = preset.numerator
    video_parameters["frame_rate_denom"] = preset.denominator


@ref_pseudocode(deviation="inferred_implementation")
def preset_pixel_aspect_ratio(video_parameters, index):
    """(11.4.7) Set pixel aspect ratio from preset."""
    preset = PRESET_PIXEL_ASPECT_RATIOS[index]
    video_parameters["pixel_aspect_ratio_numer"] = preset.numerator
    video_parameters["pixel_aspect_ratio_denom"] = preset.denominator


@ref_pseudocode(deviation="inferred_implementation")
def preset_signal_range(video_parameters, index):
    """(11.4.7) Set signal range from preset."""
    preset = PRESET_SIGNAL_RANGES[index]
    video_parameters["luma_offset"] = preset.luma_offset
    video_parameters["luma_excursion"] = preset.luma_excursion
    video_parameters["color_diff_offset"] = preset.color_diff_offset
    video_parameters["color_diff_excursion"] = preset.color_diff_excursion


@ref_pseudocode(deviation="inferred_implementation")
def preset_color_primaries(video_parameters, index):
    """(11.4.10.2) Set the color primaries parameter from a preset."""
    video_parameters["color_primaries_index"] = index


@ref_pseudocode(deviation="inferred_implementation")
def preset_color_matrix(video_parameters, index):
    """(11.4.10.3) Set the color matrix parameter from a preset."""
    video_parameters["color_matrix_index"] = index


@ref_pseudocode(deviation="inferred_implementation")
def preset_transfer_function(video_parameters, index):
    """(11.4.10.4) Set the transfer function parameter from a preset."""
    video_parameters["transfer_function_index"] = index


@ref_pseudocode(deviation="inferred_implementation")
def preset_color_spec(video_parameters, index):
    """(11.4.10.1) Load a preset color specification."""
    preset = PRESET_COLOR_SPECS[index]
    preset_color_primaries(video_parameters, preset.color_primaries_index)
    preset_color_matrix(video_parameters, preset.color_matrix_index)
    preset_transfer_function(video_parameters, preset.transfer_function_index)
