"""
Tables of values defined in the VC-2 spec.
"""

from attr import attrs, attrib

from vc2_conformance.tables.constants import (
    BaseVideoFormats,
    ParseCodes,
    Profiles,
)

__all__ = [
    "BaseVideoFormatParameters",
    "BASE_VIDEO_FORMAT_PARAMETERS",
    "ProfileParameters",
    "PROFILES",
]


@attrs
class BaseVideoFormatParameters(object):
    """(B) An entry in (Table B.1a, B.1b or B.1c)"""
    
    frame_width = attrib()
    frame_height = attrib()
    
    color_diff_format_index = attrib()
    """
    An entry from the enum ColorDifferenceSamplingFormats. Listed as 'color
    difference sampling' in (Table B.1).
    """
    
    source_sampling = attrib()
    """
    An entry from the enum SourceSamplingModes. Specifies progressive or interlaced.
    """
    
    top_field_first = attrib()
    """If True, the top-line of the frame is in the first field."""
    
    frame_rate_index = attrib()
    """The frame rate, one of the indices of PRESET_FRAME_RATES."""
    
    pixel_aspect_ratio_index = attrib()
    """The pixel aspect ratio, one of the indices of PRESET_PIXEL_ASPECT_RATIOS."""
    
    clean_width = attrib()
    clean_height = attrib()
    left_offset = attrib()
    top_offset = attrib()
    """See (11.4.8) and (E.4.2)."""
    
    signal_range_index = attrib()
    """The signal ranges, one of the indices of PRESET_SIGNAL_RANGES."""
    
    color_spec_index = attrib()
    """The color specification, one of the indices of PRESET_COLOR_SPECS."""


BASE_VIDEO_FORMAT_PARAMETERS = {
    #                name
    #                |                                        frame_width
    #                |                                        |     frame_height
    #                |                                        |     |     color_diff_format_index
    #                |                                        |     |     |  source_sampling
    #                |                                        |     |     |  |  top_field_first
    #                |                                        |     |     |  |  |       frame_rate_index
    #                |                                        |     |     |  |  |       |   pixel_aspect_ratio_index
    #                |                                        |     |     |  |  |       |   |  clean_width
    #                |                                        |     |     |  |  |       |   |  |     clean_height
    #                |                                        |     |     |  |  |       |   |  |     |     left_offset
    #                |                                        |     |     |  |  |       |   |  |     |     |  top_offset
    #                |                                        |     |     |  |  |       |   |  |     |     |  |  signal_range_index
    #                |                                        |     |     |  |  |       |   |  |     |     |  |  |  color_spec_index
    #                |                                        |     |     |  |  |       |   |  |     |     |  |  |  |
    BaseVideoFormats.custom_format: BaseVideoFormatParameters(640,  480,  2, 0, False,  1,  1, 640,  480,  0, 0, 1, 0),
    BaseVideoFormats.qsif525:       BaseVideoFormatParameters(176,  120,  2, 0, False,  9,  2, 176,  120,  0, 0, 1, 1),
    BaseVideoFormats.qcif:          BaseVideoFormatParameters(176,  144,  2, 0, True,   10, 3, 176,  144,  0, 0, 1, 2),
    BaseVideoFormats.sif525:        BaseVideoFormatParameters(352,  240,  2, 0, False,  9,  2, 352,  240,  0, 0, 1, 1),
    BaseVideoFormats.cif:           BaseVideoFormatParameters(352,  288,  2, 0, True,   10, 3, 352,  288,  0, 0, 1, 2),
    BaseVideoFormats._4sif525:      BaseVideoFormatParameters(704,  480,  2, 0, False,  9,  2, 704,  480,  0, 0, 1, 1),
    BaseVideoFormats._4cif:         BaseVideoFormatParameters(704,  576,  2, 0, True,   10, 3, 704,  576,  0, 0, 1, 2),
    BaseVideoFormats.sd480i_60:     BaseVideoFormatParameters(720,  480,  1, 1, False,  4,  2, 704,  480,  8, 0, 3, 1),
    BaseVideoFormats.sd576i_50:     BaseVideoFormatParameters(720,  576,  1, 1, True,   3,  3, 704,  576,  8, 0, 3, 2),
    BaseVideoFormats.hd720p_60:     BaseVideoFormatParameters(1280, 720,  1, 0, True,   7,  1, 1280, 720,  0, 0, 3, 3),
    BaseVideoFormats.hd720p_50:     BaseVideoFormatParameters(1280, 720,  1, 0, True,   6,  1, 1280, 720,  0, 0, 3, 3),
    BaseVideoFormats.hd1080i_60:    BaseVideoFormatParameters(1920, 1080, 1, 1, True,   4,  1, 1920, 1080, 0, 0, 3, 3),
    BaseVideoFormats.hd1080i_50:    BaseVideoFormatParameters(1920, 1080, 1, 1, True,   3,  1, 1920, 1080, 0, 0, 3, 3),
    BaseVideoFormats.hd1080p_60:    BaseVideoFormatParameters(1920, 1080, 1, 0, True,   7,  1, 1920, 1080, 0, 0, 3, 3),
    BaseVideoFormats.hd1080p_50:    BaseVideoFormatParameters(1920, 1080, 1, 0, True,   6,  1, 1920, 1080, 0, 0, 3, 3),
    BaseVideoFormats.dc2k:          BaseVideoFormatParameters(2048, 1080, 0, 0, True,   2,  1, 2048, 1080, 0, 0, 4, 4),
    BaseVideoFormats.dc4k:          BaseVideoFormatParameters(4096, 2160, 0, 0, True,   2,  1, 4096, 2160, 0, 0, 4, 4),
    BaseVideoFormats.uhdtv_4k_60:   BaseVideoFormatParameters(3840, 2160, 1, 0, True,   7,  1, 3840, 2160, 0, 0, 3, 5),
    BaseVideoFormats.uhdtv_4k_50:   BaseVideoFormatParameters(3840, 2160, 1, 0, True,   6,  1, 3840, 2160, 0, 0, 3, 5),
    BaseVideoFormats.uhdtv_8k_60:   BaseVideoFormatParameters(7680, 4320, 1, 0, True,   7,  1, 7680, 4320, 0, 0, 3, 5),
    BaseVideoFormats.uhdtv_8k_50:   BaseVideoFormatParameters(7680, 4320, 1, 0, True,   6,  1, 7680, 4320, 0, 0, 3, 5),
    BaseVideoFormats.hd1080p_24:    BaseVideoFormatParameters(1920, 1080, 1, 0, True,   1,  1, 1920, 1080, 0, 0, 3, 3),
    BaseVideoFormats.sd_pro486:     BaseVideoFormatParameters(720,  486,  1, 1, False,  4,  2, 720,  486,  0, 0, 3, 3),
}
"""
(B) Base video format specifications from (Table B.1a, B.1b, B.1c), indexed by
:py:class:`BaseVideoFormats`.
"""

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
