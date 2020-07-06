import pytest

from mock import Mock

from decoder_test_utils import (
    serialise_to_bytes,
    bytes_to_state,
    populate_parse_offsets,
)

from vc2_conformance import bitstream
from vc2_conformance import decoder

import vc2_data_tables as tables

from vc2_conformance.symbol_re import Matcher


class TestParseStreamAndParseSequence(object):
    @pytest.fixture
    def sh_bytes(self):
        # A sequence header
        return serialise_to_bytes(bitstream.SequenceHeader())

    @pytest.fixture
    def sh_parse_offset(self, sh_bytes):
        # Offset for parse_infoa values
        return tables.PARSE_INFO_HEADER_BYTES + len(sh_bytes)

    @pytest.fixture
    def sh_data_unit_bytes(self, sh_bytes, sh_parse_offset):
        # parse_info + sequence header
        return (
            serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.sequence_header,
                    next_parse_offset=sh_parse_offset,
                )
            )
            + sh_bytes
        )

    def test_immediate_end_of_sequence(self, sh_data_unit_bytes):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(parse_code=tables.ParseCodes.end_of_sequence)
            )
        )
        with pytest.raises(decoder.GenericInvalidSequence) as exc_info:
            decoder.parse_stream(state)

        assert exc_info.value.parse_code is tables.ParseCodes.end_of_sequence
        assert exc_info.value.expected_parse_codes == [
            tables.ParseCodes.sequence_header
        ]
        assert exc_info.value.expected_end is False

    def test_no_sequence_header(self, sh_data_unit_bytes):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.padding_data,
                    next_parse_offset=tables.PARSE_INFO_HEADER_BYTES,
                )
            )
        )
        with pytest.raises(decoder.GenericInvalidSequence) as exc_info:
            decoder.parse_stream(state)

        assert exc_info.value.parse_code is tables.ParseCodes.padding_data
        assert exc_info.value.expected_parse_codes == [
            tables.ParseCodes.sequence_header
        ]
        assert exc_info.value.expected_end is False

    @pytest.mark.parametrize(
        "picture_coding_mode,num_pictures,exp_fail",
        [
            (tables.PictureCodingModes.pictures_are_frames, 0, False),
            (tables.PictureCodingModes.pictures_are_frames, 1, False),
            (tables.PictureCodingModes.pictures_are_frames, 2, False),
            (tables.PictureCodingModes.pictures_are_frames, 3, False),
            (tables.PictureCodingModes.pictures_are_frames, 4, False),
            (tables.PictureCodingModes.pictures_are_fields, 0, False),
            (tables.PictureCodingModes.pictures_are_fields, 1, True),
            (tables.PictureCodingModes.pictures_are_fields, 2, False),
            (tables.PictureCodingModes.pictures_are_fields, 3, True),
            (tables.PictureCodingModes.pictures_are_fields, 4, False),
        ],
    )
    def test_odd_number_of_fields_disallowed(
        self, picture_coding_mode, num_pictures, exp_fail
    ):
        # A sequence with num_pictures HQ pictures
        seq = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.sequence_header,
                    ),
                    sequence_header=bitstream.SequenceHeader(
                        picture_coding_mode=picture_coding_mode,
                        video_parameters=bitstream.SourceParameters(
                            frame_size=bitstream.FrameSize(
                                # Don't waste time on full-sized frames
                                custom_dimensions_flag=True,
                                frame_width=4,
                                frame_height=4,
                            ),
                            clean_area=bitstream.CleanArea(
                                custom_clean_area_flag=True,
                                clean_width=4,
                                clean_height=4,
                            ),
                        ),
                    ),
                ),
            ]
            + [
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture,
                    ),
                    picture_parse=bitstream.PictureParse(
                        picture_header=bitstream.PictureHeader(picture_number=n,),
                    ),
                )
                for n in range(num_pictures)
            ]
            + [
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.end_of_sequence,
                    ),
                ),
            ]
        )
        populate_parse_offsets(seq)

        state = bytes_to_state(serialise_to_bytes(seq))
        if exp_fail:
            with pytest.raises(decoder.OddNumberOfFieldsInSequence) as exc_info:
                decoder.parse_stream(state)
            assert exc_info.value.num_fields_in_sequence == num_pictures
        else:
            decoder.parse_stream(state)

    @pytest.mark.parametrize(
        "num_slices_to_send,exp_fail",
        [(0, True), (1, True), (2, True), (3, True), (4, True), (5, True), (6, False)],
    )
    def test_incomplete_picture_fragments_at_eos_fails(
        self, num_slices_to_send, exp_fail
    ):
        # A sequence with a 3x2 slice picture fragment with num_slices_to_send slices in
        # it
        seq = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.sequence_header,
                    ),
                    sequence_header=bitstream.SequenceHeader(
                        video_parameters=bitstream.SourceParameters(
                            frame_size=bitstream.FrameSize(
                                # Don't waste time on full-sized frames
                                custom_dimensions_flag=True,
                                frame_width=8,
                                frame_height=8,
                            ),
                            clean_area=bitstream.CleanArea(
                                custom_clean_area_flag=True,
                                clean_width=8,
                                clean_height=8,
                            ),
                        ),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture_fragment,
                    ),
                    fragment_parse=bitstream.FragmentParse(
                        fragment_header=bitstream.FragmentHeader(
                            fragment_slice_count=0,
                        ),
                        transform_parameters=bitstream.TransformParameters(
                            slice_parameters=bitstream.SliceParameters(
                                slices_x=3, slices_y=2,
                            ),
                        ),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture_fragment,
                    ),
                    fragment_parse=bitstream.FragmentParse(
                        fragment_header=bitstream.FragmentHeader(
                            fragment_slice_count=num_slices_to_send,
                        ),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.end_of_sequence,
                    ),
                ),
            ]
        )
        # Don't include second (non-header) fragment if sending no slices
        if num_slices_to_send == 0:
            del seq["data_units"][2]

        populate_parse_offsets(seq)

        state = bytes_to_state(serialise_to_bytes(seq))
        if exp_fail:
            with pytest.raises(
                decoder.SequenceContainsIncompleteFragmentedPicture
            ) as exc_info:
                decoder.parse_stream(state)
            first_fragment_offset = (
                seq["data_units"][0]["parse_info"]["next_parse_offset"]
                + tables.PARSE_INFO_HEADER_BYTES
            )
            assert exc_info.value.initial_fragment_offset == (first_fragment_offset, 7)
            assert exc_info.value.fragment_slices_received == num_slices_to_send
            assert exc_info.value.fragment_slices_remaining == 6 - num_slices_to_send
        else:
            decoder.parse_stream(state)

    @pytest.mark.parametrize(
        "num_slices_to_send,exp_fail",
        [(0, True), (1, True), (2, True), (3, True), (4, True), (5, True), (6, False)],
    )
    def test_picture_and_incomplete_fragment_interleaving_disallowed(
        self, num_slices_to_send, exp_fail
    ):
        # A sequence with a 3x2 slice picture fragment with num_slices_to_send slices in
        # it followed by an HQ picture
        seq = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.sequence_header,
                    ),
                    sequence_header=bitstream.SequenceHeader(
                        video_parameters=bitstream.SourceParameters(
                            frame_size=bitstream.FrameSize(
                                # Don't waste time on full-sized pictures
                                custom_dimensions_flag=True,
                                frame_width=8,
                                frame_height=8,
                            ),
                            clean_area=bitstream.CleanArea(
                                custom_clean_area_flag=True,
                                clean_width=8,
                                clean_height=8,
                            ),
                        ),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture_fragment,
                    ),
                    fragment_parse=bitstream.FragmentParse(
                        fragment_header=bitstream.FragmentHeader(
                            picture_number=0, fragment_slice_count=0,
                        ),
                        transform_parameters=bitstream.TransformParameters(
                            slice_parameters=bitstream.SliceParameters(
                                slices_x=3, slices_y=2,
                            ),
                        ),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture_fragment,
                    ),
                    fragment_parse=bitstream.FragmentParse(
                        fragment_header=bitstream.FragmentHeader(
                            picture_number=0, fragment_slice_count=num_slices_to_send,
                        ),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture,
                    ),
                    picture_parse=bitstream.PictureParse(
                        picture_header=bitstream.PictureHeader(picture_number=1,),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.end_of_sequence,
                    ),
                ),
            ]
        )
        # Don't include second (non-header) fragment if sending no slices
        if num_slices_to_send == 0:
            del seq["data_units"][2]

        populate_parse_offsets(seq)

        state = bytes_to_state(serialise_to_bytes(seq))
        if exp_fail:
            with pytest.raises(
                decoder.PictureInterleavedWithFragmentedPicture
            ) as exc_info:
                decoder.parse_stream(state)
            first_fragment_offset = (
                seq["data_units"][0]["parse_info"]["next_parse_offset"]
                + tables.PARSE_INFO_HEADER_BYTES
            )
            assert exc_info.value.initial_fragment_offset == (first_fragment_offset, 7)
            picture_offset = (
                sum(
                    seq["data_units"][i]["parse_info"]["next_parse_offset"]
                    for i in range(len(seq["data_units"]) - 2)
                )
                + tables.PARSE_INFO_HEADER_BYTES
            )
            assert exc_info.value.this_offset == (picture_offset, 7)
            assert exc_info.value.fragment_slices_received == num_slices_to_send
            assert exc_info.value.fragment_slices_remaining == 6 - num_slices_to_send
        else:
            decoder.parse_stream(state)

    def test_output_picture(self):
        # This test adds a callback for output_picture and makes sure that both
        # fragments and pictures call it correctly (and that sanity-checks very
        # loosely that decoding etc. is happening). Finally, it also checks
        # that two concatenated sequences are read one after another.

        # A sequence with a HQ picture followed by a HQ fragment (both all
        # zeros)
        seq1 = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.sequence_header,
                    ),
                    sequence_header=bitstream.SequenceHeader(
                        video_parameters=bitstream.SourceParameters(
                            frame_size=bitstream.FrameSize(
                                # Don't waste time on full-sized frames
                                custom_dimensions_flag=True,
                                frame_width=4,
                                frame_height=2,
                            ),
                            clean_area=bitstream.CleanArea(
                                custom_clean_area_flag=True,
                                clean_width=4,
                                clean_height=2,
                            ),
                            color_diff_sampling_format=bitstream.ColorDiffSamplingFormat(
                                custom_color_diff_format_flag=True,
                                color_diff_format_index=tables.ColorDifferenceSamplingFormats.color_4_2_2,  # noqa: E501
                            ),
                            # Output values will be treated as 8-bit (and thus all
                            # decode to 128)
                            signal_range=bitstream.SignalRange(
                                custom_signal_range_flag=True,
                                index=tables.PresetSignalRanges.video_8bit_full_range,
                            ),
                        ),
                        picture_coding_mode=tables.PictureCodingModes.pictures_are_frames,
                    ),
                ),
                # A HQ picture
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture,
                    ),
                    picture_parse=bitstream.PictureParse(
                        picture_header=bitstream.PictureHeader(picture_number=10,),
                    ),
                ),
                # A fragmented HQ picture (sent over two fragments to ensure the
                # callback only fires after a whole picture arrives)
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture_fragment,
                    ),
                    fragment_parse=bitstream.FragmentParse(
                        fragment_header=bitstream.FragmentHeader(
                            picture_number=11, fragment_slice_count=0,
                        ),
                        transform_parameters=bitstream.TransformParameters(
                            slice_parameters=bitstream.SliceParameters(
                                slices_x=2, slices_y=1,
                            ),
                        ),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture_fragment,
                    ),
                    fragment_parse=bitstream.FragmentParse(
                        fragment_header=bitstream.FragmentHeader(
                            picture_number=11,
                            fragment_slice_count=1,
                            fragment_x_offset=0,
                            fragment_y_offset=0,
                        ),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture_fragment,
                    ),
                    fragment_parse=bitstream.FragmentParse(
                        fragment_header=bitstream.FragmentHeader(
                            picture_number=11,
                            fragment_slice_count=1,
                            fragment_x_offset=1,
                            fragment_y_offset=0,
                        ),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.end_of_sequence,
                    ),
                ),
            ]
        )

        # Another (HQ) picture in a separate sequence
        seq2 = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.sequence_header,
                    ),
                    sequence_header=bitstream.SequenceHeader(
                        video_parameters=bitstream.SourceParameters(
                            frame_size=bitstream.FrameSize(
                                # Don't waste time on full-sized frames
                                custom_dimensions_flag=True,
                                frame_width=4,
                                frame_height=2,
                            ),
                            clean_area=bitstream.CleanArea(
                                custom_clean_area_flag=True,
                                clean_width=4,
                                clean_height=2,
                            ),
                            color_diff_sampling_format=bitstream.ColorDiffSamplingFormat(
                                custom_color_diff_format_flag=True,
                                color_diff_format_index=tables.ColorDifferenceSamplingFormats.color_4_2_2,  # noqa: E501
                            ),
                            # Output values will be treated as 8-bit (and thus all
                            # decode to 128)
                            signal_range=bitstream.SignalRange(
                                custom_signal_range_flag=True,
                                index=tables.PresetSignalRanges.video_8bit_full_range,
                            ),
                        ),
                        picture_coding_mode=tables.PictureCodingModes.pictures_are_frames,
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.high_quality_picture,
                    ),
                    picture_parse=bitstream.PictureParse(
                        picture_header=bitstream.PictureHeader(picture_number=12),
                    ),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.end_of_sequence,
                    ),
                ),
            ]
        )
        populate_parse_offsets(seq1)
        populate_parse_offsets(seq2)

        state = bytes_to_state(serialise_to_bytes(seq1) + serialise_to_bytes(seq2))
        state["_output_picture_callback"] = Mock()
        decoder.parse_stream(state)

        assert state["_output_picture_callback"].call_count == 3

        for i, (args, kwargs) in enumerate(
            state["_output_picture_callback"].call_args_list
        ):
            assert kwargs == {}
            # Should get a 4x2 mid-gray frame with 4:2:2 color difference sampling
            assert args[0] == {
                "pic_num": 10 + i,
                "Y": [[128, 128, 128, 128], [128, 128, 128, 128]],
                "C1": [[128, 128], [128, 128]],
                "C2": [[128, 128], [128, 128]],
            }
            # Just sanity check the second argument looks like a set of video parameters
            assert args[1]["frame_width"] == 4
            assert args[1]["frame_height"] == 2
            assert args[1]["luma_offset"] == 0
            assert args[1]["luma_offset"] == 0
            assert args[1]["luma_excursion"] == 255
            assert args[1]["color_diff_offset"] == 128
            assert args[1]["color_diff_excursion"] == 255
            # And the picture coding mode too...
            assert args[2] == tables.PictureCodingModes.pictures_are_frames


