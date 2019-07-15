import pytest

from copy import deepcopy

from io import BytesIO

from vc2_conformance import tables

from vc2_conformance.state import State

from vc2_conformance.bitstream import vc2

from vc2_conformance.bitstream import (
    vc2_default_values,
    vc2_default_values_with_auto,
    AUTO,
    autofill_picture_number,
    autofill_parse_offsets,
    autofill_parse_offsets_finalize,
    autofill_and_serialise_sequence,
    Sequence,
    DataUnit,
    ParseInfo,
    PictureParse,
    PictureHeader,
    FragmentParse,
    FragmentHeader,
    Padding,
    AuxiliaryData,
    SequenceHeader,
    SourceParameters,
    FrameSize,
    BitstreamReader,
    BitstreamWriter,
    Serialiser,
    Deserialiser
)

class TestAutofillPictureNumber(object):
    
    @pytest.mark.parametrize("seq", [
        # Empty dictionary
        Sequence(),
        # Empty sequence
        Sequence(data_units=[]),
        # Sequence with immediate end-of-sequence
        Sequence(data_units=[DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.end_of_sequence),
        )]),
        # Sequence with no pictures
        Sequence(data_units=[
            DataUnit(parse_info=ParseInfo(parse_code=tables.ParseCodes.sequence_header)),
            DataUnit(parse_info=ParseInfo(parse_code=tables.ParseCodes.padding_data)),
            DataUnit(parse_info=ParseInfo(parse_code=tables.ParseCodes.auxiliary_data)),
            DataUnit(parse_info=ParseInfo(parse_code=tables.ParseCodes.end_of_sequence)),
        ]),
    ])
    def test_non_picture_sequence(self, seq):
        # Shouldn't crash or make any changes
        seq_orig = deepcopy(seq)
        autofill_picture_number(seq)
        assert seq == seq_orig
    
    @pytest.mark.parametrize("seq", (
        [
            # Pictures
            Sequence(data_units=[DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                picture_parse=PictureParse(
                    picture_header=PictureHeader(
                        picture_number=1234,
                    )
                ),
            )])
            for parse_code in [
                tables.ParseCodes.high_quality_picture,
                tables.ParseCodes.low_delay_picture,
            ]
        ] + [
            # Fragments
            Sequence(data_units=[DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        picture_number=1234,
                        fragment_slice_count=fragment_slice_count,
                    )
                ),
            )])
            for parse_code in [
                tables.ParseCodes.high_quality_picture_fragment,
                tables.ParseCodes.low_delay_picture_fragment,
            ]
            for fragment_slice_count in [0, 1]
        ]
    ))
    def test_dont_change_non_auto_picture_numbers(self, seq):
        # Shouldn't crash or make any changes
        seq_orig = deepcopy(seq)
        autofill_picture_number(seq)
        assert seq == seq_orig
    
    @pytest.mark.parametrize("parse_code", [
        tables.ParseCodes.high_quality_picture,
        tables.ParseCodes.low_delay_picture,
    ])
    def test_pictures(self, parse_code):
        seq = Sequence(data_units=[
            # First in sequence should be auto-numbered to expected start
            # offset
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                picture_parse=PictureParse(
                    picture_header=PictureHeader(picture_number=AUTO)
                ),
            ),
            # If picture number not mentioned, it should be autofilled
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                picture_parse=PictureParse(
                    picture_header=PictureHeader()
                ),
            ),
            # If explicit picture number given, should be used
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                picture_parse=PictureParse(
                    picture_header=PictureHeader(picture_number=0xFFFFFFFE)
                ),
            ),
            # Should continue from last explicit number if given
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                picture_parse=PictureParse(
                    picture_header=PictureHeader(picture_number=AUTO)
                ),
            ),
            # Should wrap-around
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                picture_parse=PictureParse(
                    picture_header=PictureHeader(picture_number=AUTO)
                ),
            ),
        ])
        
        autofill_picture_number(seq, 1234)
        
        picture_numbers = [
            data_unit["picture_parse"]["picture_header"]["picture_number"]
            for data_unit in seq["data_units"]
        ]
        assert picture_numbers == [
            1234,
            1235,
            0xFFFFFFFE,
            0xFFFFFFFF,
            0x0,
        ]
    
    @pytest.mark.parametrize("parse_code", [
        tables.ParseCodes.high_quality_picture_fragment,
        tables.ParseCodes.low_delay_picture_fragment,
    ])
    def test_fragments(self, parse_code):
        seq = Sequence(data_units=[
            # First in sequence should be auto-numbered to expected start
            # offset
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        picture_number=AUTO,
                        fragment_slice_count=0,
                    )
                ),
            ),
            # If not the first fragment in the picture, the picture number
            # should not be incremented
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        picture_number=AUTO,
                        fragment_slice_count=1,
                    )
                ),
            ),
            # If picture number not mentioned, it should still be autofilled
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        fragment_slice_count=1,
                    )
                ),
            ),
            # Should auto increment on new picture started
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        picture_number=AUTO,
                        fragment_slice_count=0,
                    )
                ),
            ),
            # If explicit picture number when given, should be used
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        picture_number=4321,
                        fragment_slice_count=0,
                    )
                ),
            ),
            # ...even if that changes the picture number mid picture
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        picture_number=0xFFFFFFFE,
                        fragment_slice_count=1,
                    )
                ),
            ),
            # Should continue on from last explicit number
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        picture_number=AUTO,
                        fragment_slice_count=0,
                    )
                ),
            ),
            # Should wrap-around
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        picture_number=AUTO,
                        fragment_slice_count=0,
                    )
                ),
            ),
        ])
        
        autofill_picture_number(seq, 1234)
        
        picture_numbers = [
            data_unit["fragment_parse"]["fragment_header"]["picture_number"]
            for data_unit in seq["data_units"]
        ]
        assert picture_numbers == [
            1234,
            1234,
            1234,
            1235,
            4321,
            0xFFFFFFFE,
            0xFFFFFFFF,
            0x0,
        ]


