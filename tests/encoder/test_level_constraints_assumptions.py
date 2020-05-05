"""
Encoder level constraints assumptions
=====================================

In order to generate streams conforming to particular VC-2 levels, the
:py:mod:`vc2_conformance.encoder` module must find coding choices which satisfy
the VC-2 level constraints as given in
:py:mod:`~vc2_conformance.level_constraints.LEVEL_CONSTRAINTS`. In the general
case, a complex constraint solver would be required to make these choices. In
practice, however, VC-2's level constraints (currently) have certain structural
properties which mean a global constraint solver is unnecessary. The tests in
this file verify that these properties hold for the existing VC-2 level
constraints table (and will fail should this ever changes).


Background
----------

The VC-2 level constraints table introduces dependencies between coding
choices. For example, levels may permit only certain combinations of resolution
and frame rate. Therefore, for a given level, the frame rates you can pick may
depend on the frame size you chose and vice versa -- that is, these parameters
are not necessarily independent.

In an ideal world, the :py:class:`vc2_conformance.codec_features.CodecFeatures`
would fully constrain the choices an encoder might make as far as complying
with a particular VC-2 level might be concerned. As such, the encoder, in an
ideal world, would not need to concern itself with limiting its choices to meet
the requirements of a particular level -- if a conforming set of codec features
are provided the encoder would always produce a conformant stream.

Unfortunately, VC-2's levels constrain not just semantic coding options (such
as picture formats or transform parameters) but also constrain the syntax of
how those parameters are encoded.

For instance, one might use the '1080p50' base video format to indicate a
1920x1080 50 FPS format, or one might use some other base video format and use
the custom dimensions and frame rate flags to specify the same options. In
principle, the choice shouldn't matter (though some choices might take up fewer
bits in a bitstream than others), however VC-2's levels explicitly enforce
particular encodings.

The result of levels constraining parameter encoding choices is that some
semantically irrelevant choices the encoder must make autonomously are
constrained by the VC-2 level. As a consequence, the encoder is also
responsible for making these choices conform to the level constraints table --
i.e. some kind of automated constraint solver is required.

In practice, level constraints tend to be simple and so it is not necessary to
use a global constraint solver to pick all stream parameters. In the sections
below we'll more concretely define what 'simple' means and what simplifications
this permits.


Level constraint independence testing
-------------------------------------

Constraint tables (:py:mod:`vc2_conformance._constraint_table`) are expressed
as a series of 'columns', each of which describes a permitted set of
parameters. For example, consider the following extract from the VC-2
constraint table:

=======================  ============  =====  =====
level                    1             64     64
...                      ...           ...    ...
base_video_format        1,2,3,4,5,6   13     14
picture_coding_mode      0             0      0
custom_frame_rate_flag   FALSE         ANY    FALSE
frame_rate_index         n/a           8      n/a
...                      ...           ...    ...
wavelet_index            0,1,2,3,4     4      4
dwt_depth                0-4           2      2
...                      ...           ...    ...
=======================  ============  =====  =====

The first column of this table indicates the criteria for a level 1 stream.
Specifically, any stream meeting the criteria below is a valid level 1 stream:

* The base video format must be 1, 2, 3, 4, 5 or 6
* The picture coding mode must be 0
* The custom frame rate flag must be false (and no frame rate index given)
* The wavelet index must be 0, 1, 2, 3 or 4
* The transform depth between 0 and 4.

Each of the parameters specified by this level may be chosen independently
(albeit within the limited ranges given). Therefore we can say that for level
1, all of the parameters are independent.

The second and third columns together give the requirements for a level 64
stream. This time:

* The base video format must be 13 or 14
* The picture coding mode must be 0
* The custom frame rate flag may be used only if the base video format is 13
  (and if it is, the frame rate index must be 8).
* The wavelet index must be 4
* The transform depth must be 2

In this case the parameters are *not* all independent: the choice of base video
format may restrict the use of a custom frame rate (and vice versa). Some
parameters are independent, however: since both columns specify wavelet index
4, no matter the other options, we always have the same (albeit singular)
option of '4' available.

As illustrated by this example, we can say parameters are independent within a
level when all columns associated with that level always permit same values for
that parameter.

.. note::

    Though parameters for which all columns contain the same value are
    always independent, the reverse is not true. That is, it is possible that
    some parameters are independent despite having different values in
    different columns. For example, consider the following constraint table:

    =======  ===  ===  ===  ===
    level    100  100  100  100
    param_a  1    2    1    2
    param_b  10   10   20   20
    =======  ===  ===  ===  ===

    Here, parameters 'a' and 'b' do not have the same value in every column,
    but *are* independent from each other because every combination of values is
    permitted. That is the table above is equivalent to:

    =======  =====
    level    100
    param_a  1,2
    param_b  10,20
    =======  =====

    As a consequence, the simple 'all columns the same' independence test may
    (falsely) identify some columns as non-independent. This will only be a
    problem if a level is introduced in the future which relies on this
    expanded form of table for a field we require to be independent.


Required degree of parameter independence for encoder correctness
-----------------------------------------------------------------

Whenever non-independent parameters are to be chosen by the encoder, a
constraint solving mechanism must be used to ensure a valid combination of
choices are made. As such, the fewer the number choices, and the fewer places
they are to be made, the simpler the implementation can be.

The encoder behaviour is controlled by a supplied set of
:py:class:`~vc2_conformance.codec_features.CodecFeatures` (which are provided
by a user of the conformance software). These specifications directly define a
significant number of the levels-constrained parameters, and these may be
enumerated using
:py:func:`vc2_conformance.codec_features.codec_features_to_trivial_level_constraints`.
It is the user's responsibility to choose codec features which satisfy the
restrictions of the level they choose.

.. note::

    Should a non-conformant configuration be supplied, this will be detected
    later when the test-case generator uses the bit stream validator to decode
    the generated stream.

The remaining level-constrained parameters can be grouped into two categories:
sequence header (11.1) parameters and everything else. The sequence header
parameters are noteworthy as from the level constraints table we can see that
these are not always independent in certain levels. For example, see level 64
in the example constraint table earlier. As a consequence, a simple constraint
solver is used in :py:mod:`vc2_conformance.encoder.sequence_header` to generate
sequence headers conforming to the current level.

So long as all non-sequence header related parameters are independent, no other
constraint solving logic is required, and what exists can be contained entirely
within the sequence header generator. This test file verifies this is the case,
ensuring that this encoder implementation cannot invalidate any level
constraints by not using a global constraint solver.
"""

