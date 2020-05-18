import pytest

import os

import numpy as np

from copy import deepcopy

from io import BytesIO

from vc2_data_tables import WaveletFilters

from vc2_conformance.state import State

from vc2_conformance.bitstream import autofill_and_serialise_sequence

from vc2_conformance import file_format

from vc2_conformance.decoder import (
    init_io,
    parse_stream,
)

from vc2_conformance.test_cases.decoder.real_pictures import real_pictures

from sample_codec_features import MINIMAL_CODEC_FEATURES
from smaller_real_pictures import alternative_real_pictures


LOVELL_IMAGE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "test_images", "lovell.raw",
)
"""
A simple 64x64, 8 bit, 4:2:2 sampled test picture, cropped out of a real
photograph.
"""


def encode_and_decode(sequence):
    f = BytesIO()
    autofill_and_serialise_sequence(f, sequence)
    f.seek(0)

    pictures = []
    state = State(_output_picture_callback=lambda p, vp: pictures.append(p))
    init_io(state, f)
    parse_stream(state)

    return pictures


@pytest.fixture
def codec_features():
    return deepcopy(MINIMAL_CODEC_FEATURES)


def test_real_pictures(codec_features):
    picture, video_parameters, picture_coding_mode = file_format.read(
        LOVELL_IMAGE_PATH,
    )

    codec_features["wavelet_index"] = WaveletFilters.le_gall_5_3
    codec_features["wavelet_index_ho"] = WaveletFilters.le_gall_5_3
    codec_features["dwt_depth"] = 2
    codec_features["dwt_depth_ho"] = 0

    codec_features["slices_x"] = 8
    codec_features["slices_y"] = 16
    codec_features["lossless"] = False
    codec_features["picture_bytes"] = (64 * 64 * 2) // 2  # ~2:1 compression

    codec_features["video_parameters"] = video_parameters

    with alternative_real_pictures([LOVELL_IMAGE_PATH]):
        sequence = real_pictures(codec_features)

    coded_pictures = encode_and_decode(sequence)

    assert len(coded_pictures) == 1
    coded_picture = coded_pictures[0]

    for component in ["Y", "C1", "C2"]:
        before = np.array(picture[component])
        after = np.array(coded_picture[component])

        # Coding should be lossy
        assert not np.array_equal(before, after)

        # PSNR should be reasonable
        error = after - before
        square_error = error * error
        mean_square_error = np.mean(square_error)
        max_value = 255.0
        peak_signal_to_noise_ratio = (20 * np.log(max_value) / np.log(10)) - (
            10 * np.log(mean_square_error) / np.log(10)
        )

        # NB: This is a pretty low PSNR threshold but appropriate here since
        # we're encoding a very small (and, for its size, very detailed) image.
        assert peak_signal_to_noise_ratio > 45.0
