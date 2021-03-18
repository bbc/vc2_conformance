"""
The :py:mod:`vc2_conformance.encoder.sequence_header` module contains routines
for encoding a set of video format and codec parameters into sequence headers.

The :py:func:`make_sequence_header_data_unit` function is used to generate
sequence headers by the encoder:

.. autofunction:: make_sequence_header_data_unit

In practice there are often many potential sequence header encodings for a
given set of video parameters. For example, when a video format closely matches
a predefined base video format, the various ``custom_*_flag`` overrides may
largely be omitted. This is optional, however, and an encoder is free to use
these overrides explicitly even when they're not required.

The :py:func:`make_sequence_header_data_unit` function always attempts to use
the most compact encoding it can. Some test cases, however may wish to use less
compact encodings and so to support this the :py:func:`iter_sequence_headers`
function is provided:

.. autofunction:: iter_sequence_headers

"""

from functools import partial

from vc2_data_tables import (
    Levels,
    ParseCodes,
    BaseVideoFormats,
    BASE_VIDEO_FORMAT_PARAMETERS,
    PRESET_FRAME_RATES,
    PRESET_PIXEL_ASPECT_RATIOS,
    PRESET_SIGNAL_RANGES,
    PRESET_COLOR_SPECS,
)

from vc2_conformance.constraint_table import (
    filter_constraint_table,
    allowed_values_for,
)

from vc2_conformance.level_constraints import (
    LEVEL_CONSTRAINTS,
    LEVEL_CONSTRAINT_ANY_VALUES,
)

from vc2_conformance.codec_features import codec_features_to_trivial_level_constraints

from vc2_conformance.pseudocode.video_parameters import set_source_defaults

from vc2_conformance.bitstream import (
    DataUnit,
    ParseInfo,
    ParseParameters,
    SequenceHeader,
    SourceParameters,
    FrameSize,
    ColorDiffSamplingFormat,
    ScanFormat,
    FrameRate,
    PixelAspectRatio,
    CleanArea,
    SignalRange,
    ColorSpec,
    ColorPrimaries,
    ColorMatrix,
    TransferFunction,
)

from vc2_conformance.encoder.exceptions import IncompatibleLevelAndVideoFormatError


__all__ = [
    "rank_base_video_format_similarity",
    "rank_allowed_base_video_format_similarity",
    "iter_source_parameter_options",
    "make_parse_parameters",
    "iter_sequence_headers",
    "make_sequence_header",
    "make_sequence_header_data_unit",
]


def zip_longest_repeating_final_value(*iterables):
    """
    Like :py:func:`zip`, but if some iterators finish before others, their last
    value is repeated to fill in the missing entries.

    For example::

        >>> list(zip_longest_repeat_last(
        ...     [1, 2, 3],
        ...     ["a", "b", "c", "d", "e"],
        ... ))
        [(1, "a"), (2, "b"), (3, "c"), (3, "d"), (3, "e")]

    If an iterator doesn't produce any values, its missing values will be
    filled with None.
    """
    iterators = list(map(iter, iterables))

    last_zipped = (None,) * len(iterators)

    some_iterators_running = True
    while some_iterators_running:
        zipped = []
        some_iterators_running = False
        for i, iterator in enumerate(iterators):
            try:
                zipped.append(next(iterator))
                some_iterators_running = True
            except StopIteration:
                zipped.append(last_zipped[i])

        if some_iterators_running:
            last_zipped = tuple(zipped)
            yield last_zipped


