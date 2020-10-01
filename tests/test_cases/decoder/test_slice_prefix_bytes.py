import pytest

import logging

from io import BytesIO

from vc2_data_tables import Profiles, Levels

from vc2_conformance.picture_generators import (
    repeat_pictures,
    mid_gray,
)

from vc2_conformance.constraint_table import AnyValue, ValueSet

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.encoder import make_sequence

from vc2_conformance.codec_features import CodecFeatures

from sample_codec_features import MINIMAL_CODEC_FEATURES

from vc2_conformance.pseudocode.state import State

from vc2_conformance.bitstream import (
    BitstreamReader,
    MonitoredDeserialiser,
    to_bit_offset,
    parse_stream,
    Stream,
    autofill_and_serialise_stream,
)

from vc2_conformance.test_cases.decoder.slice_prefix_bytes import (
    iter_slice_parameters_in_sequence,
    slice_prefix_bytes,
)

from alternative_level_constraints import alternative_level_1


@pytest.mark.parametrize("fragment_slice_count", [0, 3])
def test_iter_slice_parameters_in_sequence(fragment_slice_count):
    codec_features = MINIMAL_CODEC_FEATURES.copy()
    codec_features["profile"] = Profiles.high_quality
    codec_features["fragment_slice_count"] = fragment_slice_count

    num_pictures = 2

    sequence = make_sequence(
        codec_features,
        repeat_pictures(
            mid_gray(
                codec_features["video_parameters"],
                codec_features["picture_coding_mode"],
            ),
            num_pictures,
        ),
    )

    slice_parameters = list(iter_slice_parameters_in_sequence(sequence))

    # Should have found every set of slice parameters
    assert len(slice_parameters) == num_pictures


def deserialise_and_measure_slice_data_unit_sizes(bitstream):
    """
    Deserialise a bitstream, returning the number of bytes in each data unit
    which contains picture slices.
    """
    out = []

    slice_start_offset = [None]
    contained_slices = [False]

    def monitor(des, target, _value):
        # Dirty: Relies on implementation detail of vc2_fixeddicts...
        if des.path(target)[4:] in (
            ["picture_parse", "wavelet_transform", "padding"],
            ["fragment_parse", "fragment_header", "fragment_slice_count"],
            ["fragment_parse", "fragment_header", "fragment_y_offset"],
        ):
            slice_start_offset[0] = to_bit_offset(*des.io.tell())
        elif target == "qindex":
            contained_slices[0] = True
        elif target == "parse_code" and slice_start_offset[0] is not None:
            if contained_slices[0]:
                out.append(to_bit_offset(*des.io.tell()) - slice_start_offset[0])
            contained_slices[0] = False

    reader = BitstreamReader(BytesIO(bitstream))
    with MonitoredDeserialiser(monitor, reader) as des:
        parse_stream(des, State())

    return out


class TestSlicePrefixBytes(object):
    @pytest.mark.parametrize("fragment_slice_count", [0, 1])
    def test_low_delay_profile_no_tests(self, fragment_slice_count):
        codec_features = CodecFeatures(
            MINIMAL_CODEC_FEATURES,
            profile=Profiles.low_delay,
            fragment_slice_count=fragment_slice_count,
        )
        assert len(list(slice_prefix_bytes(codec_features))) == 0

    def test_level_assumptions(self):
        # The test case generator assumes that levels either require the slice
        # prefix bytes to be zero or allow it to be anything -- any condition
        # other than this would require the test case generator to be more
        # flexible than it is.
        #
        # The above assumption is verified below
        for values in LEVEL_CONSTRAINTS:
            if Profiles.high_quality in values["profile"]:
                assert values["slice_prefix_bytes"] == AnyValue() or values[
                    "slice_prefix_bytes"
                ] == ValueSet(0)

    @pytest.mark.parametrize(
        "fragment_slice_count,picture_bytes",
        [
            # Non-fragmented
            (0, 64),
            # Fragmented
            (1, 64),
            # Number of bytes requires slice size scaler > 1
            (0, 2 * 300),
        ],
    )
    def test_length_unchanged_for_non_lossless(
        self, fragment_slice_count, picture_bytes
    ):
        codec_features = CodecFeatures(
            MINIMAL_CODEC_FEATURES,
            profile=Profiles.high_quality,
            picture_bytes=picture_bytes,
            fragment_slice_count=fragment_slice_count,
        )

        # Get length of sequence containing no prefix bytes
        f = BytesIO()
        autofill_and_serialise_stream(
            f,
            Stream(
                sequences=[
                    make_sequence(
                        codec_features,
                        mid_gray(
                            codec_features["video_parameters"],
                            codec_features["picture_coding_mode"],
                        ),
                    )
                ]
            ),
        )
        expected_data_unit_lengths = deserialise_and_measure_slice_data_unit_sizes(
            f.getvalue()
        )
        # Sanity check the deserialise_and_measure_slice_data_unit_sizes
        # function is working...
        assert len(expected_data_unit_lengths) >= 1

        test_cases = list(slice_prefix_bytes(codec_features))

        assert len(test_cases) == 3

        for test_case in test_cases:
            f = BytesIO()
            autofill_and_serialise_stream(f, test_case.value)
            data_unit_lengths = deserialise_and_measure_slice_data_unit_sizes(
                f.getvalue()
            )
            assert data_unit_lengths == expected_data_unit_lengths

    @pytest.mark.parametrize("fragment_slice_count", [0, 1])
    @pytest.mark.parametrize("lossless", [False, True])
    def test_data_is_as_expected(self, fragment_slice_count, lossless):
        codec_features = CodecFeatures(
            MINIMAL_CODEC_FEATURES,
            profile=Profiles.high_quality,
            picture_bytes=None if lossless else 64,
            lossless=lossless,
            fragment_slice_count=fragment_slice_count,
        )

        test_cases = list(slice_prefix_bytes(codec_features))

        assert len(test_cases) == 3

        for test_case in test_cases:
            f = BytesIO()
            autofill_and_serialise_stream(f, test_case.value)
            f.seek(0)

            log = []

            def log_prefix_bytes(_des, target, value):
                if target == "prefix_bytes":
                    log.append(value)

            with MonitoredDeserialiser(log_prefix_bytes, BitstreamReader(f)) as des:
                parse_stream(des, State())
            # Sanity check for test
            assert len(log) > 0

            for prefix_bytes in log:
                if test_case.subcase_name == "zeros":
                    assert all(b == 0 for b in bytearray(prefix_bytes))
                elif test_case.subcase_name == "ones":
                    assert all(b == 0xFF for b in bytearray(prefix_bytes))
                elif test_case.subcase_name == "end_of_sequence":
                    assert b"BBCD" in prefix_bytes
                else:
                    assert False

    def test_level_constrained(self, caplog):
        caplog.set_level(logging.WARNING)

        with alternative_level_1():
            codec_features = CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                profile=Profiles.high_quality,
                level=Levels(1),
            )

            test_cases = list(slice_prefix_bytes(codec_features))
            assert len(test_cases) == 0

            # Shouldn't warn in this case
            assert caplog.text == ""

    def test_tiny_picture_bytes(self, caplog):
        caplog.set_level(logging.WARNING)
        codec_features = CodecFeatures(
            MINIMAL_CODEC_FEATURES,
            profile=Profiles.high_quality,
            # Enough to provide the minimum 4 bytes per slice but not enough
            # for 13 bytes per slice for the end of sequence parse
            picture_bytes=16,
        )

        test_cases = list(slice_prefix_bytes(codec_features))
        assert len(test_cases) == 3

        assert "picture_bytes" in caplog.text
