"""
The :py:mod:`vc2_conformance.decoder.sequence_header` module contains pseudocode
functions from (11) Sequence Header.
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_data_tables import (
    BaseVideoFormats,
    PictureCodingModes,
    Profiles,
    Levels,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetFrameRates,
    PresetPixelAspectRatios,
    PresetSignalRanges,
    PresetColorSpecs,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
)

from vc2_conformance.level_constraints import LEVEL_SEQUENCE_RESTRICTIONS

from vc2_conformance.version_constraints import (
    MINIMUM_MAJOR_VERSION,
    preset_frame_rate_version_implication,
    preset_signal_range_version_implication,
    preset_color_spec_version_implication,
    preset_color_primaries_version_implication,
    preset_color_matrix_version_implication,
    preset_transfer_function_version_implication,
    profile_version_implication,
)

from vc2_conformance.pseudocode.video_parameters import (
    set_source_defaults,
    set_coding_parameters,
    preset_frame_rate,
    preset_pixel_aspect_ratio,
    preset_signal_range,
    preset_color_primaries,
    preset_color_matrix,
    preset_transfer_function,
    preset_color_spec,
)

from vc2_conformance.decoder.assertions import (
    assert_in_enum,
    assert_level_constraint,
    log_version_lower_bound,
)

from vc2_conformance.decoder.exceptions import (
    SequenceHeaderChangedMidSequence,
    BadBaseVideoFormat,
    BadPictureCodingMode,
    BadProfile,
    BadLevel,
    BadColorDifferenceSamplingFormat,
    BadSourceSamplingMode,
    BadPresetFrameRateIndex,
    BadPresetPixelAspectRatio,
    CleanAreaOutOfRange,
    BadCustomSignalExcursion,
    BadPresetSignalRange,
    BadPresetColorSpec,
    BadPresetColorPrimaries,
    BadPresetColorMatrix,
    BadPresetTransferFunction,
    PictureDimensionsNotMultipleOfFrameDimensions,
    ZeroPixelFrameSize,
    FrameRateHasZeroNumerator,
    FrameRateHasZeroDenominator,
    PixelAspectRatioContainsZeros,
    PresetFrameRateNotSupportedByVersion,
    PresetSignalRangeNotSupportedByVersion,
    PresetColorSpecNotSupportedByVersion,
    PresetColorPrimariesNotSupportedByVersion,
    PresetColorMatrixNotSupportedByVersion,
    PresetTransferFunctionNotSupportedByVersion,
    ProfileNotSupportedByVersion,
    MinorVersionNotZero,
    MajorVersionTooLow,
)

from vc2_conformance.symbol_re import Matcher

from vc2_conformance.decoder.io import (
    record_bitstream_start,
    record_bitstream_finish,
    tell,
    read_bool,
    read_uint,
)


__all__ = [
    "sequence_header",
    "parse_parameters",
    "source_parameters",
    "frame_size",
    "color_diff_sampling_format",
    "scan_format",
    "frame_rate",
    "pixel_aspect_ratio",
    "clean_area",
    "signal_range",
    "color_spec",
    "color_primaries",
    "color_matrix",
    "transfer_function",
]


@ref_pseudocode
def sequence_header(state):
    """(11.1)"""
    # Record this sequence_header as it appears in the bitstream
    ## Begin not in spec
    this_sequence_header_offset = tell(state)[0]
    record_bitstream_start(state)
    ## End not in spec

    parse_parameters(state)

    base_video_format = read_uint(state)

    # (11.4.1) Check base video format is supported
    ## Begin not in spec
    assert_in_enum(base_video_format, BaseVideoFormats, BadBaseVideoFormat)
    ## End not in spec

    # (C.3) Check level allows this base format
    ## Begin not in spec
    assert_level_constraint(state, "base_video_format", base_video_format)
    ## End not in spec

    video_parameters = source_parameters(state, base_video_format)

    state["picture_coding_mode"] = read_uint(state)

    # (11.5) Ensure picture coding mode is valid
    ## Begin not in spec
    assert_in_enum(
        state["picture_coding_mode"], PictureCodingModes, BadPictureCodingMode
    )
    ## End not in spec

    # (C.3) Check level allows this picture coding mode
    ## Begin not in spec
    assert_level_constraint(state, "picture_coding_mode", state["picture_coding_mode"])
    ## End not in spec

    set_coding_parameters(state, video_parameters)

    # Errata: The spec only says the frame_height must be an integer multiple
    # of the color_diff_height but, in addition, the luma_height should be a
    # multiple and the color_diff_width should be a multiple of
    # luma_width/frame_width
    #
    # (11.6.2) Check frame_height is an integer multiple of color_diff_height
    ## Begin not in spec
    if (
        # Prevent divide-by-zero in tests below
        state["luma_height"] == 0
        or state["luma_width"] == 0
        or state["color_diff_height"] == 0
        or state["color_diff_width"] == 0
        or
        # Actually check multiples
        video_parameters["frame_height"] % state["luma_height"] != 0
        or video_parameters["frame_width"] % state["luma_width"] != 0
        or video_parameters["frame_height"] % state["color_diff_height"] != 0
        or video_parameters["frame_width"] % state["color_diff_width"] != 0
    ):
        raise PictureDimensionsNotMultipleOfFrameDimensions(
            state["luma_width"],
            state["luma_height"],
            state["color_diff_width"],
            state["color_diff_height"],
            video_parameters["frame_width"],
            video_parameters["frame_height"],
        )
    ## End not in spec

    # (11.1) Check that the this sequence_header is byte-for-byte identical
    # with the previous sequence_header in the sequence
    ## Begin not in spec
    this_sequence_header_bytes = record_bitstream_finish(state)
    if "_last_sequence_header_bytes" in state:
        if this_sequence_header_bytes != state["_last_sequence_header_bytes"]:
            raise SequenceHeaderChangedMidSequence(
                state["_last_sequence_header_offset"],
                state["_last_sequence_header_bytes"],
                this_sequence_header_offset,
                this_sequence_header_bytes,
            )
    state["_last_sequence_header_bytes"] = this_sequence_header_bytes
    state["_last_sequence_header_offset"] = this_sequence_header_offset
    ## End not in spec

    return video_parameters


@ref_pseudocode
def parse_parameters(state):
    """(11.2.1)"""
    state["major_version"] = read_uint(state)

    # (11.2.2) Check the major_version  is at least 1. (It may need to be
    # higher depending on the features used on the sequence, but this will be
    # checked as the stream is processed. Later, at the end of the stream we'll
    # also check the major_version was not too high for the set of features
    # actually used.)
    ## Begin not in spec
    if state["major_version"] < MINIMUM_MAJOR_VERSION:
        raise MajorVersionTooLow(state["major_version"])
    ## End not in spec

    state["minor_version"] = read_uint(state)

    # (11.2.2) Check the minor_version is 0.
    ## Begin not in spec
    if state["minor_version"] != 0:
        raise MinorVersionNotZero(state["minor_version"])
    ## End not in spec

    state["profile"] = read_uint(state)

    # (C.2) Profile must be a supported value
    assert_in_enum(state["profile"], Profiles, BadProfile)  ## Not in spec

    # (11.2.2) Profile must be supported by current version
    ## Begin not in spec
    minimum_required_version = profile_version_implication(state["profile"])
    if state["major_version"] < minimum_required_version:
        raise ProfileNotSupportedByVersion(state["profile"], state["major_version"])
    log_version_lower_bound(state, minimum_required_version)
    ## End not in spec

    state["level"] = read_uint(state)

    # (C.3) Level must be a supported value
    assert_in_enum(state["level"], Levels, BadLevel)  ## Not in spec

    # (C.3) Levels may constrain the order and choice of data units in a
    # sequence. See the various level standards documents (e.g. ST 2042-2) for
    # details.
    ## Begin not in spec
    if "_level_sequence_matcher" not in state:
        state["_level_sequence_matcher"] = Matcher(
            LEVEL_SEQUENCE_RESTRICTIONS[state["level"]].sequence_restriction_regex
        )
        # If we're at this point we're currently reading the first sequence
        # header (in the first data unit) of a sequence. Advance the state
        # machine accordingly.
        assert state["_level_sequence_matcher"].match_symbol("sequence_header")
    ## End not in spec

    # (C.3) Levels may constrain the allowed profiles and versions
    ## Begin not in spec
    assert_level_constraint(state, "level", state["level"])
    assert_level_constraint(state, "profile", state["profile"])
    assert_level_constraint(state, "major_version", state["major_version"])
    assert_level_constraint(state, "minor_version", state["minor_version"])
    ## End not in spec


@ref_pseudocode
def source_parameters(state, base_video_format):
    """(11.4.1)"""
    video_parameters = set_source_defaults(base_video_format)
    frame_size(state, video_parameters)
    color_diff_sampling_format(state, video_parameters)
    scan_format(state, video_parameters)
    frame_rate(state, video_parameters)
    pixel_aspect_ratio(state, video_parameters)
    clean_area(state, video_parameters)
    signal_range(state, video_parameters)
    color_spec(state, video_parameters)
    return video_parameters


@ref_pseudocode
def frame_size(state, video_parameters):
    """(11.4.3)"""
    custom_dimensions_flag = read_bool(state)
    # (C.3) Check level allows this value
    ## Begin not in spec
    assert_level_constraint(state, "custom_dimensions_flag", custom_dimensions_flag)
    ## End not in spec

    if custom_dimensions_flag:
        video_parameters["frame_width"] = read_uint(state)
        # (C.3) Check level allows this value
        ## Begin not in spec
        assert_level_constraint(state, "frame_width", video_parameters["frame_width"])
        ## End not in spec

        video_parameters["frame_height"] = read_uint(state)
        # (C.3) Check level allows this value
        ## Begin not in spec
        assert_level_constraint(state, "frame_height", video_parameters["frame_height"])
        ## End not in spec

        # Errata: spec doesn't prevent zero-pixel pictures
        #
        # (11.4.3) Frames must be at least one pixel wide and tall
        ## Begin not in spec
        if (
            video_parameters["frame_width"] == 0
            or video_parameters["frame_height"] == 0
        ):
            raise ZeroPixelFrameSize(
                video_parameters["frame_width"],
                video_parameters["frame_height"],
            )
        ## End not in spec


@ref_pseudocode
def color_diff_sampling_format(state, video_parameters):
    """(11.4.4)"""
    custom_color_diff_format_flag = read_bool(state)
    # (C.3) Check level allows custom color difference sampling
    ## Begin not in spec
    assert_level_constraint(
        state, "custom_color_diff_format_flag", custom_color_diff_format_flag
    )
    ## End not in spec

    if custom_color_diff_format_flag:
        video_parameters["color_diff_format_index"] = read_uint(state)

        # (11.4.4) Index shall be a known value
        ## Begin not in spec
        assert_in_enum(
            video_parameters["color_diff_format_index"],
            ColorDifferenceSamplingFormats,
            BadColorDifferenceSamplingFormat,
        )
        ## End not in spec

        # (C.3) Check level allows this value
        ## Begin not in spec
        assert_level_constraint(
            state,
            "color_diff_format_index",
            video_parameters["color_diff_format_index"],
        )
        ## End not in spec


@ref_pseudocode
def scan_format(state, video_parameters):
    """(11.4.5)"""
    custom_scan_format_flag = read_bool(state)
    # (C.3) Check level allows custom scan formats
    ## Begin not in spec
    assert_level_constraint(state, "custom_scan_format_flag", custom_scan_format_flag)
    ## End not in spec

    if custom_scan_format_flag:
        video_parameters["source_sampling"] = read_uint(state)

        # (11.4.5) Mode be a known value
        ## Begin not in spec
        assert_in_enum(
            video_parameters["source_sampling"],
            SourceSamplingModes,
            BadSourceSamplingMode,
        )
        ## End not in spec

        # (C.3) Check level allows this value
        ## Begin not in spec
        assert_level_constraint(
            state,
            "source_sampling",
            video_parameters["source_sampling"],
        )
        ## End not in spec


@ref_pseudocode
def frame_rate(state, video_parameters):
    """(11.4.6)"""
    custom_frame_rate_flag = read_bool(state)
    # (C.3) Check level allows custom frame rates
    ## Begin not in spec
    assert_level_constraint(state, "custom_frame_rate_flag", custom_frame_rate_flag)
    ## End not in spec

    if custom_frame_rate_flag:
        index = read_uint(state)

        # (C.3) Check level allows the specified preset
        assert_level_constraint(state, "frame_rate_index", index)  ## Not in spec

        if index == 0:
            video_parameters["frame_rate_numer"] = read_uint(state)
            # (C.3) Check level allows the specified numerator
            ## Begin not in spec
            assert_level_constraint(
                state,
                "frame_rate_numer",
                video_parameters["frame_rate_numer"],
            )
            ## End not in spec

            video_parameters["frame_rate_denom"] = read_uint(state)
            # (C.3) Check level allows the specified denominator
            ## Begin not in spec
            assert_level_constraint(
                state,
                "frame_rate_denom",
                video_parameters["frame_rate_denom"],
            )
            ## End not in spec

            # Errata: spec doesn't prevent divide-by-zero in custom frame rate
            # fractions.
            #
            # (11.4.6) frame_rate_denom must not be zero (i.e. a divide by zero)
            ## Begin not in spec
            if video_parameters["frame_rate_denom"] == 0:
                raise FrameRateHasZeroDenominator(video_parameters["frame_rate_numer"])
            ## End not in spec

            # Errata: spec doesn't prevent 0 fps
            #
            # (11.4.6) frame_rate_numer must not be zero (i.e. 0 fps)
            ## Begin not in spec
            if video_parameters["frame_rate_numer"] == 0:
                raise FrameRateHasZeroNumerator(video_parameters["frame_rate_denom"])
            ## End not in spec

        else:
            # (11.4.6) Frame rate preset must be a known value
            ## Begin not in spec
            assert_in_enum(index, PresetFrameRates, BadPresetFrameRateIndex)
            ## End not in spec

            # (11.2.2) Frame rate preset must be supported by current version
            ## Begin not in spec
            minimum_required_version = preset_frame_rate_version_implication(index)
            if state["major_version"] < minimum_required_version:
                raise PresetFrameRateNotSupportedByVersion(
                    index, state["major_version"]
                )
            log_version_lower_bound(state, minimum_required_version)
            ## End not in spec

            preset_frame_rate(video_parameters, index)


@ref_pseudocode
def pixel_aspect_ratio(state, video_parameters):
    """(11.4.7)"""
    custom_pixel_aspect_ratio_flag = read_bool(state)
    # (C.3) Check level allows custom pixel aspect ratio
    ## Begin not in spec
    assert_level_constraint(
        state, "custom_pixel_aspect_ratio_flag", custom_pixel_aspect_ratio_flag
    )
    ## End not in spec

    if custom_pixel_aspect_ratio_flag:
        index = read_uint(state)
        # (C.3) Check level allows the specified preset
        ## Begin not in spec
        assert_level_constraint(state, "pixel_aspect_ratio_index", index)
        ## End not in spec

        if index == 0:
            video_parameters["pixel_aspect_ratio_numer"] = read_uint(state)
            # (C.3) Check level allows the specified numerator
            ## Begin not in spec
            assert_level_constraint(
                state,
                "pixel_aspect_ratio_numer",
                video_parameters["pixel_aspect_ratio_numer"],
            )
            ## End not in spec

            video_parameters["pixel_aspect_ratio_denom"] = read_uint(state)
            # (C.3) Check level allows the specified denominator
            ## Begin not in spec
            assert_level_constraint(
                state,
                "pixel_aspect_ratio_denom",
                video_parameters["pixel_aspect_ratio_denom"],
            )
            ## End not in spec

            # Errata: spec fails to require ratio to be non-zero on either side
            #
            # (11.4.7) ratio must not contain zeros
            ## Begin not in spec
            if (
                video_parameters["pixel_aspect_ratio_numer"] == 0
                or video_parameters["pixel_aspect_ratio_denom"] == 0
            ):
                raise PixelAspectRatioContainsZeros(
                    video_parameters["pixel_aspect_ratio_numer"],
                    video_parameters["pixel_aspect_ratio_denom"],
                )
            ## End not in spec
        else:
            # (11.4.7) Pixel aspect ratio preset must be a known value
            ## Begin not in spec
            assert_in_enum(index, PresetPixelAspectRatios, BadPresetPixelAspectRatio)
            ## End not in spec

            preset_pixel_aspect_ratio(video_parameters, index)


@ref_pseudocode
def clean_area(state, video_parameters):
    """(11.4.8)"""
    custom_clean_area_flag = read_bool(state)
    # (C.3) Check level allows custom clean area
    ## Begin not in spec
    assert_level_constraint(state, "custom_clean_area_flag", custom_clean_area_flag)
    ## End not in spec

    if custom_clean_area_flag:
        video_parameters["clean_width"] = read_uint(state)
        # (C.3) Check level allows this width
        ## Begin not in spec
        assert_level_constraint(state, "clean_width", video_parameters["clean_width"])
        ## End not in spec

        video_parameters["clean_height"] = read_uint(state)
        # (C.3) Check level allows this height
        ## Begin not in spec
        assert_level_constraint(state, "clean_height", video_parameters["clean_height"])
        ## End not in spec

        video_parameters["left_offset"] = read_uint(state)
        # (C.3) Check level allows this offset
        ## Begin not in spec
        assert_level_constraint(state, "left_offset", video_parameters["left_offset"])
        ## End not in spec

        video_parameters["top_offset"] = read_uint(state)
        # (C.3) Check level allows this offset
        ## Begin not in spec
        assert_level_constraint(state, "top_offset", video_parameters["top_offset"])
        ## End not in spec

    # (11.4.8) The clean area is restricted to being within the existing
    # picture area
    ## Begin not in spec
    if not (
        video_parameters["clean_width"] + video_parameters["left_offset"]
        <= video_parameters["frame_width"]
        and video_parameters["clean_height"] + video_parameters["top_offset"]
        <= video_parameters["frame_height"]
    ):
        raise CleanAreaOutOfRange(
            video_parameters["clean_width"],
            video_parameters["clean_height"],
            video_parameters["left_offset"],
            video_parameters["top_offset"],
            video_parameters["frame_width"],
            video_parameters["frame_height"],
        )
    ## End not in spec


@ref_pseudocode
def signal_range(state, video_parameters):
    """(11.4.9)"""
    custom_signal_range_flag = read_bool(state)
    # (C.3) Check level allows custom signal range
    ## Begin not in spec
    assert_level_constraint(state, "custom_signal_range_flag", custom_signal_range_flag)
    ## End not in spec

    if custom_signal_range_flag:
        index = read_uint(state)
        # (C.3) Check level allows the specified preset
        ## Begin not in spec
        assert_level_constraint(state, "custom_signal_range_index", index)
        ## End not in spec

        if index == 0:
            video_parameters["luma_offset"] = read_uint(state)
            # (C.3) Check level allows this offset
            ## Begin not in spec
            assert_level_constraint(
                state, "luma_offset", video_parameters["luma_offset"]
            )
            ## End not in spec

            video_parameters["luma_excursion"] = read_uint(state)
            # (C.3) Check level allows this excursion
            ## Begin not in spec
            assert_level_constraint(
                state, "luma_excursion", video_parameters["luma_excursion"]
            )
            ## End not in spec

            # (11.4.9) Check luma_excursion is valid
            #
            # Errata: Spec fails to constrain excursions.  Excursions *must* be
            # >= 1 or the pseudocode behaviour will be undefined.
            ## Begin not in spec
            if video_parameters["luma_excursion"] < 1:
                raise BadCustomSignalExcursion(
                    "luma", video_parameters["luma_excursion"]
                )
            ## End not in spec

            video_parameters["color_diff_offset"] = read_uint(state)
            # (C.3) Check level allows this offset
            ## Begin not in spec
            assert_level_constraint(
                state, "color_diff_offset", video_parameters["color_diff_offset"]
            )
            ## End not in spec

            video_parameters["color_diff_excursion"] = read_uint(state)
            # (C.3) Check level allows this excursion
            ## Begin not in spec
            assert_level_constraint(
                state, "color_diff_excursion", video_parameters["color_diff_excursion"]
            )
            ## End not in spec

            # (11.4.9) Check color_diff_excursion is valid
            #
            # Errata: Spec fails to constrain excursions.  Excursions *must* be
            # >= 1 or the pseudocode behaviour will be undefined.
            ## Begin not in spec
            if video_parameters["color_diff_excursion"] < 1:
                raise BadCustomSignalExcursion(
                    "color_diff", video_parameters["color_diff_excursion"]
                )
            ## End not in spec
        else:
            # (11.4.9) Signal range preset must be a known value
            ## Begin not in spec
            assert_in_enum(index, PresetSignalRanges, BadPresetSignalRange)
            ## End not in spec

            # (11.2.2) Signal range preset must be supported by current version
            ## Begin not in spec
            minimum_required_version = preset_signal_range_version_implication(index)
            if state["major_version"] < minimum_required_version:
                raise PresetSignalRangeNotSupportedByVersion(
                    index, state["major_version"]
                )
            log_version_lower_bound(state, minimum_required_version)
            ## End not in spec

            preset_signal_range(video_parameters, index)


@ref_pseudocode
def color_spec(state, video_parameters):
    """(11.4.10.1)"""
    custom_color_spec_flag = read_bool(state)
    # (C.3) Check level allows custom color specs
    ## Begin not in spec
    assert_level_constraint(state, "custom_color_spec_flag", custom_color_spec_flag)
    ## End not in spec

    if custom_color_spec_flag:
        index = read_uint(state)

        # (11.4.10.1) Index should be a supported value
        assert_in_enum(index, PresetColorSpecs, BadPresetColorSpec)  ## Not in spec

        # (C.3) Check level allows the specified preset
        assert_level_constraint(state, "color_spec_index", index)  ## Not in spec

        preset_color_spec(video_parameters, index)

        if index == 0:
            color_primaries(state, video_parameters)
            color_matrix(state, video_parameters)
            transfer_function(state, video_parameters)
        ## Begin not in spec
        else:
            # (11.2.2) Color spec must be supported by current version
            minimum_required_version = preset_color_spec_version_implication(index)
            if state["major_version"] < minimum_required_version:
                raise PresetColorSpecNotSupportedByVersion(
                    index, state["major_version"]
                )
            log_version_lower_bound(state, minimum_required_version)
        ## End not in spec


@ref_pseudocode
def color_primaries(state, video_parameters):
    """(11.4.10.2)"""
    custom_color_primaries_flag = read_bool(state)
    # (C.3) Check level allows custom color primaries
    ## Begin not in spec
    assert_level_constraint(
        state, "custom_color_primaries_flag", custom_color_primaries_flag
    )
    ## End not in spec

    if custom_color_primaries_flag:
        index = read_uint(state)

        # (11.4.10.2) Index should be a supported value
        ## Begin not in spec
        assert_in_enum(index, PresetColorPrimaries, BadPresetColorPrimaries)
        ## End not in spec

        # (C.3) Check level allows the specified preset
        ## Begin not in spec
        assert_level_constraint(state, "color_primaries_index", index)
        ## End not in spec

        # (11.2.2) Preset must be supported by current version
        ## Begin not in spec
        minimum_required_version = preset_color_primaries_version_implication(index)
        if state["major_version"] < minimum_required_version:
            raise PresetColorPrimariesNotSupportedByVersion(
                index, state["major_version"]
            )
        log_version_lower_bound(state, minimum_required_version)
        ## End not in spec

        preset_color_primaries(video_parameters, index)


@ref_pseudocode
def color_matrix(state, video_parameters):
    """(11.4.10.3)"""
    custom_color_matrix_flag = read_bool(state)
    # (C.3) Check level allows custom color matrices
    ## Begin not in spec
    assert_level_constraint(state, "custom_color_matrix_flag", custom_color_matrix_flag)
    ## End not in spec

    if custom_color_matrix_flag:
        index = read_uint(state)

        # (11.4.10.3) Index should be a supported value
        assert_in_enum(index, PresetColorMatrices, BadPresetColorMatrix)  ## Not in spec

        # (C.3) Check level allows the specified preset
        ## Begin not in spec
        assert_level_constraint(state, "color_matrix_index", index)
        ## End not in spec

        # (11.2.2) Preset must be supported by current version
        ## Begin not in spec
        minimum_required_version = preset_color_matrix_version_implication(index)
        if state["major_version"] < minimum_required_version:
            raise PresetColorMatrixNotSupportedByVersion(index, state["major_version"])
        log_version_lower_bound(state, minimum_required_version)
        ## End not in spec

        preset_color_matrix(video_parameters, index)


@ref_pseudocode
def transfer_function(state, video_parameters):
    """(11.4.10.4)"""
    custom_transfer_function_flag = read_bool(state)
    # (C.3) Check level allows custom transfer functions
    ## Begin not in spec
    assert_level_constraint(
        state, "custom_transfer_function_flag", custom_transfer_function_flag
    )
    ## End not in spec

    if custom_transfer_function_flag:
        index = read_uint(state)

        # (11.4.10.3) Index should be a supported value
        ## Begin not in spec
        assert_in_enum(index, PresetTransferFunctions, BadPresetTransferFunction)
        ## End not in spec

        # (C.3) Check level allows the specified preset
        ## Begin not in spec
        assert_level_constraint(state, "transfer_function_index", index)
        ## End not in spec

        # (11.2.2) Preset must be supported by current version
        ## Begin not in spec
        minimum_required_version = preset_transfer_function_version_implication(index)
        if state["major_version"] < minimum_required_version:
            raise PresetTransferFunctionNotSupportedByVersion(
                index, state["major_version"]
            )
        log_version_lower_bound(state, minimum_required_version)
        ## End not in spec

        preset_transfer_function(video_parameters, index)
