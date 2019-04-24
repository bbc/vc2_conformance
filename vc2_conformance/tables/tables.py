"""
Tables of values defined in the VC-2 spec.
"""

from attr import attrs, attrib

from fractions import Fraction

from vc2_conformance.tables.constants import (
    ParseCodes,
    Profiles,
    PresetFrameRates,
    PresetPixelAspectRatios,
    PresetSignalRanges,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    PresetColorSpecs,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    BaseVideoFormats,
    LiftingFilterTypes,
    WaveletFilters,
)

__all__ = [
    "ProfileParameters",
    "PROFILES",
    "PRESET_FRAME_RATES",
    "PRESET_PIXEL_ASPECT_RATIOS",
    "SignalRangeParameters",
    "PRESET_SIGNAL_RANGES",
    "PRESET_COLOR_PRIMARIES",
    "PRESET_COLOR_MATRICES",
    "PRESET_TRANSFER_FUNCTIONS",
    "PRESET_COLOR_SPECS",
    "BaseVideoFormatParameters",
    "BASE_VIDEO_FORMAT_PARAMETERS",
    "LiftingStage",
    "LiftingFilterParameters",
    "LIFTING_FILTERS",
]


@attrs
class ProfileParameters(object):
    """(C.2) Parameters describing a profile specification."""
    
    allowed_data_units = attrib()
    """
    A list of supported data units. A list of values from the ParseCodes enum.
    """


PROFILES = {
    # (C.2.2)
    Profiles.low_delay: ProfileParameters([
        ParseCodes.sequence_header,
        ParseCodes.end_of_sequence,
        ParseCodes.auxiliary_data,
        ParseCodes.padding_data,
        ParseCodes.low_delay_picture,
    ]),
    # (C.2.3)
    Profiles.high_quality: ProfileParameters([
        ParseCodes.sequence_header,
        ParseCodes.end_of_sequence,
        ParseCodes.auxiliary_data,
        ParseCodes.padding_data,
        ParseCodes.high_quality_picture,
    ]),
}
"""
The list of supported profiles from (C.2) indexed by :py:class:`Profiles`.
"""


PRESET_FRAME_RATES = {
    PresetFrameRates.fps_24_over_1_001:  Fraction(24000, 1001),
    PresetFrameRates.fps_24:             Fraction(24, 1),
    PresetFrameRates.fps_25:             Fraction(25, 1),
    PresetFrameRates.fps_30_over_1_001:  Fraction(30000, 1001),
    PresetFrameRates.fps_30:             Fraction(30, 1),
    PresetFrameRates.fps_50:             Fraction(50, 1),
    PresetFrameRates.fps_60_over_1_001:  Fraction(60000, 1001),
    PresetFrameRates.fps_60:             Fraction(60, 1),
    PresetFrameRates.fps_15_over_1_001:  Fraction(15000, 1001),
    PresetFrameRates.fps_25_over_2:      Fraction(25, 2),
    PresetFrameRates.fps_48:             Fraction(48, 1),
    PresetFrameRates.fps_48_over_1_001:  Fraction(48000, 1001),
    PresetFrameRates.fps_96:             Fraction(96, 1),
    PresetFrameRates.fps_100:            Fraction(100, 1),
    PresetFrameRates.fps_120_over_1_001: Fraction(120000, 1001),
    PresetFrameRates.fps_120:            Fraction(120, 1),
}
"""
(11.4.6) Frame-rate presets from (Table 11.3) indexed by
:py:class:`PresetFrameRates`.
"""


PRESET_PIXEL_ASPECT_RATIOS = {
    PresetPixelAspectRatios.ratio_1_1: Fraction(1, 1),
    PresetPixelAspectRatios.ratio_4_3_525_line: Fraction(10, 11),
    PresetPixelAspectRatios.ratio_4_3_625_line: Fraction(12, 11),
    PresetPixelAspectRatios.ratio_16_9_525_line: Fraction(40, 33),
    PresetPixelAspectRatios.ratio_16_9_625_line: Fraction(16, 11),
    PresetPixelAspectRatios.ratio_4_3: Fraction(4, 3),
}
"""(11.4.7) Pixel aspect ratio presets from (Table 11.4) indexed by
:py:class:`PresetPixelAspectRatios`"""


@attrs(frozen=True)
class SignalRangeParameters(object):
    """
    An entry in (Table 11.5).
    """
    
    luma_offset = attrib()
    """The luma value corresponding with 0."""
    
    luma_excursion = attrib()
    """The maximum value of an offset luma value."""
    
    color_diff_offset = attrib()
    """The color difference value corresponding with 0."""
    
    color_diff_excursion = attrib()
    """The maximum value of an offset color difference value."""


