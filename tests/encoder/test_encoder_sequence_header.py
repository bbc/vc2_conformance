import pytest

from copy import deepcopy

from io import BytesIO

from collections import defaultdict

from vc2_data_tables import (
    Profiles,
    Levels,
    ParseCodes,
    BaseVideoFormats,
    BASE_VIDEO_FORMAT_PARAMETERS,
    PictureCodingModes,
    SourceSamplingModes,
    ColorDifferenceSamplingFormats,
    WaveletFilters,
    PresetPixelAspectRatios,
    PRESET_PIXEL_ASPECT_RATIOS,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    PresetColorSpecs,
)

from vc2_conformance.constraint_table import ValueSet, AnyValue

from vc2_conformance.bitstream import (
    BitstreamWriter,
    Serialiser,
    ParseInfo,
    FrameSize,
    PixelAspectRatio,
    ColorPrimaries,
    ColorMatrix,
    TransferFunction,
    ColorSpec,
)

from vc2_conformance.bitstream.vc2 import (
    source_parameters,
    parse_parameters,
    parse_info,
    sequence_header,
)

from vc2_conformance.bitstream.vc2_fixeddicts import vc2_default_values

from vc2_conformance.pseudocode.state import State

from vc2_conformance.decoder import (
    init_io,
    parse_stream,
    UnexpectedEndOfStream,
    InconsistentNextParseOffset,
)

from vc2_conformance.pseudocode.video_parameters import (
    VideoParameters,
    set_source_defaults,
)

from vc2_conformance.encoder.exceptions import IncompatibleLevelAndVideoFormatError

from vc2_conformance.encoder.sequence_header import (
    zip_longest_repeating_final_value,
    iter_custom_options_dicts,
    iter_color_spec_options,
    iter_source_parameter_options,
    count_video_parameter_differences,
    rank_base_video_format_similarity,
    rank_allowed_base_video_format_similarity,
    make_parse_parameters,
    iter_sequence_headers,
    make_sequence_header,
)

from vc2_conformance.codec_features import CodecFeatures

from sample_codec_features import MINIMAL_CODEC_FEATURES


HD_1440X1080I60_OVER_SD_SDI_CODEC_FEATURES = CodecFeatures(
    level=Levels.hd_over_sd_sdi,
    profile=Profiles.low_delay,
    major_version=2,
    minor_version=0,
    picture_coding_mode=PictureCodingModes.pictures_are_fields,
    video_parameters=VideoParameters(
        frame_width=1440,
        frame_height=1080,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        source_sampling=SourceSamplingModes.interlaced,
        top_field_first=True,
        frame_rate_numer=30000,
        frame_rate_denom=1001,
        pixel_aspect_ratio_numer=4,
        pixel_aspect_ratio_denom=3,
        clean_width=1440,
        clean_height=1080,
        left_offset=0,
        top_offset=0,
        luma_offset=64,
        luma_excursion=876,
        color_diff_offset=512,
        color_diff_excursion=896,
        color_primaries_index=PresetColorPrimaries.hdtv,
        color_matrix_index=PresetColorMatrices.hdtv,
        transfer_function_index=PresetTransferFunctions.tv_gamma,
    ),
    wavelet_index=WaveletFilters.le_gall_5_3,
    wavelet_index_ho=WaveletFilters.le_gall_5_3,
    dwt_depth=3,
    dwt_depth_ho=0,
    slices_x=90,
    slices_y=68,
    fragment_slice_count=0,
    lossless=False,
    picture_bytes=(972 * 90 * 68) // 17,
    quantization_matrix=None,
)


HD_1440X1080I50_OVER_SD_SDI_CODEC_FEATURES = CodecFeatures(
    HD_1440X1080I60_OVER_SD_SDI_CODEC_FEATURES,
    video_parameters=VideoParameters(
        HD_1440X1080I60_OVER_SD_SDI_CODEC_FEATURES["video_parameters"],
        frame_rate_numer=25,
        frame_rate_denom=1,
    ),
    slices_x=90,
    slices_y=68,
    picture_bytes=(1152 * 90 * 68) // 17,
)


