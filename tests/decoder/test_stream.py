import pytest

from io import BytesIO

from vc2_conformance import bitstream
from vc2_conformance import tables
from vc2_conformance import decoder

from vc2_conformance.state import State


def seriallise_parse_info(**kwargs):
    """
    Seriallise a ParseInfo block, returning a bytes object.
    """
    context = bitstream.ParseInfo(**kwargs)
    f = BytesIO()
    w = bitstream.BitstreamWriter(f)
    with bitstream.Serialiser(w, context) as ser:
        bitstream.parse_info(ser, State())
    w.flush()
    return f.getvalue()


def bitstream_to_state(bitstream):
    """Return a raedy-to-read state for the provided bitstream bytes."""
    f = BytesIO(bitstream)
    state = State()
    decoder.init_io(state, f)
    return state


def test_trailing_bytes_after_end_of_sequence():
    state = bitstream_to_state(
        seriallise_parse_info(parse_code=tables.ParseCodes.end_of_sequence) +
        b"\x00"
    )
    with pytest.raises(decoder.TrailingBytesAfterEndOfSequence):
        decoder.parse_sequence(state)


class TestParseInfo(object):
    
    def test_bad_parse_info_prefix(self):
        state = bitstream_to_state(seriallise_parse_info(
            parse_info_prefix=0xDEADBEEF,
        ))
        with pytest.raises(decoder.BadParseInfoPrefix) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.parse_info_prefix == 0xDEADBEEF
    
    def test_bad_parse_code(self):
        state = bitstream_to_state(seriallise_parse_info(
            parse_code=0x11
        ))
        with pytest.raises(decoder.BadParseCode) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.parse_code == 0x11
    
    def test_inconsistent_next_parse_offset(self):
        state = bitstream_to_state(
            seriallise_parse_info(
                parse_code=tables.ParseCodes.padding_data,
                next_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 10,
            ) +
            b"\x00"*9 +
            seriallise_parse_info(
                parse_code=tables.ParseCodes.end_of_sequence,
                previous_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 9,
            )
        )
        
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
        state = bitstream_to_state(seriallise_parse_info(
            parse_code=parse_code,
            next_parse_offset=0,
        ))
        decoder.parse_info(state)
    
    @pytest.mark.parametrize("parse_code", [
        tables.ParseCodes.sequence_header,
        tables.ParseCodes.auxiliary_data,
        tables.ParseCodes.padding_data,
    ])
    def test_not_allowed_zero_next_parse_offset_for_non_pictures(self, parse_code):
        state = bitstream_to_state(seriallise_parse_info(
            parse_code=parse_code,
            next_parse_offset=0,
        ))
        with pytest.raises(decoder.MissingNextParseOffset):
            decoder.parse_info(state)
    
    @pytest.mark.parametrize("parse_code", [
        tables.ParseCodes.sequence_header,
        tables.ParseCodes.auxiliary_data,
        tables.ParseCodes.padding_data,
    ])
    @pytest.mark.parametrize("next_parse_offset", [1, tables.PARSE_INFO_HEADER_BYTES-1])
    def test_never_allowed_invalid_offset(self, parse_code, next_parse_offset):
        state = bitstream_to_state(seriallise_parse_info(
            parse_code=parse_code,
            next_parse_offset=next_parse_offset,
        ))
        with pytest.raises(decoder.InvalidNextParseOffset) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.next_parse_offset == next_parse_offset
    
    def test_non_zero_next_parse_offset_for_end_of_sequence(self):
        state = bitstream_to_state(seriallise_parse_info(
            parse_code=tables.ParseCodes.end_of_sequence,
            next_parse_offset=1,
        ))
        with pytest.raises(decoder.NonZeroNextParseOffsetAtEndOfSequence) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.next_parse_offset == 1
    
    def test_non_zero_previous_parse_offset_for_start_of_sequence(self):
        state = bitstream_to_state(seriallise_parse_info(
            parse_code=tables.ParseCodes.end_of_sequence,
            previous_parse_offset=1,
        ))
        with pytest.raises(decoder.NonZeroPreviousParseOffsetAtStartOfSequence) as exc_info:
            decoder.parse_info(state)
        assert exc_info.value.previous_parse_offset == 1
    
    def test_inconsistent_previous_parse_offset(self):
        state = bitstream_to_state(
            seriallise_parse_info(
                parse_code=tables.ParseCodes.padding_data,
                next_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 10,
            ) +
            b"\x00"*10 +
            seriallise_parse_info(
                parse_code=tables.ParseCodes.end_of_sequence,
                previous_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 9,
            )
        )
        
        decoder.parse_info(state)
        decoder.read_uint_lit(state, 10)
        with pytest.raises(decoder.InconsistentPreviousParseOffset) as exc_info:
            decoder.parse_info(state)
        
        assert exc_info.value.last_parse_info_offset == 0
        assert exc_info.value.previous_parse_offset == tables.PARSE_INFO_HEADER_BYTES + 9
        assert exc_info.value.true_parse_offset == tables.PARSE_INFO_HEADER_BYTES + 10
