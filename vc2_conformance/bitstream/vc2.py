r"""
:py:class:`BitstreamValue`\ s for each of VC-2 bitstream structures.
"""

from vc2_conformance.bitstream import (
    LabelledConcatenation,
    NBits,
    UInt,
    Bool,
    Maybe,
)

from vc2_conformance.bitstream.formatters import Hex

from vc2_conformance.tables import (
    PARSE_INFO_PREFIX,
    ParseCodes,
    PictureCodingModes,
    BaseVideoFormats,
    Profiles,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetFrameRates,
    PRESET_FRAME_RATES,
    PresetPixelAspectRatios,
    PRESET_PIXEL_ASPECT_RATIOS,
    PresetSignalRanges,
)


__all__ = [
    "ParseInfo",
    "SequenceHeader",
    "ParseParameters",
    "SourceParameters",
    "FrameSize",
    "ColorDiffSamplingFormat",
    "ScanFormat",
    "FrameRate",
    "AspectRatio",
    "CleanArea",
    "SignalRange",
]


class ParseInfo(LabelledConcatenation):
    """
    (10.5.1) Parse info header defined by ``parse_info()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"parse_info_prefix"`` (:py:class:`NBits`)
    * ``"parse_code"`` (:py:class:`NBits` containing :py:class:`ParseCodes`)
    * ``"next_parse_offset"`` (:py:class:`NBits`)
    * ``"previous_parse_offset"`` (:py:class:`NBits`)
    """
    
    def __init__(self,
                 parse_info_prefix=PARSE_INFO_PREFIX,
                 parse_code=ParseCodes.end_of_sequence,
                 next_parse_offset=0,
                 previous_parse_offset=0):
        super(ParseInfo, self).__init__(
            "parse_info:",
            (
                "parse_info_prefix",
                NBits(parse_info_prefix, 32, formatter=Hex(8)),
            ),
            (
                "parse_code",
                NBits(parse_code, 8, formatter=Hex(2), enum=ParseCodes),
            ),
            ("next_parse_offset", NBits(next_parse_offset, 32)),
            ("previous_parse_offset", NBits(previous_parse_offset, 32)),
        )


class SequenceHeader(LabelledConcatenation):
    """
    (11.1) Sequence header defined by ``sequence_header()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"parse_parameters"`` (:py:class:`ParseParameters`)
    * ``"base_video_format"`` (:py:class:`UInt` containing
      :py:class:`BaseVideoFormats`)
    * ``"video_parameters"`` (:py:class:`SourceParameters`)
    * ``"picture_coding_mode"`` (:py:class:`UInt` containing
      :py:class:`PictureCodingModes`)
    """
    
    def __init__(self,
                 base_video_format=BaseVideoFormats.custom_format,
                 picture_coding_mode=PictureCodingModes.pictures_are_frames):
        super(ParseInfo, self).__init__(
            "sequence_header:",
            ("parse_parameters", ParseParameters()),
            (
                "base_video_format",
                UInt(base_video_format, enum=BaseVideoFormats),
            ),
            ("video_parameters", SourceParameters()),
            (
                "picture_coding_mode",
                UInt(picture_coding_mode, enum=PictureCodingModes),
            ),
        )


class ParseParameters(LabelledConcatenation):
    """
    (11.2.1) Sequence header defined by ``parse_parameters()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"major_version"`` (:py:class:`UInt`)
    * ``"minor_version"`` (:py:class:`UInt`)
    * ``"profile"`` (:py:class:`UInt` containing :py:class:`Profiles`)
    * ``"level"`` (:py:class:`UInt`)
    """
    
    def __init__(self,
                 major_version=3,
                 minor_version=0,
                 profile=Profiles.high_quality,
                 level=0):
        super(ParseParameters, self).__init__(
            "parse_parameters:",
            ("major_version", UInt(major_version)),
            ("minor_version", UInt(minor_version)),
            ("profile", UInt(profile, enum=Profiles)),
            ("level", UInt(level)),
        )