PRESET_SIGNAL_RANGES = {
    PresetSignalRanges.range_8_bit_full_range: SignalRangeParameters(0, 255, 128, 255),
    PresetSignalRanges.range_8_bit_video: SignalRangeParameters(16, 219, 128, 224),
    PresetSignalRanges.range_10_bit_video: SignalRangeParameters(64, 876, 512, 896),
    PresetSignalRanges.range_12_bit_video: SignalRangeParameters(256, 3504, 2048, 3584),
    PresetSignalRanges.range_10_bit_full_range: SignalRangeParameters(0, 1023, 512, 1023),
    PresetSignalRanges.range_12_bit_full_range: SignalRangeParameters(0, 4095, 2048, 4095),
    PresetSignalRanges.range_16_bit_video: SignalRangeParameters(4096, 56064, 32768, 57344),
    PresetSignalRanges.range_16_bit_full_range: SignalRangeParameters(0, 65535, 32768, 65535),
}
"""
(11.4.9) Signal offsets/ranges presets from (Table 11.5) indexed by
:py:class:`PresetSignalRanges`.
"""


PRESET_COLOR_PRIMARIES = {
    PresetColorPrimaries.hdtv: "ITU-R BT.709",
    PresetColorPrimaries.sdtv_525: "ITU-R BT.601",
    PresetColorPrimaries.sdtv_625: "ITU-R BT.601",
    PresetColorPrimaries.d_cinema: "SMPTE ST 428-1",
    PresetColorPrimaries.uhdtv: "ITU-R BT.2020",
}
"""
(11.4.10.2) Normative specification names for color primaries from (Table 11.7)
indexed by :py:class:`PresetColorPrimaries`.
"""


@attrs
class ColorMatrixParameters(object):
    """An entry in (Table 11.8)"""
    
    specification = attrib()
    """Normative specification name."""
    
    color_matrix = attrib()
    """Normative color matrix description."""

PRESET_COLOR_MATRICES = {
    PresetColorMatrices.hdtv: ColorMatrixParameters("ITU-R BT.709", "K_R=0:2126,K_B=0:0722"),
    PresetColorMatrices.sdtv: ColorMatrixParameters("ITU-R BT.601", "K_R=0:299,K_B=0:114"),
    PresetColorMatrices.reversible: ColorMatrixParameters("ITU-T H.264", "YC_GC_O"),
    PresetColorMatrices.rgb: ColorMatrixParameters(None, "Y=G, C_1=B, C_2=R"),
    PresetColorMatrices.uhdtv: ColorMatrixParameters("ITU-R BT.2020", "K_R=0:2627,K_B =0:0593"),
}
"""
(11.4.10.3) Color matrices from (Table 11.8) indexed by
:py:class:`PresetColorMatrices`.
"""


PRESET_TRANSFER_FUNCTIONS = {
    PresetTransferFunctions.tv_gamma: "ITU-R BT.2020",
    PresetTransferFunctions.extended_gamut: "ITU-R BT.1361 (suppressed)",
    PresetTransferFunctions.linear: "Linear",
    PresetTransferFunctions.d_cinema_transfer_function: "SMPTE ST 428-1",
    PresetTransferFunctions.perceptual_quality: "ITU-R BT.2100",
    PresetTransferFunctions.hybrid_log_gamma: "ITU-R BT.2100",
}
"""
(11.4.10.4) Normative specification names for transfer functions from (Table
11.9) indexed by :py:class:`PresetTransferFunctions`.
"""


@attrs
class ColorSpecificiation(object):
    """An entry in (Table 11.6)"""
    
    color_primaries_index = attrib()
    """A :py:class:`PresetColorPrimaries` index."""
    
    color_matrix_index = attrib()
    """A :py:class:`PresetColorMatrices` index."""
    
    transfer_function_index = attrib()
    """A :py:class:`PresetTransferFunctions` index."""