from collections import defaultdict

from vc2_data_tables import Profiles

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.codec_features import codec_features_to_trivial_level_constraints

from sample_codec_features import MINIMAL_CODEC_FEATURES


PARAMETERS_FIXED_BY_CODEC_FEATURES = [
    "level",
    "profile",
    "major_version",
    "minor_version",
    "picture_coding_mode",
    "wavelet_index",
    "dwt_depth",
    "slices_x",
    "slices_y",
    "slices_have_same_dimensions",
    "custom_quant_matrix",
    "slice_bytes_numerator",
    "slice_bytes_denominator",
    "slice_prefix_bytes",
]
"""
The constraint table parameters which are trivially defined by a set of
:py:class:`~vc2_conformance.codec_features.CodecFeatures`.
"""


SEQUENCE_HEADER_PARAMETERS = [
    "base_video_format",
    "custom_dimensions_flag",
    "frame_width",
    "frame_height",
    "custom_color_diff_format_flag",
    "color_diff_format_index",
    "custom_scan_format_flag",
    "source_sampling",
    "custom_frame_rate_flag",
    "frame_rate_index",
    "frame_rate_numer",
    "frame_rate_denom",
    "custom_pixel_aspect_ratio_flag",
    "pixel_aspect_ratio_index",
    "pixel_aspect_ratio_numer",
    "pixel_aspect_ratio_denom",
    "custom_clean_area_flag",
    "clean_width",
    "clean_height",
    "left_offset",
    "top_offset",
    "custom_signal_range_flag",
    "custom_signal_range_index",
    "luma_offset",
    "luma_excursion",
    "color_diff_offset",
    "color_diff_excursion",
    "custom_color_spec_flag",
    "color_spec_index",
    "custom_color_primaries_flag",
    "color_primaries_index",
    "custom_color_matrix_flag",
    "color_matrix_index",
    "custom_transfer_function_flag",
    "transfer_function_index",
    "picture_coding_mode",
]
"""
The constraint table parameters which constrain the sequence header. These
parameters are allowed to be interdependent.
"""


