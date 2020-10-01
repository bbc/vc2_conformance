"""
The :py:mod:`vc2_conformance.level_constraints` module contains definitions of
constraints imposed on VC-2 bitstreams by the various VC-2 level
specifications.

Sequence data unit ordering restrictions
----------------------------------------

Levels may restrict the ordering or choice of data unit types within a
bitstream. These restrictions are described using
:py:mod:`~vc2_conformance.symbol_re` regular expressions provided in
:py:data:`LEVEL_SEQUENCE_RESTRICTIONS`.

.. autodata:: LEVEL_SEQUENCE_RESTRICTIONS
    :annotation: = {level: LevelSequenceRestrictions, ...}

.. autoclass:: LevelSequenceRestrictions


Coding parameter restrictions
-----------------------------

Levels impose various restrictions on bitstream parameters and values. These
restrictions are collected into a constraint table (see
:py:mod:`~vc2_conformance.constraint_table`) in :py:data:`LEVEL_CONSTRAINTS`.

.. autodata:: LEVEL_CONSTRAINTS
    :annotation: = <constraint table>

.. autodata:: LEVEL_CONSTRAINT_ANY_VALUES
    :annotation: = {key: ValueSet, ...}

"""

import os

from collections import namedtuple

from vc2_conformance.constraint_table import (
    read_constraints_from_csv,
    ValueSet,
)

from vc2_data_tables.csv_readers import read_lookup_from_csv

from vc2_data_tables import (
    Levels,
    Profiles,
    BaseVideoFormats,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetFrameRates,
    PresetPixelAspectRatios,
    PresetSignalRanges,
    PresetColorSpecs,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    PictureCodingModes,
    WaveletFilters,
)


__all__ = [
    "LEVEL_SEQUENCE_RESTRICTIONS",
    "LEVEL_CONSTRAINTS",
    "LEVEL_CONSTRAINT_ANY_VALUES",
]


LevelSequenceRestrictions = namedtuple(
    "LevelSequenceRestrictions",
    "sequence_restriction_explanation,sequence_restriction_regex",
)
"""
Restrictions on sequence orderings for a VC-2 level.

Parameters
----------
sequence_restriction_explanation : str
    A human readable explanation of the restriction imposed (informative).
sequence_restriction_regex : str
    A regular expression describing the sequence ordering allowed which can be
    matched using a :py:class:`~vc2_conformance.symbol_re.Matcher`. Each symbol
    is a :py:class:`~vc2_data_tables.ParseCodes` name string.
"""

LEVEL_SEQUENCE_RESTRICTIONS = read_lookup_from_csv(
    os.path.join(os.path.dirname(__file__), "level_sequence_restrictions.csv"),
    Levels,
    LevelSequenceRestrictions,
)
"""
A lookup from :py:class:`Levels` to :py:class:`LevelSequenceRestrictions`
(loaded from ``vc2_conformance/level_sequence_restrictions.csv``) describing the
restrictions on sequences imposed by each VC-2 level.
"""


