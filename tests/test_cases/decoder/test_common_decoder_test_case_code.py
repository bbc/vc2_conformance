import pytest

from vc2_data_tables import ParseCodes

from io import BytesIO

from fractions import Fraction

from vc2_data_tables import Profiles

from vc2_conformance.state import State

from vc2_conformance.encoder import make_sequence

from vc2_conformance.bitstream import (
    Deserialiser,
    BitstreamReader,
    parse_sequence,
)

from vc2_conformance.picture_generators import (
    repeat_pictures,
    mid_gray,
)

from vc2_conformance.test_cases.decoder.common import (
    make_dummy_end_of_sequence,
    iter_transform_parameters_in_sequence,
    iter_slices_in_sequence,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES


def test_make_dummy_end_of_sequence():
    # Should deserialise correctly
    f = BytesIO(make_dummy_end_of_sequence())
    with Deserialiser(BitstreamReader(f)) as des:
        parse_sequence(des, State())

    assert len(des.context["data_units"]) == 1
    assert (
        des.context["data_units"][0]["parse_info"]["parse_code"]
        == ParseCodes.end_of_sequence
    )


@pytest.mark.parametrize("profile", Profiles)
@pytest.mark.parametrize("fragment_slice_count", [0, 3])
def test_iter_transform_parameters_in_sequence(profile, fragment_slice_count):
    codec_features = MINIMAL_CODEC_FEATURES.copy()
    codec_features["profile"] = profile
    codec_features["fragment_slice_count"] = fragment_slice_count
    codec_features["slices_x"] = 3
    codec_features["slices_y"] = 2
    codec_features["picture_bytes"] = 100

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

    transform_parameters = list(
        iter_transform_parameters_in_sequence(codec_features, sequence)
    )

    # Should have found every slice
    assert len(transform_parameters) == num_pictures


@pytest.mark.parametrize("profile", Profiles)
@pytest.mark.parametrize("fragment_slice_count", [0, 3])
def test_iter_slices_in_sequence(profile, fragment_slice_count):
    codec_features = MINIMAL_CODEC_FEATURES.copy()
    codec_features["profile"] = profile
    codec_features["fragment_slice_count"] = fragment_slice_count
    codec_features["slices_x"] = 3
    codec_features["slices_y"] = 2
    codec_features["picture_bytes"] = 100

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

    slices = list(iter_slices_in_sequence(codec_features, sequence))

    # Should have found every slice
    assert len(slices) == (
        codec_features["slices_x"] * codec_features["slices_y"] * num_pictures
    )

    # Should have correct states
    if profile == Profiles.high_quality:
        for state, _, _, _ in slices:
            assert state == State(
                slice_prefix_bytes=0,
                slice_size_scaler=1,
                slices_x=codec_features["slices_x"],
                slices_y=codec_features["slices_y"],
            )
    elif profile == Profiles.low_delay:
        slice_bytes = Fraction(
            codec_features["picture_bytes"],
            codec_features["slices_x"] * codec_features["slices_y"],
        )
        for state, _, _, _ in slices:
            assert state == State(
                slice_bytes_numerator=slice_bytes.numerator,
                slice_bytes_denominator=slice_bytes.denominator,
                slices_x=codec_features["slices_x"],
                slices_y=codec_features["slices_y"],
            )

    # Should have correct coordinates
    it = iter(slices)
    for _ in range(num_pictures):
        for exp_sy in range(codec_features["slices_y"]):
            for exp_sx in range(codec_features["slices_x"]):
                _, sx, sy, _ = next(it)
                assert exp_sx == sx
                assert exp_sy == sy
