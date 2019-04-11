"""
Constants defined by the VC-2 specification.
"""

from enum import IntEnum


__all__ = [
    "PARSE_INFO_PREFIX",
    "PARSE_INFO_HEADER_BYTES",
    "ParseCodes",
    "PictureCodingModes",
    "ColorDifferenceSamplingFormats",
    "SourceSamplingModes",
    "BaseVideoFormats",
    "Profiles",
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

PARSE_INFO_PREFIX = 0x42424344
"""
(10.5.1) The 'magic bytes' used to identify the start of a parse info header.
'BBCD' in ASCII.
"""

PARSE_INFO_HEADER_BYTES = 13
"""(15.5.1) The number of bytes in the parse_info header."""


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


class PictureCodingModes(IntEnum):
    """(11.5) Indices defined in the text. Names are not normative."""
    pictures_are_frames = 0
    pictures_are_fields = 1

class ColorDifferenceSamplingFormats(IntEnum):
    """(11.4.4) Indices from (Table 11.2)"""
    
    color_4_4_4 = 0
    color_4_2_2 = 1
    color_4_2_0 = 2


class SourceSamplingModes(IntEnum):
    """(11.4.5) Indices defined in the text. Names are not normative."""
    progressive = 0
    interlaced = 1


class BaseVideoFormats(IntEnum):
    """
    (11.3) Base video format indices from (Table 11.1). Names based on the
    normative values in this table.
    
    See also: :py:data:`BASE_VIDEO_FORMAT_PARAMETERS`.
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


class Profiles(IntEnum):
    """
    (C.2) VC-2 Profiles.
    
    See also: :py:data:`PROFILES`.
    """
    low_delay = 0
    high_quality = 3


class PresetFrameRates(IntEnum):
    """
    (11.4.6) Preset framerate indices from (Table 11.1). Names are informative.
    
    See also: :py:data:`PRESET_FRAME_RATES`.
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

class PresetPixelAspectRatios(IntEnum):
    """
    (11.4.7) Pixel aspect ratio preset indices from (Table 11.4). Names are
    informative.
    
    See also: :py:data:`PRESET_PIXEL_ASPECT_RATIOS`.
    """
    ratio_1_1 = 1
    ratio_4_3_525_line = 2  # 4:3 525 line systems
    ratio_4_3_625_line = 3  # 4:3 625 line systems
    ratio_16_9_525_line = 4  # 16:9 525 line systems
    ratio_16_9_625_line = 5  # 16:9 625 line systems
    ratio_4_3 = 6  # reduced horizontal resolution systems


class PresetSignalRanges(IntEnum):
    """
    (11.4.9) Signal offsets/ranges preset indices from (Table 11.5). Names are
    informative and based on those in the table.
    
    See also: :py:data:`PRESET_SIGNAL_RANGES`.
    """
    range_8_bit_full_range = 1
    range_8_bit_video = 2
    range_10_bit_video = 3
    range_12_bit_video = 4
    range_10_bit_full_range = 5
    range_12_bit_full_range = 6
    range_16_bit_video = 7
    range_16_bit_full_range = 8


class PresetColorPrimaries(IntEnum):
    """
    (11.4.10.2) Color primaries from (Table 11.7). Names and comments are
    informative and based on those in the table.
    
    See also: :py:data:`PRESET_COLOR_PRIMARIES`.
    """
    hdtv = 0  # Also Computer, Web, sRGB
    sdtv_525 = 1  # 525 Primaries
    sdtv_625 = 2  # 625 Primaries
    d_cinema = 3  # CIE XYZ
    uhdtv = 4  # Used in UHDTV and HDR


class PresetColorMatrices(IntEnum):
    """
    (11.4.10.3) Color primaries from (Table 11.8). Names and comments are
    informative and based on those in the table.
    
    See also: :py:data:`PRESET_COLOR_MATRICES`.
    """
    hdtv = 0  # Also Computer and Web
    sdtv = 1
    reversible = 2
    rgb = 3
    uhdtv = 4


class PresetTransferFunctions(IntEnum):
    """
    (11.4.10.4) Transfer functions from (Table 11.9). Names are informative and
    are based on those in the table.
    
    See also: :py:data:`PRESET_TRANSFER_FUNCTIONS`.
    """
    tv_gamma = 0
    extended_gamut = 1
    linear = 2
    d_cinema_transfer_function = 3
    perceptual_quality = 4
    hybrid_log_gamma = 5


class PresetColorSpecs(IntEnum):
    """
    (11.4.10.1) Preset color specification collections from (Table 11.6). Names
    are informative and based on those in the table.
    
    See also: :py:data:`PRESET_COLOR_SPECS`.
    """
    custom = 0
    sdtv_525 = 1
    sdtv_625 = 2
    hdtv = 3
    d_cinema = 4
    uhdtv = 5
    hdr_tv_pq = 6
    hdr_tv_hlg = 7


class LiftingFilterTypes(IntEnum):
    """
    (15.4.4.1) Indices of lifting filter step types. Names are informative and
    based on an interpretation of the pseudo-code in the specification.
    """
    even_add_odd = 1
    even_subtract_odd = 2
    odd_add_even = 3
    odd_subtract_even = 4


class WaveletFilters(IntEnum):
    """
    (12.4.2) Wavelet filter types supported by VC-2 using the indices
    normitively specified in  in (Table 12.1). Names are based on the
    informative names in the table.
    
    See also: :py:data:`LIFTING_FILTERS`.
    """
    
    deslauriers_dubuc_9_7 = 0
    le_gall_5_3 = 1
    deslauriers_dubuc_13_7 = 2
    haar_no_shift = 3
    haar_with_shift = 4
    fidelity = 5
    daubechies_9_7 = 6
