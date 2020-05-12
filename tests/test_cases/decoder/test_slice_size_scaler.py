import pytest

from vc2_data_tables import Profiles, Levels

from vc2_conformance.test_cases.decoder.slice_size_scaler import slice_size_scaler

from sample_codec_features import MINIMAL_CODEC_FEATURES

from vc2_conformance.test_cases.decoder.common import iter_slices_in_sequence


class TestSliceSizeScaler(object):
    def test_low_delay(self):
        assert (
            slice_size_scaler(dict(MINIMAL_CODEC_FEATURES, profile=Profiles.low_delay))
            is None
        )

    def test_level_prohibits_larger_slice_size_scaler(self):
        assert (
            slice_size_scaler(
                dict(
                    MINIMAL_CODEC_FEATURES,
                    profile=Profiles.high_quality,
                    level=Levels.uhd_over_hd_sdi,
                )
            )
            is None
        )

    @pytest.mark.parametrize(
        "lossless,picture_bytes,exp_slice_size_scaler",
        [
            # Lossy with <255 bytes per slice (slice size scaler normally 1)
            (False, 2 * 3 * (4 + 10), 2),
            # Lossy normally requiring slice size scaler of 3
            (False, 2 * 3 * (4 + 255 * 3), 4),
            # Lossless (normally requires slice size scaler of 1)
            (True, None, 2),
        ],
    )
    def test_set_slice_size_scaler(
        self, lossless, picture_bytes, exp_slice_size_scaler
    ):
        codec_features = dict(
            MINIMAL_CODEC_FEATURES,
            profile=Profiles.high_quality,
            lossless=lossless,
            picture_bytes=picture_bytes,
            slices_x=2,
            slices_y=3,
        )
        sequence = slice_size_scaler(codec_features)

        for state, _sx, _sy, hq_slice in iter_slices_in_sequence(
            codec_features, sequence
        ):
            assert state["slice_size_scaler"] == exp_slice_size_scaler

            # Slices mustn't be empty (otherwise slice_size_scaler could be
            # anything and it wouldn't matter!)
            assert (
                hq_slice["slice_y_length"]
                + hq_slice["slice_c1_length"]
                + hq_slice["slice_c2_length"]
            ) > 0
