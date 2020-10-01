from vc2_data_tables import Profiles

from vc2_conformance.bitstream import Stream

from vc2_conformance.test_cases import decoder_test_case_generator

from vc2_conformance.encoder import make_sequence

from vc2_conformance.encoder.pictures import get_safe_lossy_hq_slice_size_scaler

from vc2_conformance.constraint_table import allowed_values_for

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.codec_features import codec_features_to_trivial_level_constraints

from vc2_conformance.picture_generators import mid_gray

from vc2_conformance.test_cases.decoder.common import iter_slices_in_sequence


@decoder_test_case_generator
def slice_size_scaler(codec_features):
    """
    **Tests that the 'slice_size_scaler' field is correctly handled.**

    This test case generates a sequence which sets slice_size_scaler value
    (13.5.4) 1 larger than it otherwise would be.

    This test case is only generated for the high quality profile, and levels
    which permit a slice size scaler value greater than 1.
    """
    # Skip if not high quality profile
    if codec_features["profile"] != Profiles.high_quality:
        return None

    # Pick a minimum slice size scaler which is larger than the slice size
    # scaler which would otherwise be used
    if codec_features["lossless"]:
        # We're just going to code mid-gray frames which compress to 0 bytes so
        # slice size scaler = 1 is always sufficient.
        minimum_slice_size_scaler = 2
    else:
        minimum_slice_size_scaler = (
            get_safe_lossy_hq_slice_size_scaler(
                codec_features["picture_bytes"],
                codec_features["slices_x"] * codec_features["slices_y"],
            )
            + 1
        )

    # Skip if level prohibits non-1 slice size scaler
    if minimum_slice_size_scaler not in allowed_values_for(
        LEVEL_CONSTRAINTS,
        "slice_size_scaler",
        codec_features_to_trivial_level_constraints(codec_features),
    ):
        return None

    sequence = make_sequence(
        codec_features,
        mid_gray(
            codec_features["video_parameters"],
            codec_features["picture_coding_mode"],
        ),
        minimum_slice_size_scaler=minimum_slice_size_scaler,
    )

    # Force lossless coding modes to use a non-zero number of bytes for each
    # slice's coefficients (so that slice_size_scaler actually has to be used).
    if codec_features["lossless"]:
        for _state, _sx, _sy, hq_slice in iter_slices_in_sequence(
            codec_features, sequence
        ):
            assert hq_slice["slice_c2_length"] == 0
            hq_slice["slice_c2_length"] = 1

    return Stream(sequences=[sequence])