PRESET_COLOR_SPECS = {
    PresetColorSpecs.custom: ColorSpecificiation(
        PresetColorPrimaries.hdtv,
        PresetColorMatrices.hdtv,
        PresetTransferFunctions.tv_gamma),
    PresetColorSpecs.sdtv_525: ColorSpecificiation(
        PresetColorPrimaries.sdtv_525,
        PresetColorMatrices.sdtv,
        PresetTransferFunctions.tv_gamma),
    PresetColorSpecs.sdtv_625: ColorSpecificiation(
        PresetColorPrimaries.sdtv_625,
        PresetColorMatrices.sdtv,
        PresetTransferFunctions.tv_gamma),
    PresetColorSpecs.hdtv: ColorSpecificiation(
        PresetColorPrimaries.hdtv,
        PresetColorMatrices.hdtv,
        PresetTransferFunctions.tv_gamma),
    PresetColorSpecs.d_cinema: ColorSpecificiation(
        PresetColorPrimaries.d_cinema,
        PresetColorMatrices.reversible,
        PresetTransferFunctions.d_cinema_transfer_function),
    PresetColorSpecs.uhdtv: ColorSpecificiation(
        PresetColorPrimaries.uhdtv,
        PresetColorMatrices.uhdtv,
        PresetTransferFunctions.tv_gamma),
    PresetColorSpecs.hdr_tv_pq: ColorSpecificiation(
        PresetColorPrimaries.uhdtv,
        PresetColorMatrices.uhdtv,
        PresetTransferFunctions.perceptual_quality),
    PresetColorSpecs.hdr_tv_hlg: ColorSpecificiation(
        PresetColorPrimaries.uhdtv,
        PresetColorMatrices.uhdtv,
        PresetTransferFunctions.hybrid_log_gamma),
}
"""
(11.4.10.1) Preset color specification collections from (Table 11.6), indexed
by :py:class:`PresetColorSpecs`.
"""

@attrs
class BaseVideoFormatParameters(object):
    """(B) An entry in (Table B.1a, B.1b or B.1c)"""
    
    frame_width = attrib()
    frame_height = attrib()
    
    color_diff_format_index = attrib()
    """
    An entry from the enum :py:class:`ColorDifferenceSamplingFormats`. Listed
    as 'color difference sampling' in (Table B.1).
    """
    
    source_sampling = attrib()
    """
    An entry from the enum :py:class:`SourceSamplingModes`. Specifies
    progressive or interlaced.
    """
    
    top_field_first = attrib()
    """If True, the top-line of the frame is in the first field."""
    
    frame_rate_index = attrib()
    """The frame rate, one of the indices of PRESET_FRAME_RATES."""
    
    pixel_aspect_ratio_index = attrib()
    """The pixel aspect ratio, an entry from the enum :py:class`PresetPixelAspectRatios`."""
    
    clean_width = attrib()
    clean_height = attrib()
    left_offset = attrib()
    top_offset = attrib()
    """The clean area of the pictures. See (11.4.8) and (E.4.2)."""
    
    signal_range_index = attrib()
    """The signal ranges, an entry from the enum :py:class:`PresetSignalRanges`."""
    
    color_spec_index = attrib()
    """The color specification, an entry from the enum :py:class:`PresetColorSpecs`."""