def iter_custom_options_dicts(
    base_video_parameters,
    video_parameters,
    level_constraints_dict,
    dict_type,
    flag_key,
    parameters,
    presets=None,
    preset_index_constraint_key=None,
):
    """
    A generator which enumerates valid sets of VC-2 custom option settings
    which achieve a set of video parameters given a set of base video
    parameters and level constraints.

    Options dictionaries will be generated in ascending order of explicitness.

    Example usage::

        >>> from functools import partial
        >>> from collections import defaultdict
        >>> from vc2_data_tables import (
        ...     BASE_VIDEO_FORMAT_PARAMETERS,
        ...     PRESET_PIXEL_ASPECT_RATIOS,
        ... )
        >>> from vc2_conformance.constraint_table import AnyValue
        >>> from vc2_conformance.bitstream import (
        ...     PixelAspectRatio,
        ... )
        >>> from vc2_conformance.pseudocode.video_parameters import (
        ...     PixelAspectRatio,
        ...     set_source_defaults,
        ... )

        >>> iter_pixel_aspect_ratio_options = partial(
        ...     iter_custom_options_dicts,
        ...     dict_type=PixelAspectRatio,
        ...     flag_key="custom_pixel_aspect_ratio_flag",
        ...     parameters=[
        ...         "pixel_aspect_ratio_numer",
        ...         "pixel_aspect_ratio_denom",
        ...     ],
        ...     PRESET_PIXEL_ASPECT_RATIOS,
        ... )

        >>> # In this case, the format matches the default so can use any type
        >>> # of override
        >>> base_video_parameters = set_source_defaults(
        ...     BASE_VIDEO_FORMAT_PARAMETERS[
        ...         BaseVideoFormats.sdi576i_50
        ...     ]
        ... )
        >>> video_parameters = VideoParameters(
        ...     pixel_aspect_ratio_numer=12,
        ...     pixel_aspect_ratio_denom=11,
        ...     # ...
        ... )
        >>> level_constraints_dict = defaultdict(AnyValue)  # ...for sake of example
        >>> for f in iter_pixel_aspect_ratio_options(
        ...     base_video_parameters,
        ...     video_parameters,
        ...     level_constraints_dict,
        ... ):
        ...     print(f)
        PixelAspectRatio:
          custom_pixel_aspect_ratio_flag: False
        PixelAspectRatio:
          custom_pixel_aspect_ratio_flag: True
          index: ratio_12_11 (3)
        PixelAspectRatio:
          custom_pixel_aspect_ratio_flag: True
          index: 0
          pixel_aspect_ratio_numer: 12
          pixel_aspect_ratio_denom: 11

        >>> # In this case, the format doesn't match the base video format so
        >>> # we have to override
        >>> video_parameters = VideoParameters(
        ...     pixel_aspect_ratio_numer=4,
        ...     pixel_aspect_ratio_denom=3,
        ...     # ...
        ... )
        >>> for f in iter_pixel_aspect_ratio_options(
        ...     base_video_parameters,
        ...     video_parameters,
        ...     level_constraints_dict,
        ... ):
        ...     print(f)
        PixelAspectRatio:
          custom_pixel_aspect_ratio_flag: True
          index: reduced_horizontal_resolution (6)
        PixelAspectRatio:
          custom_pixel_aspect_ratio_flag: True
          index: 0
          pixel_aspect_ratio_numer: 4
          pixel_aspect_ratio_denom: 3

    Parameters
    ==========
    base_video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        representing the current base video parameters. See
        :py:func:`~vc2_conformance.pseudocode.video_parameters.set_source_defaults`.
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        representing the desired video parameters to be represented. Only the
        entries mentioned in ``dict_type`` will be checked.
    level_constraints_dict : {str: :py:class:`~vc2_conformance.constraint_table.ValueSet`, ...}
        A single dictionary of level constraints (i.e. a single column from
        :py:class:`vc2_conformance.level_constraints.LEVEL_CONSTRAINTS`).
    dict_type : :py:class:`~vc2_conformance.fixeddicts.fixeddict` type
        The type of :py:class:`~vc2_conformance.fixeddicts.fixeddict` which
        holds the required custom option.
    flag_key : str
        Name of the ``custom_*_flag`` entry in ``dict_type``.
    parameters : [str or (str, str), ...]
        Names of keys in ``dict_type`` to try and match in the
        video_parameters. If the dict_type and VideoParameters field names
        differ, a pair (video_parameters_name, dict_type_name) should be given
        instead.
    presets : {index: namedtuple(value, ...), ...} or None
        If present, gives the set of default values for this ``dict_type``
        which would be indicated by a field called 'index'. If this argument is
        None, no 'index' field will be added. The names in ``parameters`` must
        match the order in the presets.
    preset_index_constraint_key : str
        Required if ``presets`` is not None. The name of the
        :py:class:`vc2_conformance.level_constraints.LEVEL_CONSTRAINTS` key
        which corresponds with the index field. Ignored otherwise.
    """
    # Normalise to (vp_key, dt_key) pairs
    parameters = [(key, key) if isinstance(key, str) else key for key in parameters]

    # Is the base video format already sufficient (and are we allowed to leave
    # the flag cleared)?
    if (
        all(
            base_video_parameters[vp_key] == video_parameters[vp_key]
            for vp_key, _ in parameters
        )
        and False in level_constraints_dict[flag_key]
    ):
        yield dict_type({flag_key: False})

    # Is there a suitable preset (and are we allowed to set it)?
    if presets is not None:
        for index, values in presets.items():
            if values == tuple(video_parameters[vp_key] for vp_key, _ in parameters):
                if (
                    True in level_constraints_dict[flag_key]
                    and index in level_constraints_dict[preset_index_constraint_key]
                ):
                    yield dict_type({flag_key: True, "index": index})

    # Explicitly set the desired value (if we're allowed to do so)
    if (
        True in level_constraints_dict[flag_key]
        and (
            presets is None or 0 in level_constraints_dict[preset_index_constraint_key]
        )
        and all(
            # NB: Constraints table entry names are shared with the
            # VideoParameters keys (and not the pseudocode/bitstream fixeddicts
            # whose names are not globally unique).
            video_parameters[vp_key] in level_constraints_dict[vp_key]
            for vp_key, dt_key in parameters
        )
    ):
        out = dict_type({flag_key: True})
        if presets is not None:
            out["index"] = 0
        for vp_key, dt_key in parameters:
            out[dt_key] = video_parameters[vp_key]
        yield out


