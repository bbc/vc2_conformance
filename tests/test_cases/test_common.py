import pytest

from io import BytesIO

from enum import IntEnum

from vc2_conformance import bitstream
from vc2_conformance import tables
from vc2_conformance import decoder

from vc2_conformance.arrays import width, height

from vc2_conformance.state import State

from vc2_conformance.test_cases.common import (
    TINY_VIDEO_OPTIONS,
    get_base_video_format_satisfying,
    get_base_video_format_with,
    get_base_video_format_without,
    get_illigal_enum_values,
)


@pytest.mark.parametrize("base_video_format", tables.BaseVideoFormats)
def test_tiny_video_options(base_video_format):
    # Check that the resulting bitstream is always valid and contains 8x4,
    # 8-bit, 4:4:4 pictures regardless of the base video format.
    seq = bitstream.Sequence(data_units=[
        bitstream.DataUnit(
            parse_info=bitstream.ParseInfo(
                parse_code=tables.ParseCodes.sequence_header,
            ),
            sequence_header=bitstream.SequenceHeader(
                base_video_format=base_video_format,
                video_parameters=bitstream.SourceParameters(TINY_VIDEO_OPTIONS),
            ),
        ),
        bitstream.DataUnit(
            parse_info=bitstream.ParseInfo(
                parse_code=tables.ParseCodes.high_quality_picture,
            ),
        ),
        bitstream.DataUnit(
            parse_info=bitstream.ParseInfo(
                parse_code=tables.ParseCodes.end_of_sequence,
            ),
        ),
    ])
    
    # Seriallise the sample bitstream
    f = BytesIO()
    bitstream.autofill_and_serialise_sequence(f, seq)
    f.seek(0)
    
    # Decode (and validate) the bitstream
    pictures = []
    state = State(
        _output_picture_callback=lambda pic, params: pictures.append(pic),
    )
    decoder.init_io(state, f)
    decoder.parse_sequence(state)
    
    # Check decoded picture has correct size and depth
    assert len(pictures) == 1
    picture = pictures[0]
    
    assert width(picture["Y"]) == 8
    assert height(picture["Y"]) == 4
    
    assert width(picture["C1"]) == 8
    assert height(picture["C1"]) == 4
    
    assert width(picture["C2"]) == 8
    assert height(picture["C2"]) == 4
    
    assert all(
        pixel == 128
        for component in ["Y", "C1", "C2"]
        for row in picture[component]
        for pixel in row
    )


class TestGetBaseVideoFormatSatisfying(object):
    
    def test_match(self):
        format = tables.BaseVideoFormats.cif
        params = tables.BASE_VIDEO_FORMAT_PARAMETERS[format]
        assert get_base_video_format_satisfying(lambda p: p == params) == format
    
    def test_no_match(self):
        with pytest.raises(ValueError):
            get_base_video_format_satisfying(lambda p: False)


def test_get_base_video_format_with():
    format = get_base_video_format_with("frame_height", 1080)
    params = tables.BASE_VIDEO_FORMAT_PARAMETERS[format]
    assert params.frame_height == 1080


def test_get_base_video_format_without():
    format = get_base_video_format_without("frame_height", 1080)
    params = tables.BASE_VIDEO_FORMAT_PARAMETERS[format]
    assert params.frame_height != 1080


class TestGetIlligalEnumValues(object):
    
    class MyEnum(IntEnum):
        a = -2
        b = -1
        # Gap (0)
        d = 1
        # Gap (2)
        e = 3
        f = 4
    
    def test_works_when_unrestricted(self):
        assert get_illigal_enum_values(self.MyEnum, non_negative=False, non_zero=False) == [-3, 0, 2, 5]
    
    def test_omits_zeros_if_required(self):
        assert get_illigal_enum_values(self.MyEnum, non_negative=False, non_zero=True) == [-3, 2, 5]
    
    def test_omits_negatives_if_required(self):
        assert get_illigal_enum_values(self.MyEnum, non_negative=True, non_zero=False) == [0, 2, 5]
