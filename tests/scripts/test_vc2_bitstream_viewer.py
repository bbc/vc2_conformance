import re
import sys
import pytest

from mock import Mock

from io import BytesIO
from shlex import split

from bitarray import bitarray

from vc2_conformance import bitstream

from vc2_conformance.pseudocode import video_parameters

import vc2_data_tables as tables

from vc2_conformance.pseudocode.state import State

from vc2_conformance.scripts.vc2_bitstream_viewer import (
    relative_int,
    relative_to_abs_index,
    is_internal_error,
    _call,
    most_recent_pseudocode_function,
    format_path_summary,
    format_header_line,
    format_value_line,
    format_omission_line,
    BitstreamViewer,
    parse_args,
    main,
)


@pytest.mark.parametrize(
    "string,expected,exception",
    [
        # Plain integers
        ("0", (False, 0), None),
        ("123", (False, 123), None),
        ("-123", (False, -123), None),
        # Relative integers
        ("+0", (True, 0), None),
        ("+123", (True, 123), None),
        # Invalid integers
        ("", None, ValueError),
        ("nope", None, ValueError),
        ("+-123", None, ValueError),
        ("-+123", None, ValueError),
        ("--123", None, ValueError),
        ("++123", None, ValueError),
        # Non-string input
        (123, None, ValueError),
    ],
)
def test_relative_int(string, expected, exception):
    if exception is None:
        assert relative_int(string) == expected
    else:
        with pytest.raises(exception):
            relative_int(string)


@pytest.mark.parametrize(
    "num,length,expected",
    [
        # Non-relative values
        (0, 0, 0),
        (0, 100, 0),
        (123, 0, 123),
        (123, 100, 123),
        # Relative numbers
        (-1, 100, 99),
        (-10, 100, 90),
    ],
)
def test_relative_to_abs_index(num, length, expected):
    assert relative_to_abs_index(num, length) == expected


class TestIsInternalError(object):
    def test_error_completely_outside_script(self):
        # Errors occuring outside the script (and not called by the script) are
        # considered external
        try:
            raise Exception()
        except:  # noqa: E722
            exc_type, exc_value, exc_tb = sys.exc_info()

        assert is_internal_error(exc_tb) is False

    def test_error_within_script(self):
        # Errors occuring within the script are (obviously) internal
        try:
            relative_int("not an int")
        except:  # noqa: 722
            exc_type, exc_value, exc_tb = sys.exc_info()

        assert is_internal_error(exc_tb) is True

    def test_error_in_function_called_from_script(self):
        # If the script calls a function (not inside the VC-2 bitstream
        # pseudocode functions) which fails, this is still to be considered
        # internal
        def fail():
            raise Exception()

        try:
            _call(fail)
        except:  # noqa: 722
            exc_type, exc_value, exc_tb = sys.exc_info()

        assert is_internal_error(exc_tb) is True

    @pytest.mark.parametrize("via_script", [False, True])
    def test_error_in_vc2_function(self, via_script):
        # Will fail due to 'major_version' not being defined in the state.
        def run():
            r = bitstream.BitstreamReader(BytesIO(b"\xFF" * 100))
            with bitstream.Deserialiser(r) as serdes:
                bitstream.transform_parameters(serdes, State())

        # If a crash occurs in the VC-2 bitstream code, this is external, even
        # if called via the script
        try:
            if via_script:
                _call(run)
            else:
                run()
        except KeyError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        assert is_internal_error(exc_tb) is False

    @pytest.mark.parametrize("via_script", [False, True])
    def test_error_in_vc2_called_function(self, via_script):
        # Will fail in set_source_defaults due to an unsupported
        # base_video_format
        def run():
            r = bitstream.BitstreamReader(BytesIO(b"\xFF" * 100))
            with bitstream.Deserialiser(r) as serdes:
                bitstream.source_parameters(serdes, State(), -1)

        # If a crash occurs in the VC-2 bitstream code, this is external, even
        # if called via the script
        try:
            if via_script:
                _call(run)
            else:
                run()
        except KeyError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        assert is_internal_error(exc_tb) is False

    @pytest.mark.parametrize("via_script", [False, True])
    def test_error_in_script_function_called_via_vc2(self, via_script):
        # Will fail when '_call' is used as a monitor function (wrong
        # number of arguments).
        def run():
            r = bitstream.BitstreamReader(BytesIO(b"\xFF" * 100))
            with bitstream.MonitoredDeserialiser(io=r, monitor=_call) as serdes:
                bitstream.parse_info(serdes, State())

        # In the stack trace caused by run() above, 'parse_info' (in the VC-2
        # pseudo code) will be indirectly responsible for invalidly calling
        # '_call' (resulting in a TypeError in the script code). This is an
        # internal error
        try:
            if via_script:
                _call(run)
            else:
                run()
        except TypeError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        assert is_internal_error(exc_tb) is True


