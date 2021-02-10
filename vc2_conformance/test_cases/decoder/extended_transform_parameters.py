"""
Tests which verify the extended transform parameters (12.4.4) are correctly
read.
"""

from copy import deepcopy

from vc2_data_tables import ParseCodes

from vc2_conformance.bitstream import (
    Stream,
    autofill_major_version,
)

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.constraint_table import allowed_values_for

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.codec_features import codec_features_to_trivial_level_constraints

from vc2_conformance.picture_generators import static_sprite

from vc2_conformance.encoder import make_sequence


def update_extended_transform_parameters(sequence, *args, **kwargs):
    r"""
    Apply a :py:meth:`dict.update` to all
    :py:class:`~vc2_conformance.bitstream.ExtendedTransformParameters` in a
    :py:class:`~vc2_conformance.bitstream.Sequence`.

    Returns two values:
    * A new sequence (a copy is made and the old sequence left unmodified)
    * A bool which is True if the changes specified changed the extended
      transform parameter block.
    """
    sequence = deepcopy(sequence)
    changed = False
    for data_unit in sequence["data_units"]:
        if data_unit["parse_info"]["parse_code"] in (
            ParseCodes.low_delay_picture,
            ParseCodes.high_quality_picture,
        ):
            extended_transform_parameters = data_unit["picture_parse"][
                "wavelet_transform"
            ]["transform_parameters"]["extended_transform_parameters"]
        elif (
            data_unit["parse_info"]["parse_code"]
            in (
                ParseCodes.low_delay_picture_fragment,
                ParseCodes.high_quality_picture_fragment,
            )
            and "transform_parameters" in data_unit["fragment_parse"]
        ):
            extended_transform_parameters = data_unit["fragment_parse"][
                "transform_parameters"
            ]["extended_transform_parameters"]
        else:
            continue

        before = extended_transform_parameters.copy()
        extended_transform_parameters.update(*args, **kwargs)
        changed |= extended_transform_parameters != before

    return sequence, changed


@decoder_test_case_generator
def extended_transform_parameters(codec_features):
    """
    **Tests that extended transform parameter flags are handled correctly.**

    Ensures that extended transform parameters fields (12.4.4) are correctly
    handled by decoders for symmetric transform modes.

    ``extended_transform_parameters[asym_transform_index_flag]``
        Verifies that ``asym_transform_index_flag`` can be set to ``1``.

    ``extended_transform_parameters[asym_transform_flag]``
        Verifies that ``asym_transform_flag`` can be set to ``1``.

    These test cases are skipped for streams whose major version is less than 3
    (which do not support the extended transform parameters header).
    Additionally, these test cases are skipped for asymmetric transforms when
    the flag being tested must already be ``1``.
    """
    # Generate a base sequence in which we'll replace the extended transform
    # parameters later
    base_sequence = make_sequence(
        codec_features,
        static_sprite(
            codec_features["video_parameters"],
            codec_features["picture_coding_mode"],
        ),
    )

    # Skip this test if the generated sequence does not use major_version 3
    # since no extended transform parameters field will be present.
    autofill_major_version(Stream(sequences=[base_sequence]))
    major_versions = [
        data_unit["sequence_header"]["parse_parameters"]["major_version"]
        for data_unit in base_sequence["data_units"]
        if data_unit["parse_info"]["parse_code"] == ParseCodes.sequence_header
    ]
    if major_versions[0] != 3:
        return

    # Try enabling the asym_transform_index_flag and asym_transform_flag, if
    # not already enabled and if the current level permits it
    constrained_values = codec_features_to_trivial_level_constraints(codec_features)
    if True in allowed_values_for(
        LEVEL_CONSTRAINTS, "asym_transform_index_flag", constrained_values
    ):
        sequence, changed = update_extended_transform_parameters(
            base_sequence,
            asym_transform_index_flag=True,
            wavelet_index_ho=codec_features["wavelet_index_ho"],
        )
        if changed:
            yield TestCase(Stream(sequences=[sequence]), "asym_transform_index_flag")

    if True in allowed_values_for(
        LEVEL_CONSTRAINTS, "asym_transform_flag", constrained_values
    ):
        sequence, changed = update_extended_transform_parameters(
            base_sequence,
            asym_transform_flag=True,
            dwt_depth_ho=codec_features["dwt_depth_ho"],
        )
        if changed:
            yield TestCase(Stream(sequences=[sequence]), "asym_transform_flag")
