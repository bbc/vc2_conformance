"""
Common utlity functions or test values for use in test cases
============================================================
"""

from vc2_conformance.tables import (
    BaseVideoFormats,
    BASE_VIDEO_FORMAT_PARAMETERS,
    PresetSignalRanges,
    ColorDifferenceSamplingFormats,
)

from vc2_conformance.bitstream import (
    SourceParameters,
    FrameSize,
    CleanArea,
    SignalRange,
    ColorDiffSamplingFormat,
)


TINY_VIDEO_OPTIONS = SourceParameters(
    frame_size=FrameSize(
        custom_dimensions_flag=True,
        frame_width=8,
        frame_height=4,
    ),
    clean_area=CleanArea(
        custom_clean_area_flag=True,
        left_offset=0,
        top_offset=0,
        clean_width=8,
        clean_height=4,
    ),
    color_diff_sampling_format=ColorDiffSamplingFormat(
        custom_color_diff_format_flag=True,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
    ),
    signal_range=SignalRange(
        custom_signal_range_flag=True,
        index=PresetSignalRanges.video_8bit_full_range,
    ),
)
"""
A minimal :py:class:`vc2_conformance.bitstream.SourceParameters` which
specifies a 8x4, 8-bit, 4:4:4 video format which any decoder should be able to
support when coded using a single slice per picture.

To be used whenever picture content is of no interest (e.g. when only metadata
or syntax is being checked).
"""


def get_base_video_format_satisfying(parameter_predicate):
    """
    Return the first base video format index for which 'parameter_predicate'
    returns True.
    
    Parameters
    ==========
    parameter_predicate : function(:py:class:`BaseVideoFormatParameters`) -> bool
        This function will be called with :py:class:`BaseVideoFormatParameters`
        options and should return True when an acceptable combination of
        parameters has been presented and False otherwise.
    
    Returns
    =======
    base_video_format : :py:class:`vc2_conformance.tables.BaseVideoFormats`
        The index of a base video format satisfying parameter_predicate.
    
    Raises
    ======
    ValueError
        If no base video format satisfies parameter_predicate.
    """
    for base_video_format in BaseVideoFormats:
        if parameter_predicate(BASE_VIDEO_FORMAT_PARAMETERS[base_video_format]):
            return base_video_format
    raise ValueError("No base video format satisfies predicate")


def get_base_video_format_with(parameter, value):
    """
    Return the first base video format index with the specified
    :py:class:`vc2_conformance.tables.BaseVideoFormatParameters` parameter set
    to the specified value.
    """
    return get_base_video_format_satisfying(
        lambda params: getattr(params, parameter) == value
    )


def get_base_video_format_without(parameter, value):
    """
    Return the first base video format index with the specified
    :py:class:`vc2_conformance.tables.BaseVideoFormatParameters` parameter
    *not* set to the specified value.
    """
    return get_base_video_format_satisfying(
        lambda params: getattr(params, parameter) != value
    )


def get_illigal_enum_values(enum, non_negative=True, non_zero=False):
    """
    Given an :py:class:`enum.IntEnum` type, returns a selection of values which
    fall outside the range of allowed values.
    
    Parameters
    ==========
    enum : :py:class:`IntEnum`
    non_negative : bool
        If True (the default), do not include negative indices in the output.
    non_zero : bool
        If True, do not include zero in the output.
    """
    all_values = set(enum)
    return [
        value
        for value in range(min(all_values) - 1, max(all_values) + 2)
        if (
            value not in all_values and
            (value >= 0 if non_negative else True) and
            (value != 0 if non_zero else True)
        )
    ]
