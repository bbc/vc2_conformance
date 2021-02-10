import pytest

from copy import deepcopy

from io import BytesIO

import vc2_data_tables as tables

from vc2_conformance.pseudocode.state import State

from vc2_conformance.bitstream import vc2

from vc2_conformance.bitstream import (
    vc2_default_values_with_auto,
    AUTO,
    autofill_picture_number,
    autofill_major_version,
    autofill_parse_offsets,
    autofill_parse_offsets_finalize,
    autofill_and_serialise_stream,
    Stream,
    Sequence,
    DataUnit,
    ParseInfo,
    ParseParameters,
    PictureParse,
    PictureHeader,
    FragmentParse,
    FragmentHeader,
    Padding,
    AuxiliaryData,
    SequenceHeader,
    WaveletTransform,
    TransformParameters,
    ExtendedTransformParameters,
    SourceParameters,
    FrameSize,
    FrameRate,
    SignalRange,
    ColorSpec,
    ColorPrimaries,
    ColorMatrix,
    TransferFunction,
    BitstreamReader,
    BitstreamWriter,
    Serialiser,
    Deserialiser,
)

from vc2_conformance.bitstream.vc2_autofill import (
    get_auto,
    get_transform_parameters,
)


class TestGetAuto(object):
    def test_has_value_already(self):
        assert (
            get_auto(
                ParseParameters(major_version=99),
                "major_version",
                ParseParameters,
            )
            == 99
        )

    def test_fallback_on_autofill(self):
        assert (
            get_auto(
                ParseParameters(),
                "major_version",
                ParseParameters,
            )
            is AUTO
        )


class TestGetTransformParameters(object):
    @pytest.mark.parametrize(
        "data_unit",
        [
            # Non-picture containing data units
            DataUnit(parse_info=ParseInfo(parse_code=parse_code))
            for parse_code in [
                tables.ParseCodes.sequence_header,
                tables.ParseCodes.end_of_sequence,
                tables.ParseCodes.auxiliary_data,
                tables.ParseCodes.padding_data,
            ]
        ]
        + [
            # Non-first fragments
            DataUnit(
                parse_info=ParseInfo(parse_code=parse_code),
                fragment_parse=FragmentParse(
                    fragment_header=FragmentHeader(
                        fragment_slice_count=1,
                    )
                ),
            )
            for parse_code in [
                tables.ParseCodes.low_delay_picture_fragment,
                tables.ParseCodes.high_quality_picture_fragment,
            ]
        ],
    )
    def test_non_picture_or_first_fragment(self, data_unit):
        assert get_transform_parameters(data_unit) is None

    @pytest.mark.parametrize(
        "parse_code",
        [
            tables.ParseCodes.low_delay_picture,
            tables.ParseCodes.high_quality_picture,
        ],
    )
    @pytest.mark.parametrize(
        "existing_tp",
        [
            {},
            TransformParameters(),
        ],
    )
    def test_picture_tp_already_exists(self, parse_code, existing_tp):
        data_unit = DataUnit(
            parse_info=ParseInfo(parse_code=parse_code),
            picture_parse=PictureParse(
                wavelet_transform=WaveletTransform(
                    transform_parameters=existing_tp,
                ),
            ),
        )
        assert get_transform_parameters(data_unit) is existing_tp

    @pytest.mark.parametrize(
        "parse_code",
        [
            tables.ParseCodes.low_delay_picture,
            tables.ParseCodes.high_quality_picture,
        ],
    )
    def test_picture_tp_created(self, parse_code):
        data_unit = DataUnit(
            parse_info=ParseInfo(parse_code=parse_code),
        )
        tp = get_transform_parameters(data_unit)
        assert tp == TransformParameters()
        tp["dwt_depth"] = 4

        # Transform parameters (and parent structures) created
        assert data_unit == DataUnit(
            parse_info=ParseInfo(parse_code=parse_code),
            picture_parse=PictureParse(
                wavelet_transform=WaveletTransform(
                    transform_parameters=TransformParameters(
                        dwt_depth=4,
                    ),
                ),
            ),
        )

    @pytest.mark.parametrize(
        "parse_code",
        [
            tables.ParseCodes.low_delay_picture_fragment,
            tables.ParseCodes.high_quality_picture_fragment,
        ],
    )
    @pytest.mark.parametrize(
        "existing_tp",
        [
            {},
            TransformParameters(),
        ],
    )
    def test_fragment_tp_already_exists(self, parse_code, existing_tp):
        data_unit = DataUnit(
            parse_info=ParseInfo(parse_code=parse_code),
            fragment_parse=FragmentParse(
                fragment_header=FragmentHeader(
                    fragment_slice_count=0,
                ),
                transform_parameters=existing_tp,
            ),
        )
        assert get_transform_parameters(data_unit) is existing_tp

    @pytest.mark.parametrize(
        "parse_code",
        [
            tables.ParseCodes.low_delay_picture_fragment,
            tables.ParseCodes.high_quality_picture_fragment,
        ],
    )
    def test_fragment_tp_created(self, parse_code):
        data_unit = DataUnit(
            parse_info=ParseInfo(parse_code=parse_code),
        )
        tp = get_transform_parameters(data_unit)
        assert tp == TransformParameters()
        tp["dwt_depth"] = 4

        # Transform parameters (and parent structures) created
        assert data_unit == DataUnit(
            parse_info=ParseInfo(parse_code=parse_code),
            fragment_parse=FragmentParse(
                transform_parameters=TransformParameters(
                    dwt_depth=4,
                ),
            ),
        )


