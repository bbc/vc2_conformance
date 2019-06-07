import pytest

from decoder_test_utils import seriallise_to_bytes, bytes_to_state

from vc2_conformance import bitstream
from vc2_conformance import tables
from vc2_conformance import decoder

from vc2_conformance._symbol_re import Matcher


def parse_info_to_bytes(**kwargs):
    """
    Seriallise a ParseInfo block, returning a bytes object.
    """
    return seriallise_to_bytes(bitstream.ParseInfo(**kwargs), bitstream.parse_info)


class TestParseSequence(object):
    
    @pytest.fixture
    def sh_bytes(self):
        # A sequence header
        return seriallise_to_bytes(bitstream.SequenceHeader(), bitstream.sequence_header)
    
    @pytest.fixture
    def sh_parse_offset(self, sh_bytes):
        # Offset for parse_infoa values
        return tables.PARSE_INFO_HEADER_BYTES + len(sh_bytes)

    @pytest.fixture
    def sh_data_unit_bytes(self, sh_bytes, sh_parse_offset):
        # parse_info + sequence header
        return parse_info_to_bytes(
            parse_code=tables.ParseCodes.sequence_header,
            next_parse_offset=sh_parse_offset,
        ) + sh_bytes

    def test_trailing_bytes_after_end_of_sequence(self, sh_data_unit_bytes, sh_parse_offset):
        state = bytes_to_state(
            sh_data_unit_bytes +
            parse_info_to_bytes(
                parse_code=tables.ParseCodes.end_of_sequence,
                previous_parse_offset=sh_parse_offset,
            ) +
            b"\x00"
        )
        with pytest.raises(decoder.TrailingBytesAfterEndOfSequence):
            decoder.parse_sequence(state)
    
    def test_immediate_end_of_sequence(self, sh_data_unit_bytes):
        state = bytes_to_state(
            parse_info_to_bytes(parse_code=tables.ParseCodes.end_of_sequence)
        )
        with pytest.raises(decoder.GenericInvalidSequence) as exc_info:
            decoder.parse_sequence(state)
        
        assert exc_info.value.parse_code is tables.ParseCodes.end_of_sequence
        assert exc_info.value.expected_parse_codes == [tables.ParseCodes.sequence_header]
        assert exc_info.value.expected_end is False
    
    def test_no_sequence_header(self, sh_data_unit_bytes):
        state = bytes_to_state(
            parse_info_to_bytes(
                parse_code=tables.ParseCodes.padding_data,
                next_parse_offset=tables.PARSE_INFO_HEADER_BYTES,
            )
        )
        with pytest.raises(decoder.GenericInvalidSequence) as exc_info:
            decoder.parse_sequence(state)
        
        assert exc_info.value.parse_code is tables.ParseCodes.padding_data
        assert exc_info.value.expected_parse_codes == [tables.ParseCodes.sequence_header]
        assert exc_info.value.expected_end is False
    
    @pytest.mark.xfail
    @pytest.mark.parametrize("picture_coding_mode,num_pictures,exp_fail", [
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
    ])
    def test_odd_number_of_fields_disallowed(self, picture_coding_mode,
                                             num_pictures, exp_fail):
        sh = seriallise_to_bytes(
            bitstream.SequenceHeader(
                picture_coding_mode=picture_coding_mode,
            ),
            bitstream.sequence_header,
        )
        sh_and_pi = parse_info_to_bytes(
            parse_code=tables.ParseCodes.sequence_header,
            next_parse_offset=(
                tables.PARSE_INFO_HEADER_BYTES +
                len(sh)
            ),
        ) + sh
        
        # TODO: Add an odd number of minimal pictures/fields once picture
        # parsing is supported
        
        eos = parse_info_to_bytes(
            parse_code=tables.ParseCodes.end_of_sequence,
            previous_parse_offset=len(sh_and_pi),
        )
        
        state = bytes_to_state(sh_and_pi + eos)
        if exp_fail:
            with pytest.raises(decoder.OddNumberOfFieldsInSequence) as exc_info:
                decoder.parse_sequence(state)
            assert exc_info.value.num_fields_in_sequence == num_pictures
        else:
            decoder.parse_sequence(state)
    
    @pytest.mark.xfail
    @pytest.mark.parametrize("num_slices_to_send,exp_fail", [
        (0, False),
        (1, True),
        (2, True),
        (3, True),
        (4, False),
    ])
    def test_incomplete_picture_fragments_at_eos_fails(self, num_slices_to_send, exp_fail):
        sh = seriallise_to_bytes(
            bitstream.SequenceHeader(),
            bitstream.sequence_header,
        )
        sh_and_pi = parse_info_to_bytes(
            parse_code=tables.ParseCodes.sequence_header,
            next_parse_offset=(
                tables.PARSE_INFO_HEADER_BYTES +
                len(sh)
            ),
        ) + sh
        
        # TODO: Create a 4-slice picture and send num_slices_to_send worth of
        # fragments before ending the stream.
        
        eos = parse_info_to_bytes(
            parse_code=tables.ParseCodes.end_of_sequence,
            previous_parse_offset=len(sh_and_pi),
        )
        
        state = bytes_to_state(sh_and_pi + eos)
        if exp_fail:
            with pytest.raises(decoder.SequenceContainsIncompleteFragmentedPicture) as exc_info:
                decoder.parse_sequence(state)
            assert exc_info.value.initial_fragment_offset == (len(sh_and_pi), 7)
            assert exc_info.value.fragment_slices_received == num_slices_to_send
            assert exc_info.value.fragment_slices_remaining == 4 - num_slices_to_send
        else:
            decoder.parse_sequence(state)
    
    @pytest.mark.xfail
    @pytest.mark.parametrize("num_slices_to_send,exp_fail", [
        (0, False),
        (1, True),
        (2, True),
        (3, True),
        (4, False),
    ])
    def test_picture_and_incomplete_fragment_interleaving_disallowed(self, num_slices_to_send, exp_fail):
        sh = seriallise_to_bytes(
            bitstream.SequenceHeader(),
            bitstream.sequence_header,
        )
        sh_and_pi = parse_info_to_bytes(
            parse_code=tables.ParseCodes.sequence_header,
            next_parse_offset=(
                tables.PARSE_INFO_HEADER_BYTES +
                len(sh)
            ),
        ) + sh
        
        # TODO: Create a 4-slice picture and send num_slices_to_send worth of
        # fragments before sending a picture and then the remaining slcies.
        
        eos = parse_info_to_bytes(
            parse_code=tables.ParseCodes.end_of_sequence,
            previous_parse_offset=len(sh_and_pi),
        )
        
        state = bytes_to_state(sh_and_pi + eos)
        if exp_fail:
            with pytest.raises(decoder.PictureInterleavedWithFragmentedPicture) as exc_info:
                decoder.parse_sequence(state)
            assert exc_info.value.initial_fragment_offset == (len(sh_and_pi), 7)
            assert exc_info.value.this_offset == None  # TODO
            assert exc_info.value.fragment_slices_received == num_slices_to_send
            assert exc_info.value.fragment_slices_remaining == 4 - num_slices_to_send
        else:
            decoder.parse_sequence(state)


