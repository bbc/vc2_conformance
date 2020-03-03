"""
Sample :Py:class:`vc2_conformance.codec_features.CodecFeatures`
objects for use in this test suite.
"""

from vc2_data_tables import (
    Levels,
    Profiles,
    PictureCodingModes,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    WaveletFilters,
)

from vc2_conformance.codec_features import CodecFeatures

from vc2_conformance.video_parameters import VideoParameters


MINIMAL_CODEC_FEATURES = CodecFeatures(
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
    dwt_depth=1,
    dwt_depth_ho=0,
    slices_x=2,
    slices_y=1,
    fragment_slice_count=0,
    lossless=False,
    picture_bytes=24,
    quantization_matrix=None,
)
"""
A set of minimal codec features. A progressive, 8x4, 8bit, 4:4:4, YCbCr format
with a single 2D Haar transform applied in two horizontal slices and 4:1
compression ratio.
"""