iter_frame_size_options = partial(
    iter_custom_options_dicts,
    dict_type=FrameSize,
    flag_key="custom_dimensions_flag",
    parameters=["frame_width", "frame_height"],
)

iter_color_diff_sampling_format_options = partial(
    iter_custom_options_dicts,
    dict_type=ColorDiffSamplingFormat,
    flag_key="custom_color_diff_format_flag",
    parameters=["color_diff_format_index"],
)

iter_scan_format_options = partial(
    iter_custom_options_dicts,
    dict_type=ScanFormat,
    flag_key="custom_scan_format_flag",
    parameters=["source_sampling"],
)

iter_frame_rate_options = partial(
    iter_custom_options_dicts,
    dict_type=FrameRate,
    flag_key="custom_frame_rate_flag",
    parameters=["frame_rate_numer", "frame_rate_denom"],
    presets=PRESET_FRAME_RATES,
    preset_index_constraint_key="frame_rate_index",
)

iter_pixel_aspect_ratio_options = partial(
    iter_custom_options_dicts,
    dict_type=PixelAspectRatio,
    flag_key="custom_pixel_aspect_ratio_flag",
    parameters=["pixel_aspect_ratio_numer", "pixel_aspect_ratio_denom"],
    presets=PRESET_PIXEL_ASPECT_RATIOS,
    preset_index_constraint_key="pixel_aspect_ratio_index",
)

iter_clean_area_options = partial(
    iter_custom_options_dicts,
    dict_type=CleanArea,
    flag_key="custom_clean_area_flag",
    parameters=["clean_width", "clean_height", "top_offset", "left_offset"],
)

iter_signal_range_options = partial(
    iter_custom_options_dicts,
    dict_type=SignalRange,
    flag_key="custom_signal_range_flag",
    parameters=[
        "luma_offset",
        "luma_excursion",
        "color_diff_offset",
        "color_diff_excursion",
    ],
    presets=PRESET_SIGNAL_RANGES,
    preset_index_constraint_key="custom_signal_range_index",
)

iter_color_primaries_options = partial(
    iter_custom_options_dicts,
    dict_type=ColorPrimaries,
    flag_key="custom_color_primaries_flag",
    parameters=[("color_primaries_index", "index")],
)