class TestMostRecentPseudocodeFunction(object):
    def test_function_in_bitstream_module(self):
        try:
            # Should crash due to missing 'major_version' in state
            bitstream.transform_parameters(Mock(), State())
        except:  # noqa: 722
            exc_type, exc_value, exc_tb = sys.exc_info()
        assert (
            most_recent_pseudocode_function(exc_tb) == "transform_parameters (12.4.1)"
        )

    def test_function_in_main_codebase(self):
        try:
            # Should crash due to invalid base video format index
            video_parameters.set_source_defaults(-1)
        except:  # noqa: 722
            exc_type, exc_value, exc_tb = sys.exc_info()
        assert most_recent_pseudocode_function(exc_tb) == "set_source_defaults (11.4.2)"


def test_path_summary():
    assert format_path_summary([]) == ""
    assert format_path_summary(["foo", 1, "bar", 2]) == "foo: 1: bar: 2"


def test_format_xxx_line_functions():
    # Tested in one test to ensure consistency
    string = "\n".join(
        [
            format_header_line("> header"),
            format_value_line(123, bitarray("0" * 48), "> > label", "> >", False),
            format_omission_line(171, 1024),
            format_value_line(1195, bitarray("0" * 48), "> > label", "> >", True),
        ]
    )

    assert string == (
        "                                                  > header\n"
        "000000000123: 00000000000000000000000000000000    > > label\n"
        "              0000000000000000                    > >\n"
        "000000000171: <1024 bits omitted>                 ...\n"
        "000000001195: 00000000000000000000000000000000    > > label\n"
        "              0000000000000000*                   > >"
    )


@pytest.fixture
def minimal_sequence_bitstream_fname(tmpdir):
    fname = str(tmpdir.join("bitstream.vc2"))

    with open(fname, "wb") as f:
        context = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.end_of_sequence,
                    )
                ),
            ]
        )
        w = bitstream.BitstreamWriter(f)
        with bitstream.Serialiser(w, context, bitstream.vc2_default_values) as ser:
            bitstream.parse_sequence(ser, State())

    return fname


@pytest.fixture
def padding_sequence_bitstream_fname(tmpdir):
    fname = str(tmpdir.join("bitstream.vc2"))

    with open(fname, "wb") as f:
        context = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.padding_data,
                        next_parse_offset=tables.PARSE_INFO_HEADER_BYTES + 2,
                    ),
                    padding=bitstream.Padding(bytes=b"\xAA\xFF"),
                ),
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_code=tables.ParseCodes.end_of_sequence,
                    )
                ),
            ]
        )
        w = bitstream.BitstreamWriter(f)
        with bitstream.Serialiser(w, context, bitstream.vc2_default_values) as ser:
            bitstream.parse_sequence(ser, State())

    return fname


@pytest.fixture
def bad_parse_info_prefix_bitstream_fname(tmpdir):
    fname = str(tmpdir.join("bitstream.vc2"))

    with open(fname, "wb") as f:
        context = bitstream.Sequence(
            data_units=[
                bitstream.DataUnit(
                    parse_info=bitstream.ParseInfo(
                        parse_info_prefix=0xDEADBEEF,
                        parse_code=tables.ParseCodes.end_of_sequence,
                    ),
                ),
            ]
        )
        w = bitstream.BitstreamWriter(f)
        with bitstream.Serialiser(w, context, bitstream.vc2_default_values) as ser:
            bitstream.parse_sequence(ser, State())

    return fname


