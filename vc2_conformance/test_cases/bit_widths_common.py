"""
Common logic relating to loading :py:mod:`vc2_bit_widths` data and assembling
test pictures.
"""

import os

from vc2_data_tables import QUANTISATION_MATRICES

from vc2_conformance.dimensions_and_depths import compute_dimensions_and_depths

from vc2_bit_widths.helpers import (
    quantisation_index_bound,
    evaluate_filter_bounds,
    evaluate_test_pattern_outputs,
    generate_test_pictures,
)

from vc2_bit_widths.bundle import (
    bundle_get_static_filter_analysis,
    bundle_get_optimised_synthesis_test_patterns,
)

from vc2_conformance_data import STATIC_FILTER_ANALYSIS_BUNDLE_FILENAME


__all__ = [
    "get_bundle_filename",
    "get_test_pictures",
]


class MissingStaticAnalysisError(KeyError):
    """
    Exception thrown when a static analysis is not available for the codec
    configuration used.
    """


def get_bundle_filename():
    """
    Get the filename to use for loading the VC-2 bit widths analysis bundle
    file.

    If the ``VC2_BIT_WIDTHS_BUNDLE`` environment variable is set, uses this as
    the bundle file. Otherwise, falls back to
    :py:data:`vc2_conformance_data.STATIC_FILTER_ANALYSIS_BUNDLE_FILENAME`
    which contains analyses for all codec configurations with a default
    quantisation matrix.
    """
    default_filename = STATIC_FILTER_ANALYSIS_BUNDLE_FILENAME

    # NB, Also uses the default if the environment variable is present but
    # empty
    return os.environ.get("VC2_BIT_WIDTHS_BUNDLE", "") or default_filename


def get_test_pictures(codec_features, bundle_filename=get_bundle_filename()):
    """
    Gets a set of test pictures for a codec with the specified codec
    configuration.

    Raises a :py:exc:`MissingStaticAnalysisError` if no static filter analysis
    is available for the specified codec.

    Parameters
    ==========
    bundle_filename : str
        Filename of the VC-2 bit widths bundle file to read test patterns from.
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`

    Returns
    =======
    analysis_luma_pictures : [:py:class:`AnalysisPicture`, ...]
    synthesis_luma_pictures : [:py:class:`SynthesisPicture`, ...]
    analysis_color_diff_pictures : [:py:class:`AnalysisPicture`, ...]
    synthesis_color_diff_pictures : [:py:class:`SynthesisPicture`, ...]
        Test pictures for luma and color difference components respectively.
        (See :py:func:`vc2_bit_widths.helpers.generate_test_pictures`.)
    """
    if codec_features["quantization_matrix"] is not None:
        quantisation_matrix = codec_features["quantization_matrix"]
    else:
        quantisation_matrix = QUANTISATION_MATRICES[
            (
                codec_features["wavelet_index"],
                codec_features["wavelet_index_ho"],
                codec_features["dwt_depth"],
                codec_features["dwt_depth_ho"],
            )
        ]

    dimensions_and_depths = compute_dimensions_and_depths(
        codec_features["video_parameters"],
        codec_features["picture_coding_mode"],
    )

    # Load the test pattern specifications
    try:
        (
            analysis_signal_bounds,
            synthesis_signal_bounds,
            analysis_test_patterns,
            synthesis_test_patterns,
        ) = bundle_get_static_filter_analysis(
            bundle_filename,
            codec_features["wavelet_index"],
            codec_features["wavelet_index_ho"],
            codec_features["dwt_depth"],
            codec_features["dwt_depth_ho"],
        )
    except KeyError:
        raise MissingStaticAnalysisError()

    all_analysis_pictures = []
    all_synthesis_pictures = []
    for component in ["Y", "C1"]:
        picture_bit_width = dimensions_and_depths[component].depth_bits
        picture_width = dimensions_and_depths[component].width
        picture_height = dimensions_and_depths[component].height

        # ...using optimised synthesis test patterns if available...
        try:
            synthesis_test_patterns = bundle_get_optimised_synthesis_test_patterns(
                bundle_filename,
                codec_features["wavelet_index"],
                codec_features["wavelet_index_ho"],
                codec_features["dwt_depth"],
                codec_features["dwt_depth_ho"],
                quantisation_matrix,
                picture_bit_width,
            )
        except KeyError:
            pass

        # Determine the maximum quantisation index which may be usefully used for
        # the codec configuration specified
        concrete_analysis_bounds, concrete_synthesis_bounds = evaluate_filter_bounds(
            codec_features["wavelet_index"],
            codec_features["wavelet_index_ho"],
            codec_features["dwt_depth"],
            codec_features["dwt_depth_ho"],
            analysis_signal_bounds,
            synthesis_signal_bounds,
            picture_bit_width,
        )
        max_quantisation_index = quantisation_index_bound(
            concrete_analysis_bounds,
            quantisation_matrix,
        )

        # Find the worst-case quantisation index for the synthesis test patterns
        _, synthesis_test_pattern_outputs = evaluate_test_pattern_outputs(
            codec_features["wavelet_index"],
            codec_features["wavelet_index_ho"],
            codec_features["dwt_depth"],
            codec_features["dwt_depth_ho"],
            picture_bit_width,
            quantisation_matrix,
            max_quantisation_index,
            analysis_test_patterns,
            synthesis_test_patterns,
        )

        # Generate packed test pictures
        analysis_pictures, synthesis_pictures = generate_test_pictures(
            picture_width,
            picture_height,
            picture_bit_width,
            analysis_test_patterns,
            synthesis_test_patterns,
            synthesis_test_pattern_outputs,
        )

        all_analysis_pictures.append(analysis_pictures)
        all_synthesis_pictures.append(synthesis_pictures)

    return (
        all_analysis_pictures[0],
        all_synthesis_pictures[0],
        all_analysis_pictures[1],
        all_synthesis_pictures[1],
    )
