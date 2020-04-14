from decoder_test_utils import populate_parse_offsets, serialise_to_bytes

from vc2_conformance import bitstream

import vc2_data_tables as tables


class TestPopulateParseOffsets(object):
    def test_empty_sequence(self):
        seq = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.end_of_sequence,
                    ),
                ),
            ]
        )

        populate_parse_offsets(seq)

        assert seq["data_units"][0]["parse_info"]["next_parse_offset"] == 0
        assert seq["data_units"][0]["parse_info"]["previous_parse_offset"] == 0

    def test_non_empty_sequence(self):
        sh = bitstream.SequenceHeader()

        seq = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.sequence_header,
                    ),
                    sequence_header=sh,
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.sequence_header,
                    ),
                    sequence_header=sh,
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.end_of_sequence,
                    ),
                ),
            ]
        )

        sh_length = len(serialise_to_bytes(sh))
        populate_parse_offsets(seq)

        assert seq["data_units"][0]["parse_info"]["next_parse_offset"] == (
            tables.PARSE_INFO_HEADER_BYTES + sh_length
        )
        assert seq["data_units"][0]["parse_info"]["previous_parse_offset"] == 0

        assert seq["data_units"][1]["parse_info"]["next_parse_offset"] == (
            tables.PARSE_INFO_HEADER_BYTES + sh_length
        )
        assert seq["data_units"][1]["parse_info"]["previous_parse_offset"] == (
            tables.PARSE_INFO_HEADER_BYTES + sh_length
        )

        assert seq["data_units"][2]["parse_info"]["next_parse_offset"] == 0
        assert seq["data_units"][2]["parse_info"]["previous_parse_offset"] == (
            tables.PARSE_INFO_HEADER_BYTES + sh_length
        )
