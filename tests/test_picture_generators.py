import pytest

import os

import numpy as np

from fractions import Fraction

from itertools import cycle

from smaller_real_pictures import (
    TEST_PICTURES_PATHS,
    replace_real_pictures_with_test_pictures,
)

from vc2_data_tables import (
    ColorDifferenceSamplingFormats,
    PictureCodingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    SourceSamplingModes,
)

from vc2_conformance.video_parameters import VideoParameters

from vc2_conformance.color_conversion import (
    to_xyz,
    matmul_colors,
    XYZ_TO_LINEAR_RGB,
)

from vc2_conformance.file_format import compute_dimensions_and_depths

from vc2_conformance_data import NATURAL_PICTURES_FILENAMES

from vc2_conformance.picture_generators import (
    POINTER_SPRITE_PATH,
    read_as_xyz,
    resize,
    read_as_xyz_to_fit,
    seconds_to_samples,
    progressive_to_interlaced,
    progressive_to_split_fields,
    interleave_fields,
    progressive_to_pictures,
    xyz_to_native,
    pipe,
    read_and_adapt_pointer_sprite,
    repeat_pictures,
    real_pictures,
    moving_sprite,
    static_sprite,
    mid_gray,
    linear_ramps,
)


def test_sprite_image_path():
    # Indirectly test by checking that the pointer sprite filename is
    # accessible
    assert os.path.isfile(POINTER_SPRITE_PATH)


def test_read_as_xyz():
    # Test on the well-defined pointer sprite
    xyz, video_parameters, picture_coding_mode = read_as_xyz(POINTER_SPRITE_PATH)
    
    assert xyz.shape == (128, 128, 3)
    assert xyz.dtype == float
    
    # Top-left corner of square
    assert np.all(xyz[0, 0, :] > [0.5, 0.5, 0.5])
    
    # Within black circle
    assert np.array_equal(xyz[32, 32, :], [0, 0, 0])
    
    # Video format should roughly match expectations
    assert video_parameters["color_diff_format_index"] == ColorDifferenceSamplingFormats.color_4_4_4
    assert video_parameters["color_matrix_index"] == PresetColorMatrices.rgb
    assert picture_coding_mode == PictureCodingModes.pictures_are_frames


def test_resize():
    # A fairly crude test: a test picture which looks like:
    #
    #     R  G  B
    #   RRRRRRRRRRR
    #     R  G  B
    #   GGGGGGGGGGG
    #     R  G  B
    #   BBBBBBBBBBB
    #     R  G  B
    
    test_image = np.zeros((140, 140, 3), dtype=float)
    test_image[:, 20:40, 0] = 1.0
    test_image[:, 60:80, 1] = 1.0
    test_image[:, 100:120, 2] = 1.0
    test_image[20:40, :, 0] = 1.0
    test_image[60:80, :, 1] = 1.0
    test_image[100:120, :, 2] = 1.0
    
    new_image = resize(test_image, 70, 35)
    
    expected_image = np.zeros((35, 70, 3), dtype=float)
    expected_image[:, 10:20, 0] = 1.0
    expected_image[:, 30:40, 1] = 1.0
    expected_image[:, 50:60, 2] = 1.0
    expected_image[5:10, :, 0] = 1.0
    expected_image[15:20, :, 1] = 1.0
    expected_image[25:30, :, 2] = 1.0
    
    # Crude image similarity check...
    assert np.sum(np.abs(new_image - expected_image)) / expected_image.size < 0.02


@pytest.mark.parametrize("filename", TEST_PICTURES_PATHS)
@pytest.mark.parametrize("width,height", [
    (160, 160),
    (190, 160),
    (160, 190),
])
@pytest.mark.parametrize("pixel_aspect_ratio", [
    Fraction(1, 1),
    Fraction(4, 3),
])
def test_read_as_xyz_to_fit(filename, width, height, pixel_aspect_ratio):
    image = read_as_xyz_to_fit(filename, width, height, pixel_aspect_ratio)
    
    # Test images should be desired shape
    assert image.shape == (height, width, 3)
    
    # Image should contain a single, centered square
    ys, xs = np.nonzero(np.sum(image, axis=2))
    
    # Square is in center
    cx = np.mean(xs)
    cy = np.mean(ys)
    assert np.isclose(cx, width / 2.0, atol=1.0)
    assert np.isclose(cy, height / 2.0, atol=1.0)
    
    # Shape is square given the current pixel aspect ratio
    sw = np.max(xs) - np.min(xs)
    sh = np.max(ys) - np.min(ys)
    shape_aspect_ratio = float(sw) / float(sh)
    assert np.isclose(
        shape_aspect_ratio,
        1.0/pixel_aspect_ratio,
        atol=0.05,
    )