@pytest.fixture
def truncated_bitstream_fname(tmpdir, minimal_sequence_bitstream_fname):
    f = tmpdir.join("bitstream.vc2")
    f.write_binary(open(minimal_sequence_bitstream_fname, "rb").read(7))
    return str(f)


@pytest.fixture
def missing_sequence_header_bitstream_fname(tmpdir):
    fname = str(tmpdir.join("bitstream.vc2"))

    with open(fname, "wb") as f:
        w = bitstream.BitstreamWriter(f)

        state = State(major_version=3)

        context = bitstream.ParseInfo(parse_code=tables.ParseCodes.high_quality_picture)
        with bitstream.Serialiser(w, context, bitstream.vc2_default_values) as ser:
            bitstream.parse_info(ser, state)

        context = bitstream.PictureParse(
            wavelet_transform=bitstream.WaveletTransform(
                transform_parameters=bitstream.TransformParameters(
                    slice_parameters=bitstream.SliceParameters(slices_x=0, slices_y=0,),
                ),
            ),
        )
        with bitstream.Serialiser(w, context, bitstream.vc2_default_values) as ser:
            bitstream.picture_parse(ser, state)

    return fname


class TestBitstreamViewer(object):
    @pytest.mark.parametrize(
        "shown,hidden,exp_shown,exp_hidden",
        [
            # Empty case
            ([], [], None, None),
            # Check populate recursively
            (
                ["transform_parameters"],
                [],
                set(
                    [
                        bitstream.TransformParameters,
                        bitstream.ExtendedTransformParameters,
                        bitstream.SliceParameters,
                        bitstream.QuantMatrix,
                    ]
                ),
                None,
            ),
            (
                [],
                ["transform_parameters"],
                None,
                set(
                    [
                        bitstream.TransformParameters,
                        bitstream.ExtendedTransformParameters,
                        bitstream.SliceParameters,
                        bitstream.QuantMatrix,
                    ]
                ),
            ),
            # When both hidden and shown used, hidden values are removed from
            # 'shown' set and then no 'hidden' set it given.
            (
                ["transform_parameters"],
                ["slice_parameters"],
                set(
                    [
                        bitstream.TransformParameters,
                        bitstream.ExtendedTransformParameters,
                        bitstream.QuantMatrix,
                    ]
                ),
                None,
            ),
        ],
    )
    def test_show_hide_sets(self, shown, hidden, exp_shown, exp_hidden):
        v = BitstreamViewer(
            None, shown_pseudocode_names=shown, hidden_pseudocode_names=hidden,
        )

        if exp_shown is None:
            assert v._shown_types is None
        else:
            assert v._shown_types == exp_shown

        if exp_hidden is None:
            assert v._hidden_types is None
        else:
            assert v._hidden_types == exp_hidden

    @pytest.mark.parametrize("verbosity", [0, 1, 2])
    def test_print_error_no_context(self, verbosity, capsys):
        # Check that error messages can be printed at all levels of verbosity
        # even when nothing is opened and no traceback has ocurred
        v = BitstreamViewer(None, verbose=verbosity)
        v._print_error("foobar")
        assert capsys.readouterr().err.endswith(": error: foobar\n")

    def print_error_with_mock_state(self, verbosity, message):
        v = BitstreamViewer(None, verbose=verbosity)

        v._last_tell = (1, 7)

        v._reader = bitstream.BitstreamReader(BytesIO(b"\xFF" + b"\xAA" * 16 + b"\x00"))
        v._reader.seek(1, 3)

        v._serdes = Mock(path=Mock(return_value=["foo", "bar"]))

        try:
            raise KeyError("missing")
        except KeyError:
            v._print_error(message)

    def test_print_error_with_context_verbose_0(self, capsys):
        self.print_error_with_mock_state(0, "foobar")
        assert capsys.readouterr().err.endswith(": error: foobar\n")

    def test_print_error_with_context_verbose_1(self, capsys):
        self.print_error_with_mock_state(1, "foobar")
        assert (
            re.match(
                "000000000008: 10101010101010101010101010101010    <next 128 bits>\n"
                "              10101010101010101010101010101010    \n"
                "              10101010101010101010101010101010    \n"
                "              10101010101010101010101010101010    \n"
                ".*: offset: 12\n"
                ".*: target: foo: bar\n"
                ".*: error: foobar\n",
                capsys.readouterr().err,
            )
            is not None
        )

    def test_print_error_with_context_verbose_2(self, capsys):
        self.print_error_with_mock_state(2, "foobar")
        err = capsys.readouterr().err

        assert err.startswith(
            "000000000008: 10101010101010101010101010101010    <next 128 bits>\n"
            "              10101010101010101010101010101010    \n"
            "              10101010101010101010101010101010    \n"
            "              10101010101010101010101010101010    \n"
            "Traceback"
        )

        assert (
            re.match(
                "KeyError: 'missing'\n"
                ".*: offset: 12\n"
                ".*: target: foo: bar\n"
                ".*: error: foobar",
                "\n".join(err.splitlines()[-4:]),
            )
            is not None
        )

    def test_print_value(self, capsys):
        v = BitstreamViewer(None)

        v._reader = Mock()
        v._reader.bits_remaining = None

        v._serdes = Mock()
        v._serdes.path.return_value = ["foo", "parse_info", "parse_code"]
        v._serdes.cur_context = bitstream.ParseInfo(
            parse_info_prefix=tables.PARSE_INFO_PREFIX,
            parse_code=0x10,
            next_parse_offset=123,
            previous_parse_offset=0,
        )

        # Test that:
        # * First time, the whole path should be printed
        # * Formatted value should be shown
        v._print_value(123, bitarray("1010"), "parse_code", 0x10)
        assert capsys.readouterr().out == (
            "                                                  +- foo:\n"
            "                                                  | +- parse_info:\n"
            "000000000123: 1010                                | | +- parse_code: end_of_sequence (0x10)\n"
        )

        # Test that when only the tail of the the path changes, no headers are
        # repeated.
        v._serdes.path.return_value = ["foo", "parse_info", "next_parse_offset"]
        v._print_value(123, bitarray("1010"), "next_parse_offset", 123)
        assert capsys.readouterr().out == (
            "000000000123: 1010                                | | +- next_parse_offset: 123\n"
        )

        # Test that:
        # * When the path changes only the minimum set of changes are shown
        #   ordinary dict values can be printed
        # * Ordinary dict values are printed using 'str'
        v._serdes.path.return_value = ["foo", "bar", "baz", "qux"]
        v._serdes.cur_context = {"qux": 321}  # An ordinary dict
        v._print_value(123, bitarray("1010"), "qux", 321)
        assert capsys.readouterr().out == (
            "                                                  | +- bar:\n"
            "                                                  | | +- baz:\n"
            "000000000123: 1010                                | | | +- qux: 321\n"
        )

        # Test that when changing only an intermediate path entry, the whole
        # subtree is shown
        v._serdes.path.return_value = ["foo", "BAR", "baz", "qux"]
        v._print_value(123, bitarray("1010"), "qux", 321)
        assert capsys.readouterr().out == (
            "                                                  | +- BAR:\n"
            "                                                  | | +- baz:\n"
            "000000000123: 1010                                | | | +- qux: 321\n"
        )

        # Test that:
        # * Array values are formatted appropriately
        # * Paths can become less deeply nested
        v._serdes.path.return_value = ["slice", "y_transform", 1]
        v._serdes.cur_context = bitstream.LDSlice(y_transform=[0, 123])
        v._print_value(123, bitarray("1010"), "y_transform", 123)
        assert capsys.readouterr().out == (
            "                                                  +- slice:\n"
            "                                                  | +- y_transform:\n"
            "000000000123: 1010                                | | +- 1: 123\n"
        )

    def test_print_internal_state(self, capsys):
        v = BitstreamViewer(None)

        v._state = State(major_version=3, minor_version=0)

        v._print_internal_state()
        assert capsys.readouterr().out == (
            "----------------------------------------------\n"
            "State:\n"
            "  major_version: 3\n"
            "  minor_version: 0\n"
            "----------------------------------------------\n"
        )

    def test_print_omitted_bits(self, capsys):
        v = BitstreamViewer(None)

        v._last_displayed_tell = (1, 7)

        v._print_omitted_bits((2, 3))
        assert capsys.readouterr().out == (
            "000000000008: <12 bits omitted>                   ...\n"
        )

    @pytest.mark.parametrize(
        "kwargs",
        [
            # Defaults
            {},
            # Explicitly include first bit
            {"from_offset": 0},
            # Exclude few enough bits that we still include the whole last value
            {"to_offset": -1},
            {"to_offset": -31},
        ],
    )
    def test_normal_display(self, capsys, minimal_sequence_bitstream_fname, kwargs):
        v = BitstreamViewer(minimal_sequence_bitstream_fname, **kwargs)
        assert v.run() == 0

        # Should include whole data structure and end as expected.
        assert capsys.readouterr().out == (
            "                                                  +- sequences:\n"
            "                                                  | +- 0:\n"
            "                                                  | | +- data_units:\n"
            "                                                  | | | +- 0:\n"
            "                                                  | | | | +- parse_info:\n"
            "000000000000:                                     | | | | | +- padding: 0b\n"
            "000000000000: 01000010010000100100001101000100    | | | | | +- parse_info_prefix: Correct (0x42424344)\n"
            "000000000032: 00010000                            | | | | | +- parse_code: end_of_sequence (0x10)\n"
            "000000000040: 00000000000000000000000000000000    | | | | | +- next_parse_offset: 0\n"
            "000000000072: 00000000000000000000000000000000    | | | | | +- previous_parse_offset: 0\n"
        )

    @pytest.mark.parametrize(
        "kwargs",
        [
            # Clip off first and last value exactly
            {"from_offset": 32, "to_offset": -32},  # Relative
            {"from_offset": 32, "to_offset": 32 + 8 + 32},  # Absolute
            # Clip off some of the parse_code and next_parse_offset too but not
            # enough to prevent them being displayed
            {"from_offset": 33, "to_offset": -33},
            {"from_offset": 39, "to_offset": -63},
        ],
    )
    def test_from_to_display(self, capsys, minimal_sequence_bitstream_fname, kwargs):
        v = BitstreamViewer(minimal_sequence_bitstream_fname, **kwargs)
        assert v.run() == 0

        # Should include whole data structure and end as expected.
        assert capsys.readouterr().out == (
            "000000000000: <32 bits omitted>                   ...\n"
            "                                                  +- sequences:\n"
            "                                                  | +- 0:\n"
            "                                                  | | +- data_units:\n"
            "                                                  | | | +- 0:\n"
            "                                                  | | | | +- parse_info:\n"
            "000000000032: 00010000                            | | | | | +- parse_code: end_of_sequence (0x10)\n"
            "000000000040: 00000000000000000000000000000000    | | | | | +- next_parse_offset: 0\n"
        )

    def test_filtered_display_show(self, capsys, padding_sequence_bitstream_fname):
        v = BitstreamViewer(
            padding_sequence_bitstream_fname, shown_pseudocode_names=["padding"],
        )
        assert v.run() == 0

        assert capsys.readouterr().out == (
            "000000000000: <104 bits omitted>                  ...\n"
            "                                                  +- sequences:\n"
            "                                                  | +- 0:\n"
            "                                                  | | +- data_units:\n"
            "                                                  | | | +- 0:\n"
            "                                                  | | | | +- padding:\n"
            "000000000104:                                     | | | | | +- padding: 0b\n"
            "000000000104: 1010101011111111                    | | | | | +- bytes: 0xAA_FF\n"
            "000000000120: <104 bits omitted>                  ...\n"
        )

    def test_filtered_display_hide(self, capsys, padding_sequence_bitstream_fname):
        v = BitstreamViewer(
            padding_sequence_bitstream_fname, hidden_pseudocode_names=["parse_info"],
        )
        assert v.run() == 0

        assert capsys.readouterr().out == (
            "000000000000: <104 bits omitted>                  ...\n"
            "                                                  +- sequences:\n"
            "                                                  | +- 0:\n"
            "                                                  | | +- data_units:\n"
            "                                                  | | | +- 0:\n"
            "                                                  | | | | +- padding:\n"
            "000000000104:                                     | | | | | +- padding: 0b\n"
            "000000000104: 1010101011111111                    | | | | | +- bytes: 0xAA_FF\n"
            "000000000120: <104 bits omitted>                  ...\n"
        )

    def test_show_internal_state(self, capsys, padding_sequence_bitstream_fname):
        v = BitstreamViewer(padding_sequence_bitstream_fname, show_internal_state=True)
        assert v.run() == 0

        assert capsys.readouterr().out == (
            "                                                  +- sequences:\n"
            "                                                  | +- 0:\n"
            "                                                  | | +- data_units:\n"
            "                                                  | | | +- 0:\n"
            "                                                  | | | | +- parse_info:\n"
            "000000000000:                                     | | | | | +- padding: 0b\n"
            "000000000000: 01000010010000100100001101000100    | | | | | +- parse_info_prefix: Correct (0x42424344)\n"
            "000000000032: 00110000                            | | | | | +- parse_code: padding_data (0x30)\n"
            "000000000040: 00000000000000000000000000001111    | | | | | +- next_parse_offset: 15\n"
            "000000000072: 00000000000000000000000000000000    | | | | | +- previous_parse_offset: 0\n"
            "                                                  | | | | +- padding:\n"
            "000000000104:                                     | | | | | +- padding: 0b\n"
            "000000000104: 1010101011111111                    | | | | | +- bytes: 0xAA_FF\n"
            "----------------------------------------------\n"
            "State:\n"
            "  parse_code: padding_data (0x30)\n"
            "  next_parse_offset: 15\n"
            "  previous_parse_offset: 0\n"
            "----------------------------------------------\n"
            "                                                  | | | +- 1:\n"
            "                                                  | | | | +- parse_info:\n"
            "000000000120:                                     | | | | | +- padding: 0b\n"
            "000000000120: 01000010010000100100001101000100    | | | | | +- parse_info_prefix: Correct (0x42424344)\n"
            "000000000152: 00010000                            | | | | | +- parse_code: end_of_sequence (0x10)\n"
            "000000000160: 00000000000000000000000000000000    | | | | | +- next_parse_offset: 0\n"
            "000000000192: 00000000000000000000000000000000    | | | | | +- previous_parse_offset: 0\n"
            "----------------------------------------------\n"
            "State:\n"
            "  parse_code: end_of_sequence (0x10)\n"
            "  next_parse_offset: 0\n"
            "  previous_parse_offset: 0\n"
            "----------------------------------------------\n"
        )

    def test_clear_previous_data_units(self, padding_sequence_bitstream_fname):
        v = BitstreamViewer(
            padding_sequence_bitstream_fname, shown_pseudocode_names=["padding"],
        )
        assert v.run() == 0
        assert len(v._serdes.context["sequences"][0]["data_units"]) == 2
        assert v._serdes.context["sequences"][0]["data_units"][0] is None
        assert v._serdes.context["sequences"][0]["data_units"][1] is not None

    def test_check_parse_info_prefix(
        self, capsys, bad_parse_info_prefix_bitstream_fname
    ):
        # Checking enabled: should stop on bad prefix
        v = BitstreamViewer(
            bad_parse_info_prefix_bitstream_fname, check_parse_info_prefix=True
        )
        assert v.run() == 2

        out, err = capsys.readouterr()
        assert out == (
            "                                                  +- sequences:\n"
            "                                                  | +- 0:\n"
            "                                                  | | +- data_units:\n"
            "                                                  | | | +- 0:\n"
            "                                                  | | | | +- parse_info:\n"
            "000000000000:                                     | | | | | +- padding: 0b\n"
            "000000000000: 11011110101011011011111011101111    | | | | | +- parse_info_prefix: INCORRECT (0xDEADBEEF)\n"
        )
        assert err.endswith(": error: invalid parse_info prefix (0xDEADBEEF)\n")

        # Disable checking should result in non-crashing run
        v = BitstreamViewer(
            bad_parse_info_prefix_bitstream_fname, check_parse_info_prefix=False
        )
        assert v.run() == 0
        out, err = capsys.readouterr()
        assert out == (
            "                                                  +- sequences:\n"
            "                                                  | +- 0:\n"
            "                                                  | | +- data_units:\n"
            "                                                  | | | +- 0:\n"
            "                                                  | | | | +- parse_info:\n"
            "000000000000:                                     | | | | | +- padding: 0b\n"
            "000000000000: 11011110101011011011111011101111    | | | | | +- parse_info_prefix: INCORRECT (0xDEADBEEF)\n"
            "000000000032: 00010000                            | | | | | +- parse_code: end_of_sequence (0x10)\n"
            "000000000040: 00000000000000000000000000000000    | | | | | +- next_parse_offset: 0\n"
            "000000000072: 00000000000000000000000000000000    | | | | | +- previous_parse_offset: 0\n"
        )
        assert err == ""

    def test_report_eof(self, capsys, truncated_bitstream_fname):
        v = BitstreamViewer(truncated_bitstream_fname, verbose=1)
        assert v.run() == 3

        out, err = capsys.readouterr()
        assert out == (
            "                                                  +- sequences:\n"
            "                                                  | +- 0:\n"
            "                                                  | | +- data_units:\n"
            "                                                  | | | +- 0:\n"
            "                                                  | | | | +- parse_info:\n"
            "000000000000:                                     | | | | | +- padding: 0b\n"
            "000000000000: 01000010010000100100001101000100    | | | | | +- parse_info_prefix: Correct (0x42424344)\n"
            "000000000032: 00010000                            | | | | | +- parse_code: end_of_sequence (0x10)\n"
        )
        assert (
            re.match(
                r"000000000040: 0000000000000000                    <next 16 bits>\n"
                r".*: offset: 56\n"
                r".*: target: sequences: 0: data_units: 0: parse_info\n"
                r".*: error: reached the end of the file while parsing parse_info \(10.5.1\)\n",
                err,
            )
            is not None
        )

    def test_report_parse_errors(self, capsys, missing_sequence_header_bitstream_fname):
        v = BitstreamViewer(missing_sequence_header_bitstream_fname,)
        assert v.run() == 4

        out, err = capsys.readouterr()
        assert err.endswith(
            ": error: transform_parameters (12.4.1) failed to parse bitstream (KeyError: 'major_version') (missing sequence_header, fragment or earlier out of range value?)\n"
        )


