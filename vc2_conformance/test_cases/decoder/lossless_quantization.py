"""
Test specifically for lossless decoders that verifies basic support for
quantisation.
"""

import logging

from copy import deepcopy

from io import BytesIO

from vc2_conformance.bitstream import Stream, autofill_and_serialise_stream

from vc2_conformance.test_cases import decoder_test_case_generator

from vc2_conformance.picture_generators import mid_gray

from vc2_conformance.encoder import make_sequence

from vc2_conformance.pseudocode.state import State

from vc2_conformance.test_cases.decoder.common import (
    iter_transform_parameters_in_sequence,
    iter_slices_in_sequence,
)

from vc2_conformance.encoder.pictures import (
    get_quantization_marix,
    calculate_hq_length_field,
)

from vc2_conformance.decoder import init_io, parse_stream


MINIMUM_DISTINCT_QINDEX = 7
"""
The quantization index at and above which the value of ``inverse_quant(1, qi)``
is distinct for all quantization indices.
"""


def compute_qindex_with_distinct_quant_factors(quant_matrix):
    """
    Given a quantization matrix, return a qindex high enough that all
    quantization factors used will be greater than
    :py:data:`MINIMUM_DISTINCT_QINDEX`.
    """
    # The quantization index should be chosen such that:
    #
    # * Even for the most heavily skewed quantization matrix entry some
    #   quantisation still occurs
    # * When inverse quantisation is applied to '1', the result should be
    #   distinct for all quantisation indices used
    max_quant_matrix_value = max(
        v for subbands in quant_matrix.values() for v in subbands.values()
    )
    return max_quant_matrix_value + MINIMUM_DISTINCT_QINDEX


def check_for_signal_clipping(sequence):
    """
    Given a :py:class:`vc2_conformance.bitstream.Sequence`, return True if any
    picture component signal was clipped during decoding.
    """
    # NB: Internally we just check for saturated signal levels. This way we
    # avoid the need to modify the decoder to remove the clipper and all that
    # faff...

    # Serialise
    f = BytesIO()
    # NB: Deepcopy required due to autofill_and_serialise_stream mutating the
    # stream
    stream = Stream(sequences=[deepcopy(sequence)])
    autofill_and_serialise_stream(f, stream)
    f.seek(0)

    # Decode and look for saturated pixel values
    state = State()
    may_have_clipped = [False]

    def output_picture_callback(picture, video_parameters, picture_coding_mode):
        components_and_depths = [
            ("Y", state["luma_depth"]),
            ("C1", state["color_diff_depth"]),
            ("C2", state["color_diff_depth"]),
        ]

        for component, depth in components_and_depths:
            min_value = min(min(row) for row in picture[component])
            max_value = max(max(row) for row in picture[component])
            if min_value == 0:
                may_have_clipped[0] = True
            if max_value == (1 << depth) - 1:
                may_have_clipped[0] = True

    state["_output_picture_callback"] = output_picture_callback
    init_io(state, f)
    parse_stream(state)

    return may_have_clipped[0]


@decoder_test_case_generator
def lossless_quantization(codec_features):
    """
    **Tests support for quantization in lossless decoders.**

    Quantization can, in principle, be used in lossless coding modes in cases
    where all transform coefficients are divisible by the same factor. This
    test case contains a synthetic test pattern with this property.

    This test case is only generated for lossless codecs.

    .. note::

        For informational purposes, an example decoded test pattern is shown
        below:

        .. image:: /_static/user_guide/lossless_quantization.png

        Note the faint repeating pattern.
    """
    # Don't bother with this test for lossy coding modes (quantization is
    # tested elsewhere)
    if not codec_features["lossless"]:
        return None

    # Pick a non-zero qindex which will ensure all transform coefficients, when
    # set to 1 in the bitstream, will dequantize to different values (when the
    # quant matrix entry is different).
    quant_matrix = get_quantization_marix(codec_features)
    qindex = compute_qindex_with_distinct_quant_factors(quant_matrix)

    # Start with a mid-gray frame (coeffs set to 0). We'll hand-modify this to
    # contain all 1s because a picture which does this may be slightly larger
    # than the unclipped picture size and therefore we can't rely on the
    # encoder to produce such a signal.
    sequence = make_sequence(
        codec_features,
        mid_gray(
            codec_features["video_parameters"],
            codec_features["picture_coding_mode"],
        ),
    )

    # Set qindex and all transform coefficients to 1
    max_length = 0
    for _state, _sx, _sy, hq_slice in iter_slices_in_sequence(codec_features, sequence):
        hq_slice["qindex"] = qindex
        for c in ["y", "c1", "c2"]:
            hq_slice["{}_transform".format(c)] = [
                1 for _ in hq_slice["{}_transform".format(c)]
            ]
            length = calculate_hq_length_field(hq_slice["{}_transform".format(c)], 1)
            hq_slice["slice_{}_length".format(c)] = length
            max_length = max(length, max_length)

    # Update slice size scaler to keep all length fields to 8 bits or fewer
    slice_size_scaler = max(1, (max_length + 254) // 255)
    for transform_parameters in iter_transform_parameters_in_sequence(
        codec_features, sequence
    ):
        transform_parameters["slice_parameters"][
            "slice_size_scaler"
        ] = slice_size_scaler
    for _state, _sx, _sy, hq_slice in iter_slices_in_sequence(codec_features, sequence):
        for c in ["y", "c1", "c2"]:
            hq_slice["slice_{}_length".format(c)] += slice_size_scaler - 1
            hq_slice["slice_{}_length".format(c)] //= slice_size_scaler

    # If the resulting picture clips, give up on this test case. We make the
    # assumption that while a clever lossless encoder may use quantization it
    # is unlikely to rely on signal clipping in the decoder. As a consequence,
    # to avoid producing a test case which a decoder might reasonably fail to
    # decode due to internal signal width limitations, we bail.
    #
    # In practice, even for the largest VC-2 filters, transform depths and
    # wonkiest quantisation matrices, the generated signals should fit (very)
    # comfortably into 8 bit video signal ranges. As such, if this check fails
    # it is very likely a highly degenerate codec configuration has been
    # specified.
    if check_for_signal_clipping(sequence):
        logging.warning(
            "The lossless_quantization test case generator could not produce a "
            "losslessly compressible image and has been omitted. This probably "
            "means an (impractically) high transform depth or custom quantisation "
            "matrix entry or an extremely low picture bit depth was used."
        )
        return None

    return Stream(sequences=[sequence])
