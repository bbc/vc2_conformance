r"""
:py:class:`BitstreamValue`\ s for each of VC-2 bitstream structures.
"""

from vc2_conformance.bitstream import (
    LabelledConcatenation,
    NBits,
    EnumValue,
    UInt,
)

from vc2_conformance.bitstream.formatters import Hex

from vc2_conformance.tables import (
    PARSE_INFO_PREFIX,
    ParseCodes,
    PictureCodingModes,
    BaseVideoFormats,
    Profiles,
)


__all__ = [
    "ParseInfo",
]


class ParseInfo(LabelledConcatenation):
    """
    (10.5.1) Parse info header defined by ``parse_info()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"parse_info_prefix"`` (:py:class:`NBits`)
    * ``"parse_code"`` (:py:class:`EnumValue` on :py:class:`ParseCodes`)
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
                EnumValue(
                    NBits(length=8, formatter=Hex(2)),
                    ParseCodes,
                    value=parse_code
                ),
            ),
            ("next_parse_offset", NBits(next_parse_offset, 32)),
            ("previous_parse_offset", NBits(previous_parse_offset, 32)),
        )

class SequenceHeader(LabelledConcatenation):
    """
    (11.1) Sequence header defined by ``sequence_header()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"parse_parameters"`` (:py:class:`ParseParameters`)
    * ``"base_video_format"`` (:py:class:`EnumValue` of
      :py:class:`BaseVideoFormats`)
    * ``"video_parameters"`` (:py:class:`SourceParameters`)
    * ``"picture_coding_mode"`` (:py:class:`EnumValue` on
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
                EnumValue(
                    UInt(),
                    BaseVideoFormats,
                    value=base_video_format,
                ),
            ),
            ("video_parameters", SourceParameters()),
            (
                "picture_coding_mode",
                EnumValue(
                    UInt(),
                    PictureCodingModes,
                    value=picture_coding_mode,
                ),
            ),
        )

class ParseParameters(LabelledConcatenation):
    """
    (11.2.1) Sequence header defined by ``parse_parameters()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"major_version"`` (:py:class:`UInt`)
    * ``"minor_version"`` (:py:class:`UInt`)
    * ``"profile"`` (:py:class:`EnumValue` on :py:class:`Profiles`)
    * ``"level"`` (:py:class:`UInt`)
    """
    
    def __init__(self,
                 major_version=3,
                 minor_version=0,
                 profile=Profiles.high_quality,
                 level=0):
        super(ParseInfo, self).__init__(
            "parse_parameters:",
            ("major_version", UInt(major_version)),
            ("minor_version", UInt(minor_version)),
            ("profile", EnumValue(UInt(), Profiles, value=profile)),
            ("level", UInt(level)),
        )