class TestAutofillPictureNumber(object):
    @pytest.mark.parametrize(
        "seq",
        [
            # Empty dictionary
            Sequence(),
            # Empty sequence
            Sequence(data_units=[]),
            # Sequence with immediate end-of-sequence
            Sequence(
                data_units=[
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.end_of_sequence
                        ),
                    )
                ]
            ),
            # Sequence with no pictures
            Sequence(
                data_units=[
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.sequence_header
                        )
                    ),
                    DataUnit(
                        parse_info=ParseInfo(parse_code=tables.ParseCodes.padding_data)
                    ),
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.auxiliary_data
                        )
                    ),
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.end_of_sequence
                        )
                    ),
                ]
            ),
        ],
    )
    def test_non_picture_sequence(self, seq):
        # Shouldn't crash or make any changes
        stream = Stream(sequences=[seq])
        stream_orig = deepcopy(stream)
        autofill_picture_number(stream)
        assert stream == stream_orig

    @pytest.mark.parametrize(
        "seq",
        (
            [
                # Pictures
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(parse_code=parse_code),
                            picture_parse=PictureParse(
                                picture_header=PictureHeader(
                                    picture_number=1234,
                                )
                            ),
                        )
                    ]
                )
                for parse_code in [
                    tables.ParseCodes.high_quality_picture,
                    tables.ParseCodes.low_delay_picture,
                ]
            ]
            + [
                # Fragments
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(parse_code=parse_code),
                            fragment_parse=FragmentParse(
                                fragment_header=FragmentHeader(
                                    picture_number=1234,
                                    fragment_slice_count=fragment_slice_count,
                                )
                            ),
                        )
                    ]
                )
                for parse_code in [
                    tables.ParseCodes.high_quality_picture_fragment,
                    tables.ParseCodes.low_delay_picture_fragment,
                ]
                for fragment_slice_count in [0, 1]
            ]
        ),
    )
    def test_dont_change_non_auto_picture_numbers(self, seq):
        # Shouldn't crash or make any changes
        stream = Stream(sequences=[seq])
        stream_orig = deepcopy(stream)
        autofill_picture_number(stream)
        assert stream == stream_orig

    @pytest.mark.parametrize(
        "parse_code",
        [tables.ParseCodes.high_quality_picture, tables.ParseCodes.low_delay_picture],
    )
    def test_pictures(self, parse_code):
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
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
                            picture_parse=PictureParse(picture_header=PictureHeader()),
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
                    ]
                )
            ]
        )

        autofill_picture_number(stream, 1234)

        picture_numbers = [
            data_unit["picture_parse"]["picture_header"]["picture_number"]
            for seq in stream["sequences"]
            for data_unit in seq["data_units"]
        ]
        assert picture_numbers == [
            1234,
            1235,
            0xFFFFFFFE,
            0xFFFFFFFF,
            0x0,
        ]

    @pytest.mark.parametrize(
        "parse_code",
        [
            tables.ParseCodes.high_quality_picture_fragment,
            tables.ParseCodes.low_delay_picture_fragment,
        ],
    )
    def test_fragments(self, parse_code):
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
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
                    ]
                )
            ]
        )

        autofill_picture_number(stream, 1234)

        picture_numbers = [
            data_unit["fragment_parse"]["fragment_header"]["picture_number"]
            for seq in stream["sequences"]
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

    @pytest.mark.parametrize(
        "parse_code",
        [tables.ParseCodes.high_quality_picture, tables.ParseCodes.low_delay_picture],
    )
    def test_multiple_sequences(self, parse_code):
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(parse_info=ParseInfo(parse_code=parse_code)),
                        DataUnit(parse_info=ParseInfo(parse_code=parse_code)),
                        DataUnit(parse_info=ParseInfo(parse_code=parse_code)),
                    ]
                ),
                Sequence(
                    data_units=[
                        DataUnit(parse_info=ParseInfo(parse_code=parse_code)),
                        DataUnit(parse_info=ParseInfo(parse_code=parse_code)),
                        DataUnit(parse_info=ParseInfo(parse_code=parse_code)),
                    ]
                ),
            ]
        )

        autofill_picture_number(stream, 1234)

        picture_numbers = [
            data_unit["picture_parse"]["picture_header"]["picture_number"]
            for seq in stream["sequences"]
            for data_unit in seq["data_units"]
        ]
        assert picture_numbers == [
            1234,
            1235,
            1236,
            # Restarts in second sequence
            1234,
            1235,
            1236,
        ]