class TestZipLongestRepeatingFinalValue(object):
    def test_no_iterators(self):
        assert list(zip_longest_repeating_final_value()) == []

    def test_single_empty_iterator(self):
        assert list(zip_longest_repeating_final_value([])) == []

    def test_single_singleton_iterator(self):
        assert list(zip_longest_repeating_final_value([1])) == [(1,)]

    def test_single_iterator(self):
        assert list(zip_longest_repeating_final_value([1, 2, 3])) == [
            (1,),
            (2,),
            (3,),
        ]

    def test_multiple_same_length_iterators(self):
        assert (
            list(
                zip_longest_repeating_final_value(
                    [1, 2, 3],
                    "abc",
                    [True, False, None],
                )
            )
            == [(1, "a", True), (2, "b", False), (3, "c", None)]
        )

    def test_multiple_different_length_iterators(self):
        assert (
            list(
                zip_longest_repeating_final_value(
                    [1, 2, 3],
                    "?",
                    [True, False],
                )
            )
            == [(1, "?", True), (2, "?", False), (3, "?", False)]
        )

    def test_one_iterator_empty(self):
        assert list(zip_longest_repeating_final_value([1, 2, 3], [],)) == [
            (1, None),
            (2, None),
            (3, None),
        ]


class TestIterCustomOptionsDicts(object):
    @pytest.mark.parametrize(
        "bvp,vp,lcd,exp",
        [
            # Override required
            (
                VideoParameters(
                    frame_width=640,
                    frame_height=480,
                ),
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                defaultdict(AnyValue),
                [
                    FrameSize(
                        custom_dimensions_flag=True,
                        frame_width=1920,
                        frame_height=1080,
                    ),
                ],
            ),
            # Override optional
            (
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                defaultdict(AnyValue),
                [
                    FrameSize(
                        custom_dimensions_flag=False,
                    ),
                    FrameSize(
                        custom_dimensions_flag=True,
                        frame_width=1920,
                        frame_height=1080,
                    ),
                ],
            ),
            # Force no-custom by disallowing the custom flag
            (
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                defaultdict(AnyValue, custom_dimensions_flag=ValueSet(False)),
                [
                    FrameSize(
                        custom_dimensions_flag=False,
                    )
                ],
            ),
            # Force no-custom by disallowing the required dimensions
            (
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                defaultdict(AnyValue, frame_height=ValueSet(720)),
                [
                    FrameSize(
                        custom_dimensions_flag=False,
                    )
                ],
            ),
            # Force custom flag
            (
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                defaultdict(AnyValue, custom_dimensions_flag=ValueSet(True)),
                [
                    FrameSize(
                        custom_dimensions_flag=True,
                        frame_width=1920,
                        frame_height=1080,
                    ),
                ],
            ),
            # Make impossible
            (
                VideoParameters(
                    frame_width=1920,
                    frame_height=720,
                ),
                VideoParameters(
                    frame_width=1920,
                    frame_height=1080,
                ),
                defaultdict(AnyValue, frame_height=ValueSet(720)),
                [],
            ),
        ],
    )
    def test_no_presets(self, bvp, vp, lcd, exp):
        dicts = list(
            iter_custom_options_dicts(
                bvp,
                vp,
                lcd,
                dict_type=FrameSize,
                flag_key="custom_dimensions_flag",
                parameters=["frame_width", "frame_height"],
            )
        )

        assert dicts == exp

    @pytest.mark.parametrize(
        "bvp,vp,lcd,exp",
        [
            # Custom required (no preset available)
            (
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=2,
                    pixel_aspect_ratio_denom=1,
                ),
                defaultdict(AnyValue),
                [
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=True,
                        index=0,
                        pixel_aspect_ratio_numer=2,
                        pixel_aspect_ratio_denom=1,
                    ),
                ],
            ),
            # Custom required (preset available)
            (
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=4,
                    pixel_aspect_ratio_denom=3,
                ),
                defaultdict(AnyValue),
                [
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=True,
                        index=PresetPixelAspectRatios.reduced_horizontal_resolution,
                    ),
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=True,
                        index=0,
                        pixel_aspect_ratio_numer=4,
                        pixel_aspect_ratio_denom=3,
                    ),
                ],
            ),
            # Custom optional
            (
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                defaultdict(AnyValue),
                [
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=False,
                    ),
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=True,
                        index=PresetPixelAspectRatios.ratio_1_1,
                    ),
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=True,
                        index=0,
                        pixel_aspect_ratio_numer=1,
                        pixel_aspect_ratio_denom=1,
                    ),
                ],
            ),
            # Force no-custom by disallowing the flag
            (
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                defaultdict(AnyValue, custom_pixel_aspect_ratio_flag=ValueSet(False)),
                [
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=False,
                    )
                ],
            ),
            # Force no-custom by disallowing required indices
            (
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                defaultdict(AnyValue, pixel_aspect_ratio_index=ValueSet(99)),
                [
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=False,
                    )
                ],
            ),
            # Force no full custom by disallowing 0 index
            (
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                defaultdict(
                    AnyValue,
                    pixel_aspect_ratio_index=ValueSet(
                        PresetPixelAspectRatios.ratio_1_1
                    ),
                ),
                [
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=False,
                    ),
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=True,
                        index=PresetPixelAspectRatios.ratio_1_1,
                    ),
                ],
            ),
            # Force full custom
            (
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                defaultdict(
                    AnyValue,
                    custom_pixel_aspect_ratio_flag=ValueSet(True),
                    pixel_aspect_ratio_index=ValueSet(0),
                ),
                [
                    PixelAspectRatio(
                        custom_pixel_aspect_ratio_flag=True,
                        index=0,
                        pixel_aspect_ratio_numer=1,
                        pixel_aspect_ratio_denom=1,
                    ),
                ],
            ),
            # Make impossible
            (
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                ),
                defaultdict(
                    AnyValue,
                    custom_pixel_aspect_ratio_flag=ValueSet(True),
                    pixel_aspect_ratio_index=ValueSet(0),
                    pixel_aspect_ratio_numer=ValueSet(1),
                    pixel_aspect_ratio_denom=ValueSet(2),
                ),
                [],
            ),
        ],
    )
    def test_with_presets(self, bvp, vp, lcd, exp):
        dicts = list(
            iter_custom_options_dicts(
                bvp,
                vp,
                lcd,
                dict_type=PixelAspectRatio,
                flag_key="custom_pixel_aspect_ratio_flag",
                parameters=["pixel_aspect_ratio_numer", "pixel_aspect_ratio_denom"],
                presets=PRESET_PIXEL_ASPECT_RATIOS,
                preset_index_constraint_key="pixel_aspect_ratio_index",
            )
        )

        assert dicts == exp

    @pytest.mark.parametrize(
        "bvp,vp,exp",
        [
            # Values match
            (
                VideoParameters(
                    color_primaries_index=PresetColorPrimaries.hdtv,
                ),
                VideoParameters(
                    color_primaries_index=PresetColorPrimaries.hdtv,
                ),
                [
                    ColorPrimaries(
                        custom_color_primaries_flag=False,
                    ),
                    ColorPrimaries(
                        custom_color_primaries_flag=True,
                        index=PresetColorPrimaries.hdtv,
                    ),
                ],
            ),
            # Values don't match
            (
                VideoParameters(
                    color_primaries_index=PresetColorPrimaries.uhdtv,
                ),
                VideoParameters(
                    color_primaries_index=PresetColorPrimaries.hdtv,
                ),
                [
                    ColorPrimaries(
                        custom_color_primaries_flag=True,
                        index=PresetColorPrimaries.hdtv,
                    ),
                ],
            ),
        ],
    )
    def test_with_differing_key_names(self, bvp, vp, exp):
        dicts = list(
            iter_custom_options_dicts(
                bvp,
                vp,
                defaultdict(AnyValue),
                dict_type=ColorPrimaries,
                flag_key="custom_color_primaries_flag",
                parameters=[("color_primaries_index", "index")],
                preset_index_constraint_key="color_primaries_index",
            )
        )

        assert dicts == exp