class TestAutofillParseOffsets(object):
    
    @pytest.mark.parametrize("seq", [
        Sequence(),
        Sequence(data_units=[]),
    ])
    def test_doesnt_crash_on_empty_sequence(self, seq):
        seq_orig = deepcopy(seq)
        assert autofill_parse_offsets(seq) == ([], [])
        assert seq == seq_orig
    
    @pytest.mark.parametrize("parse_code", [
        tables.ParseCodes.padding_data,
        tables.ParseCodes.auxiliary_data,
    ])
    def test_padding_and_aux_data(self, parse_code):
        seq = Sequence(data_units=[
            # Next parse offset not given (should be treated as auto)
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
            ),
            # Next parse offset is explicitly AUTO
            DataUnit(
                parse_info=ParseInfo(
                    parse_code=parse_code,
                    next_parse_offset=AUTO,
                ),
            ),
            # Next parse offset is given (should not be modified)
            DataUnit(
                parse_info=ParseInfo(
                    parse_code=parse_code,
                    next_parse_offset=100,
                ),
            ),
        ])
        for data_unit in seq["data_units"]:
            if parse_code == tables.ParseCodes.padding_data:
                data_unit["padding"] = Padding(bytes=b"1234")
            elif parse_code == tables.ParseCodes.auxiliary_data:
                data_unit["auxiliary_data"] = AuxiliaryData(bytes=b"1234")
        
        assert autofill_parse_offsets(seq) == ([], [0, 1, 2])
        
        next_parse_offsets = [
            data_unit["parse_info"]["next_parse_offset"]
            for data_unit in seq["data_units"]
        ]
        assert next_parse_offsets == [13+4, 13+4, 100]
        
        previous_parse_offsets = [
            data_unit["parse_info"]["previous_parse_offset"]
            for data_unit in seq["data_units"]
        ]
        assert previous_parse_offsets == [0, 0, 0]
    
    @pytest.mark.parametrize("parse_code", [
        tables.ParseCodes.padding_data,
        tables.ParseCodes.auxiliary_data,
    ])
    def test_padding_and_aux_data_default_data(self, parse_code):
        # No data given (default (empty) data should be assumed)
        seq = Sequence(data_units=[
            DataUnit(parse_info=ParseInfo(parse_code=parse_code)),
        ])
        
        assert autofill_parse_offsets(seq) == ([], [0])
        
        assert seq["data_units"][0]["parse_info"]["next_parse_offset"] == 13
        assert seq["data_units"][0]["parse_info"]["previous_parse_offset"] == 0
    
    @pytest.mark.parametrize("explicit_auto", [True, False])
    @pytest.mark.parametrize("parse_code", [
        parse_code
        for parse_code in tables.ParseCodes
        if parse_code not in (
            tables.ParseCodes.padding_data,
            tables.ParseCodes.auxiliary_data,
        )
    ])
    def test_values_to_be_set_later_are_set_to_zero(self, parse_code, explicit_auto):
        seq = Sequence(data_units=[
            # An automatically set data unit
            DataUnit(parse_info=ParseInfo(
                parse_code=parse_code,
            )),
            # One which is explicitly set (and should not be overridden)
            DataUnit(parse_info=ParseInfo(
                parse_code=parse_code,
                next_parse_offset=100,
                previous_parse_offset=200,
            )),
        ])
        if explicit_auto:
            seq["data_units"][0]["parse_info"]["next_parse_offset"] = AUTO
            seq["data_units"][0]["parse_info"]["previous_parse_offset"] = AUTO
        
        assert autofill_parse_offsets(seq) == ([0], [0])
        
        assert seq["data_units"][0]["parse_info"]["next_parse_offset"] == 0
        assert seq["data_units"][0]["parse_info"]["previous_parse_offset"] == 0
        
        assert seq["data_units"][1]["parse_info"]["next_parse_offset"] == 100
        assert seq["data_units"][1]["parse_info"]["previous_parse_offset"] == 200
    
    def test_finalizer_works(self):
        f = BytesIO()
        w = BitstreamWriter(f)
        
        # Sequence with every data unit type and fully automatic numbers
        seq = Sequence(data_units=[
            DataUnit(
                parse_info=ParseInfo(parse_code=tables.ParseCodes.sequence_header),
                sequence_header=SequenceHeader(
                    video_parameters=SourceParameters(
                        # Tiny custom frame-size used to reduce test suite
                        # runtime
                        frame_size=FrameSize(
                            custom_dimensions_flag=True,
                            frame_width=4,
                            frame_height=4,
                        )
                    ),
                ),
            ),
            DataUnit(
                parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture),
                picture_parse=PictureParse(picture_header=PictureHeader(picture_number=0)),
            ),
            DataUnit(
                parse_info=ParseInfo(parse_code=tables.ParseCodes.low_delay_picture),
                picture_parse=PictureParse(picture_header=PictureHeader(picture_number=0)),
            ),
            DataUnit(
                parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture_fragment),
                fragment_parse=FragmentParse(fragment_header=FragmentHeader(picture_number=0)),
            ),
            DataUnit(
                parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture_fragment),
                fragment_parse=FragmentParse(fragment_header=FragmentHeader(picture_number=0)),
            ),
            DataUnit(
                parse_info=ParseInfo(parse_code=tables.ParseCodes.padding_data),
                padding=Padding(bytes=b"123"),
            ),
            DataUnit(
                parse_info=ParseInfo(parse_code=tables.ParseCodes.auxiliary_data),
                auxiliary_data=AuxiliaryData(bytes=b"123"),
            ),
            DataUnit(
                parse_info=ParseInfo(parse_code=tables.ParseCodes.end_of_sequence),
            ),
        ])
        
        (
            next_parse_offsets_to_autofill,
            previous_parse_offsets_to_autofill,
        ) = autofill_parse_offsets(seq)
        
        with Serialiser(w, seq, vc2_default_values_with_auto) as serdes:
            vc2.parse_sequence(serdes, State())
        w.flush()
        
        offset_before = w.tell()
        autofill_parse_offsets_finalize(
            w,
            serdes.context,
            next_parse_offsets_to_autofill,
            previous_parse_offsets_to_autofill,
        )
        assert w.tell() == w.tell()
        
        f.seek(0)
        r = BitstreamReader(f)
        with Deserialiser(r) as serdes:
            vc2.parse_sequence(serdes, State())
        
        parse_infos = [
            data_unit["parse_info"]
            for data_unit in serdes.context["data_units"]
        ]
        
        # Check for start/end offsets being zero
        assert parse_infos[0]["previous_parse_offset"] == 0
        assert parse_infos[-1]["next_parse_offset"] == 0
        
        # Check for consistency and plusibility of offsets
        for pi1, pi2 in zip(parse_infos, parse_infos[1:]):
            assert pi1["next_parse_offset"] > 13
            assert pi2["previous_parse_offset"] > 13
            
            assert pi1["next_parse_offset"] == pi2["previous_parse_offset"]