class TestParseInfo(object):
    
    def test_bad_parse_info_prefix(self):
        state = bytes_to_state(parse_info_to_bytes(
            parse_info_prefix=0xDEADBEEF,
        ))
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.BadParseInfoPrefix) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.parse_info_prefix == 0xDEADBEEF
    
    def test_bad_parse_code(self):
        state = bytes_to_state(parse_info_to_bytes(
            parse_code=0x11
        ))
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.BadParseCode) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.parse_code == 0x11
    
    def test_inconsistent_next_parse_offset(self):
        state = bytes_to_state(
            parse_info_to_bytes(
                parse_code=tables.ParseCodes.padding_data,
                next_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 10,
            ) +
            b"\x00"*9 +
            parse_info_to_bytes(
                parse_code=tables.ParseCodes.end_of_sequence,
                previous_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 9,
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
    
    @pytest.mark.parametrize("parse_code", [
        tables.ParseCodes.low_delay_picture,
        tables.ParseCodes.low_delay_picture_fragment,
        tables.ParseCodes.high_quality_picture,
        tables.ParseCodes.high_quality_picture_fragment,
    ])
    def test_allowed_zero_next_parse_offset_for_pictures(self, parse_code):
        state = bytes_to_state(parse_info_to_bytes(
            parse_code=parse_code,
            next_parse_offset=0,
        ))
        state["_generic_sequence_matcher"] = Matcher(".*")
        decoder.parse_info(state)
    
    @pytest.mark.parametrize("parse_code", [
        tables.ParseCodes.sequence_header,
        tables.ParseCodes.auxiliary_data,
        tables.ParseCodes.padding_data,
    ])
    def test_not_allowed_zero_next_parse_offset_for_non_pictures(self, parse_code):
        state = bytes_to_state(parse_info_to_bytes(
            parse_code=parse_code,
            next_parse_offset=0,
        ))
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.MissingNextParseOffset):
            decoder.parse_info(state)
    
    @pytest.mark.parametrize("parse_code", [
        tables.ParseCodes.sequence_header,
        tables.ParseCodes.auxiliary_data,
        tables.ParseCodes.padding_data,
    ])
    @pytest.mark.parametrize("next_parse_offset", [1, tables.PARSE_INFO_HEADER_BYTES-1])
    def test_never_allowed_invalid_offset(self, parse_code, next_parse_offset):
        state = bytes_to_state(parse_info_to_bytes(
            parse_code=parse_code,
            next_parse_offset=next_parse_offset,
        ))
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.InvalidNextParseOffset) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.next_parse_offset == next_parse_offset
    
    def test_non_zero_next_parse_offset_for_end_of_sequence(self):
        state = bytes_to_state(parse_info_to_bytes(
            parse_code=tables.ParseCodes.end_of_sequence,
            next_parse_offset=1,
        ))
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.NonZeroNextParseOffsetAtEndOfSequence) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.next_parse_offset == 1
    
    def test_non_zero_previous_parse_offset_for_start_of_sequence(self):
        state = bytes_to_state(parse_info_to_bytes(
            parse_code=tables.ParseCodes.end_of_sequence,
            previous_parse_offset=1,
        ))
        state["_generic_sequence_matcher"] = Matcher(".*")
        with pytest.raises(decoder.NonZeroPreviousParseOffsetAtStartOfSequence) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.previous_parse_offset == 1
    
    def test_inconsistent_previous_parse_offset(self):
        state = bytes_to_state(
            parse_info_to_bytes(
                parse_code=tables.ParseCodes.padding_data,
                next_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 10,
            ) +
            b"\x00"*10 +
            parse_info_to_bytes(
                parse_code=tables.ParseCodes.end_of_sequence,
                previous_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 9,
            )
        )
        state["_generic_sequence_matcher"] = Matcher(".*")
        
        decoder.parse_info(state)
        decoder.read_uint_lit(state, 10)
        with pytest.raises(decoder.InconsistentPreviousParseOffset) as exc_info:
            decoder.parse_info(state)
        
        assert exc_info.value.last_parse_info_offset == 0
        assert exc_info.value.previous_parse_offset == tables.PARSE_INFO_HEADER_BYTES + 9
        assert exc_info.value.true_parse_offset == tables.PARSE_INFO_HEADER_BYTES + 10
    
    def test_invalid_generic_sequence(self):
        state = bytes_to_state(parse_info_to_bytes(
            parse_code=tables.ParseCodes.end_of_sequence,
        ))
        state["_generic_sequence_matcher"] = Matcher("sequence_header")
        
        with pytest.raises(decoder.GenericInvalidSequence) as exc_info:
            decoder.parse_info(state)
        
        assert exc_info.value.parse_code is tables.ParseCodes.end_of_sequence
        assert exc_info.value.expected_parse_codes == [tables.ParseCodes.sequence_header]
        assert exc_info.value.expected_end is False
    
    @pytest.mark.parametrize("parse_code,allowed", [
        (tables.ParseCodes.padding_data, True),
        (tables.ParseCodes.low_delay_picture, False),
    ])
    def test_profile_restricts_allowed_parse_codes(self, parse_code, allowed):
        state = bytes_to_state(parse_info_to_bytes(
                parse_code=parse_code,
                next_parse_offset=tables.PARSE_INFO_HEADER_BYTES,
        ))
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
        state = bytes_to_state(parse_info_to_bytes(
            parse_code=tables.ParseCodes.end_of_sequence,
        ))
        state["_generic_sequence_matcher"] = Matcher(".*")
        state["_level_sequence_matcher"] = Matcher("sequence_header")
        
        with pytest.raises(decoder.LevelInvalidSequence) as exc_info:
            decoder.parse_info(state)
        
        assert exc_info.value.parse_code is tables.ParseCodes.end_of_sequence
        assert exc_info.value.expected_parse_codes == [tables.ParseCodes.sequence_header]
        assert exc_info.value.expected_end is False