class TestAutofillMajorVersion(object):
    def test_empty_stream_unmodified(self):
        s = {}
        autofill_major_version(s)
        assert s == {}

    def test_minimal_sequence_unmodified(self):
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.end_of_sequence
                            )
                        )
                    ]
                )
            ]
        )
        stream_orig = deepcopy(stream)
        autofill_major_version(stream)
        assert stream == stream_orig

    def test_manual_version_numbers_unaltered(self):
        # The following stream includes a (conflicting) major version of 2 and
        # defined extended transform parameters. Because the major version is
        # explicit, the auto filler should just ignore the conflicting
        # version/ETP.
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.sequence_header
                            ),
                            sequence_header=SequenceHeader(
                                parse_parameters=ParseParameters(
                                    major_version=2,
                                ),
                            ),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.high_quality_picture_fragment
                            ),
                            fragment_parse=FragmentParse(
                                transform_parameters=TransformParameters(
                                    extended_transform_parameters=ExtendedTransformParameters(
                                        asym_transform_flag=True,
                                        dwt_depth_ho=2,
                                    ),
                                ),
                            ),
                        ),
                    ]
                )
            ]
        )
        stream_orig = deepcopy(stream)
        autofill_major_version(stream)
        assert stream == stream_orig

    @pytest.mark.parametrize(
        "parameters, exp_version",
        [
            # Nothing exciting: v1
            ({}, 1),
            # Simple version thresholds
            ({"frame_rate_index": 11}, 1),
            ({"frame_rate_index": 12}, 3),
            ({"signal_range_index": 4}, 1),
            ({"signal_range_index": 5}, 3),
            ({"color_spec_index": 4}, 1),
            ({"color_spec_index": 5}, 3),
            ({"color_matrix_index": 3}, 1),
            ({"color_matrix_index": 4}, 3),
            ({"color_primaries_index": 3}, 1),
            ({"color_primaries_index": 4}, 3),
            ({"transfer_function_index": 3}, 1),
            ({"transfer_function_index": 4}, 3),
            ({"wavelet_index_ho": tables.WaveletFilters.haar_no_shift}, 1),
            ({"wavelet_index_ho": tables.WaveletFilters.fidelity}, 3),
            ({"dwt_depth_ho": 0}, 1),
            ({"dwt_depth_ho": 1}, 3),
            ({"profile": tables.Profiles.low_delay}, 1),
            ({"profile": tables.Profiles.high_quality}, 2),
            ({"parse_code": tables.ParseCodes.low_delay_picture_fragment}, 3),
            ({"parse_code": tables.ParseCodes.high_quality_picture_fragment}, 3),
            # Check highest version chosen when several possible
            (
                {
                    "profile": tables.Profiles.high_quality,  # Requires v2
                    "dwt_depth_ho": 1,  # Requires v3
                },
                3,
            ),
        ],
    )
    def test_version_selection(self, parameters, exp_version):
        profile = parameters.get("profile", tables.Profiles.low_delay)
        frame_rate_index = parameters.get("frame_rate_index")
        signal_range_index = parameters.get("signal_range_index")
        color_spec_index = parameters.get("color_spec_index", 0)
        color_primaries_index = parameters.get("color_primaries_index", 0)
        color_matrix_index = parameters.get("color_matrix_index", 0)
        transfer_function_index = parameters.get("transfer_function_index", 0)
        wavelet_index = parameters.get(
            "wavelet_index", tables.WaveletFilters.haar_no_shift
        )
        wavelet_index_ho = parameters.get("wavelet_index_ho")
        dwt_depth_ho = parameters.get("dwt_depth_ho", None)
        parse_code = parameters.get("parse_code", tables.ParseCodes.low_delay_picture)

        # Kept separate to allow later checking of the version chosen
        pp = ParseParameters(major_version=AUTO, profile=profile)

        # Repeated in the appropriate place for fragments and pictures
        tp = TransformParameters(
            wavelet_index=wavelet_index,
            dwt_depth=2,
            extended_transform_parameters=ExtendedTransformParameters(
                asym_transform_index_flag=wavelet_index_ho is not None,
                wavelet_index_ho=wavelet_index_ho,
                asym_transform_flag=dwt_depth_ho is not None,
                dwt_depth_ho=dwt_depth_ho,
            ),
        )

        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.sequence_header
                            ),
                            sequence_header=SequenceHeader(
                                parse_parameters=pp,
                                video_parameters=SourceParameters(
                                    frame_rate=FrameRate(
                                        custom_frame_rate_flag=frame_rate_index
                                        is not None,
                                        index=frame_rate_index,
                                    ),
                                    signal_range=SignalRange(
                                        custom_signal_range_flag=signal_range_index
                                        is not None,
                                        index=signal_range_index,
                                    ),
                                    color_spec=ColorSpec(
                                        custom_color_spec_flag=True,
                                        index=color_spec_index,
                                        color_primaries=ColorPrimaries(
                                            custom_color_primaries_flag=color_primaries_index
                                            is not None,
                                            index=color_primaries_index,
                                        ),
                                        color_matrix=ColorMatrix(
                                            custom_color_matrix_flag=color_matrix_index
                                            is not None,
                                            index=color_matrix_index,
                                        ),
                                        transfer_function=TransferFunction(
                                            custom_transfer_function_flag=transfer_function_index
                                            is not None,
                                            index=transfer_function_index,
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=parse_code,
                            ),
                            picture_parse=PictureParse(
                                wavelet_transform=WaveletTransform(
                                    transform_parameters=tp,
                                )
                            ),
                            fragment_parse=FragmentParse(
                                transform_parameters=tp,
                            ),
                        ),
                    ]
                )
            ]
        )
        autofill_major_version(stream)
        assert pp["major_version"] == exp_version
        if pp["major_version"] == 3:
            assert "extended_transform_parameters" in tp
        else:
            assert "extended_transform_parameters" not in tp

    def test_insertion_of_parse_parameters_when_absent(self):
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.sequence_header
                            )
                        )
                    ]
                )
            ]
        )
        autofill_major_version(stream)

        # A parse parameters field (and the inferred version number) should
        # have been inserted (since the major_version field defaults to AUTO)
        assert stream == Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.sequence_header
                            ),
                            sequence_header=SequenceHeader(
                                parse_parameters=ParseParameters(
                                    major_version=2,
                                ),
                            ),
                        )
                    ]
                )
            ]
        )

    def test_removal_of_extended_transform_parameters(self):
        # NB: The stream specified below is actually compatible with version 2
        # so the extended transform parameters field should be removed if and
        # only if the major version was set to AUTO in the proceeding sequence
        # header.
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.sequence_header,
                            ),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.high_quality_picture,
                            ),
                            picture_parse=PictureParse(
                                wavelet_transform=WaveletTransform(
                                    transform_parameters=TransformParameters(
                                        wavelet_index=tables.WaveletFilters.haar_no_shift,
                                        dwt_depth=2,
                                        extended_transform_parameters=ExtendedTransformParameters(
                                            asym_transform_index_flag=True,
                                            wavelet_index_ho=tables.WaveletFilters.haar_no_shift,
                                            asym_transform_flag=True,
                                            dwt_depth_ho=0,
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ]
                )
            ]
        )
        autofill_major_version(stream)
        assert stream == Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.sequence_header,
                            ),
                            sequence_header=SequenceHeader(
                                parse_parameters=ParseParameters(
                                    major_version=2,
                                ),
                            ),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.high_quality_picture,
                            ),
                            picture_parse=PictureParse(
                                wavelet_transform=WaveletTransform(
                                    transform_parameters=TransformParameters(
                                        wavelet_index=tables.WaveletFilters.haar_no_shift,
                                        dwt_depth=2,
                                    ),
                                ),
                            ),
                        ),
                    ]
                )
            ]
        )


