"""
Routines for generating sensible
:py:class:`~vc2_conformance.bitstream.SequenceHeader` dictionaries ready for
serialisation given a description of an arbitrary video format.
"""

from functools import partial

from vc2_data_tables import (
    ParseCodes,
    BaseVideoFormats,
    BASE_VIDEO_FORMAT_PARAMETERS,
    PRESET_FRAME_RATES,
    PRESET_PIXEL_ASPECT_RATIOS,
    PRESET_SIGNAL_RANGES,
    PRESET_COLOR_SPECS,
)

from vc2_conformance.video_parameters import (
    set_source_defaults,
    set_coding_parameters,
)

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


__all__ = [
    "rank_base_video_format_similarity",
    "iter_source_parameter_options",
    "make_parse_parameters",
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
    dict_type,
    flag_key,
    parameters,
    presets=None,
):
    """
    A generator which enumerates valid sets of VC-2 custom option settings
    which achieve a set of video parameters given a set of base video
    parameters.

    Options dictionaries will be generated in ascending order of explicitness.

    Example usage::

        >>> from functools import partial
        >>> from vc2_data_tables import (
        ...     BASE_VIDEO_FORMAT_PARAMETERS,
        ...     PRESET_PIXEL_ASPECT_RATIOS,
        ... )
        >>> from vc2_conformance.bitstream import (
        ...     PixelAspectRatio,
        ... )
        >>> from vc2_conformance.video_parameters import (
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
        >>> for f in iter_pixel_aspect_ratio_options(
        ...     base_video_parameters,
        ...     video_parameters,
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
        None, no 'index' field will not be added. The names in ``parameters``
        must match the order in the presets.
    base_video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        representing the current base video parameters. See
        :py:func:`~vc2_conformance.video_parameters.set_source_defaults`.
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        representing the desired video parameters to be represented. Only the
        entries mentioned in ``presets`` will be checked.
    """
    # Normalise to (vp_key, dt_key) pairs
    parameters = [(key, key) if isinstance(key, str) else key for key in parameters]

    # Is the base video format already sufficient?
    if all(
        base_video_parameters[vp_key] == video_parameters[vp_key]
        for vp_key, _ in parameters
    ):
        yield dict_type({flag_key: False})

    # Is there a suitable preset?
    if presets is not None:
        for index, values in presets.items():
            if values == tuple(video_parameters[vp_key] for vp_key, _ in parameters):
                yield dict_type({flag_key: True, "index": index})

    # Explicitly set the desired value
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
)

