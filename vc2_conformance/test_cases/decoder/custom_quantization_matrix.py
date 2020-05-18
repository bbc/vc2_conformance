from itertools import count, repeat, cycle

from vc2_data_tables import QUANTISATION_MATRICES

from vc2_conformance.bitstream import Stream

from vc2_conformance.codec_features import CodecFeatures

from vc2_conformance.test_cases import TestCase, decoder_test_case_generator

from vc2_conformance.encoder import make_sequence

from vc2_conformance._constraint_table import allowed_values_for, ValueSet, AnyValue

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.codec_features import codec_features_to_trivial_level_constraints

from vc2_conformance.picture_generators import white_noise


@decoder_test_case_generator
def default_quantization_matrix(codec_features):
    """
    **Tests that the default quantization matrix can be used.**

    This test case is only generated when a non ``default`` value is specified
    for the ``quantization_matrix`` codec features CSV entry but when a default
    quantization matrix is defined.

    This test is also omitted for lossless codecs.

    .. note::

        This is the only test case which sets the ``custom_quant_matrix`` flag
        (12.4.5.3) to 0 when a ``quantization_matrix`` is supplied in the codec
        features CSV.
    """
    # Skip if already using the default quantisation matrix
    if codec_features["quantization_matrix"] is None:
        return None

    # Skip for lossless codecs since no quantization is applied
    if codec_features["lossless"]:
        return None

    # Skip if no default quantization matrix is defined for the codec in use
    if (
        codec_features["wavelet_index"],
        codec_features["wavelet_index_ho"],
        codec_features["dwt_depth"],
        codec_features["dwt_depth_ho"],
    ) not in QUANTISATION_MATRICES:
        return None

    # Skip if the level requires a custom quantisation matrix to be specified
    constrained_values = codec_features_to_trivial_level_constraints(codec_features)
    del constrained_values["custom_quant_matrix"]
    if False not in allowed_values_for(
        LEVEL_CONSTRAINTS, "custom_quant_matrix", constrained_values
    ):
        return None

    # Override the quantization_matrix setting in the codec features to force
    # the default quantization matrix to be used
    codec_features = CodecFeatures(codec_features, quantization_matrix=None,)

    # White noise signal used since it should put some energy into all
    # subbands so differences in quantisation should be evident. Also,
    # maximises the chances of quantisation being applied.
    return Stream(
        sequences=[
            make_sequence(
                codec_features,
                white_noise(
                    codec_features["video_parameters"],
                    codec_features["picture_coding_mode"],
                ),
            )
        ]
    )


def quantization_matrix_from_generator(codec_features, generator):
    """
    Generate a quantization matrix for the specified set of codec_features
    where the values are taken from the provided generator function.
    """
    values = iter(generator)

    dwt_depth = codec_features["dwt_depth"]
    dwt_depth_ho = codec_features["dwt_depth_ho"]

    out = {}
    if dwt_depth_ho == 0:
        out[0] = {"LL": int(next(values))}
    else:
        out[0] = {"L": int(next(values))}
        for level in range(1, dwt_depth_ho + 1):
            out[level] = {"H": int(next(values))}
    for level in range(dwt_depth_ho + 1, dwt_depth + dwt_depth_ho + 1):
        out[level] = {
            "HL": int(next(values)),
            "LH": int(next(values)),
            "HH": int(next(values)),
        }

    return out


@decoder_test_case_generator
def custom_quantization_matrix(codec_features):
    """
    **Tests that a custom quantization matrix can be specified.**

    A series of bitstreams with different custom quantisation matrices are
    generated as follows:

    ``custom_quantization_matrix[zeros]``
        Specifies a custom quantisation matrix with all matrix values set to zero.

    ``custom_quantization_matrix[arbitrary]``
        Specifies a custom quantisation matrix with all matrix values set to
        different, though arbitrary, values.

    ``custom_quantization_matrix[default]``
        Specifies a custom quantisation matrix containing the same values as
        the default quantisation matrix. This test case is only generated when
        a default quantization matrix is defined for the codec.

    These test cases are only generated when permitted by the VC-2 level in use
    and for lossy coding modes.
    """
    # Skip for lossless codecs since no quantization is applied
    if codec_features["lossless"]:
        return

    # Skip if the level disallows custom quantisation matrices
    constrained_values = codec_features_to_trivial_level_constraints(codec_features)
    constrained_values["custom_quant_matrix"] = True
    allowed_quant_matrix_values = allowed_values_for(
        LEVEL_CONSTRAINTS, "quant_matrix_values", constrained_values
    )
    if allowed_quant_matrix_values == ValueSet():
        return

    # A set of alternative quantisation matrices to test
    # [(description, quantization_matrix), ...]
    candidate_matrices = []

    # A special case: a flat (all zeros) quantisation matrix
    candidate_matrices.append(
        ("zeros", quantization_matrix_from_generator(codec_features, repeat(0)))
    )

    # An arbitrary quantisation matrix with different values in each entry (if
    # possible)
    if allowed_quant_matrix_values == AnyValue():
        values = count()
    else:
        values = cycle(sorted(allowed_quant_matrix_values.iter_values()))
    candidate_matrices.append(
        ("arbitrary", quantization_matrix_from_generator(codec_features, values))
    )

    # If a default quantisation matrix is available, try explicitly giving the
    # values from the default quant matrix
    wavelet_specification = (
        codec_features["wavelet_index"],
        codec_features["wavelet_index_ho"],
        codec_features["dwt_depth"],
        codec_features["dwt_depth_ho"],
    )
    if wavelet_specification in QUANTISATION_MATRICES:
        candidate_matrices.append(
            ("default", QUANTISATION_MATRICES[wavelet_specification],)
        )

    # Generate test cases for each custom quantisation matrix.
    for description, quantization_matrix in candidate_matrices:
        # If we happen to have generated the quantization matrix specified in
        # the codec features, skip that case...
        if quantization_matrix == codec_features["quantization_matrix"]:
            continue

        # If we the level restricts the quantisation matrix values such that
        # the generated cases is not allowed, skip it.
        if not all(
            value in allowed_quant_matrix_values
            for orients in quantization_matrix.values()
            for value in orients.values()
        ):
            continue

        # White noise signal used since it should put some energy into all
        # subbands so differences in quantisation should be evident. Also,
        # maximises the chances of quantisation being applied.
        yield TestCase(
            Stream(
                sequences=[
                    make_sequence(
                        CodecFeatures(
                            codec_features, quantization_matrix=quantization_matrix
                        ),
                        white_noise(
                            codec_features["video_parameters"],
                            codec_features["picture_coding_mode"],
                        ),
                    )
                ]
            ),
            description,
        )
