import pytest

from itertools import islice

from vc2_data_tables import (
    Levels,
    Profiles,
    PictureCodingModes,
    WaveletFilters,
    BaseVideoFormats,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
)

from vc2_conformance.video_parameters import (
    set_source_defaults,
    VideoParameters,
)

from vc2_conformance.test_cases.codec_features import (
    CodecFeatures,
    read_dict_list_csv,
    spreadsheet_column_names,
    parse_int_enum,
    parse_bool,
    parse_quantization_matrix,
    InvalidCodecFeaturesError,
    read_codec_features_csv,
)


class TestReadDictListCSV(object):
    
    def test_empty(self):
        assert read_dict_list_csv([]) == []
    
    def test_no_non_comments(self):
        assert read_dict_list_csv([
            "#comment,foo,bar",
            ",also,comment",
            "",
        ]) == []
    
    def test_single_dict(self):
        assert read_dict_list_csv([
            "a,one",
            "b,two",
            "c,three",
        ]) == [{
            "a": "one",
            "b": "two",
            "c": "three",
        }]
    
    def test_multiple_dicts(self):
        assert read_dict_list_csv([
            "a,one,ay",
            "b,two,bee",
            "c,three,see",
        ]) == [
            {
                "a": "one",
                "b": "two",
                "c": "three",
            },
            {
                "a": "ay",
                "b": "bee",
                "c": "see",
            },
        ]
    
    def test_comment_rows(self):
        assert read_dict_list_csv([
            "#a,comment,row",
            "a,one",
            ",another one",
            "b,two",
            ",,",
            "c,three",
            "",
        ]) == [
            {
                "a": "one",
                "b": "two",
                "c": "three",
            },
        ]
    
    def test_missing_entries(self):
        assert read_dict_list_csv([
            "a,one,even",
            "b,two,,odd",
            "c,three,even",
        ]) == [
            {
                "a": "one",
                "b": "two",
                "c": "three",
            },
            {
                "a": "even",
                "c": "even",
            },
            {
                "b": "odd",
            },
        ]
    
    def test_strip_whitespace(self):
        assert read_dict_list_csv([
            " # a comment ",
            "a ,one ",
            " ,an empty row",
            " b, two",
            " c , three ",
        ]) == [
            {
                "a": "one",
                "b": "two",
                "c": "three",
            },
        ]


def test_spreadsheet_column_names():
    assert list(islice(spreadsheet_column_names(), 0, 3)) == ["A", "B", "C"]
    assert list(islice(spreadsheet_column_names(), 24, 28)) == ["Y", "Z", "AA", "AB"]
    assert list(islice(spreadsheet_column_names(), 50, 54)) == ["AY", "AZ", "BA", "BB"]


class TestParseIntEnum(object):
    
    @pytest.mark.parametrize("string,exp", [
        ("0", Profiles.low_delay),
        ("3", Profiles.high_quality),
        ("low_delay", Profiles.low_delay),
        ("high_quality", Profiles.high_quality),
    ])
    def test_valid(self, string, exp):
        value = parse_int_enum(Profiles, string)
        assert value == exp
        assert type(value) is type(exp)
    
    @pytest.mark.parametrize("string", [
        "",
        "1",
        "foo",
    ])
    def test_invalid(self, string):
        with pytest.raises(ValueError):
            parse_int_enum(Profiles, string)


class TestParseBool(object):
    
    @pytest.mark.parametrize("string,exp", [
        ("1", True),
        ("TRue", True),
        ("0", False),
        ("FAlse", False),
    ])
    def test_valid(self, string, exp):
        value = parse_bool(string)
        assert value is exp
    
    @pytest.mark.parametrize("string", [
        "",
        "foo",
        "tar",
        "2",
    ])
    def test_invalid(self, string):
        with pytest.raises(ValueError):
            parse_bool(string)


class TestParseQuantisationMatrix(object):
    
    @pytest.mark.parametrize("string,dwt_depth,dwt_depth_ho,expected", [
        ("123", 0, 0, {0: {"LL": 123}}),
        ("1 2 3 4", 1, 0, {0: {"LL": 1}, 1: {"HL": 2, "LH": 3, "HH": 4}}),
        (
            "1 2 3 4 5",
            1,
            1,
            {
                0: {"L": 1},
                1: {"H": 2},
                2: {"HL": 3, "LH": 4, "HH": 5},
            }
        ),
        # More than one whitespace separator
        ("  123  ", 0, 0, {0: {"LL": 123}}),
        ("  1   2   ", 0, 1, {0: {"L": 1}, 1: {"H": 2}}),
    ])
    def test_valid(self, string, dwt_depth, dwt_depth_ho, expected):
        assert parse_quantization_matrix(
            dwt_depth,
            dwt_depth_ho,
            string,
        ) == expected
    
    @pytest.mark.parametrize("string,dwt_depth,dwt_depth_ho", [
        # Bad integers
        ("nope", 0, 0),
        # Too short
        ("", 0, 0),
        ("0", 0, 1),
        ("0 0 0", 1, 0),
        # Too long
        ("1 2", 0, 0),
        ("1 2 3", 0, 1),
        ("1 2 3 4 5", 1, 0),
    ])
    def test_invalid(self, string, dwt_depth, dwt_depth_ho):
        with pytest.raises(ValueError):
            parse_quantization_matrix(
                dwt_depth,
                dwt_depth_ho,
                string,
            )