@pytest.mark.parametrize(
    "bvp,vp,lcd, exp",
    [
        # Built-in combination, optionally specified
        (
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            defaultdict(AnyValue),
            [
                ColorSpec(
                    custom_color_spec_flag=False,
                ),
                ColorSpec(
                    custom_color_spec_flag=True,
                    index=PresetColorSpecs.hdtv,
                ),
                ColorSpec(
                    custom_color_spec_flag=True,
                    index=0,
                    color_primaries=ColorPrimaries(
                        custom_color_primaries_flag=False,
                    ),
                    color_matrix=ColorMatrix(
                        custom_color_matrix_flag=False,
                    ),
                    transfer_function=TransferFunction(
                        custom_transfer_function_flag=False,
                    ),
                ),
                ColorSpec(
                    custom_color_spec_flag=True,
                    index=0,
                    color_primaries=ColorPrimaries(
                        custom_color_primaries_flag=True,
                        index=PresetColorPrimaries.hdtv,
                    ),
                    color_matrix=ColorMatrix(
                        custom_color_matrix_flag=True,
                        index=PresetColorMatrices.hdtv,
                    ),
                    transfer_function=TransferFunction(
                        custom_transfer_function_flag=True,
                        index=PresetTransferFunctions.tv_gamma,
                    ),
                ),
            ],
        ),
        # Partially matches the "custom" preset
        (
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.linear,
            ),
            defaultdict(AnyValue),
            [
                ColorSpec(
                    custom_color_spec_flag=True,
                    index=0,
                    color_primaries=ColorPrimaries(
                        custom_color_primaries_flag=False,
                    ),
                    color_matrix=ColorMatrix(
                        custom_color_matrix_flag=False,
                    ),
                    transfer_function=TransferFunction(
                        custom_transfer_function_flag=True,
                        index=PresetTransferFunctions.linear,
                    ),
                ),
                ColorSpec(
                    custom_color_spec_flag=True,
                    index=0,
                    color_primaries=ColorPrimaries(
                        custom_color_primaries_flag=True,
                        index=PresetColorPrimaries.hdtv,
                    ),
                    color_matrix=ColorMatrix(
                        custom_color_matrix_flag=True,
                        index=PresetColorMatrices.hdtv,
                    ),
                    transfer_function=TransferFunction(
                        custom_transfer_function_flag=True,
                        index=PresetTransferFunctions.linear,
                    ),
                ),
            ],
        ),
        # Custom not allowed (by disabling flag)
        (
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            defaultdict(AnyValue, custom_color_spec_flag=ValueSet(False)),
            [ColorSpec(custom_color_spec_flag=False)],
        ),
        # Custom not allowed (by disabling usable index and invalidating
        # required combination of explicit values)
        (
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.d_cinema,
                color_matrix_index=PresetColorMatrices.reversible,
                transfer_function_index=PresetTransferFunctions.d_cinema,
            ),
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.d_cinema,
                color_matrix_index=PresetColorMatrices.reversible,
                transfer_function_index=PresetTransferFunctions.d_cinema,
            ),
            defaultdict(
                AnyValue,
                color_spec_index=ValueSet(0),
                custom_color_primaries_flag=ValueSet(False),
                custom_color_matrix_flag=ValueSet(False),
                custom_transfer_function_flag=ValueSet(False),
            ),
            [ColorSpec(custom_color_spec_flag=False)],
        ),
        # Full custom not allowed (by disabling index 0)
        (
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.d_cinema,
                color_matrix_index=PresetColorMatrices.reversible,
                transfer_function_index=PresetTransferFunctions.d_cinema,
            ),
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.d_cinema,
                color_matrix_index=PresetColorMatrices.reversible,
                transfer_function_index=PresetTransferFunctions.d_cinema,
            ),
            defaultdict(
                AnyValue,
                color_spec_index=ValueSet(PresetColorSpecs.d_cinema),
            ),
            [
                ColorSpec(custom_color_spec_flag=False),
                ColorSpec(
                    custom_color_spec_flag=True,
                    index=PresetColorSpecs.d_cinema,
                ),
            ],
        ),
        # Full custom required
        (
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.d_cinema,
                color_matrix_index=PresetColorMatrices.reversible,
                transfer_function_index=PresetTransferFunctions.d_cinema,
            ),
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.d_cinema,
                color_matrix_index=PresetColorMatrices.reversible,
                transfer_function_index=PresetTransferFunctions.d_cinema,
            ),
            defaultdict(
                AnyValue,
                custom_color_spec_flag=ValueSet(True),
                color_spec_index=ValueSet(0),
            ),
            [
                ColorSpec(
                    custom_color_spec_flag=True,
                    index=0,
                    color_primaries=ColorPrimaries(
                        custom_color_primaries_flag=True,
                        index=PresetColorPrimaries.d_cinema,
                    ),
                    color_matrix=ColorMatrix(
                        custom_color_matrix_flag=True,
                        index=PresetColorMatrices.reversible,
                    ),
                    transfer_function=TransferFunction(
                        custom_transfer_function_flag=True,
                        index=PresetTransferFunctions.d_cinema,
                    ),
                ),
            ],
        ),
        # Impossible (because custom disabled)
        (
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.d_cinema,
                color_matrix_index=PresetColorMatrices.reversible,
                transfer_function_index=PresetTransferFunctions.d_cinema,
            ),
            defaultdict(
                AnyValue,
                custom_color_spec_flag=ValueSet(False),
            ),
            [],
        ),
        # Impossible (because underlying parameters cannot be customised)
        (
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            VideoParameters(
                color_primaries_index=PresetColorPrimaries.d_cinema,
                color_matrix_index=PresetColorMatrices.reversible,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            defaultdict(
                AnyValue, color_primaries_index=ValueSet(PresetColorPrimaries.hdtv)
            ),
            [],
        ),
    ],
)
def test_iter_color_spec_options(bvp, vp, lcd, exp):
    assert list(iter_color_spec_options(bvp, vp, lcd)) == exp