iter_color_matrix_options = partial(
    iter_custom_options_dicts,
    dict_type=ColorMatrix,
    flag_key="custom_color_matrix_flag",
    parameters=[("color_matrix_index", "index")],
)

iter_transfer_function_options = partial(
    iter_custom_options_dicts,
    dict_type=TransferFunction,
    flag_key="custom_transfer_function_flag",
    parameters=[("transfer_function_index", "index")],
)


def iter_color_spec_options(
    base_video_parameters, video_parameters, level_constraints_dict
):
    """
    Generates a series of :py:class:`vc2_conformance.bitstream.ColorSpec`
    dictionaries which may be used to achieve the specified video parameters
    while obeying the provided level constraints.

    Where defaults are permissible, examples will be produced with each flag
    set to both True and False, though not every combination of flags will be
    given.

    Parameters
    ==========
    base_video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        representing the current base video parameters. See
        :py:func:`~vc2_conformance.pseudocode.video_parameters.set_source_defaults`.
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        representing the desired video parameters to be represented. Only the
        color mode related entries mentioned in will be checked.
    level_constraints_dict : {str: :py:class:`~vc2_conformance.constraint_table.ValueSet`, ...}
        A single dictionary of level constraints (i.e. a single column from
        :py:class:`vc2_conformance.level_constraints.LEVEL_CONSTRAINTS`).
    """
    # Is this already covered by the base format (and are we allowed to use it)?
    if (
        all(
            base_video_parameters[key] == video_parameters[key]
            for key in [
                "color_primaries_index",
                "color_matrix_index",
                "transfer_function_index",
            ]
        )
        and False in level_constraints_dict["custom_color_spec_flag"]
    ):
        yield ColorSpec(
            custom_color_spec_flag=False,
        )

    # Can a preset (other than 0) satisfy the requirement (and are we allowed
    # to use it)?
    for index, (
        primaries,
        matrix,
        tf,
    ) in PRESET_COLOR_SPECS.items():
        if (
            index != 0
            and video_parameters["color_primaries_index"] == primaries
            and video_parameters["color_matrix_index"] == matrix
            and video_parameters["transfer_function_index"] == tf
            and True in level_constraints_dict["custom_color_spec_flag"]
            and index in level_constraints_dict["color_spec_index"]
        ):
            yield ColorSpec(
                custom_color_spec_flag=True,
                index=index,
            )

    # Work through all possible ways to express this using fully custom formats
    # (if we're allowed to do so)
    custom_base_vp = base_video_parameters.copy()
    custom_presets = PRESET_COLOR_SPECS[0]
    custom_base_vp["color_primaries_index"] = custom_presets.color_primaries_index
    custom_base_vp["color_matrix_index"] = custom_presets.color_matrix_index
    custom_base_vp["transfer_function_index"] = custom_presets.transfer_function_index

    if (
        True in level_constraints_dict["custom_color_spec_flag"]
        and 0 in level_constraints_dict["color_spec_index"]
    ):
        for (
            color_primaries,
            color_matrix,
            transfer_function,
        ) in zip_longest_repeating_final_value(
            iter_color_primaries_options(
                custom_base_vp,
                video_parameters,
                level_constraints_dict,
            ),
            iter_color_matrix_options(
                custom_base_vp,
                video_parameters,
                level_constraints_dict,
            ),
            iter_transfer_function_options(
                custom_base_vp,
                video_parameters,
                level_constraints_dict,
            ),
        ):
            # Give up if we're unable to produce a needed custom color option
            if (
                color_primaries is None
                or color_matrix is None
                or transfer_function is None
            ):
                break

            yield ColorSpec(
                custom_color_spec_flag=True,
                index=0,
                color_primaries=color_primaries,
                color_matrix=color_matrix,
                transfer_function=transfer_function,
            )