iter_pixel_aspect_ratio_options = partial(
    iter_custom_options_dicts,
    dict_type=PixelAspectRatio,
    flag_key="custom_pixel_aspect_ratio_flag",
    parameters=["pixel_aspect_ratio_numer", "pixel_aspect_ratio_denom"],
    presets=PRESET_PIXEL_ASPECT_RATIOS,
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


def iter_color_spec_options(base_video_parameters, video_parameters):
    """
    Generates a series of :py:class:`vc2_conformance.bitstream.ColorSpec`
    dictionaries which may be used to achieve the specified video parameters.

    Where defaults are permissible, examples will be produced with each flag
    set to both True and False, though not every combination of flags will be
    given.
    """
    # Is this already covered by the base format?
    if all(
        base_video_parameters[key] == video_parameters[key]
        for key in [
            "color_primaries_index",
            "color_matrix_index",
            "transfer_function_index",
        ]
    ):
        yield ColorSpec(custom_color_spec_flag=False,)

    # Can a preset (other than 0) satisfy the requirement?
    for index, (primaries, matrix, tf,) in PRESET_COLOR_SPECS.items():
        if (
            index != 0
            and video_parameters["color_primaries_index"] == primaries
            and video_parameters["color_matrix_index"] == matrix
            and video_parameters["transfer_function_index"] == tf
        ):
            yield ColorSpec(
                custom_color_spec_flag=True, index=index,
            )

    # Work through all possible ways to express this using fully custom formats
    custom_base_vp = base_video_parameters.copy()
    custom_presets = PRESET_COLOR_SPECS[0]
    custom_base_vp["color_primaries_index"] = custom_presets.color_primaries_index
    custom_base_vp["color_matrix_index"] = custom_presets.color_matrix_index
    custom_base_vp["transfer_function_index"] = custom_presets.transfer_function_index

    for (
        color_primaries,
        color_matrix,
        transfer_function,
    ) in zip_longest_repeating_final_value(
        iter_color_primaries_options(custom_base_vp, video_parameters),
        iter_color_matrix_options(custom_base_vp, video_parameters),
        iter_transfer_function_options(custom_base_vp, video_parameters),
    ):
        yield ColorSpec(
            custom_color_spec_flag=True,
            index=0,
            color_primaries=color_primaries,
            color_matrix=color_matrix,
            transfer_function=transfer_function,
        )


def iter_source_parameter_options(base_video_parameters, video_parameters):
    """
    Generates a series of
    :py:class:`vc2_conformance.bitstream.SourceParameters` dictionaries which
    may be used to set the specified ``video_parameters``, starting from the
    supplied ``base_video_parameters``.

    Parameters
    ==========
    base_video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        representing the current base video parameters. See
        :py:func:`~vc2_conformance.video_parameters.set_source_defaults`.
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        The :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        representing the desired video parameters to be represented.

    Generates
    =========
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
        iter_frame_size_options(base_video_parameters, video_parameters),
        iter_color_diff_sampling_format_options(
            base_video_parameters, video_parameters
        ),
        iter_scan_format_options(base_video_parameters, video_parameters),
        iter_frame_rate_options(base_video_parameters, video_parameters),
        iter_pixel_aspect_ratio_options(base_video_parameters, video_parameters),
        iter_clean_area_options(base_video_parameters, video_parameters),
        iter_signal_range_options(base_video_parameters, video_parameters),
        iter_color_spec_options(base_video_parameters, video_parameters),
    ):
        yield SourceParameters(
            frame_size=frame_size,
            color_diff_sampling_format=color_diff_sampling_format,
            scan_format=scan_format,
            frame_rate=frame_rate,
            pixel_aspect_ratio=pixel_aspect_ratio,
            clean_area=clean_area,
            signal_range=signal_range,
            color_spec=color_spec,
        )


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


def rank_base_video_format_similarity(video_parameters):
    """
    Given a set of
    :py:class:`~vc2_conformance.video_parameters.VideoParameters`, return an
    ordered list of :py:class:`~vc2_data_tables.BaseVideoFormats` with the most
    similar format first and least similar last.

    .. note::
        The returned :py:class:`~vc2_data_tables.BaseVideoFormats` will always
        have the same ``top_field_first`` setting.
    """
    return sorted(
        (
            index
            for index in BaseVideoFormats
            if (
                BASE_VIDEO_FORMAT_PARAMETERS[index].top_field_first
                == video_parameters["top_field_first"]
            )
        ),
        key=lambda index: count_video_parameter_differences(
            set_source_defaults(index), video_parameters,
        ),
    )


def make_parse_parameters(codec_features):
    """
    Create a :py:class:`~vc2_conformance.bitstream.ParseParameters` object
    using the version, profile and level specified in the
    :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    dictionary provided.
    """
    return ParseParameters(
        major_version=codec_features["major_version"],
        minor_version=codec_features["minor_version"],
        profile=codec_features["profile"],
        level=codec_features["level"],
    )


def make_sequence_header(codec_features):
    """
    Create a :py:class:`~vc2_conformance.bitstream.SequenceHeader` object which
    sensibly encodes the video format specified in
    :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    dictionary provided.
    """
    # Pick a base video format similar to the desired video format
    base_video_format = rank_base_video_format_similarity(
        codec_features["video_parameters"],
    )[0]

    # Pick a set of SourceParameters which minimally encode any differences
    # between the base video format and target video format
    source_parameters = next(
        iter(
            iter_source_parameter_options(
                set_source_defaults(base_video_format),
                codec_features["video_parameters"],
            )
        )
    )

    return SequenceHeader(
        parse_parameters=make_parse_parameters(codec_features),
        base_video_format=base_video_format,
        video_parameters=source_parameters,
        picture_coding_mode=codec_features["picture_coding_mode"],
    )


def make_sequence_header_data_unit(codec_features):
    """
    Create a :py:class:`~vc2_conformance.bitstream.DataUnit` object containing
    a sequence header which sensibly encodes the features specified in
    :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    dictionary provided.
    """
    return DataUnit(
        parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
        sequence_header=make_sequence_header(codec_features),
    )