def test_parameters_fixed_by_codec_features_list():
    # This sanity check makes sure that every entry in
    # PARAMETERS_FIXED_BY_CODEC_FEATURES actually can be inferred from a set of
    # codec features (by the codec_features_to_trivial_level_constraints
    # function to be specific)

    expected = set()
    for profile in Profiles:
        values = codec_features_to_trivial_level_constraints(
            dict(MINIMAL_CODEC_FEATURES, profile=profile)
        )
        expected.update(values.keys())

    assert set(PARAMETERS_FIXED_BY_CODEC_FEATURES) == expected


def test_non_sequence_header_constraints_are_independent():
    # This test verifies that we don't need a global constraint solver in the
    # encoder module in order to generate streams which conform to a particular
    # VC-2 level. (Please make sure to read the extensive introductory notes at
    # the top of this module to understand why this might be necessary and why
    # this test is sufficient).
    #
    # This test checks that, after fixing the parameters which can be inferred
    # directly from the CodecFeatures (see PARAMETERS_FIXED_BY_CODEC_FEATURES),
    # only the sequence header related parameters are interdependent. In
    # particular, this means that we only need to perform constraint solving
    # for sequence header generation and not the whole stream.
    #
    # If this test begins to fail when a new VC-2 level is added, one of two
    # things may have happened:
    #
    # 1. The new level may have introduced a new dependency between non
    #    sequence header parameters
    # 2. The new level may have independent parameters which are expressed in a
    #    way this test function is unable to identify are independent (see
    #    notes at top of module).
    #
    # In case 1, some (probably significant) effort will be required to extend
    # the constraint solving behaviour of the encoder from just the
    # sequence_header module to the encoder in general. Test case generators
    # which generate custom sequence headers will also need to be updated
    # accordingly.
    #
    # In case 2, this test will need to be improved to handle these cases.

    # Find all groups of columns which might be selected by the
    # PARAMETERS_FIXED_BY_CODEC_FEATURES
    constraint_column_groups = defaultdict(list)
    for column in LEVEL_CONSTRAINTS:
        constraint_column_groups[
            tuple(column[key] for key in PARAMETERS_FIXED_BY_CODEC_FEATURES)
        ].append(column)

    # Check, for each set of columns, that any parameter not listed in
    # SEQUENCE_HEADER_PARAMETERS is independent
    for columns in constraint_column_groups.values():
        keys = set(key for column in columns for key in column)

        non_independent_parameters = set(
            key
            for key in keys
            if any(column.get(key) != columns[0].get(key) for column in columns[1:])
        )

        assert non_independent_parameters - set(SEQUENCE_HEADER_PARAMETERS) == set()


def test_slice_prefix_bytes_can_be_zero():
    # The current encoder does not support setting slice_prefix_bytes to
    # anything other than 0 (simplifying things somewhat). This test verifies
    # that no level requires anything different.
    for values in LEVEL_CONSTRAINTS:
        if Profiles.high_quality in values["profile"]:
            assert 0 in values["slice_prefix_bytes"]