def iter_source_parameter_options(
    base_video_parameters, video_parameters, level_constraints_dict
):
    """
    Generates a series of
    :py:class:`vc2_conformance.bitstream.SourceParameters` dictionaries which
    may be used to set the specified ``video_parameters``, starting from the
    supplied ``base_video_parameters``.

    Parameters
    ==========
    base_video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        representing the current base video parameters. See
        :py:func:`~vc2_conformance.pseudocode.video_parameters.set_source_defaults`.
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        representing the desired video parameters to be represented.
    level_constraints_dict : {str: :py:class:`~vc2_conformance.constraint_table.ValueSet`, ...}
        A single dictionary of level constraints (i.e. a single column from
        :py:class:`vc2_conformance.level_constraints.LEVEL_CONSTRAINTS`). All
        generated parameter sets will meet the restrictions imposed (which may
        include preventing any cases being generated).

    Yields
    ======
    source_parameters : :py:class:`vc2_conformance.bitstream.SourceParameters`
        A series of :py:class:`vc2_conformance.bitstream.SourceParameters`
        dictionaries, starting with the simplest (fewest custom overrides
        possible), building up to the most explicit (all options have custom
        overrides).
    """
    # Special case: (11.3) The top field first parameter cannot be overriden
    # from the base video format. If these are mismatched, we cannot produce
    # any useful results.
    if base_video_parameters["top_field_first"] != video_parameters["top_field_first"]:
        return

    for (
        frame_size,
        color_diff_sampling_format,
        scan_format,
        frame_rate,
        pixel_aspect_ratio,
        clean_area,
        signal_range,
        color_spec,
    ) in zip_longest_repeating_final_value(
        *(
            fn(base_video_parameters, video_parameters, level_constraints_dict)
            for fn in [
                iter_frame_size_options,
                iter_color_diff_sampling_format_options,
                iter_scan_format_options,
                iter_frame_rate_options,
                iter_pixel_aspect_ratio_options,
                iter_clean_area_options,
                iter_signal_range_options,
                iter_color_spec_options,
            ]
        )
    ):
        source_parameters = SourceParameters(
            frame_size=frame_size,
            color_diff_sampling_format=color_diff_sampling_format,
            scan_format=scan_format,
            frame_rate=frame_rate,
            pixel_aspect_ratio=pixel_aspect_ratio,
            clean_area=clean_area,
            signal_range=signal_range,
            color_spec=color_spec,
        )

        # Give up immediately if any of the parts cannot be satisifed
        if any(value is None for value in source_parameters.values()):
            break

        yield source_parameters


def count_video_parameter_differences(a, b):
    """
    Given two sets of :py:class:`VideoParameters`, return a count of the values
    which differ.
    """
    # NB: Should always be the same in practice...
    all_keys = set(a) | set(b)

    differences = 0
    for key in all_keys:
        if key not in a:
            differences += 1
        elif key not in b:
            differences += 1
        elif a[key] != b[key]:
            differences += 1

    return differences


def rank_base_video_format_similarity(
    video_parameters,
    base_video_formats=list(BaseVideoFormats),
):
    """
    Given a set of
    :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`, return an
    ordered list of :py:class:`~vc2_data_tables.BaseVideoFormats` with the most
    similar format first and least similar last.

    .. note::
        The returned :py:class:`~vc2_data_tables.BaseVideoFormats` will always
        have the same ``top_field_first`` setting.

    Parameters
    ==========
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
        The video parameters against which to rank base video formats'
        similarity.
    base_video_formats : [:py:class:`~vc2_data_tables.BaseVideoFormats`, ...]
        Optional. The base video format indices to consider. Defaults to all
        base video formats.
    """
    return sorted(
        (
            index
            for index in base_video_formats
            if (
                BASE_VIDEO_FORMAT_PARAMETERS[index].top_field_first
                == video_parameters["top_field_first"]
            )
        ),
        key=lambda index: count_video_parameter_differences(
            set_source_defaults(index),
            video_parameters,
        ),
    )


def rank_allowed_base_video_format_similarity(codec_features):
    """
    Produce a ranked list of base video format IDs for the provided codec
    features. Video formats with the wrong 'top field first' value and which
    aren't allowed by the current level are omitted. The most similar base
    format is returned first.

    Raises
    :py:exc:`~vc2_conformance.encoder.exceptions.IncompatibleLevelAndVideoFormatError`
    if no suitable base video format is available.
    """

    constrained_values = codec_features_to_trivial_level_constraints(codec_features)

    return rank_base_video_format_similarity(
        codec_features["video_parameters"],
        list(
            allowed_values_for(
                LEVEL_CONSTRAINTS,
                "base_video_format",
                constrained_values,
                LEVEL_CONSTRAINT_ANY_VALUES["base_video_format"],
            ).iter_values()
        ),
    )