def test_autofill_and_serialise_sequence():
    f = BytesIO()
    
    # Sequence with every data unit type and fully automatic numbers
    seq = Sequence(data_units=[
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.sequence_header),
            sequence_header=SequenceHeader(
                video_parameters=SourceParameters(
                    # Tiny custom frame-size used to reduce test suite runtime
                    frame_size=FrameSize(
                        custom_dimensions_flag=True,
                        frame_width=4,
                        frame_height=4,
                    )
                ),
            ),
        ),
        # Pictures
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.low_delay_picture),
        ),
        # High quality fragment
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture_fragment),
            fragment_parse=FragmentParse(fragment_header=FragmentHeader(fragment_slice_count=0)),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture_fragment),
            fragment_parse=FragmentParse(fragment_header=FragmentHeader(fragment_slice_count=1)),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture_fragment),
            fragment_parse=FragmentParse(fragment_header=FragmentHeader(fragment_slice_count=1)),
        ),
        # Low delay fragment
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture_fragment),
            fragment_parse=FragmentParse(fragment_header=FragmentHeader(fragment_slice_count=0)),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture_fragment),
            fragment_parse=FragmentParse(fragment_header=FragmentHeader(fragment_slice_count=1)),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.high_quality_picture_fragment),
            fragment_parse=FragmentParse(fragment_header=FragmentHeader(fragment_slice_count=1)),
        ),
        # Other types
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.padding_data),
            padding=Padding(bytes=b"123"),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.auxiliary_data),
            auxiliary_data=AuxiliaryData(bytes=b"123"),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=tables.ParseCodes.end_of_sequence),
        ),
    ])
    
    autofill_and_serialise_sequence(f, seq)
    
    f.seek(0)
    r = BitstreamReader(f)
    with Deserialiser(r) as serdes:
        vc2.parse_sequence(serdes, State())
    
    parse_infos = [
        data_unit["parse_info"]
        for data_unit in serdes.context["data_units"]
    ]
    
    # Check for start/end offsets being zero
    assert parse_infos[0]["previous_parse_offset"] == 0
    assert parse_infos[-1]["next_parse_offset"] == 0
    
    # Check for consistency and plusibility of offsets
    for pi1, pi2 in zip(parse_infos, parse_infos[1:]):
        assert pi1["next_parse_offset"] > 13
        assert pi2["previous_parse_offset"] > 13
        
        assert pi1["next_parse_offset"] == pi2["previous_parse_offset"]
    
    # Check picture numbers
    picture_numbers = [
        (
            data_unit.get("picture_parse", {}).get("picture_header", {}) or
            data_unit.get("fragment_parse", {}).get("fragment_header", {})
        ).get("picture_number")
        for data_unit in serdes.context["data_units"]
    ]
    assert picture_numbers == [
        None,
        0,
        1,
        2,
        2,
        2,
        3,
        3,
        3,
        None,
        None,
        None,
    ]