class TestIterSourceParameterOptions(object):
    def test_valid_bitstream(self):
        # This test runs all of the option sets produced through the bitstream
        # generator to verify that 1: the dictionaries all contain the expected
        # fields and 2: that they encode the options they're supposed to. This
        # test also indirectly tests all of the contributing option generating
        # functions.
        base_video_format = BaseVideoFormats.hd1080p_50
        video_parameters = set_source_defaults(base_video_format)
        level_constraints_dict = defaultdict(AnyValue)

        source_parameters_sets = list(
            iter_source_parameter_options(
                video_parameters, video_parameters, level_constraints_dict
            )
        )

        for context in source_parameters_sets:
            state = State()

            f = BytesIO()
            with Serialiser(BitstreamWriter(f), context) as ser:
                resulting_video_parameters = source_parameters(
                    ser,
                    state,
                    base_video_format,
                )

            assert resulting_video_parameters == video_parameters

    def test_covers_all_flag_states(self):
        # Checks that the examples produced show every flag in every possible
        # state (when the options we choose correspond with a base video
        # format).

        base_video_format = BaseVideoFormats.hd1080p_50
        video_parameters = set_source_defaults(base_video_format)
        level_constraints_dict = defaultdict(AnyValue)

        source_parameters_sets = list(
            iter_source_parameter_options(
                video_parameters, video_parameters, level_constraints_dict
            )
        )

        # {flag_name: set([bool, ...]), ...}
        observed_flag_settings = defaultdict(set)

        for src_parameters in source_parameters_sets:
            flag_settings = {}

            def find_flags(d):
                if isinstance(d, dict):
                    for key, value in d.items():
                        if key.endswith("_flag"):
                            assert key not in flag_settings
                            flag_settings[key] = value
                        else:
                            find_flags(value)

            find_flags(src_parameters)
            for flag, setting in flag_settings.items():
                observed_flag_settings[flag].add(setting)

        assert all(
            settings == set([True, False])
            for settings in observed_flag_settings.values()
        )

    def test_mismatched_top_field_first(self):
        base_video_parameters = set_source_defaults(BaseVideoFormats.custom_format)
        video_parameters = set_source_defaults(BaseVideoFormats.hd1080p_50)
        level_constraints_dict = defaultdict(AnyValue)

        assert (
            list(
                iter_source_parameter_options(
                    base_video_parameters, video_parameters, level_constraints_dict
                )
            )
            == []
        )

    def test_unsatisfiable_level_constraints(self):
        base_video_parameters = set_source_defaults(BaseVideoFormats.hd720p_50)
        video_parameters = set_source_defaults(BaseVideoFormats.hd1080p_50)
        level_constraints_dict = defaultdict(
            AnyValue,
            custom_dimensions_flag=ValueSet(False),
        )

        assert (
            list(
                iter_source_parameter_options(
                    base_video_parameters, video_parameters, level_constraints_dict
                )
            )
            == []
        )


