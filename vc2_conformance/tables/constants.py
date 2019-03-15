"""
Constants defined by the VC-2 specification.
"""

from enum import Enum


__all__ = [
    "PARSE_INFO_PREFIX",
    "ParseCodes",
    "PictureCodingModes",
    "ColorDifferenceSamplingFormats",
    "SourceSamplingModes",
    "BaseVideoFormats",
    "Profiles",
]

PARSE_INFO_PREFIX = 0x42424344
"""
(10.5.1) The 'magic bytes' used to identify the start of a parse info header.
'BBCD' in ASCII.
"""


class ParseCodes(Enum):
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


class PictureCodingModes(Enum):
    """(11.5) Indices defined in the text. Names are not normative."""
    pictures_are_frames = 0
    pictures_are_fields = 1

class ColorDifferenceSamplingFormats(Enum):
    """(11.4.4) Indices from (Table 11.2)"""
    
    color_4_4_4 = 0
    color_4_2_2 = 1
    color_4_2_0 = 2


class SourceSamplingModes(Enum):
    """(11.4.5) Indices defined in the text. Names are not normative."""
    progressive = 0
    interlaced = 1


class BaseVideoFormats(Enum):
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


class Profiles(Enum):
    """
    (C.2) VC-2 Profiles.
    
    See also: :py:data:`PROFILES`.
    """
    low_delay = 0
    high_quality = 3