BASE_VIDEO_FORMAT_PARAMETERS = {
    BaseVideoFormats.custom_format: BaseVideoFormatParameters(
        frame_width=640,
        frame_height=480,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=False,
        frame_rate_index=PresetFrameRates.fps_24_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=640,
        clean_height=480,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_8_bit_full_range,
        color_spec_index=PresetColorSpecs.custom),
    BaseVideoFormats.qsif525: BaseVideoFormatParameters(
        frame_width=176,
        frame_height=120,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=False,
        frame_rate_index=PresetFrameRates.fps_15_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_4_3_525_line,
        clean_width=176,
        clean_height=120,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_8_bit_full_range,
        color_spec_index=PresetColorSpecs.sdtv_525),
    BaseVideoFormats.qcif: BaseVideoFormatParameters(
        frame_width=176,
        frame_height=144,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_25_over_2,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_4_3_525_line,
        clean_width=176,
        clean_height=144,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_8_bit_full_range,
        color_spec_index=PresetColorSpecs.sdtv_625),
    BaseVideoFormats.sif525: BaseVideoFormatParameters(
        frame_width=352,
        frame_height=240,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=False,
        frame_rate_index=PresetFrameRates.fps_15_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_4_3_525_line,
        clean_width=352,
        clean_height=240,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_8_bit_full_range,
        color_spec_index=PresetColorSpecs.sdtv_525),
    BaseVideoFormats.cif: BaseVideoFormatParameters(
        frame_width=352,
        frame_height=288,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_25_over_2,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_4_3_525_line,
        clean_width=352,
        clean_height=288,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_8_bit_full_range,
        color_spec_index=PresetColorSpecs.sdtv_625),
    BaseVideoFormats._4sif525: BaseVideoFormatParameters(
        frame_width=704,
        frame_height=480,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=False,
        frame_rate_index=PresetFrameRates.fps_15_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_4_3_525_line,
        clean_width=704,
        clean_height=480,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_8_bit_full_range,
        color_spec_index=PresetColorSpecs.sdtv_525),
    BaseVideoFormats._4cif: BaseVideoFormatParameters(
        frame_width=704,
        frame_height=576,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_25_over_2,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_4_3_525_line,
        clean_width=704,
        clean_height=576,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_8_bit_full_range,
        color_spec_index=PresetColorSpecs.sdtv_625),
    BaseVideoFormats.sd480i_60: BaseVideoFormatParameters(
        frame_width=720,
        frame_height=480,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.interlaced,
        top_field_first=False,
        frame_rate_index=PresetFrameRates.fps_30_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_4_3_525_line,
        clean_width=704,
        clean_height=480,
        left_offset=8,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.sdtv_525),
    BaseVideoFormats.sd576i_50: BaseVideoFormatParameters(
        frame_width=720,
        frame_height=576,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.interlaced,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_25,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_4_3_525_line,
        clean_width=704,
        clean_height=576,
        left_offset=8,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.sdtv_625),
    BaseVideoFormats.hd720p_60: BaseVideoFormatParameters(
        frame_width=1280,
        frame_height=720,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_60_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=1280,
        clean_height=720,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.hdtv),
    BaseVideoFormats.hd720p_50: BaseVideoFormatParameters(
        frame_width=1280,
        frame_height=720,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_50,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=1280,
        clean_height=720,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.hdtv),
    BaseVideoFormats.hd1080i_60: BaseVideoFormatParameters(
        frame_width=1920,
        frame_height=1080,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.interlaced,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_30_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=1920,
        clean_height=1080,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.hdtv),
    BaseVideoFormats.hd1080i_50: BaseVideoFormatParameters(
        frame_width=1920,
        frame_height=1080,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.interlaced,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_25,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=1920,
        clean_height=1080,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.hdtv),
    BaseVideoFormats.hd1080p_60: BaseVideoFormatParameters(
        frame_width=1920,
        frame_height=1080,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_60_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=1920,
        clean_height=1080,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.hdtv),
    BaseVideoFormats.hd1080p_50: BaseVideoFormatParameters(
        frame_width=1920,
        frame_height=1080,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_50,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=1920,
        clean_height=1080,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.hdtv),
    BaseVideoFormats.dc2k: BaseVideoFormatParameters(
        frame_width=2048,
        frame_height=1080,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_24,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=2048,
        clean_height=1080,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_12_bit_video,
        color_spec_index=PresetColorSpecs.d_cinema),
    BaseVideoFormats.dc4k: BaseVideoFormatParameters(
        frame_width=4096,
        frame_height=2160,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_24,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=4096,
        clean_height=2160,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_12_bit_video,
        color_spec_index=PresetColorSpecs.d_cinema),
    BaseVideoFormats.uhdtv_4k_60: BaseVideoFormatParameters(
        frame_width=3840,
        frame_height=2160,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_60_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=3840,
        clean_height=2160,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.uhdtv),
    BaseVideoFormats.uhdtv_4k_50: BaseVideoFormatParameters(
        frame_width=3840,
        frame_height=2160,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_50,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=3840,
        clean_height=2160,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.uhdtv),
    BaseVideoFormats.uhdtv_8k_60: BaseVideoFormatParameters(
        frame_width=7680,
        frame_height=4320,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_60_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=7680,
        clean_height=4320,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.uhdtv),
    BaseVideoFormats.uhdtv_8k_50: BaseVideoFormatParameters(
        frame_width=7680,
        frame_height=4320,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_50,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=7680,
        clean_height=4320,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.uhdtv),
    BaseVideoFormats.hd1080p_24: BaseVideoFormatParameters(
        frame_width=1920,
        frame_height=1080,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_index=PresetFrameRates.fps_24_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_1_1,
        clean_width=1920,
        clean_height=1080,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.hdtv),
    BaseVideoFormats.sd_pro486: BaseVideoFormatParameters(
        frame_width=720,
        frame_height=486,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.interlaced,
        top_field_first=False,
        frame_rate_index=PresetFrameRates.fps_30_over_1_001,
        pixel_aspect_ratio_index=PresetPixelAspectRatios.ratio_4_3_525_line,
        clean_width=720,
        clean_height=486,
        left_offset=0,
        top_offset=0,
        signal_range_index=PresetSignalRanges.range_10_bit_video,
        color_spec_index=PresetColorSpecs.hdtv),
}
"""
(B) Base video format specifications from (Table B.1a, B.1b, B.1c), indexed by
:py:class:`BaseVideoFormats`.
"""