class TestParseInfo(object):
    def test_bad_parse_info_prefix(self):
        state = bytes_to_state(
            serialise_to_bytes(bitstream.ParseInfo(parse_info_prefix=0xDEADBEEF,))
        )
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.BadParseInfoPrefix) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.parse_info_prefix == 0xDEADBEEF

    def test_bad_parse_code(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.ParseInfo(parse_code=0x11)))
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.BadParseCode) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.parse_code == 0x11

    def test_inconsistent_next_parse_offset(self):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.padding_data,
                    next_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 10,
                )
            )
            + b"\x00" * 9
            + serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.end_of_sequence,
                    previous_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 9,
                )
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")

        decoder.parse_info(state)
        decoder.read_uint_lit(state, 9)
        with pytest.raises(decoder.InconsistentNextParseOffset) as exc_info:
            decoder.parse_info(state)

        assert exc_info.value.parse_info_offset == 0
        assert exc_info.value.next_parse_offset == tables.PARSE_INFO_HEADER_BYTES + 10
        assert exc_info.value.true_parse_offset == tables.PARSE_INFO_HEADER_BYTES + 9

    @pytest.mark.parametrize(
        "parse_code",
        [
            tables.ParseCodes.low_delay_picture,
            tables.ParseCodes.low_delay_picture_fragment,
            tables.ParseCodes.high_quality_picture,
            tables.ParseCodes.high_quality_picture_fragment,
        ],
    )
    def test_allowed_zero_next_parse_offset_for_pictures(self, parse_code):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(parse_code=parse_code, next_parse_offset=0,)
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")
        decoder.parse_info(state)

    @pytest.mark.parametrize(
        "parse_code",
        [
            tables.ParseCodes.sequence_header,
            tables.ParseCodes.auxiliary_data,
            tables.ParseCodes.padding_data,
        ],
    )
    def test_not_allowed_zero_next_parse_offset_for_non_pictures(self, parse_code):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(parse_code=parse_code, next_parse_offset=0,)
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.MissingNextParseOffset) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.parse_code == parse_code

    @pytest.mark.parametrize(
        "parse_code",
        [
            tables.ParseCodes.sequence_header,
            tables.ParseCodes.auxiliary_data,
            tables.ParseCodes.padding_data,
        ],
    )
    @pytest.mark.parametrize(
        "next_parse_offset", [1, tables.PARSE_INFO_HEADER_BYTES - 1]
    )
    def test_never_allowed_invalid_offset(self, parse_code, next_parse_offset):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=parse_code, next_parse_offset=next_parse_offset,
                )
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.InvalidNextParseOffset) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.next_parse_offset == next_parse_offset

    def test_non_zero_next_parse_offset_for_end_of_sequence(self):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.end_of_sequence, next_parse_offset=1,
                )
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.NonZeroNextParseOffsetAtEndOfSequence) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.next_parse_offset == 1

    def test_non_zero_previous_parse_offset_for_start_of_sequence(self):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.end_of_sequence,
                    previous_parse_offset=1,
                )
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(
            decoder.NonZeroPreviousParseOffsetAtStartOfSequence
        ) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.previous_parse_offset == 1

    def test_inconsistent_previous_parse_offset(self):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.padding_data,
                    next_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 10,
                )
            )
            + b"\x00" * 10
            + serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=tables.ParseCodes.end_of_sequence,
                    previous_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 9,
                )
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")

        decoder.parse_info(state)
        decoder.read_uint_lit(state, 10)
        with pytest.raises(decoder.InconsistentPreviousParseOffset) as exc_info:
            decoder.parse_info(state)

        assert exc_info.value.last_parse_info_offset == 0
        assert (
            exc_info.value.previous_parse_offset == tables.PARSE_INFO_HEADER_BYTES + 9
        )
        assert exc_info.value.true_parse_offset == tables.PARSE_INFO_HEADER_BYTES + 10

    def test_invalid_generic_sequence(self):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(parse_code=tables.ParseCodes.end_of_sequence,)
            )
        )
        state["_generic_sequence_matcher"] = Matcher("sequence_header")

        with pytest.raises(decoder.GenericInvalidSequence) as exc_info:
            decoder.parse_info(state)

        assert exc_info.value.parse_code is tables.ParseCodes.end_of_sequence
        assert exc_info.value.expected_parse_codes == [
            tables.ParseCodes.sequence_header
        ]
        assert exc_info.value.expected_end is False

    @pytest.mark.parametrize(
        "parse_code,allowed",
        [
            (tables.ParseCodes.padding_data, True),
            (tables.ParseCodes.low_delay_picture, False),
        ],
    )
    def test_profile_restricts_allowed_parse_codes(self, parse_code, allowed):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(
                    parse_code=parse_code,
                    next_parse_offset=tables.PARSE_INFO_HEADER_BYTES,
                )
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")
        state["profile"] = tables.Profiles.high_quality

        if allowed:
            decoder.parse_info(state)
        else:
            with pytest.raises(decoder.ParseCodeNotAllowedInProfile) as exc_info:
                decoder.parse_info(state)
            assert exc_info.value.parse_code == tables.ParseCodes.low_delay_picture
            assert exc_info.value.profile == tables.Profiles.high_quality

    def test_level_restricts_sequence(self):
        state = bytes_to_state(
            serialise_to_bytes(
                bitstream.ParseInfo(parse_code=tables.ParseCodes.end_of_sequence,)
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")
        state["_level_sequence_matcher"] = Matcher("sequence_header")
        state["level"] = tables.Levels.unconstrained

        with pytest.raises(decoder.LevelInvalidSequence) as exc_info:
            decoder.parse_info(state)

        assert exc_info.value.parse_code is tables.ParseCodes.end_of_sequence
        assert exc_info.value.expected_parse_codes == [
            tables.ParseCodes.sequence_header
        ]
        assert exc_info.value.expected_end is False
        assert exc_info.value.level == tables.Levels.unconstrained