class TestAutofillParseOffsets(object):
    @pytest.mark.parametrize(
        "stream", [Stream(), Stream(sequences=[Sequence(data_units=[])])]
    )
    def test_doesnt_crash_on_empty_stream(self, stream):
        stream_orig = deepcopy(stream)
        assert autofill_parse_offsets(stream) == ([], [])
        assert stream == stream_orig

    @pytest.mark.parametrize(
        "parse_code",
        [tables.ParseCodes.padding_data, tables.ParseCodes.auxiliary_data],
    )
    def test_padding_and_aux_data(self, parse_code):
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        # Next parse offset not given (should be treated as auto)
                        DataUnit(parse_info=ParseInfo(parse_code=parse_code)),
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
                    ]
                )
            ]
        )
        for seq in stream["sequences"]:
            for data_unit in seq["data_units"]:
                if parse_code == tables.ParseCodes.padding_data:
                    data_unit["padding"] = Padding(bytes=b"1234")
                elif parse_code == tables.ParseCodes.auxiliary_data:
                    data_unit["auxiliary_data"] = AuxiliaryData(bytes=b"1234")

        assert autofill_parse_offsets(stream) == ([], [(0, 0), (0, 1), (0, 2)])

        next_parse_offsets = [
            data_unit["parse_info"]["next_parse_offset"]
            for seq in stream["sequences"]
            for data_unit in seq["data_units"]
        ]
        assert next_parse_offsets == [13 + 4, 13 + 4, 100]

        previous_parse_offsets = [
            data_unit["parse_info"]["previous_parse_offset"]
            for seq in stream["sequences"]
            for data_unit in seq["data_units"]
        ]
        assert previous_parse_offsets == [0, 0, 0]

    @pytest.mark.parametrize(
        "parse_code",
        [tables.ParseCodes.padding_data, tables.ParseCodes.auxiliary_data],
    )
    def test_padding_and_aux_data_default_data(self, parse_code):
        # No data given (default (empty) data should be assumed)
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[DataUnit(parse_info=ParseInfo(parse_code=parse_code))]
                )
            ]
        )

        assert autofill_parse_offsets(stream) == ([], [(0, 0)])

        parse_info = stream["sequences"][0]["data_units"][0]["parse_info"]
        assert parse_info["next_parse_offset"] == 13
        assert parse_info["previous_parse_offset"] == 0

    @pytest.mark.parametrize("explicit_auto", [True, False])
    @pytest.mark.parametrize(
        "parse_code",
        [
            parse_code
            for parse_code in tables.ParseCodes
            if parse_code
            not in (
                tables.ParseCodes.padding_data,
                tables.ParseCodes.auxiliary_data,
            )
        ],
    )
    def test_values_to_be_set_later_are_set_to_zero(self, parse_code, explicit_auto):
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        # An automatically set data unit
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=parse_code,
                            )
                        ),
                        # One which is explicitly set (and should not be overridden)
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=parse_code,
                                next_parse_offset=100,
                                previous_parse_offset=200,
                            )
                        ),
                    ]
                )
            ]
        )
        if explicit_auto:
            parse_info = stream["sequences"][0]["data_units"][0]["parse_info"]
            parse_info["next_parse_offset"] = AUTO
            parse_info["previous_parse_offset"] = AUTO

        assert autofill_parse_offsets(stream) == ([(0, 0)], [(0, 0)])

        parse_info_0 = stream["sequences"][0]["data_units"][0]["parse_info"]
        assert parse_info_0["next_parse_offset"] == 0
        assert parse_info_0["previous_parse_offset"] == 0

        parse_info_1 = stream["sequences"][0]["data_units"][1]["parse_info"]
        assert parse_info_1["next_parse_offset"] == 100
        assert parse_info_1["previous_parse_offset"] == 200

    def test_finalizer_works(self):
        f = BytesIO()
        w = BitstreamWriter(f)

        # Sequence with every data unit type and fully automatic numbers
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.sequence_header
                            ),
                            sequence_header=SequenceHeader(
                                parse_parameters=ParseParameters(major_version=3),
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
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.high_quality_picture
                            ),
                            picture_parse=PictureParse(
                                picture_header=PictureHeader(picture_number=0)
                            ),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.low_delay_picture
                            ),
                            picture_parse=PictureParse(
                                picture_header=PictureHeader(picture_number=0)
                            ),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.high_quality_picture_fragment
                            ),
                            fragment_parse=FragmentParse(
                                fragment_header=FragmentHeader(picture_number=0)
                            ),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.high_quality_picture_fragment
                            ),
                            fragment_parse=FragmentParse(
                                fragment_header=FragmentHeader(picture_number=0)
                            ),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.padding_data
                            ),
                            padding=Padding(bytes=b"123"),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.auxiliary_data
                            ),
                            auxiliary_data=AuxiliaryData(bytes=b"123"),
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.end_of_sequence
                            ),
                        ),
                    ]
                )
            ]
        )

        (
            next_parse_offsets_to_autofill,
            previous_parse_offsets_to_autofill,
        ) = autofill_parse_offsets(stream)

        with Serialiser(w, stream, vc2_default_values_with_auto) as serdes:
            vc2.parse_stream(serdes, State())
        w.flush()

        offset_before = w.tell()
        autofill_parse_offsets_finalize(
            w,
            serdes.context,
            next_parse_offsets_to_autofill,
            previous_parse_offsets_to_autofill,
        )
        assert w.tell() == offset_before

        f.seek(0)
        r = BitstreamReader(f)
        with Deserialiser(r) as serdes:
            vc2.parse_stream(serdes, State())

        parse_infos = [
            data_unit["parse_info"]
            for sequence in serdes.context["sequences"]
            for data_unit in sequence["data_units"]
        ]

        # Check for start/end offsets being zero
        assert parse_infos[0]["previous_parse_offset"] == 0
        assert parse_infos[-1]["next_parse_offset"] == 0

        # Check for consistency and plusibility of offsets
        for pi1, pi2 in zip(parse_infos, parse_infos[1:]):
            assert pi1["next_parse_offset"] > 13
            assert pi2["previous_parse_offset"] > 13

            assert pi1["next_parse_offset"] == pi2["previous_parse_offset"]

    def test_works_on_multiple_sequences(self):
        f = BytesIO()
        w = BitstreamWriter(f)

        # Sequence with every data unit type and fully automatic numbers
        stream = Stream(
            sequences=[
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.padding_data
                            )
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.padding_data
                            )
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.end_of_sequence
                            )
                        ),
                    ]
                ),
                Sequence(
                    data_units=[
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.padding_data
                            )
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.padding_data
                            )
                        ),
                        DataUnit(
                            parse_info=ParseInfo(
                                parse_code=tables.ParseCodes.end_of_sequence
                            )
                        ),
                    ]
                ),
            ]
        )

        (
            next_parse_offsets_to_autofill,
            previous_parse_offsets_to_autofill,
        ) = autofill_parse_offsets(stream)

        print(stream)
        with Serialiser(w, stream, vc2_default_values_with_auto) as serdes:
            vc2.parse_stream(serdes, State())
        w.flush()

        autofill_parse_offsets_finalize(
            w,
            serdes.context,
            next_parse_offsets_to_autofill,
            previous_parse_offsets_to_autofill,
        )

        f.seek(0)
        r = BitstreamReader(f)
        with Deserialiser(r) as serdes:
            vc2.parse_stream(serdes, State())

        parse_infos = [
            [data_unit["parse_info"] for data_unit in sequence["data_units"]]
            for sequence in serdes.context["sequences"]
        ]

        # Check for start/end offsets being zero
        for sequence_pis in parse_infos:
            assert sequence_pis[0]["previous_parse_offset"] == 0
            assert sequence_pis[-1]["next_parse_offset"] == 0

            # Check for offset correctness
            for pi1, pi2 in zip(sequence_pis, sequence_pis[1:]):
                assert pi1["next_parse_offset"] == 13
                assert pi2["previous_parse_offset"] == 13


