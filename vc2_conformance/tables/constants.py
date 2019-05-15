"""
Constants
=========

.. currentmodule:: vc2_conformance.tables
"""

from enum import IntEnum

from vc2_conformance.metadata import ref_value, ref_enum

__all__ = [
    "PARSE_INFO_PREFIX",
    "PARSE_INFO_HEADER_BYTES",
    "ParseCodes",
    "PictureCodingModes",
    "ColorDifferenceSamplingFormats",
    "SourceSamplingModes",
    "BaseVideoFormats",
    "Profiles",
    "Levels",
    "PresetFrameRates",
    "PresetPixelAspectRatios",
    "PresetSignalRanges",
    "PresetColorPrimaries",
    "PresetColorMatrices",
    "PresetTransferFunctions",
    "PresetColorSpecs",
    "LiftingFilterTypes",
    "WaveletFilters",
]

PARSE_INFO_PREFIX = ref_value(0x42424344, "10.5.1")
"""
(10.5.1) The 'magic bytes' used to identify the start of a parse info header.
'BBCD' in ASCII.
"""

PARSE_INFO_HEADER_BYTES = ref_value(13, "15.5.1")
"""(15.5.1) The number of bytes in the parse_info header."""


@ref_enum
class ParseCodes(IntEnum):
    """
    (10.5.2) Valid parse_code values from (Table 10.1). Names are not normative.
    """
    # VC-2 Syntax
    sequence_header = 0x00
    end_of_sequence = 0x10
    auxiliary_data = 0x20
    padding_data = 0x30
    
    # Pictures
    low_delay_picture = 0xC8
    high_quality_picture = 0xE8
    
    # Picture fragments
    low_delay_picture_fragment = 0xCC
    high_quality_picture_fragment = 0xEC


@ref_enum
class PictureCodingModes(IntEnum):
    """(11.5) Indices defined in the text. Names are not normative."""
    pictures_are_frames = 0
    pictures_are_fields = 1

@ref_enum
class ColorDifferenceSamplingFormats(IntEnum):
    """(11.4.4) Indices from (Table 11.2)"""
    
    color_4_4_4 = 0
    color_4_2_2 = 1
    color_4_2_0 = 2


@ref_enum
class SourceSamplingModes(IntEnum):
    """(11.4.5) Indices defined in the text. Names are not normative."""
    progressive = 0
    interlaced = 1


@ref_enum
class BaseVideoFormats(IntEnum):
    """
    (11.3) Base video format indices from (Table 11.1). Names based on the
    normative values in this table.
    
    See also: :py:data:`~.tables.BASE_VIDEO_FORMAT_PARAMETERS`.
    """
    custom_format = 0
    qsif525 = 1
    qcif = 2
    sif525 = 3
    cif = 4
    _4sif525 = 5
    _4cif = 6
    sd480i_60 = 7
    sd576i_50 = 8
    hd720p_60 = 9
    hd720p_50 = 10
    hd1080i_60 = 11
    hd1080i_50 = 12
    hd1080p_60 = 13
    hd1080p_50 = 14
    dc2k = 15
    dc4k = 16
    uhdtv_4k_60 = 17
    uhdtv_4k_50 = 18
    uhdtv_8k_60 = 19
    uhdtv_8k_50 = 20
    hd1080p_24 = 21
    sd_pro486 = 22


@ref_enum
class Profiles(IntEnum):
    """
    (C.2) VC-2 Profiles.
    
    See also: :py:data:`~.tables.PROFILES`.
    """
    low_delay = 0
    high_quality = 3


@ref_enum
class Levels(IntEnum):
    """
    (C.3) VC-2 Levels.
    
    Levels listed below are defined in:
    
    * (SMPTE ST 2042-2:2017) VC-2 Level Definitions
    * (SMPTE RP 2047-1) VC-2 Mezzanine Compression of 1080P High Definition Video Sources
    * (SMPTE RP 2047-3) VC-2 Level 65 Compression of High Definition Video Sources for Use with a Standard Definition Infrastructure
    * (SMPTE RP 2047-5) VC-2 Level 66 Compression of Ultra High Definition Video Sources for use with a High Definition Infrastructure
    
    Names are informative and inferred from the requirements of the levels
    document.
    """
    unconstrained = 0
    
    # Generalized levels (ST 2402-2)
    sub_sd = 1
    sd = 2
    hd = 3
    digital_cinema_2k = 4
    digital_cinema_4k = 5
    uhdtv_4k = 6
    uhdtv_8k = 7
    
    # Specialized levels
    p60_hd_over_single_link_sdi = 64  # (ST 2047-1)
    hd_over_sd_sdi = 65  # (ST 2047-3)
    uhd_over_hd_sdi = 66  # (ST 2047-5)


