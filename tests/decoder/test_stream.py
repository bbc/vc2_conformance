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