class SourceParameters(LabelledConcatenation):
    """
    (11.4.1) Video format overrides defined by ``source_parameters()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"frame_size"`` (:py:class:`FrameSize`)
    * ``"color_diff_sampling_format"``
      (:py:class:`ColorDiffSamplingFormat`)
    * ``"scan_format"`` (:py:class:`ScanFormat`)
    * ``"frame_rate"`` (:py:class:`FrameRate`)
    * ``"pixel_aspect_ratio"`` (:py:class:`PixelAspectRatio`)
    * ``"clean_area"`` (:py:class:`CleanArea`)
    * ``"signal_range"`` (:py:class:`SignalRange`)
    * ``"color_spec"`` (:py:class:`ColorSpec`)
    """
    
    def __init__(self):
        super(SourceParameters, self).__init__(
            "source_parameters:",
            ("frame_size", FrameSize()),
            ("color_diff_sampling_format", ColorDiffSamplingFormat()),
            ("scan_format", ScanFormat()),
            ("frame_rate", FrameRate()),
            ("pixel_aspect_ratio", PixelAspectRatio()),
            ("clean_area", CleanArea()),
            ("signal_range", SignalRange()),
            ("color_spec", ColorSpec()),
        )


class FrameSize(LabelledConcatenation):
    """
    (11.4.3) Frame size override defined by ``frame_size()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_dimensions_flag"`` (:py:class:`Bool`)
    * ``"frame_width"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"frame_height"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self, custom_dimensions_flag=False, frame_width=0, frame_height=0):
        flag = Bool(custom_dimensions_flag)
        is_custom = lambda: flag.value
        super(FrameSize, self).__init__(
            "frame_size:",
            ("custom_dimensions_flag", flag),
            ("frame_width", Maybe(UInt(frame_width), is_custom)),
            ("frame_height", Maybe(UInt(frame_height), is_custom)),
        )


class ColorDiffSamplingFormat(LabelledConcatenation):
    """
    (11.4.4) Color-difference sampling override defined by
    ``color_diff_sampling_format()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_color_diff_format_flag"`` (:py:class:`Bool`)
    * ``"color_diff_format_index"`` (:py:class:`UInt` containing
      :py:class:`ColorDifferenceSamplingFormats`, in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 custom_color_diff_format_flag=False,
                 color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4):
        flag = Bool(custom_color_diff_format_flag)
        super(ColorDiffSamplingFormat, self).__init__(
            "color_diff_sampling_format:",
            ("custom_color_diff_format_flag", flag),
            (
                "color_diff_format_index",
                Maybe(
                    UInt(
                        color_diff_format_index,
                        enum=ColorDifferenceSamplingFormats,
                    ),
                    lambda: flag.value,
                ),
            ),
        )


class ScanFormat(LabelledConcatenation):
    """
    (11.4.5) Scan format override defined by ``scan_format()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_scan_format_flag"`` (:py:class:`Bool`)
    * ``"source_sampling"`` (:py:class:`UInt` containing
      :py:class:`SourceSamplingModes`, in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 custom_scan_format_flag=False,
                 source_sampling=SourceSamplingModes.progressive):
        flag = Bool(custom_scan_format_flag)
        super(ScanFormat, self).__init__(
            "scan_format:",
            ("custom_scan_format_flag", flag),
            (
                "source_sampling",
                Maybe(
                    UInt(source_sampling, enum=SourceSamplingModes),
                    lambda: flag.value,
                ),
            ),
        )


class FrameRate(LabelledConcatenation):
    """
    (11.4.6) Frame-rate override defined by ``frame_rate()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_frame_rate_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetFrameRates`, in a :py:class:`Maybe`)
    * ``"frame_rate_numer"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"frame_rate_denom"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 custom_frame_rate_flag=False,
                 index=0,
                 frame_rate_numer=0,
                 frame_rate_denom=1):
        flag = Bool(custom_frame_rate_flag)
        index = Maybe(
            UInt(
                index,
                enum=PresetFrameRates,
                # Show the preset framerate in a more human-readable form than
                # the enum name
                get_value_name=(
                    lambda p:
                    "{} fps".format(PRESET_FRAME_RATES[PresetFrameRates(p)])
                ),
            ),
            lambda: flag.value,
        )
        is_full_custom = lambda: flag.value and index.value == 0
        super(FrameRate, self).__init__(
            "frame_rate:",
            ("custom_frame_rate_flag", flag),
            ("index", index),
            ("frame_rate_numer", Maybe(UInt(frame_rate_numer), is_full_custom)),
            ("frame_rate_denom", Maybe(UInt(frame_rate_denom), is_full_custom)),
        )


class AspectRatio(LabelledConcatenation):
    """
    (11.4.7) Pixel aspect ratio override defined by ``aspect_ratio()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_pixel_aspect_ratio_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetPixelAspectRatios`, in a :py:class:`Maybe`)
    * ``"pixel_aspect_ratio_numer"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"pixel_aspect_ratio_denom"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    @staticmethod
    def _get_index_value_name(index):
        """
        A 'get_value_name' compatible function to return a human-readable
        version of an aspect ratio index.
        """
        enum_value = PresetPixelAspectRatios(index)
        ratio = PRESET_PIXEL_ASPECT_RATIOS[enum_value]
        return "{}:{}".format(ratio.numerator, ratio.denominator)
    
    def __init__(self,
                 custom_pixel_aspect_ratio_flag=False,
                 index=PresetPixelAspectRatios.ratio_1_1,
                 pixel_aspect_ratio_numer=1,
                 pixel_aspect_ratio_denom=1):
        flag = Bool(custom_pixel_aspect_ratio_flag)
        index = Maybe(
            UInt(
                index,
                enum=PresetPixelAspectRatios,
                get_value_name=AspectRatio._get_index_value_name
            ),
            lambda: flag.value,
        )
        is_full_custom = lambda: flag.value and index.value == 0
        super(AspectRatio, self).__init__(
            "aspect_ratio:",
            ("custom_pixel_aspect_ratio_flag", flag),
            ("index", index),
            ("pixel_aspect_ratio_numer", Maybe(UInt(pixel_aspect_ratio_numer), is_full_custom)),
            ("pixel_aspect_ratio_denom", Maybe(UInt(pixel_aspect_ratio_denom), is_full_custom)),
        )