class TestCountVideoParameterDifferences(object):
    def test_empty(self):
        assert (
            count_video_parameter_differences(
                VideoParameters(),
                VideoParameters(),
            )
            == 0
        )

    def test_single_equal(self):
        assert (
            count_video_parameter_differences(
                VideoParameters(top_field_first=True),
                VideoParameters(top_field_first=True),
            )
            == 0
        )

    def test_single_different(self):
        assert (
            count_video_parameter_differences(
                VideoParameters(top_field_first=True),
                VideoParameters(top_field_first=False),
            )
            == 1
        )

    def test_fields_missing(self):
        assert (
            count_video_parameter_differences(
                VideoParameters(frame_width=1920),
                VideoParameters(frame_height=1920),
            )
            == 2
        )

    def test_complete(self):
        assert (
            count_video_parameter_differences(
                VideoParameters(set_source_defaults(BaseVideoFormats.hd1080p_50)),
                VideoParameters(set_source_defaults(BaseVideoFormats.hd1080p_60)),
            )
            == 2
        )  # frame_rate_{numer,denom}


class TestRankBaseVideoFormatSimilarity(object):
    def test_matching(self):
        video_parameters = set_source_defaults(BaseVideoFormats.hd1080p_50)

        ranking = rank_base_video_format_similarity(video_parameters)

        # Exact match
        assert ranking[0] == BaseVideoFormats.hd1080p_50

        # Close match (source sampling differs)
        assert ranking[1] == BaseVideoFormats.hd1080i_50

        # Next closest (frame rate numer/denom differs)
        assert set(ranking[2:5]) == set(
            [
                BaseVideoFormats.hd1080i_60,
                BaseVideoFormats.hd1080p_60,
                BaseVideoFormats.hd1080p_24,
            ]
        )

    @pytest.mark.parametrize("top_field_first", [True, False])
    def test_top_field_first_always_matches(self, top_field_first):
        video_parameters = VideoParameters(top_field_first=top_field_first)

        for index in rank_base_video_format_similarity(video_parameters):
            assert set_source_defaults(index)["top_field_first"] == top_field_first

    def test_match_against_subset(self):
        video_parameters = VideoParameters(top_field_first=True)

        candidates = [
            BaseVideoFormats.hd1080p_50,
            BaseVideoFormats.hd1080p_60,
            BaseVideoFormats.hd720p_50,
            BaseVideoFormats.hd720p_60,
        ]

        assert set(
            rank_base_video_format_similarity(video_parameters, candidates)
        ) == set(candidates)