def make_parse_parameters(codec_features):
    """
    Create a :py:class:`~vc2_conformance.bitstream.ParseParameters` object
    using the profile and level specified in the
    :py:class:`~vc2_conformance.codec_features.CodecFeatures` dictionary
    provided.
    """
    return ParseParameters(
        profile=codec_features["profile"],
        level=codec_features["level"],
    )


def iter_sequence_headers(codec_features):
    """
    Generate a series of :py:class:`~vc2_conformance.bitstream.SequenceHeader`
    objects which encode the video format specified in
    :py:class:`~vc2_conformance.codec_features.CodecFeatures` dictionary
    provided.

    This generator will start with an efficient encoding of the required
    features, built on the most closely matched base video format. This will be
    followed by successively less efficient encodings (i.e. using more custom
    fields) but the same (best-matched) base video format. After this,
    encodings based on other base video formats will be produced (again
    starting with the most efficient encoding for each format first).

    This generator may output no items if the VC-2 level specified does not
    permit the format given.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`

    Yields
    ======
    sequence_header : :py:class:`~vc2_conformance.bitstream.SequenceHeader`
    """
    picture_coding_mode = codec_features["picture_coding_mode"]
    video_parameters = codec_features["video_parameters"]

    constrained_values = codec_features_to_trivial_level_constraints(codec_features)

    # Level constraints may force us to use a particular base video format for
    # this encoding so we try all possible encodings (starting with the most
    # compact) and stop when we find one compliant with the level restrictions.
    base_video_formats = rank_allowed_base_video_format_similarity(codec_features)
    for base_video_format in base_video_formats:
        base_video_parameters = set_source_defaults(base_video_format)

        filtered_constraint_table = filter_constraint_table(
            LEVEL_CONSTRAINTS,
            dict(constrained_values, base_video_format=base_video_format),
        )
        for level_constraints_dict in filtered_constraint_table:
            for source_parameters in iter_source_parameter_options(
                base_video_parameters, video_parameters, level_constraints_dict
            ):
                yield SequenceHeader(
                    parse_parameters=make_parse_parameters(codec_features),
                    base_video_format=base_video_format,
                    video_parameters=source_parameters,
                    picture_coding_mode=picture_coding_mode,
                )


def make_sequence_header(codec_features):
    """
    Create a :py:class:`~vc2_conformance.bitstream.SequenceHeader` object which
    efficiently encodes the video format specified in
    :py:class:`~vc2_conformance.codec_features.CodecFeatures` dictionary
    provided.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`

    Returns
    =======
    sequence_header : :py:class:`~vc2_conformance.bitstream.SequenceHeader`

    Raises
    =======
    :py:exc:`IncompatibleLevelAndVideoFormatError`
    """
    try:
        return next(iter_sequence_headers(codec_features))
    except StopIteration:
        # No suitable encoding was possible. This (should!) only occur due to level
        # constraints so we'll blame these here.
        #
        # This assertion (should be) unreachable and is here so that we don't
        # misleadingly blame levels in the event of this code being broken!
        assert codec_features["level"] != Levels.unconstrained
        raise IncompatibleLevelAndVideoFormatError(codec_features)


def make_sequence_header_data_unit(codec_features):
    """
    Create a :py:class:`~vc2_conformance.bitstream.DataUnit` object containing
    a sequence header which sensibly encodes the features specified in
    :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    dictionary provided.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`

    Returns
    =======
    data_unit : :py:class:`~vc2_conformance.bitstream.DataUnit`

    Raises
    =======
    :py:exc:`IncompatibleLevelAndVideoFormatError`
    """
    return DataUnit(
        parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
        sequence_header=make_sequence_header(codec_features),
    )
