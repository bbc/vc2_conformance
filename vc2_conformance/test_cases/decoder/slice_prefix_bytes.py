import logging

from vc2_data_tables import Profiles

from vc2_conformance.bitstream import Stream

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.constraint_table import allowed_values_for

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.codec_features import codec_features_to_trivial_level_constraints

from vc2_conformance.encoder import make_sequence

from vc2_conformance.picture_generators import mid_gray

from vc2_conformance.test_cases.decoder.common import (
    make_dummy_end_of_sequence,
    iter_slices_in_sequence,
)


def iter_slice_parameters_in_sequence(sequence):
    """
    Iterate over all of the slice parameters blocks in a sequence.

    Generates a series of references to
    :py:class:`~vc2_conformance.bitstream.SliceParameters` dicts, one for each
    slice present in the provided
    :py:class:`~vc2_conformance.bitstream.Sequence`.
    """
    for data_unit in sequence["data_units"]:
        if "picture_parse" in data_unit:
            wt = data_unit["picture_parse"]["wavelet_transform"]
            yield wt["transform_parameters"]["slice_parameters"]
        elif "fragment_parse" in data_unit:
            if "transform_parameters" in data_unit["fragment_parse"]:
                yield data_unit["fragment_parse"]["transform_parameters"][
                    "slice_parameters"
                ]


@decoder_test_case_generator
def slice_prefix_bytes(codec_features):
    """
    **Tests the decoder can handle a non-zero number of slice prefix bytes.**

    Produces test cases with a non-zero number of slice prefix bytes
    containing the following values:

    ``slice_prefix_bytes[zeros]``
        All slice prefix bytes are 0x00.

    ``slice_prefix_bytes[ones]``
        All slice prefix bytes are 0xFF.

    ``slice_prefix_bytes[end_of_sequence]``
        All slice prefix bytes contain bits which encode an end of sequence
        data unit (10.4).

    These test cases apply only to the high quality profile and are omitted
    when the low delay profile is used.
    """
    # This test only applies to high quality codecs
    if codec_features["profile"] != Profiles.high_quality:
        return

    constrained_values = codec_features_to_trivial_level_constraints(codec_features)
    allowed_slice_prefix_bytes = allowed_values_for(
        LEVEL_CONSTRAINTS, "slice_prefix_bytes", constrained_values
    )

    mid_gray_pictures = list(
        mid_gray(
            codec_features["video_parameters"],
            codec_features["picture_coding_mode"],
        )
    )

    test_cases = [
        ("zeros", b"\x00"),
        ("ones", b"\xFF"),
        ("end_of_sequence", make_dummy_end_of_sequence()),
    ]

    for description, filler in test_cases:
        sequence = make_sequence(codec_features, mid_gray_pictures)

        # Determine how many slice prefix bytes we can fit in our slices
        if codec_features["lossless"]:
            # Lossless slices can be as large as we like; assign enough slice
            # bytes for the full set of filler bytes
            slice_prefix_bytes = len(filler)
        else:
            # Find the space assigned for coefficients in the smallest slice in
            # a fixed-bit-rate stream; we'll replace all slice coefficients
            # with slice prefix bytes.
            slice_prefix_bytes = min(
                (
                    hq_slice["slice_y_length"]
                    + hq_slice["slice_c1_length"]
                    + hq_slice["slice_c2_length"]
                )
                * state["slice_size_scaler"]
                for state, sx, sy, hq_slice in iter_slices_in_sequence(
                    codec_features, sequence
                )
            )

        # Check level constraints allow this slice_prefix_bytes
        #
        # NB: This implementation assumes that either the slice_prefix_bytes
        # field is required to be zero or it is free to be any value. This
        # assumption is verified for all existing VC-2 levels in the tests for
        # this module. Should this assumption be violated, more sophisticated
        # behaviour will be required here...
        if slice_prefix_bytes not in allowed_slice_prefix_bytes:
            continue

        if slice_prefix_bytes < len(filler):
            logging.warning(
                (
                    "Codec '%s' has a very small picture_bytes value "
                    "meaning the slice_prefix_bytes[%s] test case may not "
                    "be as useful as intended."
                ),
                codec_features["name"],
                description,
            )

        # Set the number of slice prefix bytes in all slice parameter headers
        for slice_parameters in iter_slice_parameters_in_sequence(sequence):
            assert slice_parameters["slice_prefix_bytes"] == 0
            slice_parameters["slice_prefix_bytes"] = slice_prefix_bytes

        # Add prefix bytes to all slices
        prefix_bytes = (filler * slice_prefix_bytes)[:slice_prefix_bytes]
        for state, sx, sy, hq_slice in iter_slices_in_sequence(
            codec_features, sequence
        ):
            hq_slice["prefix_bytes"] = prefix_bytes

            # Keep overall slice size the same for lossy (constant bit rate)
            # modes
            if not codec_features["lossless"]:
                total_length = (
                    hq_slice["slice_y_length"]
                    + hq_slice["slice_c1_length"]
                    + hq_slice["slice_c2_length"]
                )

                total_length -= slice_prefix_bytes // state["slice_size_scaler"]

                hq_slice["slice_y_length"] = 0
                hq_slice["slice_c1_length"] = 0
                hq_slice["slice_c2_length"] = total_length

        yield TestCase(Stream(sequences=[sequence]), description)
