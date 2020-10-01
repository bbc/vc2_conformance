import pytest

import logging

from copy import deepcopy

from io import BytesIO

from vc2_conformance.pseudocode.quantization import inverse_quant

from vc2_conformance.bitstream import autofill_and_serialise_stream

from vc2_conformance.pseudocode.state import State

from vc2_conformance.decoder import init_io, parse_stream

from vc2_conformance.test_cases.decoder.common import (
    iter_transform_parameters_in_sequence,
    iter_slices_in_sequence,
)

from vc2_conformance.test_cases.decoder.lossless_quantization import (
    MINIMUM_DISTINCT_QINDEX,
    compute_qindex_with_distinct_quant_factors,
    lossless_quantization,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES


def test_minimum_distinct_qindex():
    # Check values below this index produce non-unique values
    values = set()
    unique_values = set()
    for qi in range(1, MINIMUM_DISTINCT_QINDEX):
        value = inverse_quant(1, qi)
        if value not in values:
            unique_values.add(value)
        else:
            unique_values.difference_update([value])
        values.add(value)
    assert unique_values == set()

    # Check values above this index produce unique values (they should diverge
    # so checking the first few should do the job)
    values = set(
        inverse_quant(1, qi)
        for qi in range(MINIMUM_DISTINCT_QINDEX, MINIMUM_DISTINCT_QINDEX + 100)
    )
    assert len(values) == 100


def test_compute_qindex_with_distinct_quant_factors():
    quant_matrix = {
        0: {"L": 0},
        1: {"H": 1},
        2: {"HL": 2, "LH": 3, "HH": 4},
        3: {"HL": 5, "LH": 6, "HH": 7},
    }
    assert (
        compute_qindex_with_distinct_quant_factors(quant_matrix)
        == MINIMUM_DISTINCT_QINDEX + 7
    )


class TestLosslessQuantization(object):
    def test_lossy(self):
        assert lossless_quantization(MINIMAL_CODEC_FEATURES) is None

    @pytest.mark.parametrize("fragment_slice_count", [0, 1])
    @pytest.mark.parametrize(
        "num_coeffs_per_slice,exp_slice_size_scaler",
        [
            (1, 1),
            ((2 * 255), 1),
            ((2 * 255) + 1, 2),
            ((2 * 255) * 2, 2),
            ((2 * 255) * 2 + 1, 3),
        ],
    )
    def test_slice_size_scaler(
        self, fragment_slice_count, num_coeffs_per_slice, exp_slice_size_scaler
    ):
        # Here we use the null transform on a 1D image with a single slice.
        # This means exactly 'frame_width' values will be encoded in each
        # picture slice (each of which should be 4 bits since they're '1').
        codec_features = deepcopy(MINIMAL_CODEC_FEATURES)
        codec_features["lossless"] = True
        codec_features["picture_bytes"] = None
        codec_features["video_parameters"]["frame_width"] = num_coeffs_per_slice
        codec_features["video_parameters"]["frame_height"] = 1
        codec_features["video_parameters"]["clean_width"] = num_coeffs_per_slice
        codec_features["video_parameters"]["clean_height"] = 1
        codec_features["dwt_depth"] = 0
        codec_features["dwt_depth_ho"] = 0
        codec_features["slices_x"] = 1
        codec_features["slices_y"] = 1

        stream = lossless_quantization(codec_features)

        for tp in iter_transform_parameters_in_sequence(
            codec_features, stream["sequences"][0]
        ):
            slice_size_scaler = tp["slice_parameters"]["slice_size_scaler"]
            assert slice_size_scaler == exp_slice_size_scaler

        # Sanity check: serialise and make sure the lengths/slice size scaler
        # are sufficient (serialisation will fail if not)
        autofill_and_serialise_stream(BytesIO(), stream)

    @pytest.mark.parametrize(
        "luma_excursion,color_diff_excursion", [(4, 255), (255, 4), (4, 4)]
    )
    def test_signal_clip_test(self, caplog, luma_excursion, color_diff_excursion):
        # In this test we set the excursion (bit depth) to such absurdly small
        # values that the test signal is bound to overshoot them.
        caplog.set_level(logging.WARNING)

        codec_features = deepcopy(MINIMAL_CODEC_FEATURES)
        codec_features["lossless"] = True
        codec_features["picture_bytes"] = None
        codec_features["video_parameters"]["luma_excursion"] = luma_excursion
        codec_features["video_parameters"][
            "color_diff_excursion"
        ] = color_diff_excursion

        stream = lossless_quantization(codec_features)
        assert stream is None
        assert "could not produce a losslessly compressible image" in caplog.text

    def test_qindex_matters(self):
        codec_features = deepcopy(MINIMAL_CODEC_FEATURES)
        codec_features["lossless"] = True
        codec_features["picture_bytes"] = None

        # Sanity check: Make sure we're outputting some kind of picture which
        # really does depend on quantization
        pictures = {False: [], True: []}
        for override_qindex in [False, True]:
            stream = lossless_quantization(codec_features)

            if override_qindex:
                for _state, _sx, _sy, hq_slice in iter_slices_in_sequence(
                    codec_features,
                    stream["sequences"][0],
                ):
                    hq_slice["qindex"] = 0

            # Serialise
            f = BytesIO()
            autofill_and_serialise_stream(f, stream)
            f.seek(0)

            # Decode
            def output_picture_callback(picture, video_parameters, picture_coding_mode):
                pictures[override_qindex].append(picture)

            state = State(_output_picture_callback=output_picture_callback)
            init_io(state, f)
            parse_stream(state)

        # Make sure that the qindex mattered by checking that decoding with
        # qindex clamped to 0 resulted in different pictures
        assert pictures[False] != pictures[True]
