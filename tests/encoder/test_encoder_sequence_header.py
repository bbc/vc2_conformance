import pytest

from io import BytesIO

from collections import defaultdict

from vc2_data_tables import (
    Profiles,
    Levels,
    BaseVideoFormats,
    PresetPixelAspectRatios,
    PRESET_PIXEL_ASPECT_RATIOS,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    PresetColorSpecs,
)

from vc2_conformance.bitstream import (
    BitstreamWriter,
    Serialiser,
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
    sequence_header,
)

from vc2_conformance.bitstream.vc2_fixeddicts import vc2_default_values

from vc2_conformance.state import State

from vc2_conformance.video_parameters import (
    VideoParameters,
    set_source_defaults,
)

from vc2_conformance.encoder.sequence_header import (
    zip_longest_repeating_final_value,
    iter_custom_options_dicts,
    iter_color_spec_options,
    iter_source_parameter_options,
    count_video_parameter_differences,
    rank_base_video_format_similarity,
    make_parse_parameters,
    make_sequence_header,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES


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
        assert list(
            zip_longest_repeating_final_value([1, 2, 3], "abc", [True, False, None],)
        ) == [(1, "a", True), (2, "b", False), (3, "c", None)]

    def test_multiple_different_length_iterators(self):
        assert list(
            zip_longest_repeating_final_value([1, 2, 3], "?", [True, False],)
        ) == [(1, "?", True), (2, "?", False), (3, "?", False)]

    def test_one_iterator_empty(self):
        assert list(zip_longest_repeating_final_value([1, 2, 3], [],)) == [
            (1, None),
            (2, None),
            (3, None),
        ]


class TestIterCustomOptionsDicts(object):
    @pytest.mark.parametrize(
        "bvp,vp,exp",
        [
            # Override required
            (
                VideoParameters(frame_width=640, frame_height=480,),
                VideoParameters(frame_width=1920, frame_height=1080,),
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
                VideoParameters(frame_width=1920, frame_height=1080,),
                VideoParameters(frame_width=1920, frame_height=1080,),
                [
                    FrameSize(custom_dimensions_flag=False,),
                    FrameSize(
                        custom_dimensions_flag=True,
                        frame_width=1920,
                        frame_height=1080,
                    ),
                ],
            ),
        ],
    )
    def test_no_presets(self, bvp, vp, exp):
        dicts = list(
            iter_custom_options_dicts(
                bvp,
                vp,
                dict_type=FrameSize,
                flag_key="custom_dimensions_flag",
                parameters=["frame_width", "frame_height"],
            )
        )

        assert dicts == exp

    @pytest.mark.parametrize(
        "bvp,vp,exp",
        [
            # Custom required (no preset available)
            (
                VideoParameters(
                    pixel_aspect_ratio_numer=1, pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=2, pixel_aspect_ratio_denom=1,
                ),
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
                    pixel_aspect_ratio_numer=1, pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=4, pixel_aspect_ratio_denom=3,
                ),
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
                    pixel_aspect_ratio_numer=1, pixel_aspect_ratio_denom=1,
                ),
                VideoParameters(
                    pixel_aspect_ratio_numer=1, pixel_aspect_ratio_denom=1,
                ),
                [
                    PixelAspectRatio(custom_pixel_aspect_ratio_flag=False,),
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
        ],
    )
    def test_with_presets(self, bvp, vp, exp):
        dicts = list(
            iter_custom_options_dicts(
                bvp,
                vp,
                dict_type=PixelAspectRatio,
                flag_key="custom_pixel_aspect_ratio_flag",
                parameters=["pixel_aspect_ratio_numer", "pixel_aspect_ratio_denom"],
                presets=PRESET_PIXEL_ASPECT_RATIOS,
            )
        )

        assert dicts == exp

    @pytest.mark.parametrize(
        "bvp,vp,exp",
        [
            # Values match
            (
                VideoParameters(color_primaries_index=PresetColorPrimaries.hdtv,),
                VideoParameters(color_primaries_index=PresetColorPrimaries.hdtv,),
                [
                    ColorPrimaries(custom_color_primaries_flag=False,),
                    ColorPrimaries(
                        custom_color_primaries_flag=True,
                        index=PresetColorPrimaries.hdtv,
                    ),
                ],
            ),
            # Values don't match
            (
                VideoParameters(color_primaries_index=PresetColorPrimaries.uhdtv,),
                VideoParameters(color_primaries_index=PresetColorPrimaries.hdtv,),
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
                dict_type=ColorPrimaries,
                flag_key="custom_color_primaries_flag",
                parameters=[("color_primaries_index", "index")],
            )
        )

        assert dicts == exp


@pytest.mark.parametrize(
    "bvp,vp,exp",
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
            [
                ColorSpec(custom_color_spec_flag=False,),
                ColorSpec(custom_color_spec_flag=True, index=PresetColorSpecs.hdtv,),
                ColorSpec(
                    custom_color_spec_flag=True,
                    index=0,
                    color_primaries=ColorPrimaries(custom_color_primaries_flag=False,),
                    color_matrix=ColorMatrix(custom_color_matrix_flag=False,),
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
                        custom_color_matrix_flag=True, index=PresetColorMatrices.hdtv,
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
            [
                ColorSpec(
                    custom_color_spec_flag=True,
                    index=0,
                    color_primaries=ColorPrimaries(custom_color_primaries_flag=False,),
                    color_matrix=ColorMatrix(custom_color_matrix_flag=False,),
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
                        custom_color_matrix_flag=True, index=PresetColorMatrices.hdtv,
                    ),
                    transfer_function=TransferFunction(
                        custom_transfer_function_flag=True,
                        index=PresetTransferFunctions.linear,
                    ),
                ),
            ],
        ),
    ],
)
def test_iter_color_spec_options(bvp, vp, exp):
    assert list(iter_color_spec_options(bvp, vp)) == exp


class TestIterSourceParameterOptions(object):
    def test_valid_bitstream(self):
        # This test runs all of the option sets produced through the bitstream
        # generator to verify that 1: the dictionaries all contain the expected
        # fields and 2: that they encode the options they're supposed to. This
        # test also indirectly tests all of the contributing option generating
        # functions.
        base_video_format = BaseVideoFormats.hd1080p_50
        video_parameters = set_source_defaults(base_video_format)

        source_parameters_sets = list(
            iter_source_parameter_options(video_parameters, video_parameters,)
        )

        for context in source_parameters_sets:
            state = State()

            f = BytesIO()
            with Serialiser(BitstreamWriter(f), context) as ser:
                resulting_video_parameters = source_parameters(
                    ser, state, base_video_format,
                )

            assert resulting_video_parameters == video_parameters

    def test_covers_all_flag_states(self):
        # Checks that the examples produced show every flag in every possible
        # state (when the options we choose correspond with a base video
        # format).

        base_video_format = BaseVideoFormats.hd1080p_50
        video_parameters = set_source_defaults(base_video_format)

        source_parameters_sets = list(
            iter_source_parameter_options(video_parameters, video_parameters,)
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

        assert (
            list(
                iter_source_parameter_options(base_video_parameters, video_parameters,)
            )
            == []
        )


class TestCountVideoParameterDifferences(object):
    def test_empty(self):
        assert (
            count_video_parameter_differences(VideoParameters(), VideoParameters(),)
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
                VideoParameters(frame_width=1920), VideoParameters(frame_height=1920),
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


def serialise(context, pseudocode, state=None, *args, **kwargs):
    state = state if state is not None else State()
    with Serialiser(BitstreamWriter(BytesIO()), context, vc2_default_values,) as ser:
        return pseudocode(ser, state, *args, **kwargs)


def test_make_parse_parameters():
    state = State()
    serialise(make_parse_parameters(MINIMAL_CODEC_FEATURES), parse_parameters, state)
    assert state["major_version"] == 3
    assert state["minor_version"] == 0
    assert state["profile"] == Profiles.high_quality
    assert state["level"] == Levels.unconstrained


def test_make_sequence_header():
    video_parameters = serialise(
        make_sequence_header(MINIMAL_CODEC_FEATURES), sequence_header,
    )
    assert video_parameters == MINIMAL_CODEC_FEATURES["video_parameters"]
