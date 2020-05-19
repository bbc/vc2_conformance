import pytest

from copy import deepcopy

from sample_codec_features import MINIMAL_CODEC_FEATURES

from vc2_data_tables import WaveletFilters

from vc2_conformance.string_utils import wrap_paragraphs

from vc2_conformance.encoder.exceptions import (
    MissingQuantizationMatrixError,
    PictureBytesSpecifiedForLosslessModeError,
    InsufficientHQPictureBytesError,
    InsufficientLDPictureBytesError,
    LosslessUnsupportedByLowDelayError,
    AsymmetricTransformPreVersion3Error,
    IncompatibleLevelAndVideoFormatError,
    IncompatibleLevelAndExtendedTransformParametersError,
)


@pytest.fixture
def codec_features():
    return deepcopy(MINIMAL_CODEC_FEATURES)


def test_missing_quantization_matrix_error(codec_features):
    codec_features["wavelet_index"] = WaveletFilters.haar_with_shift
    codec_features["wavelet_index_ho"] = WaveletFilters.le_gall_5_3
    codec_features["dwt_depth"] = 2
    codec_features["dwt_depth_ho"] = 1
    assert wrap_paragraphs(
        MissingQuantizationMatrixError(codec_features).explain()
    ) == wrap_paragraphs(
        """
            No default quantization matrix is available for the wavelet
            transform specified for minimal and no custom quantization matrix was
            provided.

            * wavelet_index: haar_with_shift (4)
            * wavelet_index_ho: le_gall_5_3 (1)
            * dwt_depth: 2
            * dwt_depth_ho: 1
        """
    )


def test_picture_bytes_specified_for_lossless_mode_error(codec_features):
    codec_features["lossless"] = True
    codec_features["picture_bytes"] = 123
    assert wrap_paragraphs(
        PictureBytesSpecifiedForLosslessModeError(codec_features).explain()
    ) == wrap_paragraphs(
        """
            The codec configuration minimal specifies a lossless format but did not
            omit picture_bytes (it is set to 123).
        """
    )


def test_insufficient_hq_picture_bytes_error(codec_features):
    codec_features["picture_bytes"] = 3
    assert wrap_paragraphs(
        InsufficientHQPictureBytesError(codec_features).explain()
    ) == wrap_paragraphs(
        """
            The codec configuration minimal specifies picture_bytes as 3 but this
            is too small.

            A 2 by 1 slice high quality profile encoding must allow at least
            4*2*1 = 8 bytes. (That is, 1 byte for the qindex field and 3
            bytes for the length fields of each high quality slice (13.5.4))
        """
    )


def test_insufficient_ld_picture_bytes_error(codec_features):
    codec_features["picture_bytes"] = 1
    assert wrap_paragraphs(
        InsufficientLDPictureBytesError(codec_features).explain()
    ) == wrap_paragraphs(
        """
            The codec configuration minimal specifies picture_bytes as 1 but
            this is too small.

            A 2 by 1 slice low delay profile encoding must allow at least 2*1 =
            2 bytes. (That is, 7 bits for the qindex field and 1 bit for the
            slice_y_length field of each low delay slice (13.5.3.1))
        """
    )


def test_lossless_unsuported_by_low_delay_error(codec_features):
    assert wrap_paragraphs(
        LosslessUnsupportedByLowDelayError(codec_features).explain()
    ) == wrap_paragraphs(
        """
            Low delay profile does not support lossless encoding for minimal.
        """
    )


def test_asymmetric_transform_pre_version_3_error(codec_features):
    codec_features["wavelet_index"] = WaveletFilters.haar_with_shift
    codec_features["wavelet_index_ho"] = WaveletFilters.le_gall_5_3
    codec_features["dwt_depth"] = 2
    codec_features["dwt_depth_ho"] = 1
    assert wrap_paragraphs(
        AsymmetricTransformPreVersion3Error(codec_features).explain()
    ) == wrap_paragraphs(
        """
            An asymmetric wavelet transform was specified for minimal but the
            major_version was not >= 3 (12.4.1).

            * wavelet_index: haar_with_shift (4)
            * wavelet_index_ho: le_gall_5_3 (1)
            * dwt_depth: 2
            * dwt_depth_ho: 1
        """
    )


def test_incompatible_level_and_video_format_error(codec_features):
    assert wrap_paragraphs(
        IncompatibleLevelAndVideoFormatError(codec_features).explain()
    ) == wrap_paragraphs(
        """
            Level unconstrained (0) specified for minimal but the video format
            requested is not permitted by this level.
        """
    )


def test_incompatible_level_and_extended_transform_parameters_error(codec_features):
    codec_features["wavelet_index"] = WaveletFilters.haar_with_shift
    codec_features["wavelet_index_ho"] = WaveletFilters.le_gall_5_3
    codec_features["dwt_depth"] = 2
    codec_features["dwt_depth_ho"] = 1
    assert wrap_paragraphs(
        IncompatibleLevelAndExtendedTransformParametersError(codec_features).explain()
    ) == wrap_paragraphs(
        """
            Level unconstrained (0) specified for minimal but the asymmetric
            transform type specified is not not permitted by this level.

            * wavelet_index: haar_with_shift (4)
            * wavelet_index_ho: le_gall_5_3 (1)
            * dwt_depth: 2
            * dwt_depth_ho: 1
        """
    )