class TestRankAllowedBaseVideoFormatSimilarity(object):
    def test_unconstrained(self):
        base_video_formats = rank_allowed_base_video_format_similarity(
            MINIMAL_CODEC_FEATURES
        )

        suitable_base_video_formats = set(
            index
            for index, params in BASE_VIDEO_FORMAT_PARAMETERS.items()
            if params.top_field_first is True
        )

        assert set(base_video_formats) == suitable_base_video_formats

    def test_constrained_by_level(self):
        base_video_formats = rank_allowed_base_video_format_similarity(
            HD_1440X1080I60_OVER_SD_SDI_CODEC_FEATURES
        )

        assert base_video_formats == [BaseVideoFormats.hd1080i_60]

    def test_impossible(self):
        codec_features = deepcopy(HD_1440X1080I60_OVER_SD_SDI_CODEC_FEATURES)
        codec_features["video_parameters"]["top_field_first"] = False

        assert rank_allowed_base_video_format_similarity(codec_features) == []


def serialise(context, pseudocode, state=None, file=None, *args, **kwargs):
    state = state if state is not None else State()
    file = file if file is not None else BytesIO()
    with Serialiser(
        BitstreamWriter(file),
        context,
        vc2_default_values,
    ) as ser:
        return pseudocode(ser, state, *args, **kwargs)


