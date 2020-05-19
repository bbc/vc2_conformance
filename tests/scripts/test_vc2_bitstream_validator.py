import pytest

import sys

import traceback

from vc2_conformance.string_utils import wrap_paragraphs

from vc2_conformance.state import State

from vc2_conformance.decoder import parse_stream

from vc2_conformance.file_format import read

from vc2_conformance.py2x_compat import quote

from vc2_conformance import bitstream

import vc2_data_tables as tables

from vc2_conformance.scripts.vc2_bitstream_validator import (
    format_pseudocode_traceback,
    BitstreamValidator,
    parse_args,
)


def test_format_parse_code_traceback():
    # Capture a traceback resulting from the I/O subsystem not being
    # initialised

    try:
        parse_stream(State())
    except KeyError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        tb = traceback.extract_tb(exc_tb)

    assert format_pseudocode_traceback(tb) == (
        "* parse_stream (10.3)\n" "  * is_end_of_stream (A.0.0)"
    )


class TestBitstreamValidator(object):
    @pytest.fixture
    def output_name(self, tmpdir):
        return str(tmpdir.join("picture_%d.raw"))

    @pytest.fixture
    def filename(self, tmpdir):
        return str(tmpdir.join("bitstream.vc2"))

    @pytest.fixture
    def valid_bitstream(self, filename):
        """
        Creates a valid bitstream in the file whose name is returned by this
        fixture. This bitstream consists of two small pictures.


        A minimal bitstream with a pair of 4x4 pixel 4:2:0 8-bit pictures with
        picture numbers 100 and 101.
        """
        with open(filename, "wb") as f:
            w = bitstream.BitstreamWriter(f)
            seq = bitstream.Sequence(
                data_units=[
                    bitstream.DataUnit(
                        parse_info=bitstream.ParseInfo(
                            parse_code=tables.ParseCodes.sequence_header,
                            next_parse_offset=19,
                        ),
                        sequence_header=bitstream.SequenceHeader(
                            video_parameters=bitstream.SourceParameters(
                                frame_size=bitstream.FrameSize(
                                    custom_dimensions_flag=True,
                                    frame_width=4,
                                    frame_height=4,
                                ),
                                clean_area=bitstream.CleanArea(
                                    custom_clean_area_flag=True,
                                    left_offset=0,
                                    top_offset=0,
                                    clean_width=4,
                                    clean_height=4,
                                ),
                                color_diff_sampling_format=bitstream.ColorDiffSamplingFormat(  # noqa: E501
                                    custom_color_diff_format_flag=True,
                                    color_diff_format_index=tables.ColorDifferenceSamplingFormats.color_4_2_0,  # noqa: E501
                                ),
                            ),
                            picture_coding_mode=tables.PictureCodingModes.pictures_are_frames,  # noqa: E501
                        ),
                    ),
                    bitstream.DataUnit(
                        parse_info=bitstream.ParseInfo(
                            parse_code=tables.ParseCodes.high_quality_picture,
                            next_parse_offset=24,
                            previous_parse_offset=19,
                        ),
                        picture_parse=bitstream.PictureParse(
                            picture_header=bitstream.PictureHeader(picture_number=100,),
                        ),
                    ),
                    bitstream.DataUnit(
                        parse_info=bitstream.ParseInfo(
                            parse_code=tables.ParseCodes.high_quality_picture,
                            next_parse_offset=24,
                            previous_parse_offset=24,
                        ),
                        picture_parse=bitstream.PictureParse(
                            picture_header=bitstream.PictureHeader(picture_number=101,),
                        ),
                    ),
                    bitstream.DataUnit(
                        parse_info=bitstream.ParseInfo(
                            parse_code=tables.ParseCodes.end_of_sequence,
                            previous_parse_offset=24,
                        )
                    ),
                ]
            )
            with bitstream.Serialiser(w, seq, bitstream.vc2_default_values) as ser:
                bitstream.parse_sequence(ser, State())
            w.flush()

        return filename

    def test_valid_bitstream(self, valid_bitstream, output_name, capsys):
        v = BitstreamValidator(valid_bitstream, True, 0, output_name)
        assert v.run() == 0

        # Check no error reported and that status line is shown
        stdout, stderr = capsys.readouterr()
        assert "%] Starting bitstream validation" in stderr
        assert "%] Decoded picture written to {}".format(output_name % 0) in stderr
        assert "%] Decoded picture written to {}".format(output_name % 1) in stderr
        assert stdout == (
            "No errors found in bitstream. "
            "Verify decoded pictures to confirm conformance.\n"
        )

        # Check picture files are as expected
        for i, expected_picture_number in enumerate([100, 101]):
            picture, video_parameters, picture_coding_mode = read(output_name % i)
            assert picture["pic_num"] == expected_picture_number

    def test_valid_multi_sequence_stream(
        self, tmpdir, valid_bitstream, output_name, capsys,
    ):
        filename = str(tmpdir.join("multi_sequence.vc2"))

        with open(filename, "wb") as f:
            f.write(open(valid_bitstream, "rb").read() * 2)

        v = BitstreamValidator(filename, True, 0, output_name)
        assert v.run() == 0

        # Check no error reported and that status line is shown
        stdout, stderr = capsys.readouterr()
        assert "%] Starting bitstream validation" in stderr
        assert "%] Decoded picture written to {}".format(output_name % 0) in stderr
        assert "%] Decoded picture written to {}".format(output_name % 1) in stderr
        assert "%] Decoded picture written to {}".format(output_name % 2) in stderr
        assert "%] Decoded picture written to {}".format(output_name % 3) in stderr
        assert stdout == (
            "No errors found in bitstream. "
            "Verify decoded pictures to confirm conformance.\n"
        )

        # Check picture files are as expected
        for i, expected_picture_number in enumerate([100, 101, 100, 101]):
            picture, video_parameters, picture_coding_mode = read(output_name % i)
            assert picture["pic_num"] == expected_picture_number

    def test_disabled_status_line(self, valid_bitstream, output_name, capsys):
        v = BitstreamValidator(valid_bitstream, False, 0, output_name)
        assert v.run() == 0

        # Check no status messages are shown
        stdout, stderr = capsys.readouterr()
        assert stderr == ""

    def test_io_error(self, filename, output_name, capsys):
        # File does not exist
        v = BitstreamValidator(filename, False, 0, output_name)
        assert v.run() == 1

        stdout, stderr = capsys.readouterr()

        assert stdout == ""
        assert "No such file or directory" in stderr

    def test_null_bitstream_warning(self, filename, output_name, capsys):
        # Create an empty file
        with open(filename, "wb"):
            pass

        v = BitstreamValidator(filename, False, 0, output_name)
        assert v.run() == 0

        stdout, stderr = capsys.readouterr()

        assert stderr == "Warning: 0 bytes read, bitstream is empty.\n"
        assert stdout == (
            "No errors found in bitstream. "
            "Verify decoded pictures to confirm conformance.\n"
        )

    def test_invalid_bitstream(self, filename, output_name, capsys):
        with open(filename, "wb") as f:
            f.write(b"NOPE")

        v = BitstreamValidator(filename, False, 0, output_name)
        assert v.run() == 2

        stdout, stderr = capsys.readouterr()

        assert (
            wrap_paragraphs(stdout)
            == wrap_paragraphs(
                """
                Conformance error at bit offset 32
                ==================================

                An invalid prefix, 0x4E4F5045, was encountered in a parse info
                block (10.5.1). The expected prefix is 0x42424344.


                Details
                -------

                Is the parse_info block byte aligned (10.5.1)?

                Did the preceeding data unit over- or under-run the expected
                length? For example, were any unused bits in a picture slice
                filled with the correct number of padding bits (A.4.2)?


                Suggested bitstream viewer commands
                -----------------------------------

                To view the offending part of the bitstream:

                    vc2-bitstream-viewer {} --offset 32


                Pseudocode traceback
                --------------------

                Most recent call last:

                * parse_stream (10.3)
                  * parse_sequence (10.4.1)
                    * parse_info (10.5.1)
        """.format(  # noqa: E501
                    quote(filename)
                )
            ).strip()
        )
        assert stderr.endswith("error: non-conformant bitstream (see above)\n")

    @pytest.mark.parametrize("verbosity", [0, 1])
    def test_internal_error(self, valid_bitstream, capsys, verbosity):
        # Provide an invalid output format string (these are caught by the
        # argument parser normally) which will crash the
        # _output_picture_callback.
        v = BitstreamValidator(valid_bitstream, False, verbosity, "bad_output_name")

        assert v.run() == 3

        stdout, stderr = capsys.readouterr()
        assert "internal error" in stderr
        assert "TypeError" in stderr

        # Make sure traceback included in verbosity is non-zero
        if verbosity == 0:
            assert "Traceback" not in stderr
        else:
            assert "Traceback" in stderr


def test_parse_args_output_name_validation():
    args = parse_args(["foo", "--output", "has_pattern_%d.raw"])
    assert args.output == "has_pattern_%d.raw"

    with pytest.raises(SystemExit):
        parse_args(["foo", "--output", "no_pattern_sign.raw"])