@attrs
class LiftingStage(object):
    """
    (15.4.4.1) Definition of a lifting stage/operation in a lifting filter.
    """
    
    lift_type = attrib()
    """
    Specifies which lifting filtering operation is taking place. One
    of the indices from the LiftingFilterTypes enumeration.
    """
    
    S = attrib()
    """Scale factor (right-shift applied to weighted sum)"""
    
    L = attrib()
    """Length of filter."""
    
    D = attrib()
    """Offset of filter."""
    
    taps = attrib()
    """An array of integers defining the filter coefficients."""

@attrs
class LiftingFilterParameters(object):
    """
    (15.4.4.3) The generic container for the details described by (Table 15.1
    to 15.6).
    """
    filter_bit_shift = attrib()
    """Right-shift to apply after synthesis (or before analysis)."""
    
    stages = attrib()
    """
    A list of LiftingStage objects to be used in sequence to perform synthesis
    with this filter.
    """

LIFTING_FILTERS = {
    WaveletFilters.deslauriers_dubuc_9_7: LiftingFilterParameters(
        stages=[
            LiftingStage(lift_type=LiftingFilterTypes(2), S=2, L=2, D=0, taps=[1, 1]),
            LiftingStage(lift_type=LiftingFilterTypes(3), S=4, L=4, D=-1, taps=[-1, 9, 9, -1]),
        ],
        filter_bit_shift=1,
    ),
    WaveletFilters.le_gall_5_3: LiftingFilterParameters(
        stages=[
            LiftingStage(lift_type=LiftingFilterTypes(2), S=2, L=2, D=0, taps=[1, 1]),
            LiftingStage(lift_type=LiftingFilterTypes(3), S=1, L=2, D=0, taps=[1, 1]),
        ],
        filter_bit_shift=1,
    ),
    WaveletFilters.deslauriers_dubuc_13_7: LiftingFilterParameters(
        stages=[
            LiftingStage(lift_type=LiftingFilterTypes(2), S=5, L=4, D=-1, taps=[-1, 9, 9, -1]),
            LiftingStage(lift_type=LiftingFilterTypes(3), S=4, L=4, D=-1, taps=[-1, 9, 9, -1]),
        ],
        filter_bit_shift=1,
    ),
    WaveletFilters.haar_no_shift: LiftingFilterParameters(
        stages=[
            LiftingStage(lift_type=LiftingFilterTypes(2), S=1, L=1, D=1, taps=[1]),
            LiftingStage(lift_type=LiftingFilterTypes(3), S=0, L=1, D=0, taps=[1]),
        ],
        filter_bit_shift=0,
    ),
    WaveletFilters.haar_with_shift: LiftingFilterParameters(
        stages=[
            LiftingStage(lift_type=LiftingFilterTypes(2), S=1, L=1, D=1, taps=[1]),
            LiftingStage(lift_type=LiftingFilterTypes(3), S=0, L=1, D=0, taps=[1]),
        ],
        filter_bit_shift=1,
    ),
    WaveletFilters.fidelity: LiftingFilterParameters(
        stages=[
            LiftingStage(lift_type=LiftingFilterTypes(3), S=8, L=8, D=-3, taps=[-2, -10, -25, 81, 81, -25, 10, -2]),
            LiftingStage(lift_type=LiftingFilterTypes(2), S=8, L=8, D=-3, taps=[-8, 21, -46, 161, 161, -46, 21, -8]),
        ],
        filter_bit_shift=0,
    ),
    WaveletFilters.daubechies_9_7: LiftingFilterParameters(
        stages=[
            LiftingStage(lift_type=LiftingFilterTypes(2), S=12, L=2, D=0, taps=[1817, 1817]),
            LiftingStage(lift_type=LiftingFilterTypes(4), S=12, L=2, D=0, taps=[3616, 3616]),
            LiftingStage(lift_type=LiftingFilterTypes(1), S=12, L=2, D=0, taps=[217, 217]),
            LiftingStage(lift_type=LiftingFilterTypes(3), S=12, L=2, D=0, taps=[6497, 6497]),
        ],
        filter_bit_shift=1,
    ),
}
"""
(15.4.4.3) Filter definitions taken from (Table 15.1 to 15.6) indexed by :py:class:`WaveletFilters`.
"""