class TestReadCodecFeaturesCSV(object):
    
    def test_empty(self):
        assert read_codec_features_csv([]) == []
    
    def test_basic_valid(self):
        assert read_codec_features_csv([
            "name,                      hd",
            "level,                     unconstrained,        0",
            "profile,                   high_quality,         3",
            "major_version,             3,                    3",
            "minor_version,             0,                    0",
            "base_video_format,         hd1080p_50,           custom_format",
            "picture_coding_mode,       pictures_are_frames,  pictures_are_frames",
            "frame_width,               default,              8",
            "frame_height,              default,              4",
            "color_diff_format_index,   default,              color_4_4_4",
            "source_sampling,           default,              progressive",
            "top_field_first,           default,              TRUE",
            "frame_rate_numer,          default,              1",
            "frame_rate_denom,          default,              1",
            "pixel_aspect_ratio_numer,  default,              1",
            "pixel_aspect_ratio_denom,  default,              1",
            "clean_width,               default,              8",
            "clean_height,              default,              4",
            "left_offset,               default,              0",
            "top_offset,                default,              0",
            "luma_offset,               default,              0",
            "luma_excursion,            default,              255",
            "color_diff_offset,         default,              128",
            "color_diff_excursion,      default,              255",
            "color_primaries_index,     default,              hdtv",
            "color_matrix_index,        default,              hdtv",
            "transfer_function_index,   default,              tv_gamma",
            "wavelet_index,             haar_with_shift,      haar_with_shift",
            "wavelet_index_ho,          haar_with_shift,      haar_with_shift",
            "dwt_depth,                 2,                    2",
            "dwt_depth_ho,              0,                    0",
            "slices_x,                  120,                  2",
            "slices_y,                  108,                  1",
            "lossless,                  FALSE,                FALSE",
            "picture_bytes,             1036800,              24",
            "quantization_matrix,       default,              0 0 0 0 0 0 0",
        ]) == [
            CodecFeatures(
                name="hd",
                level=Levels.unconstrained,
                profile=Profiles.high_quality,
                major_version=3,
                minor_version=0,
                picture_coding_mode=PictureCodingModes.pictures_are_frames,
                video_parameters=set_source_defaults(BaseVideoFormats.hd1080p_50),
                wavelet_index=WaveletFilters.haar_with_shift,
                wavelet_index_ho=WaveletFilters.haar_with_shift,
                dwt_depth=2,
                dwt_depth_ho=0,
                slices_x=120,
                slices_y=108,
                lossless=False,
                picture_bytes=1036800,
                quantization_matrix=None,
            ),
            CodecFeatures(
                name="column_C",
                level=Levels.unconstrained,
                profile=Profiles.high_quality,
                major_version=3,
                minor_version=0,
                picture_coding_mode=PictureCodingModes.pictures_are_frames,
                video_parameters=VideoParameters(
                    frame_width=8,
                    frame_height=4,
                    color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
                    source_sampling=SourceSamplingModes.progressive,
                    top_field_first=True,
                    frame_rate_numer=1,
                    frame_rate_denom=1,
                    pixel_aspect_ratio_numer=1,
                    pixel_aspect_ratio_denom=1,
                    clean_width=8,
                    clean_height=4,
                    left_offset=0,
                    top_offset=0,
                    luma_offset=0,
                    luma_excursion=255,
                    color_diff_offset=128,
                    color_diff_excursion=255,
                    color_primaries_index=PresetColorPrimaries.hdtv,
                    color_matrix_index=PresetColorMatrices.hdtv,
                    transfer_function_index=PresetTransferFunctions.tv_gamma,
                ),
                wavelet_index=WaveletFilters.haar_with_shift,
                wavelet_index_ho=WaveletFilters.haar_with_shift,
                dwt_depth=2,
                dwt_depth_ho=0,
                slices_x=2,
                slices_y=1,
                lossless=False,
                picture_bytes=24,
                quantization_matrix={
                    0: {"LL": 0},
                    1: {"HL": 0, "LH": 0, "HH": 0},
                    2: {"HL": 0, "LH": 0, "HH": 0},
                },
            )
        ]
    
    def test_missing_row(self):
        with pytest.raises(InvalidCodecFeaturesError, match=r".*quantization_matrix.*"):
            read_codec_features_csv([
                "name,                      hd",
                "level,                     unconstrained",
                "profile,                   high_quality",
                "major_version,             3",
                "minor_version,             0",
                "base_video_format,         hd1080p_50",
                "picture_coding_mode,       pictures_are_frames",
                "frame_width,               default",
                "frame_height,              default",
                "color_diff_format_index,   default",
                "source_sampling,           default",
                "top_field_first,           default",
                "frame_rate_numer,          default",
                "frame_rate_denom,          default",
                "pixel_aspect_ratio_numer,  default",
                "pixel_aspect_ratio_denom,  default",
                "clean_width,               default",
                "clean_height,              default",
                "left_offset,               default",
                "top_offset,                default",
                "luma_offset,               default",
                "luma_excursion,            default",
                "color_diff_offset,         default",
                "color_diff_excursion,      default",
                "color_primaries_index,     default",
                "color_matrix_index,        default",
                "transfer_function_index,   default",
                "wavelet_index,             haar_with_shift",
                "wavelet_index_ho,          haar_with_shift",
                "dwt_depth,                 2",
                "dwt_depth_ho,              0",
                "slices_x,                  120",
                "slices_y,                  108",
                "lossless,                  FALSE",
                "picture_bytes,             1036800",
                #"quantization_matrix,       default",
            ])
    
    def test_extra_row(self):
        with pytest.raises(InvalidCodecFeaturesError, match=r".*foobar.*"):
            read_codec_features_csv([
                "name,                      hd",
                "level,                     unconstrained",
                "profile,                   high_quality",
                "major_version,             3",
                "minor_version,             0",
                "base_video_format,         hd1080p_50",
                "picture_coding_mode,       pictures_are_frames",
                "frame_width,               default",
                "frame_height,              default",
                "color_diff_format_index,   default",
                "source_sampling,           default",
                "top_field_first,           default",
                "frame_rate_numer,          default",
                "frame_rate_denom,          default",
                "pixel_aspect_ratio_numer,  default",
                "pixel_aspect_ratio_denom,  default",
                "clean_width,               default",
                "clean_height,              default",
                "left_offset,               default",
                "top_offset,                default",
                "luma_offset,               default",
                "luma_excursion,            default",
                "color_diff_offset,         default",
                "color_diff_excursion,      default",
                "color_primaries_index,     default",
                "color_matrix_index,        default",
                "transfer_function_index,   default",
                "wavelet_index,             haar_with_shift",
                "wavelet_index_ho,          haar_with_shift",
                "dwt_depth,                 2",
                "dwt_depth_ho,              0",
                "slices_x,                  120",
                "slices_y,                  108",
                "lossless,                  FALSE",
                "picture_bytes,             1036800",
                "quantization_matrix,       default",
                "foobar,                    123",
            ])
    
    def test_contradictory_lossless(self):
        with pytest.raises(InvalidCodecFeaturesError, match=r".*lossless.*"):
            read_codec_features_csv([
                "name,                      hd",
                "level,                     unconstrained",
                "profile,                   high_quality",
                "major_version,             3",
                "minor_version,             0",
                "base_video_format,         hd1080p_50",
                "picture_coding_mode,       pictures_are_frames",
                "frame_width,               default",
                "frame_height,              default",
                "color_diff_format_index,   default",
                "source_sampling,           default",
                "top_field_first,           default",
                "frame_rate_numer,          default",
                "frame_rate_denom,          default",
                "pixel_aspect_ratio_numer,  default",
                "pixel_aspect_ratio_denom,  default",
                "clean_width,               default",
                "clean_height,              default",
                "left_offset,               default",
                "top_offset,                default",
                "luma_offset,               default",
                "luma_excursion,            default",
                "color_diff_offset,         default",
                "color_diff_excursion,      default",
                "color_primaries_index,     default",
                "color_matrix_index,        default",
                "transfer_function_index,   default",
                "wavelet_index,             haar_with_shift",
                "wavelet_index_ho,          haar_with_shift",
                "dwt_depth,                 2",
                "dwt_depth_ho,              0",
                "slices_x,                  120",
                "slices_y,                  108",
                "lossless,                  TRUE",
                "picture_bytes,             1036800",
                "quantization_matrix,       default",
            ])
    
    def test_no_default_quantisation_matrix_available(self):
        with pytest.raises(InvalidCodecFeaturesError, match=r".*Default.*"):
            read_codec_features_csv([
                "name,                      hd",
                "level,                     unconstrained",
                "profile,                   high_quality",
                "major_version,             3",
                "minor_version,             0",
                "base_video_format,         hd1080p_50",
                "picture_coding_mode,       pictures_are_frames",
                "frame_width,               default",
                "frame_height,              default",
                "color_diff_format_index,   default",
                "source_sampling,           default",
                "top_field_first,           default",
                "frame_rate_numer,          default",
                "frame_rate_denom,          default",
                "pixel_aspect_ratio_numer,  default",
                "pixel_aspect_ratio_denom,  default",
                "clean_width,               default",
                "clean_height,              default",
                "left_offset,               default",
                "top_offset,                default",
                "luma_offset,               default",
                "luma_excursion,            default",
                "color_diff_offset,         default",
                "color_diff_excursion,      default",
                "color_primaries_index,     default",
                "color_matrix_index,        default",
                "transfer_function_index,   default",
                "wavelet_index,             haar_with_shift",
                "wavelet_index_ho,          haar_with_shift",
                "dwt_depth,                 99",
                "dwt_depth_ho,              0",
                "slices_x,                  120",
                "slices_y,                  108",
                "lossless,                  FALSE",
                "picture_bytes,             1036800",
                "quantization_matrix,       default",
            ])