def test_seconds_to_samples():
    vp = VideoParameters(
        frame_rate_numer=10,
        frame_rate_denom=1,
        source_sampling=SourceSamplingModes.progressive,
    )
    assert seconds_to_samples(vp, 0) == (1, 1)
    assert seconds_to_samples(vp, 0.1) == (1, 1)
    assert seconds_to_samples(vp, 0.2) == (2, 1)
    assert seconds_to_samples(vp, 10) == (100, 1)
    assert seconds_to_samples(vp, 10.00001) == (100, 1)
    assert seconds_to_samples(vp, 9.99999) == (100, 1)
    
    vp["source_sampling"] = SourceSamplingModes.interlaced
    assert seconds_to_samples(vp, 0) == (2, 2)
    assert seconds_to_samples(vp, 0.1) == (2, 2)
    assert seconds_to_samples(vp, 0.15) == (4, 2)
    assert seconds_to_samples(vp, 0.2) == (4, 2)
    assert seconds_to_samples(vp, 10) == (200, 2)


def test_progressive_to_interlaced():
    pictures = [
        np.arange(4*6*3).reshape(4, 6, 3) * 1,
        np.arange(4*6*3).reshape(4, 6, 3) * 10,
        np.arange(4*6*3).reshape(4, 6, 3) * 100,
        np.arange(4*6*3).reshape(4, 6, 3) * 1000,
    ]
    
    vp = VideoParameters(top_field_first=True)
    pcm = PictureCodingModes.pictures_are_fields
    expected = [
        pictures[0][0::2, :, :],
        pictures[1][1::2, :, :],
        pictures[2][0::2, :, :],
        pictures[3][1::2, :, :],
    ]
    actual = iter(progressive_to_interlaced(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []
    
    vp["top_field_first"] = False
    expected = [
        pictures[0][1::2, :, :],
        pictures[1][0::2, :, :],
        pictures[2][1::2, :, :],
        pictures[3][0::2, :, :],
    ]
    actual = iter(progressive_to_interlaced(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []


def test_progressive_to_split_fields():
    pictures = [
        np.arange(4*6*3).reshape(4, 6, 3) * 1,
        np.arange(4*6*3).reshape(4, 6, 3) * 10,
        np.arange(4*6*3).reshape(4, 6, 3) * 100,
        np.arange(4*6*3).reshape(4, 6, 3) * 1000,
    ]
    
    vp = VideoParameters(top_field_first=True)
    pcm = PictureCodingModes.pictures_are_fields
    expected = [
        pictures[0][0::2, :, :],
        pictures[0][1::2, :, :],
        pictures[1][0::2, :, :],
        pictures[1][1::2, :, :],
        pictures[2][0::2, :, :],
        pictures[2][1::2, :, :],
        pictures[3][0::2, :, :],
        pictures[3][1::2, :, :],
    ]
    actual = iter(progressive_to_split_fields(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []
    
    vp["top_field_first"] = False
    expected = [
        pictures[0][1::2, :, :],
        pictures[0][0::2, :, :],
        pictures[1][1::2, :, :],
        pictures[1][0::2, :, :],
        pictures[2][1::2, :, :],
        pictures[2][0::2, :, :],
        pictures[3][1::2, :, :],
        pictures[3][0::2, :, :],
    ]
    actual = iter(progressive_to_split_fields(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []


def test_interleave_fields():
    pictures = [
        np.arange(4*6*3).reshape(4, 6, 3) * 1,
        np.arange(4*6*3).reshape(4, 6, 3) * 10,
        np.arange(4*6*3).reshape(4, 6, 3) * 100,
        np.arange(4*6*3).reshape(4, 6, 3) * 1000,
    ]
    
    vp = VideoParameters(top_field_first=True)
    pcm = PictureCodingModes.pictures_are_fields
    expected = [
        np.stack(list(zip(pictures[0], pictures[1])), axis=0).reshape(8, 6, 3),
        np.stack(list(zip(pictures[2], pictures[3])), axis=0).reshape(8, 6, 3),
    ]
    actual = iter(interleave_fields(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []
    
    vp["top_field_first"] = False
    expected = [
        np.stack(list(zip(pictures[1], pictures[0])), axis=0).reshape(8, 6, 3),
        np.stack(list(zip(pictures[3], pictures[2])), axis=0).reshape(8, 6, 3),
    ]
    actual = iter(interleave_fields(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []


def test_progressive_to_pictures():
    pictures = [
        np.arange(4*6*3).reshape(4, 6, 3) * 1,
        np.arange(4*6*3).reshape(4, 6, 3) * 10,
        np.arange(4*6*3).reshape(4, 6, 3) * 100,
        np.arange(4*6*3).reshape(4, 6, 3) * 1000,
    ]
    
    # Progressive, pictures are frames
    vp = VideoParameters(
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
    )
    pcm = PictureCodingModes.pictures_are_frames
    expected = pictures
    actual = iter(progressive_to_pictures(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []
    
    # Progressive, pictures are fields
    vp = VideoParameters(
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
    )
    pcm = PictureCodingModes.pictures_are_fields
    expected = [
        pictures[0][0::2, :, :],
        pictures[0][1::2, :, :],
        pictures[1][0::2, :, :],
        pictures[1][1::2, :, :],
        pictures[2][0::2, :, :],
        pictures[2][1::2, :, :],
        pictures[3][0::2, :, :],
        pictures[3][1::2, :, :],
    ]
    actual = iter(progressive_to_pictures(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []
    
    # Interlaced, pictures are frames
    vp = VideoParameters(
        source_sampling=SourceSamplingModes.interlaced,
        top_field_first=True,
    )
    pcm = PictureCodingModes.pictures_are_frames
    expected = [
        np.stack(list(zip(pictures[0][0::2, :, :], pictures[1][1::2, :, :])), axis=0).reshape(4, 6, 3),
        np.stack(list(zip(pictures[2][0::2, :, :], pictures[3][1::2, :, :])), axis=0).reshape(4, 6, 3),
    ]
    actual = iter(progressive_to_pictures(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []
    
    # Interlaced, pictures are fields
    vp = VideoParameters(
        source_sampling=SourceSamplingModes.interlaced,
        top_field_first=True,
    )
    pcm = PictureCodingModes.pictures_are_fields
    expected = [
        pictures[0][0::2, :, :],
        pictures[1][1::2, :, :],
        pictures[2][0::2, :, :],
        pictures[3][1::2, :, :],
    ]
    actual = iter(progressive_to_pictures(vp, pcm, pictures))
    for e in expected:
        assert np.array_equal(next(actual), e)
    assert list(actual) == []


def test_xyz_to_native():
    xyz, vp, pcm = read_as_xyz(POINTER_SPRITE_PATH)
    
    pictures = [
        xyz,
        xyz,
    ]
    
    actual = iter(xyz_to_native(vp, pcm, pictures))
    for pic_num, _ in enumerate(pictures):
        picture = next(actual)
        assert picture["pic_num"] == pic_num
        
        g = picture["Y"]
        b = picture["C1"]
        r = picture["C2"]
        
        # Tip of triangle
        assert r[0][0] == 255
        assert g[0][0] == 255
        assert b[0][0] == 255
        
        # Hole in triangle
        assert r[32][32] == 0
        assert g[32][32] == 0
        assert b[32][32] == 0
        
        # Bottom of blue '2'
        assert r[127][125] == 0
        assert g[127][125] == 0
        assert b[127][125] == 255
    assert list(actual) == []


def test_pipe():
    vp = VideoParameters(
        source_sampling=SourceSamplingModes.interlaced,
        top_field_first=True,
    )
    pcm = PictureCodingModes.pictures_are_frames
    
    def repeat_pictures(video_parameters, picture_coding_mode, iterable):
        assert video_parameters == vp
        assert picture_coding_mode == pcm
        for picture in iterable:
            yield picture
            yield picture
    
    @pipe(repeat_pictures)
    def picture_generator(video_parameters, picture_coding_mode, values):
        assert video_parameters == vp
        assert picture_coding_mode == pcm
        
        for value in values:
            yield value * 10
    
    assert list(picture_generator(vp, pcm, [1, 2, 3])) == [10, 10, 20, 20, 30, 30]


class TestReadAndAdaptPointerSprite(object):

    def test_pixel_aspect_ratio(self):
        video_parameters = VideoParameters(
            color_primaries_index=PresetColorPrimaries.uhdtv,
            pixel_aspect_ratio_numer=4,
            pixel_aspect_ratio_denom=3,
        )
        
        xyz = read_and_adapt_pointer_sprite(video_parameters)
        
        # Check aspect ratio
        h, w, _ = xyz.shape
        assert 4 * w == 3 * h
    
    def test_primaries(self):
        video_parameters = VideoParameters(
            color_primaries_index=PresetColorPrimaries.uhdtv,
            pixel_aspect_ratio_numer=1,
            pixel_aspect_ratio_denom=1,
        )
        
        xyz = read_and_adapt_pointer_sprite(video_parameters)
        
        # Check color primaries
        rgb = matmul_colors(XYZ_TO_LINEAR_RGB[
            video_parameters["color_primaries_index"]
        ], xyz)
        
        # Top left is native white
        assert np.all(np.isclose(rgb[0, 0, :], [1.0, 1.0, 1.0], rtol=0.001))
        
        # Hole centre is native black
        assert np.all(np.isclose(rgb[32, 32, :], [0.0, 0.0, 0.0], rtol=0.001))
        
        # 'V' is native red
        assert np.all(np.isclose(rgb[126, 56, :], [1.0, 0.0, 0.0], rtol=0.001))
        
        # 'C' is native green
        assert np.all(np.isclose(rgb[126, 79, :], [0.0, 1.0, 0.0], rtol=0.001))
        
        # '2' is native blue
        assert np.all(np.isclose(rgb[126, 118, :], [0.0, 0.0, 1.0], rtol=0.001))


class TestRepeatPictures(object):
    
    @pytest.fixture
    def pictures(self):
        return [
            {"Y": [[11]], "C1": [[21]], "C2": [[31]], "pic_num": 0},
            {"Y": [[12]], "C1": [[22]], "C2": [[32]], "pic_num": 1},
            {"Y": [[13]], "C1": [[23]], "C2": [[33]], "pic_num": 2},
        ]
    
    def test_zero_repeats(self, pictures):
        assert list(repeat_pictures(iter(pictures), 0)) == []
    
    def test_one_repeat(self, pictures):
        assert list(repeat_pictures(iter(pictures), 1)) == pictures
    
    def test_multiple_repeats(self, pictures):
        repeated = list(repeat_pictures(iter(pictures), 3))
        
        assert len(repeated) == len(pictures) * 3
        
        # Check repeated
        for orig, new in zip(cycle(pictures), repeated):
            assert orig["Y"] == new["Y"]
            assert orig["C1"] == new["C1"]
            assert orig["C2"] == new["C2"]
        
        # Check picture numbers consecutive
        assert [p["pic_num"] for p in repeated] == list(range(len(repeated)))


class TestMovingSprite(object):
    
    @pytest.fixture
    def video_parameters(self):
        return VideoParameters(
            frame_width=200,
            frame_height=200,
            frame_rate_numer=1,
            frame_rate_denom=1,
            pixel_aspect_ratio_numer=1,
            pixel_aspect_ratio_denom=1,
            source_sampling=SourceSamplingModes.progressive,
            top_field_first=True,
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.hdtv,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
            luma_offset=0,
            luma_excursion=255,
            color_diff_offset=128,
            color_diff_excursion=255,
        )
    
    # top_corner_pixels[picture_no][line_no][x_coord_div_8] = expected_value_div_255
    @pytest.mark.parametrize("source_sampling_mode,picture_coding_mode,top_corner_pixels", [
        (
            SourceSamplingModes.progressive,
            PictureCodingModes.pictures_are_frames,
            [
                (
                    [1, 1, 1, 1],
                    [1, 1, 1, 1]
                ),
                (
                    [0, 0, 1, 1],
                    [0, 0, 1, 1]
                ),
                (
                    [0, 0, 0, 0],
                    [0, 0, 0, 0]
                ),
            ]
        ),
        (
            SourceSamplingModes.progressive,
            PictureCodingModes.pictures_are_fields,
            [
                (
                    [1, 1, 1, 1],
                    [1, 1, 1, 1]
                ),
                (
                    [1, 1, 1, 1],
                    [1, 1, 1, 1]
                ),
                (
                    [0, 0, 1, 1],
                    [0, 0, 1, 1]
                ),
                (
                    [0, 0, 1, 1],
                    [0, 0, 1, 1]
                ),
                (
                    [0, 0, 0, 0],
                    [0, 0, 0, 0]
                ),
                (
                    [0, 0, 0, 0],
                    [0, 0, 0, 0]
                ),
            ]
        ),
        (
            SourceSamplingModes.interlaced,
            PictureCodingModes.pictures_are_frames,
            [
                (
                    [1, 1, 1, 1],
                    [0, 1, 1, 1]
                ),
                (
                    [0, 0, 1, 1],
                    [0, 0, 0, 1]
                ),
                (
                    [0, 0, 0, 0],
                    [0, 0, 0, 0]
                ),
            ]
        ),
        (
            SourceSamplingModes.interlaced,
            PictureCodingModes.pictures_are_fields,
            [
                (
                    [1, 1, 1, 1],
                    [1, 1, 1, 1]
                ),
                (
                    [0, 1, 1, 1],
                    [0, 1, 1, 1]
                ),
                (
                    [0, 0, 1, 1],
                    [0, 0, 1, 1]
                ),
                (
                    [0, 0, 0, 1],
                    [0, 0, 0, 1]
                ),
                (
                    [0, 0, 0, 0],
                    [0, 0, 0, 0]
                ),
                (
                    [0, 0, 0, 0],
                    [0, 0, 0, 0]
                ),
            ]
        ),
    ])
    def test_movement_interlacing(
        self,
        video_parameters,
        source_sampling_mode,
        picture_coding_mode,
        top_corner_pixels,
    ):
        """Check that the sprite moves correctly in all scan/coding modes."""
        video_parameters["source_sampling"] = source_sampling_mode
        pictures = iter(moving_sprite(video_parameters, picture_coding_mode, 3))
        
        for rows in top_corner_pixels:
            y = np.array(next(pictures)["Y"])
            
            # Check top-left pixels have expected values
            assert np.array_equal(y[0:2, 0:4*8:8], np.array(rows)*255)
            
        assert list(pictures) == []


@pytest.mark.parametrize("primaries", PresetColorPrimaries)
@pytest.mark.parametrize("transfer_function", PresetTransferFunctions)
def test_mid_gray(primaries, transfer_function):
    vp = VideoParameters(
        frame_width=10,
        frame_height=5,
        frame_rate_numer=1,
        frame_rate_denom=1,
        pixel_aspect_ratio_numer=1,
        pixel_aspect_ratio_denom=1,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
        # The choice of primaries and transfer function should have no effect:
        # the color should be chosen at the code level, not the color model
        # level
        color_primaries_index=primaries,
        color_matrix_index=PresetColorMatrices.hdtv,
        transfer_function_index=transfer_function,
        # Set two wonky off-center ranges; the offsets should be ignored with the
        # 'mid grey' being the middle of the code range
        luma_offset=20,
        luma_excursion=150,
        color_diff_offset=100,
        color_diff_excursion=900,
    )
    
    pictures = list(mid_gray(vp, PictureCodingModes.pictures_are_frames))
    assert len(pictures) == 1
    
    picture = pictures[0]
    y = np.array(picture["Y"])
    c1 = np.array(picture["C1"])
    c2 = np.array(picture["C2"])
    
    assert np.array_equal(y, np.full(y.shape, 128))
    
    assert np.array_equal(c1, np.full(c1.shape, 512))
    assert np.array_equal(c2, np.full(c2.shape, 512))


@pytest.mark.parametrize("primaries", PresetColorPrimaries)
@pytest.mark.parametrize("transfer_function", PresetTransferFunctions)
def test_linear_ramps(primaries, transfer_function):
    vp = VideoParameters(
        frame_width=32,
        frame_height=16,
        frame_rate_numer=1,
        frame_rate_denom=1,
        pixel_aspect_ratio_numer=1,
        pixel_aspect_ratio_denom=1,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
        color_primaries_index=primaries,
        color_matrix_index=PresetColorMatrices.rgb,
        transfer_function_index=transfer_function,
        luma_offset=0,
        luma_excursion=255,
        color_diff_offset=0,
        color_diff_excursion=255,
    )
    
    pictures = list(linear_ramps(vp, PictureCodingModes.pictures_are_frames))
    assert len(pictures) == 1
    g = np.array(pictures[0]["Y"])
    b = np.array(pictures[0]["C1"])
    r = np.array(pictures[0]["C2"])
    
    rgb = np.stack([r, g, b], axis=-1) / 255.0
    
    assert np.all(np.isclose(rgb[0, 0, :], [0, 0, 0], rtol=0.05))
    assert np.all(np.isclose(rgb[0, 30, :], [1, 1, 1], rtol=0.05))
    
    assert np.all(np.isclose(rgb[4, 0, :], [0, 0, 0], rtol=0.05))
    assert np.all(np.isclose(rgb[4, 30, :], [1, 0, 0], rtol=0.05))
    
    assert np.all(np.isclose(rgb[8, 0, :], [0, 0, 0], rtol=0.05))
    assert np.all(np.isclose(rgb[8, 30, :], [0, 1, 0], rtol=0.05))
    
    assert np.all(np.isclose(rgb[12, 0, :], [0, 0, 0], rtol=0.05))
    assert np.all(np.isclose(rgb[12, 30, :], [0, 0, 1], rtol=0.05))
    
    # Whites should be pure whites
    for c1 in range(3):
        for c2 in range(3):
            assert np.all(np.isclose(rgb[0, :, c1], rgb[0, :, c2], atol=0.05))
    
    # Colours should be pure primaries
    assert np.all(rgb[4:8, :, [1, 2]] == 0)
    assert np.all(rgb[8:12, :, [0, 2]] == 0)
    assert np.all(rgb[12:16, :, [0, 1]] == 0)
    
    # Bands should contain same values throughout
    assert np.all(rgb[0::4, :, :] == rgb[1::4, :, :])
    assert np.all(rgb[0::4, :, :] == rgb[2::4, :, :])
    assert np.all(rgb[0::4, :, :] == rgb[3::4, :, :])
    
    if transfer_function == PresetTransferFunctions.linear:
        # Should be perfectly linear
        assert np.all(np.isclose(rgb[0, :, 0], np.linspace(0, 1, 32), atol=0.05))
        assert np.all(np.isclose(rgb[4, :, 0], np.linspace(0, 1, 32), atol=0.05))
        assert np.all(np.isclose(rgb[8, :, 1], np.linspace(0, 1, 32), atol=0.05))
        assert np.all(np.isclose(rgb[12, :, 2], np.linspace(0, 1, 32), atol=0.05))
    else:
        # Should be monotonic for other transfer functions, at least
        assert np.all((rgb[0, 1:, 0] - rgb[0, :-1, 0]) >= 0)
        assert np.all((rgb[4, 1:, 0] - rgb[0, :-1, 0]) >= 0)
        assert np.all((rgb[8, 1:, 1] - rgb[0, :-1, 0]) >= 0)
        assert np.all((rgb[12, 1:, 2] - rgb[0, :-1, 0]) >= 0)


class TestGenericPictureGeneratorBehaviour(object):
    
    @pytest.fixture(params=[
        real_pictures,
        moving_sprite,
        static_sprite,
        mid_gray,
        linear_ramps,
        lambda *a, **kw: repeat_pictures(mid_gray(*a, **kw), 2),
    ])
    def picture_generator(self, request, replace_real_pictures_with_test_pictures):
        return request.param
    
    @pytest.fixture
    def vp(self):
        return VideoParameters(
            frame_width=16,
            frame_height=8,
            frame_rate_numer=1,
            frame_rate_denom=1,
            pixel_aspect_ratio_numer=1,
            pixel_aspect_ratio_denom=1,
            source_sampling=SourceSamplingModes.progressive,
            top_field_first=True,
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.hdtv,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
            luma_offset=0,
            luma_excursion=255,
            color_diff_offset=128,
            color_diff_excursion=255,
        )
    
    @pytest.mark.parametrize("ssm", SourceSamplingModes)
    @pytest.mark.parametrize("pcm", PictureCodingModes)
    def test_produces_correct_dict_type(self, picture_generator, vp, ssm, pcm):
        vp["source_sampling"] = ssm
        
        for picture in list(picture_generator(vp, pcm)):
            assert isinstance(picture["Y"], list)
            assert isinstance(picture["Y"][0], list)
            assert type(picture["Y"][0][0]) is int
            
            assert isinstance(picture["C1"], list)
            assert isinstance(picture["C1"][0], list)
            assert type(picture["C1"][0][0]) is int
            
            assert isinstance(picture["C2"], list)
            assert isinstance(picture["C2"][0], list)
            assert type(picture["C2"][0][0]) is int
            
            assert isinstance(picture["pic_num"], int)
    
    @pytest.mark.parametrize("ssm", SourceSamplingModes)
    @pytest.mark.parametrize("pcm", PictureCodingModes)
    def test_produces_whole_number_of_frames(self, picture_generator, vp, ssm, pcm):
        vp["source_sampling"] = ssm
        
        pictures = list(picture_generator(vp, pcm))
        if pcm == PictureCodingModes.pictures_are_frames:
            assert len(pictures) >= 1
        else:
            # Must have even number of frames
            assert len(pictures) >= 2
            assert (len(pictures) % 2) == 0
            
            # Even/odd fields must have even/odd picture numbers
            for i, picture in enumerate(pictures):
                assert (picture["pic_num"] % 2) == (i % 2)
            
        # Picture numbers must be consecutive
        last_num = pictures[0]["pic_num"]
        for picture in pictures[1:]:
            assert picture["pic_num"] == last_num + 1
            last_num += 1
    
    @pytest.mark.parametrize("ssm", SourceSamplingModes)
    @pytest.mark.parametrize("pcm", PictureCodingModes)
    @pytest.mark.parametrize("cds", ColorDifferenceSamplingFormats)
    def test_produces_correct_picture_sizes(self, picture_generator, vp, ssm, pcm, cds):
        vp["source_sampling"] = ssm
        vp["color_diff_format_index"] = cds
        
        picture = list(picture_generator(vp, pcm))[0]
        y = np.array(picture["Y"])
        c1 = np.array(picture["C1"])
        c2 = np.array(picture["C2"])
        
        dd = compute_dimensions_and_depths(vp, pcm)
        
        assert y.shape == (dd["Y"].height, dd["Y"].width)
        assert c1.shape == (dd["C1"].height, dd["C1"].width)
        assert c2.shape == (dd["C2"].height, dd["C2"].width)
    
    @pytest.mark.parametrize("width,height", [(1, 1), (1, 10), (10, 1)])
    def test_supports_absurd_video_sizes(self, picture_generator, vp, width, height):
        # Should produce a couple of frames for multi-frame generators
        vp["frame_rate_numer"] = 2
        vp["frame_rate_denom"] = 1
        
        vp["frame_width"] = width
        vp["frame_height"] = height
        
        pcm = PictureCodingModes.pictures_are_frames
        
        # Mustn't crash...
        list(picture_generator(vp, pcm))