LEVEL_CONSTRAINTS = read_constraints_from_csv(
    os.path.join(
        os.path.dirname(__file__),
        "level_constraints.csv",
    )
)
"""
A constraint table (see :py:mod:`vc2_conformance.constraint_table`) loaded
from ``vc2_conformance/level_constraints.csv``.

Constraints which apply due to levels. Keys correspond to particular bitstream
values or properties and are enumerated below:

* (11.2.1)
    * ``level``: int (from the :py:class:`Levels` enum)
    * ``profile``: int (from the :py:class:`Profiles` enum)
    * ``major_version``: int
    * ``minor_version``: int
* (11.1)
    * ``base_video_format``: int (from the :py:class:`BaseVideoFormats` enum)
* (11.4.3)
    * ``custom_dimensions_flag``: bool
    * ``frame_width``: int
    * ``frame_height``: int
* (11.4.4)
    * ``custom_color_diff_format_flag``: bool
    * ``color_diff_format_index``: int (from the :py:class:`ColorDifferenceSamplingFormats` enum)
* (11.4.5)
    * ``custom_scan_format_flag``: bool
    * ``source_sampling``: int (from the :py:class:`SourceSamplingModes` enum)
* (11.4.6)
    * ``custom_frame_rate_flag``: bool
    * ``frame_rate_index``: int (from the :py:class:`PresetFrameRates` enum, or 0)
    * ``frame_rate_numer``: int
    * ``frame_rate_denom``: int
* (11.4.7)
    * ``custom_pixel_aspect_ratio_flag``: bool
    * ``pixel_aspect_ratio_index``: int (from the :py:class:`PresetPixelAspectRatios` enum, or 0)
    * ``pixel_aspect_ratio_numer``: int
    * ``pixel_aspect_ratio_denom``: int
* (11.4.8)
    * ``custom_clean_area_flag``: bool
    * ``clean_width``: int
    * ``clean_height``: int
    * ``left_offset``: int
    * ``top_offset``: int
* (11.4.9)
    * ``custom_signal_range_flag``: bool
    * ``custom_signal_range_index``: int (from the :py:class:`PresetSignalRanges` enum, or 0)
    * ``luma_offset``: int
    * ``luma_excursion``: int
    * ``color_diff_offset``: int
    * ``color_diff_excursion``: int
* (11.4.10)
    * ``custom_color_spec_flag``: bool
    * ``color_spec_index``: int (from the :py:class:`PresetColorSpecs` enum)
    * ``custom_color_primaries_flag``: bool
    * ``color_primaries_index``: int (from the :py:class:`PresetColorPrimaries` enum)
    * ``custom_color_matrix_flag``: bool
    * ``color_matrix_index``: int (from the :py:class:`PresetColorMatrices` enum)
    * ``custom_transfer_function_flag``: bool
    * ``transfer_function_index``: int (from the :py:class:`PresetTransferFunctions` enum)
* (11.1)
    * ``picture_coding_mode``: int (from the :py:class:`PictureCodingModes` enum)
* (12.4.1)
    * ``wavelet_index``: int (from the :py:class:`WaveletFilters` enum)
    * ``dwt_depth``: int
* (12.4.4.1)
    * ``asym_transform_index_flag``: bool
    * ``wavelet_index_ho``: int (from the :py:class:`WaveletFilters` enum)
    * ``asym_transform_flag``: bool
    * ``dwt_depth_ho``: int
* (12.4.5.2)
    * ``slices_x``: int (giving the allowed number of slices in the x dimension)
    * ``slices_y``: int (giving the allowed number of slices in the y dimension)
    * ``slices_have_same_dimensions``: bool. True iff all slices contain
      exactly the same number of transform components.
    * ``slice_bytes_numerator``: int
    * ``slice_bytes_denominator``: int
    * ``slice_prefix_bytes``: int
    * ``slice_size_scaler``: int
* (12.4.5.3)
    * ``custom_quant_matrix``: bool
    * ``quant_matrix_values``: int (giving the allowed values within a custom
      quantisation matrix).
* (13.5.3)
    * ``qindex``: int (the allowed qindex values as defined by individual slices)
* (13.5.3.2)
    * ``total_slice_bytes``: int (total number of bytes allowed in a high quality
      picture slice, including all prefix bytes and slice size fields.

See also: :py:data:`LEVEL_CONSTRAINT_ANY_VALUES`.
"""

LEVEL_CONSTRAINT_ANY_VALUES = {
    "level": ValueSet(*Levels),
    "profile": ValueSet(*Profiles),
    "base_video_format": ValueSet(*BaseVideoFormats),
    "custom_dimensions_flag": ValueSet(False, True),
    "custom_color_diff_format_flag": ValueSet(False, True),
    "color_diff_format_index": ValueSet(*ColorDifferenceSamplingFormats),
    "custom_scan_format_flag": ValueSet(False, True),
    "source_sampling": ValueSet(*SourceSamplingModes),
    "custom_frame_rate_flag": ValueSet(False, True),
    "frame_rate_index": ValueSet(0, *PresetFrameRates),
    "custom_pixel_aspect_ratio_flag": ValueSet(False, True),
    "pixel_aspect_ratio_index": ValueSet(0, *PresetPixelAspectRatios),
    "custom_clean_area_flag": ValueSet(False, True),
    "custom_signal_range_flag": ValueSet(False, True),
    "custom_signal_range_index": ValueSet(0, *PresetSignalRanges),
    "custom_color_spec_flag": ValueSet(False, True),
    "color_spec_index": ValueSet(0, *PresetColorSpecs),
    "custom_color_primaries_flag": ValueSet(False, True),
    "color_primaries_index": ValueSet(*PresetColorPrimaries),
    "custom_color_matrix_flag": ValueSet(False, True),
    "color_matrix_index": ValueSet(*PresetColorMatrices),
    "custom_transfer_function_flag": ValueSet(False, True),
    "transfer_function_index": ValueSet(*PresetTransferFunctions),
    "picture_coding_mode": ValueSet(*PictureCodingModes),
    "wavelet_index": ValueSet(*WaveletFilters),
    "asym_transform_index_flag": ValueSet(False, True),
    "wavelet_index_ho": ValueSet(*WaveletFilters),
    "asym_transform_flag": ValueSet(False, True),
    "slices_have_same_dimensions": ValueSet(False, True),
    "custom_quant_matrix": ValueSet(False, True),
}
"""
For keys in :py:data:`LEVEL_CONSTRAINTS` which may hold
:py:class:`~vc2_conformance.constraint_table.AnyValue`, defines an explicit
:py:class:`~vc2_conformance.constraint_table.ValueSet` defining all valid
values, for example when the key refers to an enumerated value. Where the range
of allowed values is truly open ended, no value is provided in this dictionary.
"""
