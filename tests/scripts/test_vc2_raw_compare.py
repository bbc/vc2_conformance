import pytest

import os

import numpy as np

from vc2_data_tables import (
    PictureCodingModes,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
)

from vc2_conformance.file_format import read, write

from vc2_conformance.video_parameters import VideoParameters

from vc2_conformance.scripts.vc2_raw_compare import (
    read_pictures_with_only_one_metadata_file_required,
    video_parameter_diff,
    picture_coding_mode_diff,
    picture_number_diff,
    psnr,
    measure_differences,
    main,
)


def generate_picture(
    filename,
    pixel_values=0,
    picture_number=0,
    bit_width=10,
    luma_bit_width=None,
    color_diff_bit_width=None,
    picture_coding_mode=PictureCodingModes.pictures_are_fields,
    width=8,
    height=4,
):
    """
    Generate a 4:2:0 color subsampled raw picture with the specified file name.

    Parameters
    ==========
    filename : str
        Filename to write the raw picture to.
    pixel_values : int or (2D-array, 2D-array, 2D-array)
        If an integer, a ``width`` x ``height`` picture with all pixel values
        set to that value will be generated.

        If a set of three 2D arrays, uses these for the picture. The second and
        third arrays must be exactly half the width and height of the first.
    picture_number: int
        The VC-2 picture number.
    bit_width : int
        Bit depth for pixel values.
    luma_bit_width : int
        Bit depth for luma pixel values (overrides bit_width).
    color_diff_bit_width : int
        Bit depth for color difference pixel values (overrides bit_width).
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
        The picture coding mode to use.
    width, height : int
        The dimensions of the picture to generate (not the frame dimensions).
        Ignored if pixel_values is given.
    """
    if isinstance(pixel_values, int):
        pixel_values = (
            np.full((height, width), pixel_values, dtype=int),
            np.full((height // 2, width // 2), pixel_values, dtype=int),
            np.full((height // 2, width // 2), pixel_values, dtype=int),
        )
    else:
        pixel_values = (
            np.array(pixel_values[0]),
            np.array(pixel_values[1]),
            np.array(pixel_values[2]),
        )
        height, width = pixel_values[0].shape
        assert pixel_values[1].shape == (height // 2, width // 2)
        assert pixel_values[2].shape == (height // 2, width // 2)

    if luma_bit_width is None:
        luma_bit_width = bit_width
    if color_diff_bit_width is None:
        color_diff_bit_width = bit_width

    if picture_coding_mode == PictureCodingModes.pictures_are_fields:
        height *= 2

    video_parameters = VideoParameters(
        frame_width=width,
        frame_height=height,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_numer=1,
        frame_rate_denom=1,
        pixel_aspect_ratio_numer=1,
        pixel_aspect_ratio_denom=1,
        clean_width=width,
        clean_height=height,
        left_offset=0,
        top_offset=0,
        luma_offset=0,
        luma_excursion=(1 << luma_bit_width) - 1,
        color_diff_offset=0,
        color_diff_excursion=(1 << color_diff_bit_width) - 1,
        color_primaries_index=PresetColorPrimaries.hdtv,
        color_matrix_index=PresetColorMatrices.rgb,
        transfer_function_index=PresetTransferFunctions.tv_gamma,
    )

    picture = {
        "Y": pixel_values[0],
        "C1": pixel_values[1],
        "C2": pixel_values[2],
        "pic_num": picture_number,
    }

    write(picture, video_parameters, picture_coding_mode, filename)


class TestReadPicturesWithOnlyOneMetadataFileRequired(object):
    def test_two_files_with_metadata(self, tmpdir):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa, 100, width=16, height=8)
        generate_picture(fb, 200, width=32, height=16)

        (
            picture_a,
            picture_b,
            byte_for_byte_identical,
        ) = read_pictures_with_only_one_metadata_file_required(fa, fb)

        assert picture_a == read(fa)
        assert picture_b == read(fb)

    @pytest.mark.parametrize("to_remove", ["a.json", "b.json"])
    def test_two_files_one_metadata(self, tmpdir, capsys, to_remove):
        fa = str(tmpdir.join("a.json"))
        fb = str(tmpdir.join("b.json"))

        generate_picture(fa, 100)
        generate_picture(fb, 200)
        os.remove(str(tmpdir.join(to_remove)))

        (
            picture_a,
            picture_b,
            byte_for_byte_identical,
        ) = read_pictures_with_only_one_metadata_file_required(fa, fb)

        assert picture_a[0]["Y"][0][0] == 100
        assert picture_b[0]["Y"][0][0] == 200

        assert picture_a[1:] == picture_b[1:]

        out, err = capsys.readouterr()

        if to_remove == "a.json":
            assert "Metadata missing for first picture." in err
        elif to_remove == "b.json":
            assert "Metadata missing for second picture." in err

    def test_no_metadata(self, tmpdir, capsys):
        fa = str(tmpdir.join("a.json"))
        fb = str(tmpdir.join("b.json"))

        generate_picture(fa)
        generate_picture(fb)

        os.remove(fa)
        os.remove(fb)

        with pytest.raises(SystemExit):
            read_pictures_with_only_one_metadata_file_required(fa, fb)

        out, err = capsys.readouterr()
        assert "both pictures" in err

    @pytest.mark.parametrize("to_remove", ["a.raw", "b.raw"])
    def test_missing_pictures(self, tmpdir, capsys, to_remove):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa)
        generate_picture(fb)

        os.remove(str(tmpdir.join(to_remove)))

        with pytest.raises(SystemExit):
            read_pictures_with_only_one_metadata_file_required(fa, fb)

        out, err = capsys.readouterr()
        if to_remove == "a.raw":
            assert "Could not open first picture" in err
        elif to_remove == "b.raw":
            assert "Could not open second picture" in err

    @pytest.mark.parametrize("to_remove", ["a.json", "b.json"])
    def test_mismatched_raw_size(self, tmpdir, capsys, to_remove):
        fa = str(tmpdir.join("a.json"))
        fb = str(tmpdir.join("b.json"))

        generate_picture(fa, width=16, height=8)
        generate_picture(fb, width=32, height=16)

        os.remove(str(tmpdir.join(to_remove)))

        with pytest.raises(SystemExit):
            read_pictures_with_only_one_metadata_file_required(fa, fb)

        out, err = capsys.readouterr()
        if to_remove == "a.json":
            assert "First picture file has incorrect size" in err
        elif to_remove == "b.json":
            assert "Second picture file has incorrect size" in err

    def test_byte_for_byte_identical(self, tmpdir):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa, bit_width=10)
        generate_picture(fb, bit_width=10)

        (
            picture_a_1,
            picture_b_1,
            byte_for_byte_identical,
        ) = read_pictures_with_only_one_metadata_file_required(fa, fb)

        assert byte_for_byte_identical

        # Write something non-zero in the padding bits of one file
        with open(fa, "rb+") as f:
            f.seek(1)
            f.write(bytearray([0xF0]))

        (
            picture_a_2,
            picture_b_2,
            byte_for_byte_identical,
        ) = read_pictures_with_only_one_metadata_file_required(fa, fb)

        # Difference should be detected
        assert not byte_for_byte_identical

        # Pictures should be identical
        assert picture_a_1 == picture_a_2
        assert picture_b_1 == picture_b_2


def test_video_parameter_diff():
    assert video_parameter_diff(
        VideoParameters(
            frame_height=1080,
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            top_field_first=True,
        ),
        VideoParameters(
            frame_width=1920,
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
            top_field_first=True,
        ),
    ) == (
        "+ frame_width: 1920\n"
        "- frame_height: 1080\n"
        "- color_diff_format_index: color_4_4_4 (0)\n"
        "+ color_diff_format_index: color_4_2_2 (1)\n"
        "  top_field_first: True"
    )


def test_picture_coding_mode_diff():
    assert picture_coding_mode_diff(
        PictureCodingModes.pictures_are_fields, PictureCodingModes.pictures_are_frames,
    ) == ("- pictures_are_fields (1)\n" "+ pictures_are_frames (0)")


def test_picture_number_diff():
    assert picture_number_diff(123, 321) == ("- 123\n" "+ 321")


class TestPSNR(object):
    def test_identical(self):
        assert psnr(np.array([[0, 0], [0, 0]]), 100) is None

    def test_different(self):
        assert np.isclose(
            psnr(np.array([[-10, 10], [10, -10]]), 1000),
            10 * (np.log(1000 ** 2 / 10 ** 2) / np.log(10)),
        )


class TestMeasureDifferences(object):
    @pytest.fixture
    def video_parameters(self):
        return VideoParameters(
            frame_width=2,
            frame_height=2,
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
            luma_offset=0,
            luma_excursion=(1 << 8) - 1,
            color_diff_offset=0,
            color_diff_excursion=(1 << 10) - 1,
        )

    @pytest.fixture
    def picture_coding_mode(self):
        return PictureCodingModes.pictures_are_frames

    def test_identical(self, video_parameters, picture_coding_mode):
        all_deltas = {
            "Y": np.array([[0, 0], [0, 0]]),
            "C1": np.array([[0]]),
            "C2": np.array([[0]]),
        }
        identical, differences = measure_differences(
            all_deltas, video_parameters, picture_coding_mode
        )

        assert identical
        assert differences == ("Y: Identical\n" "C1: Identical\n" "C2: Identical")

    def test_different(self, video_parameters, picture_coding_mode):
        all_deltas = {
            "Y": np.array([[100, -100], [0, 0]]),
            "C1": np.array([[500]]),
            "C2": np.array([[0]]),
        }
        identical, differences = measure_differences(
            all_deltas, video_parameters, picture_coding_mode
        )

        assert not identical
        assert differences == (
            "Y: Different: PSNR = 11.1 dB, 2 pixels (50.0%) differ\n"
            "C1: Different: PSNR = 6.2 dB, 1 pixel (100.0%) differs\n"
            "C2: Identical"
        )


class TestMain(object):
    def test_video_parameters_different(self, tmpdir, capsys):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa, 100, width=16, height=8)
        generate_picture(fb, 200, width=32, height=16)

        assert main([fa, fb]) == 1
        out, err = capsys.readouterr()
        assert "Video parameters are different" in out
        assert "- frame_width" in out

    def test_picture_coding_mode_different(self, tmpdir, capsys):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        # NB: Different frame heights to ensure same picture height
        generate_picture(
            fa,
            100,
            height=4,
            picture_coding_mode=PictureCodingModes.pictures_are_fields,
        )
        generate_picture(
            fb,
            200,
            height=8,
            picture_coding_mode=PictureCodingModes.pictures_are_frames,
        )

        assert main([fa, fb]) == 2
        out, err = capsys.readouterr()
        assert "Picture coding modes are different" in out
        assert "- pictures_are_fields" in out
        assert "+ pictures_are_frames" in out

    def test_picture_numbers_different(self, tmpdir, capsys):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa, picture_number=100)
        generate_picture(fb, picture_number=200)

        assert main([fa, fb]) == 3
        out, err = capsys.readouterr()
        assert "Picture numbers are different" in out
        assert "- 100" in out
        assert "+ 200" in out

    def test_pixels_are_different(self, tmpdir, capsys):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa, 100)
        generate_picture(fb, 200)

        assert main([fa, fb]) == 4
        out, err = capsys.readouterr()
        assert "Pictures are different" in out
        assert "Y: Different" in out
        assert "C1: Different" in out
        assert "C2: Different" in out

    def test_identical(self, tmpdir, capsys):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa)
        generate_picture(fb)

        assert main([fa, fb]) == 0
        out, err = capsys.readouterr()
        assert "Pictures are identical" in out
        assert "Warning" not in out

    def test_identical_but_different_padding(self, tmpdir, capsys):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa)
        generate_picture(fb)

        # Write something non-zero in the padding bits of one file
        with open(fa, "rb+") as f:
            f.seek(1)
            f.write(bytearray([0xF0]))

        assert main([fa, fb]) == 0
        out, err = capsys.readouterr()
        assert "Pictures are identical" in out
        assert "Warning: Padding bits in raw picture data are different" in out