def test_autofill_and_serialise_stream():
    f = BytesIO()

    # Sequence with every data unit type and fully automatic numbers
    stream = Stream(
        sequences=[
            Sequence(
                data_units=[
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.sequence_header
                        ),
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
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.high_quality_picture
                        ),
                    ),
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.low_delay_picture
                        ),
                    ),
                    # High quality fragment
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.high_quality_picture_fragment
                        ),
                        fragment_parse=FragmentParse(
                            fragment_header=FragmentHeader(fragment_slice_count=0)
                        ),
                    ),
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.high_quality_picture_fragment
                        ),
                        fragment_parse=FragmentParse(
                            fragment_header=FragmentHeader(fragment_slice_count=1)
                        ),
                    ),
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.high_quality_picture_fragment
                        ),
                        fragment_parse=FragmentParse(
                            fragment_header=FragmentHeader(fragment_slice_count=1)
                        ),
                    ),
                    # Low delay fragment
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.high_quality_picture_fragment
                        ),
                        fragment_parse=FragmentParse(
                            fragment_header=FragmentHeader(fragment_slice_count=0)
                        ),
                    ),
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.high_quality_picture_fragment
                        ),
                        fragment_parse=FragmentParse(
                            fragment_header=FragmentHeader(fragment_slice_count=1)
                        ),
                    ),
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.high_quality_picture_fragment
                        ),
                        fragment_parse=FragmentParse(
                            fragment_header=FragmentHeader(fragment_slice_count=1)
                        ),
                    ),
                    # Other types
                    DataUnit(
                        parse_info=ParseInfo(parse_code=tables.ParseCodes.padding_data),
                        padding=Padding(bytes=b"123"),
                    ),
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.auxiliary_data
                        ),
                        auxiliary_data=AuxiliaryData(bytes=b"123"),
                    ),
                    DataUnit(
                        parse_info=ParseInfo(
                            parse_code=tables.ParseCodes.end_of_sequence
                        ),
                    ),
                ]
            )
        ]
    )

    autofill_and_serialise_stream(f, stream)

    f.seek(0)
    r = BitstreamReader(f)
    with Deserialiser(r) as serdes:
        vc2.parse_stream(serdes, State())

    parse_infos = [
        data_unit["parse_info"]
        for sequence in serdes.context["sequences"]
        for data_unit in sequence["data_units"]
    ]

    # Check for start/end offsets being zero
    assert parse_infos[0]["previous_parse_offset"] == 0
    assert parse_infos[-1]["next_parse_offset"] == 0

    # Check for consistency and plausibility of offsets
    for pi1, pi2 in zip(parse_infos, parse_infos[1:]):
        assert pi1["next_parse_offset"] > 13
        assert pi2["previous_parse_offset"] > 13

        assert pi1["next_parse_offset"] == pi2["previous_parse_offset"]

    # Check picture numbers
    picture_numbers = [
        (
            data_unit.get("picture_parse", {}).get("picture_header", {})
            or data_unit.get("fragment_parse", {}).get("fragment_header", {})
        ).get("picture_number")
        for sequence in serdes.context["sequences"]
        for data_unit in sequence["data_units"]
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

    # Check major version is autofilled with 3 (due to presence of fragments)
    major_versions = [
        data_unit["sequence_header"]["parse_parameters"]["major_version"]
        for sequence in serdes.context["sequences"]
        for data_unit in sequence["data_units"]
        if data_unit["parse_info"]["parse_code"] == tables.ParseCodes.sequence_header
    ]
    assert all(v == 3 for v in major_versions)