def test_make_parse_parameters():
    state = State()
    serialise(make_parse_parameters(MINIMAL_CODEC_FEATURES), parse_parameters, state)
    assert state["major_version"] == 3
    assert state["minor_version"] == 0
    assert state["profile"] == Profiles.high_quality
    assert state["level"] == Levels.unconstrained


@pytest.mark.parametrize(
    "codec_features",
    [
        # A fairly generic and unconstrained set
        MINIMAL_CODEC_FEATURES,
        # A level-constrained format (for which the level constraints must be
        # obeyed)
        HD_1440X1080I60_OVER_SD_SDI_CODEC_FEATURES,
        HD_1440X1080I50_OVER_SD_SDI_CODEC_FEATURES,
    ],
)
def test_iter_sequence_headers(codec_features):
    sequence_headers = list(iter_sequence_headers(codec_features))
    assert sequence_headers

    pi = ParseInfo(
        parse_code=ParseCodes.sequence_header,
        # An arbitrary non-zero value; this won't get picked up by the
        # conformance checker since it'll hit the end-of-file first
        next_parse_offset=999,
    )

    for sh in sequence_headers:
        f = BytesIO()
        state = State()
        serialise(pi, parse_info, state, f)
        video_parameters = serialise(sh, sequence_header, state, f)

        # Check the encoded video parameters are as requested
        assert video_parameters == codec_features["video_parameters"]

        # Check that the header does everything that the level requires. Here we
        # just check we reach the end of the sequence header without a conformance
        # error.
        f.seek(0)
        state = State()
        init_io(state, f)
        with pytest.raises((UnexpectedEndOfStream, InconsistentNextParseOffset)):
            parse_stream(state)
        assert f.tell() == len(f.getvalue())


def test_make_sequence_header_impossible():
    codec_features = deepcopy(HD_1440X1080I60_OVER_SD_SDI_CODEC_FEATURES)
    codec_features["video_parameters"]["left_offset"] = 1
    with pytest.raises(IncompatibleLevelAndVideoFormatError):
        make_sequence_header(codec_features)