@ref_enum
class PresetFrameRates(IntEnum):
    """
    (11.4.6) Preset framerate indices from (Table 11.1). Names are informative.
    
    See also: :py:data:`~.tables.PRESET_FRAME_RATES`.
    """
    fps_24_over_1_001 = 1
    fps_24 = 2
    fps_25 = 3
    fps_30_over_1_001 = 4
    fps_30 = 5
    fps_50 = 6
    fps_60_over_1_001 = 7
    fps_60 = 8
    fps_15_over_1_001 = 9
    fps_25_over_2 = 10
    fps_48 = 11
    fps_48_over_1_001 = 12
    fps_96 = 13
    fps_100 = 14
    fps_120_over_1_001 = 15
    fps_120 = 16

@ref_enum
class PresetPixelAspectRatios(IntEnum):
    """
    (11.4.7) Pixel aspect ratio preset indices from (Table 11.4). Names are
    informative.
    
    See also: :py:data:`~.tables.PRESET_PIXEL_ASPECT_RATIOS`.
    """
    ratio_1_1 = 1
    ratio_4_3_525_line = 2  # 4:3 525 line systems
    ratio_4_3_625_line = 3  # 4:3 625 line systems
    ratio_16_9_525_line = 4  # 16:9 525 line systems
    ratio_16_9_625_line = 5  # 16:9 625 line systems
    ratio_4_3 = 6  # reduced horizontal resolution systems


@ref_enum
class PresetSignalRanges(IntEnum):
    """
    (11.4.9) Signal offsets/ranges preset indices from (Table 11.5). Names are
    informative and based on those in the table.
    
    See also: :py:data:`~.tables.PRESET_SIGNAL_RANGES`.
    """
    range_8_bit_full_range = 1
    range_8_bit_video = 2
    range_10_bit_video = 3
    range_12_bit_video = 4
    range_10_bit_full_range = 5
    range_12_bit_full_range = 6
    range_16_bit_video = 7
    range_16_bit_full_range = 8


@ref_enum
class PresetColorPrimaries(IntEnum):
    """
    (11.4.10.2) Color primaries from (Table 11.7). Names and comments are
    informative and based on those in the table.
    
    See also: :py:data:`~.tables.PRESET_COLOR_PRIMARIES`.
    """
    hdtv = 0  # Also Computer, Web, sRGB
    sdtv_525 = 1  # 525 Primaries
    sdtv_625 = 2  # 625 Primaries
    d_cinema = 3  # CIE XYZ
    uhdtv = 4  # Used in UHDTV and HDR


@ref_enum
class PresetColorMatrices(IntEnum):
    """
    (11.4.10.3) Color primaries from (Table 11.8). Names and comments are
    informative and based on those in the table.
    
    See also: :py:data:`~.tables.PRESET_COLOR_MATRICES`.
    """
    hdtv = 0  # Also Computer and Web
    sdtv = 1
    reversible = 2
    rgb = 3
    uhdtv = 4


@ref_enum
class PresetTransferFunctions(IntEnum):
    """
    (11.4.10.4) Transfer functions from (Table 11.9). Names are informative and
    are based on those in the table.
    
    See also: :py:data:`~.tables.PRESET_TRANSFER_FUNCTIONS`.
    """
    tv_gamma = 0
    extended_gamut = 1
    linear = 2
    d_cinema_transfer_function = 3
    perceptual_quality = 4
    hybrid_log_gamma = 5


@ref_enum
class PresetColorSpecs(IntEnum):
    """
    (11.4.10.1) Preset color specification collections from (Table 11.6). Names
    are informative and based on those in the table.
    
    See also: :py:data:`~.tables.PRESET_COLOR_SPECS`.
    """
    custom = 0
    sdtv_525 = 1
    sdtv_625 = 2
    hdtv = 3
    d_cinema = 4
    uhdtv = 5
    hdr_tv_pq = 6
    hdr_tv_hlg = 7


@ref_enum
class LiftingFilterTypes(IntEnum):
    """
    (15.4.4.1) Indices of lifting filter step types. Names are informative and
    based on an interpretation of the pseudo-code in the specification.
    """
    even_add_odd = 1
    even_subtract_odd = 2
    odd_add_even = 3
    odd_subtract_even = 4


@ref_enum
class WaveletFilters(IntEnum):
    """
    (12.4.2) Wavelet filter types supported by VC-2 using the indices
    normitively specified in  in (Table 12.1). Names are based on the
    informative names in the table.
    
    See also: :py:data:`~.tables.LIFTING_FILTERS`.
    """
    
    deslauriers_dubuc_9_7 = 0
    le_gall_5_3 = 1
    deslauriers_dubuc_13_7 = 2
    haar_no_shift = 3
    haar_with_shift = 4
    fidelity = 5
    daubechies_9_7 = 6