class TestParseArgs(object):
    def test_filename(self):
        assert parse_args(split("foo/bar.vc2")).bitstream == "foo/bar.vc2"

    def test_status_display(self):
        assert parse_args(split("foo")).no_status is False
        assert parse_args(split("foo --no-status")).no_status is True

    def test_verbosity(self):
        assert parse_args(split("foo")).verbose == 0
        assert parse_args(split("foo -v")).verbose == 1
        assert parse_args(split("foo -vv")).verbose == 2

    def test_show_internal_state(self):
        assert parse_args(split("foo")).show_internal_state is False
        assert parse_args(split("foo -i")).show_internal_state is True

    def test_ignore_parse_info_prefix(self):
        assert parse_args(split("foo")).ignore_parse_info_prefix is False
        assert parse_args(split("foo -p")).ignore_parse_info_prefix is True

    def test_num_trailing_bits(self):
        assert parse_args(split("foo")).num_trailing_bits == 128
        assert parse_args(split("foo -b 1234")).num_trailing_bits == 1234

    @pytest.mark.parametrize(
        "args,exp_from,exp_to",
        [
            # Default: Whole file
            ("", 0, -1),
            # Explicit from and to
            ("-f 100", 100, -1),
            ("-t 100", 0, 100),
            ("-f 100 -t 200", 100, 200),
            # From/to relative to end
            ("-f -100 -t -200", -100, -200),
            # 'to' relative to 'from'
            ("-f 100 -t+5", 100, 105),
            ("-f -100 -t+5", -100, -95),
            # Offset
            ("-o 1000", 872, 1128),
            ("-o 1000 -C 100", 900, 1100),
            ("-o 1000 -B 100", 900, 1000),
            ("-o 1000 -A 100", 1000, 1100),
            ("-o 1000 -B 100 -A 200", 900, 1200),
            ("-o -1000", -1128, -872),
            # Offset gets clamped at the start/end of the file
            ("-o 100", 0, 228),
            ("-o -100", -228, -1),
        ],
    )
    def test_from_and_to_offset(self, args, exp_from, exp_to):
        args = parse_args(split("foo {}".format(args)))
        assert args.from_offset == exp_from
        assert args.to_offset == exp_to

    def test_show(self):
        assert parse_args(split("foo")).show == []
        assert parse_args(split("foo -s parse_info -s sequence_header")).show == [
            "parse_info",
            "sequence_header",
        ]

    def test_hide(self):
        assert parse_args(split("foo")).hide == []
        assert parse_args(split("foo -H parse_info -H sequence_header -S")).hide == [
            "parse_info",
            "sequence_header",
            "slice",
        ]

    @pytest.mark.parametrize(
        "args,message_pattern",
        [
            # No file
            ("", r".*bitstream.*|.*too few arguments.*"),
            # Invalid bit count
            ("foo -b NOT_AN_INT", r".*int.*"),
            # Invalid 'from'/'to'
            ("foo -f bar", r".*int.*"),
            ("foo -t bar", r".*relative_int.*"),
            ("foo -t +-1 ", r".*relative_int.*"),
            # Use of context arguments with from/to
            ("foo -A 10", r".*may only be used with --offset.*"),
            ("foo -B 10", r".*may only be used with --offset.*"),
            ("foo -C 10", r".*may only be used with --offset.*"),
            # Use of conflicting context arguments
            (
                "foo -o 100 -C 10 -A 10",
                r".*--context may not be used at the same time as.*",
            ),
            (
                "foo -o 100 -C 10 -B 10",
                r".*--context may not be used at the same time as.*",
            ),
            # Invalid show/hide arguments
            (
                "foo -s foobar",
                r".*--show includes unrecognised pseudocode function 'foobar'.*",
            ),
            (
                "foo -H foobar",
                r".*--hide includes unrecognised pseudocode function 'foobar'.*",
            ),
        ],
    )
    def test_invalid_arguments(self, capsys, args, message_pattern):
        with pytest.raises(SystemExit):
            parse_args(split(args))
        out, err = capsys.readouterr()
        assert re.match(message_pattern, err.split("\n")[-2]) is not None


def test_integration(capsys, minimal_sequence_bitstream_fname):
    # A sanity-check integration test of the whole commandline interface
    assert main([minimal_sequence_bitstream_fname]) == 0

    assert capsys.readouterr().out == (
        "                                                  +- sequences:\n"
        "                                                  | +- 0:\n"
        "                                                  | | +- data_units:\n"
        "                                                  | | | +- 0:\n"
        "                                                  | | | | +- parse_info:\n"
        "000000000000:                                     | | | | | +- padding: 0b\n"
        "000000000000: 01000010010000100100001101000100    | | | | | +- parse_info_prefix: Correct (0x42424344)\n"
        "000000000032: 00010000                            | | | | | +- parse_code: end_of_sequence (0x10)\n"
        "000000000040: 00000000000000000000000000000000    | | | | | +- next_parse_offset: 0\n"
        "000000000072: 00000000000000000000000000000000    | | | | | +- previous_parse_offset: 0\n"
    )