class CleanArea(LabelledConcatenation):
    """
    (11.4.8) Clean areas override defined by ``clean_area()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_clean_area_flag"`` (:py:class:`Bool`)
    * ``"clean_width"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"clean_height"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"left_offset"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"top_offset"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 custom_clean_area_flag=False,
                 clean_width=1, clean_height=1,
                 left_offset=0, top_offset=0):
        flag = Bool(custom_clean_area_flag)
        is_custom = lambda: flag.value
        super(CleanArea, self).__init__(
            "clean_area:",
            ("custom_clean_area_flag", flag),
            ("clean_width", Maybe(UInt(clean_width), is_custom)),
            ("clean_height", Maybe(UInt(clean_height), is_custom)),
            ("left_offset", Maybe(UInt(left_offset), is_custom)),
            ("top_offset", Maybe(UInt(top_offset), is_custom)),
        )


class SignalRange(LabelledConcatenation):
    """
    (11.4.9) Signal range override defined by ``signal_range()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_signal_range_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetSignalRanges`, in a :py:class:`Maybe`)
    * ``"luma_offset"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"luma_excursion"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"color_diff_offset"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"color_diff_excursion"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 custom_signal_range_flag=False,
                 index=0,
                 luma_offset=0,
                 luma_excursion=1,
                 color_diff_offset=0,
                 color_diff_excursion=1):
        flag = Bool(custom_signal_range_flag)
        index = Maybe(UInt(index, enum=PresetSignalRanges), lambda: flag.value)
        is_full_custom = lambda: flag.value and index.value == 0
        super(SignalRange, self).__init__(
            "signal_range:",
            ("custom_signal_range_flag", flag),
            ("index", index),
            ("luma_offset", Maybe(UInt(luma_offset), is_full_custom)),
            ("luma_excursion", Maybe(UInt(luma_excursion), is_full_custom)),
            ("color_diff_offset", Maybe(UInt(color_diff_offset), is_full_custom)),
            ("color_diff_excursion", Maybe(UInt(color_diff_excursion), is_full_custom)),
        )


class ColorSpec(LabelledConcatenation):
    """
    (11.4.10.1) Colour specification override defined by ``color_spec()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_color_spec_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetColorSpecs`, in a :py:class:`Maybe`)
    * ``"color_primaries"`` (:py:class:`ColorPrimaries` in a :py:class:`Maybe`)
    * ``"color_matrix"`` (:py:class:`ColorMatrix` in a :py:class:`Maybe`)
    * ``"transfer_function"`` (:py:class:`TransferFunction` in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 custom_signal_range_flag=False,
                 index=0,
                 luma_offset=0,
                 luma_excursion=1,
                 color_diff_offset=0,
                 color_diff_excursion=1):
        flag = Bool(custom_signal_range_flag)
        index = Maybe(UInt(index, enum=PresetSignalRanges), lambda: flag.value)
        is_full_custom = lambda: flag.value and index.value == 0
        super(SignalRange, self).__init__(
            "signal_range:",
            ("custom_signal_range_flag", flag),
            ("index", index),
            ("luma_offset", Maybe(UInt(luma_offset), is_full_custom)),
            ("luma_excursion", Maybe(UInt(luma_excursion), is_full_custom)),
            ("color_diff_offset", Maybe(UInt(color_diff_offset), is_full_custom)),
            ("color_diff_excursion", Maybe(UInt(color_diff_excursion), is_full_custom)),
        )

