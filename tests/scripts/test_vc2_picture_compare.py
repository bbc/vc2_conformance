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

from vc2_conformance.pseudocode.video_parameters import VideoParameters

from vc2_conformance.scripts.vc2_picture_compare import (
    read_pictures_with_only_one_metadata_file_required,
    video_parameter_diff,
    picture_coding_mode_diff,
    picture_number_diff,
    psnr,
    measure_differences,
    generate_difference_mask_picture,
    compare_pictures,
    enumerate_directories,
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
            np.full((height, width), pixel_values, dtype=np.int64),
            np.full((height // 2, width // 2), pixel_values, dtype=np.int64),
            np.full((height // 2, width // 2), pixel_values, dtype=np.int64),
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
        color_diff_offset=1 << (color_diff_bit_width - 1),
        color_diff_excursion=(1 << color_diff_bit_width) - 1,
        color_primaries_index=PresetColorPrimaries.hdtv,
        color_matrix_index=PresetColorMatrices.hdtv,
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
    assert (
        picture_coding_mode_diff(
            PictureCodingModes.pictures_are_fields,
            PictureCodingModes.pictures_are_frames,
        )
        == ("- pictures_are_fields (1)\n" "+ pictures_are_frames (0)")
    )


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


class TestGenerateDifferenceMaskPicture(object):
    @pytest.fixture
    def video_parameters(self):
        return VideoParameters(
            frame_width=4,
            frame_height=4,
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            source_sampling=SourceSamplingModes.progressive,
            top_field_first=True,
            frame_rate_numer=1,
            frame_rate_denom=1,
            pixel_aspect_ratio_numer=1,
            pixel_aspect_ratio_denom=1,
            clean_width=4,
            clean_height=4,
            left_offset=0,
            top_offset=0,
            luma_offset=0,
            luma_excursion=1023,
            color_diff_offset=512,
            color_diff_excursion=1023,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.hdtv,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
        )

    def test_color_4_4_4(self, video_parameters, tmpdir):
        video_parameters[
            "color_diff_format_index"
        ] = ColorDifferenceSamplingFormats.color_4_4_4

        deltas = {
            "Y": np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0], [1, 0, 0, 0]]),
            "C1": np.array([[1, 1, 1, 0], [1, 1, 0, 1], [0, 0, 0, 0], [0, 0, 0, 0]]),
            "C2": np.array([[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]),
        }

        mask = generate_difference_mask_picture(deltas, video_parameters, 100)

        write(
            mask,
            video_parameters,
            PictureCodingModes.pictures_are_frames,
            str(tmpdir.join("out.raw")),
        )

        assert mask["Y"].tolist() == [
            [1023, 1023, 1023, 0],
            [1023, 1023, 0, 1023],
            [0, 1023, 0, 1023],
            [1023, 0, 1023, 0],
        ]
        assert mask["C1"].tolist() == [
            [512, 512, 512, 512],
            [512, 512, 512, 512],
            [512, 512, 512, 512],
            [512, 512, 512, 512],
        ]
        assert mask["C2"].tolist() == [
            [512, 512, 512, 512],
            [512, 512, 512, 512],
            [512, 512, 512, 512],
            [512, 512, 512, 512],
        ]

        assert mask["pic_num"] == 100

    def test_color_4_2_2(self, video_parameters, tmpdir):
        video_parameters[
            "color_diff_format_index"
        ] = ColorDifferenceSamplingFormats.color_4_2_2

        deltas = {
            "Y": np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0], [1, 0, 0, 0]]),
            "C1": np.array([[1, 1], [1, 0], [0, 0], [0, 0]]),
            "C2": np.array([[1, 0], [1, 0], [0, 1], [0, 0]]),
        }

        mask = generate_difference_mask_picture(deltas, video_parameters, 100)

        write(
            mask,
            video_parameters,
            PictureCodingModes.pictures_are_frames,
            str(tmpdir.join("out.raw")),
        )

        assert mask["Y"].tolist() == [
            [1023, 1023, 1023, 1023],
            [1023, 1023, 0, 0],
            [0, 1023, 1023, 1023],
            [1023, 0, 0, 0],
        ]
        assert mask["C1"].tolist() == [
            [512, 512],
            [512, 512],
            [512, 512],
            [512, 512],
        ]
        assert mask["C2"].tolist() == [
            [512, 512],
            [512, 512],
            [512, 512],
            [512, 512],
        ]

        assert mask["pic_num"] == 100

    def test_color_4_2_0(self, video_parameters, tmpdir):
        video_parameters[
            "color_diff_format_index"
        ] = ColorDifferenceSamplingFormats.color_4_2_0

        deltas = {
            "Y": np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0], [1, 0, 0, 0]]),
            "C1": np.array([[1, 1], [0, 0]]),
            "C2": np.array([[1, 0], [0, 1]]),
        }

        mask = generate_difference_mask_picture(deltas, video_parameters, 100)

        write(
            mask,
            video_parameters,
            PictureCodingModes.pictures_are_frames,
            str(tmpdir.join("out.raw")),
        )

        assert mask["Y"].tolist() == [
            [1023, 1023, 1023, 1023],
            [1023, 1023, 1023, 1023],
            [0, 1023, 1023, 1023],
            [1023, 0, 1023, 1023],
        ]
        assert mask["C1"].tolist() == [
            [512, 512],
            [512, 512],
        ]
        assert mask["C2"].tolist() == [
            [512, 512],
            [512, 512],
        ]

        assert mask["pic_num"] == 100

    def test_rgb(self, video_parameters, tmpdir):
        video_parameters[
            "color_diff_format_index"
        ] = ColorDifferenceSamplingFormats.color_4_4_4
        video_parameters["color_matrix_index"] = PresetColorMatrices.rgb
        video_parameters["luma_offset"] = 0
        video_parameters["color_diff_offset"] = 0

        deltas = {
            "Y": np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0], [1, 0, 0, 0]]),
            "C1": np.array([[1, 1, 1, 0], [1, 1, 0, 1], [0, 0, 0, 0], [0, 0, 0, 0]]),
            "C2": np.array([[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]),
        }

        mask = generate_difference_mask_picture(deltas, video_parameters, 100)

        write(
            mask,
            video_parameters,
            PictureCodingModes.pictures_are_frames,
            str(tmpdir.join("out.raw")),
        )

        assert mask["Y"].tolist() == [
            [1023, 1023, 1023, 0],
            [1023, 1023, 0, 1023],
            [0, 1023, 0, 1023],
            [1023, 0, 1023, 0],
        ]
        assert mask["C1"].tolist() == [
            [1023, 1023, 1023, 0],
            [1023, 1023, 0, 1023],
            [0, 1023, 0, 1023],
            [1023, 0, 1023, 0],
        ]
        assert mask["C2"].tolist() == [
            [1023, 1023, 1023, 0],
            [1023, 1023, 0, 1023],
            [0, 1023, 0, 1023],
            [1023, 0, 1023, 0],
        ]

        assert mask["pic_num"] == 100

    def test_video_range(self, video_parameters, tmpdir):
        video_parameters[
            "color_diff_format_index"
        ] = ColorDifferenceSamplingFormats.color_4_4_4
        video_parameters["luma_offset"] = 16
        video_parameters["luma_excursion"] = 219
        video_parameters["color_diff_offset"] = 128
        video_parameters["color_diff_excursion"] = 224

        deltas = {
            "Y": np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0], [1, 0, 0, 0]]),
            "C1": np.array([[1, 1, 1, 0], [1, 1, 0, 1], [0, 0, 0, 0], [0, 0, 0, 0]]),
            "C2": np.array([[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]),
        }

        mask = generate_difference_mask_picture(deltas, video_parameters, 100)

        write(
            mask,
            video_parameters,
            PictureCodingModes.pictures_are_frames,
            str(tmpdir.join("out.raw")),
        )

        assert mask["Y"].tolist() == [
            [235, 235, 235, 16],
            [235, 235, 16, 235],
            [16, 235, 16, 235],
            [235, 16, 235, 16],
        ]
        assert mask["C1"].tolist() == [
            [128, 128, 128, 128],
            [128, 128, 128, 128],
            [128, 128, 128, 128],
            [128, 128, 128, 128],
        ]
        assert mask["C2"].tolist() == [
            [128, 128, 128, 128],
            [128, 128, 128, 128],
            [128, 128, 128, 128],
            [128, 128, 128, 128],
        ]

        assert mask["pic_num"] == 100


class TestEnumerateDirectories(object):
    @pytest.fixture
    def make_directories(self, tmpdir):
        def make_directories(filenames_a, filenames_b):
            dir_a = tmpdir.join("a")
            dir_b = tmpdir.join("b")

            os.mkdir(str(dir_a))
            os.mkdir(str(dir_b))

            for filename in filenames_a:
                open(str(dir_a.join(filename)), "w").close()
            for filename in filenames_b:
                open(str(dir_b.join(filename)), "w").close()

            return (str(dir_a), str(dir_b))

        return make_directories

    def test_unnumbered_raw_file(self, make_directories, capsys):
        dir_a, dir_b = make_directories(["foo.raw"], ["pic_1.raw"])
        with pytest.raises(SystemExit):
            enumerate_directories(dir_a, dir_b)

        out, err = capsys.readouterr()
        assert err.startswith("Error: An unnumbered file was found:")
        assert "foo.raw" in err

    def test_reused_numbers(self, make_directories, capsys):
        dir_a, dir_b = make_directories(["foo_123.raw", "bar_123.raw"], ["pic_123.raw"])
        with pytest.raises(SystemExit):
            enumerate_directories(dir_a, dir_b)

        out, err = capsys.readouterr()
        assert err.startswith("Error: More than one filename with number 123")
        assert dir_a in err

    @pytest.mark.parametrize(
        "filenames_a,filenames_b",
        [
            ([], []),
            (["pic_1.raw"], []),
            ([], ["pic_1.raw"]),
        ],
    )
    def test_empty_directory(self, make_directories, filenames_a, filenames_b, capsys):
        dir_a, dir_b = make_directories(filenames_a, filenames_b)
        with pytest.raises(SystemExit):
            enumerate_directories(dir_a, dir_b)

        out, err = capsys.readouterr()
        assert err.startswith("Error: No pictures found")

    def test_mismatched_numbers(self, make_directories, capsys):
        dir_a, dir_b = make_directories(
            ["pic_100.raw", "pic_200.raw", "pic_300.raw"],
            ["pic_200.raw", "pic_300.raw", "pic_400.raw"],
        )
        with pytest.raises(SystemExit):
            enumerate_directories(dir_a, dir_b)

        out, err = capsys.readouterr()
        assert err.startswith(
            "Error: Pictures numbered 100, 400 found in only one directory"
        )

    def test_matches_files_together_correctly(self, make_directories, capsys):
        dir_a, dir_b = make_directories(
            ["pic_1.raw", "pic_100.raw"], ["picture_1.raw", "picture_100.raw"]
        )
        assert enumerate_directories(dir_a, dir_b) == [
            (os.path.join(dir_a, "pic_1.raw"), os.path.join(dir_b, "picture_1.raw")),
            (
                os.path.join(dir_a, "pic_100.raw"),
                os.path.join(dir_b, "picture_100.raw"),
            ),
        ]

    def test_ignores_non_raw_files(self, make_directories, capsys):
        dir_a, dir_b = make_directories(
            ["pic_1.raw", "foo.xyz", "bar.xyz"], ["pic_1.raw", "bar.xyz", "baz.xyz"]
        )
        files = enumerate_directories(dir_a, dir_b)
        assert len(files) == 1
        assert files[0][0].endswith("pic_1.raw")
        assert files[0][1].endswith("pic_1.raw")


class TestComparePictures(object):
    def test_video_parameters_different(self, tmpdir):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa, 100, width=16, height=8)
        generate_picture(fb, 200, width=32, height=16)

        out, exitcode = compare_pictures(fa, fb)
        assert exitcode == 1
        assert "Video parameters are different" in out
        assert "- frame_width" in out

    def test_picture_coding_mode_different(self, tmpdir):
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

        out, exitcode = compare_pictures(fa, fb)
        assert exitcode == 2
        assert "Picture coding modes are different" in out
        assert "- pictures_are_fields" in out
        assert "+ pictures_are_frames" in out

    def test_picture_numbers_different(self, tmpdir):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa, picture_number=100)
        generate_picture(fb, picture_number=200)

        out, exitcode = compare_pictures(fa, fb)
        assert exitcode == 3
        assert "Picture numbers are different" in out
        assert "- 100" in out
        assert "+ 200" in out

    def test_pixels_are_different(self, tmpdir):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa, 100)
        generate_picture(fb, 200)

        out, exitcode = compare_pictures(fa, fb)
        assert exitcode == 4
        assert "Pictures are different" in out
        assert "Y: Different" in out
        assert "C1: Different" in out
        assert "C2: Different" in out

    def test_identical(self, tmpdir):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa)
        generate_picture(fb)

        out, exitcode = compare_pictures(fa, fb)
        assert exitcode == 0
        assert "Pictures are identical" in out
        assert "Warning" not in out

    def test_identical_but_different_padding(self, tmpdir):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))

        generate_picture(fa)
        generate_picture(fb)

        # Write something non-zero in the padding bits of one file
        with open(fa, "rb+") as f:
            f.seek(1)
            f.write(bytearray([0xF0]))

        out, exitcode = compare_pictures(fa, fb)
        assert exitcode == 0
        assert "Pictures are identical" in out
        assert "Warning: Padding bits in raw picture data are different" in out

    def test_difference_mask(self, tmpdir):
        fa = str(tmpdir.join("a.raw"))
        fb = str(tmpdir.join("b.raw"))
        mask_filename = str(tmpdir.join("mask.raw"))

        generate_picture(
            fa,
            (
                np.array([[0, 1, 2, 3], [4, 5, 6, 7]]),
                np.array([[8, 9]]),
                np.array([[10, 11]]),
            ),
            picture_number=123,
        )
        generate_picture(
            fb,
            (
                np.array([[0, 1, 2, 4], [4, 5, 7, 7]]),
                np.array([[9, 9]]),
                np.array([[10, 11]]),
            ),
            picture_number=123,
        )

        out, exitcode = compare_pictures(fa, fb, mask_filename)
        assert exitcode == 4
        assert "Pictures are different" in out

        picture, video_parameters, picture_coding_mode = read(mask_filename)

        # Mask should be as expected
        assert picture["Y"] == [[1023, 1023, 0, 1023], [1023, 1023, 1023, 0]]
        assert picture["C1"] == [[512, 512]]
        assert picture["C2"] == [[512, 512]]

        # Should match input picture numbers
        assert picture["pic_num"] == 123

        # Should match format of input pictures
        _, video_parameters_a, picture_coding_mode_a = read(fa)
        assert video_parameters == video_parameters_a
        assert picture_coding_mode == picture_coding_mode_a


class TestMain(object):
    def test_files_no_difference_mask(self, tmpdir, capsys):
        fa = os.path.join(str(tmpdir), "a.raw")
        fb = os.path.join(str(tmpdir), "b.raw")

        generate_picture(fa, 100, width=16, height=8)
        generate_picture(fb, 200, width=32, height=16)

        assert main([fa, fb]) == 1
        out, err = capsys.readouterr()
        assert "Video parameters are different" in out
        assert "- frame_width" in out

    def test_files_with_difference_mask(self, tmpdir, capsys):
        fa = os.path.join(str(tmpdir), "a.raw")
        fb = os.path.join(str(tmpdir), "b.raw")
        fd = os.path.join(str(tmpdir), "d.raw")

        generate_picture(fa)
        generate_picture(fb)

        assert main([fa, fb, "--difference-mask", fd]) == 0
        out, err = capsys.readouterr()
        assert "Pictures are identical" in out
        assert os.path.isfile(fd)

    @pytest.mark.parametrize("a_is_dir", [True, False])
    def test_directories_mixed_with_files(self, tmpdir, capsys, a_is_dir):
        if a_is_dir:
            fa = os.path.join(str(tmpdir), "a")
            os.mkdir(fa)
            generate_picture(os.path.join(fa, "pic_0.raw"))

            fb = os.path.join(str(tmpdir), "b.raw")
            generate_picture(fb)
        else:
            fa = os.path.join(str(tmpdir), "a.raw")
            generate_picture(fa)

            fb = os.path.join(str(tmpdir), "b")
            os.mkdir(fb)
            generate_picture(os.path.join(fb, "pic_0.raw"))

        assert main([fa, fb]) == 103
        out, err = capsys.readouterr()
        assert "must both be files" in err

    def test_directories_with_difference_mask(self, tmpdir, capsys):
        da = os.path.join(str(tmpdir), "a")
        db = os.path.join(str(tmpdir), "b")
        fd = os.path.join(str(tmpdir), "d")
        os.mkdir(da)
        os.mkdir(db)
        generate_picture(os.path.join(da, "pic_0.raw"))
        generate_picture(os.path.join(db, "pic_0.raw"))

        assert main([da, db, "--difference-mask", fd]) == 104
        out, err = capsys.readouterr()
        assert "may only be used when files" in err

    def test_comparing_multiple_files(self, tmpdir, capsys):
        da = os.path.join(str(tmpdir), "a")
        db = os.path.join(str(tmpdir), "b")
        os.mkdir(da)
        os.mkdir(db)

        generate_picture(os.path.join(da, "a_pic_0.raw"))
        generate_picture(os.path.join(db, "b_pic_0.raw"))

        generate_picture(os.path.join(da, "a_pic_1.raw"), pixel_values=0)
        generate_picture(os.path.join(db, "b_pic_1.raw"), pixel_values=1)

        generate_picture(os.path.join(da, "a_pic_2.raw"))
        generate_picture(os.path.join(db, "b_pic_2.raw"))

        assert main([da, db]) == 4
        out, err = capsys.readouterr()
        assert out == (
            "Comparing {} and {}:\n"
            "  Pictures are identical\n"
            "Comparing {} and {}:\n"
            "  Pictures are different:\n"
            "    Y: Different: PSNR = 60.2 dB, 32 pixels (100.0%) differ\n"
            "    C1: Different: PSNR = 60.2 dB, 8 pixels (100.0%) differ\n"
            "    C2: Different: PSNR = 60.2 dB, 8 pixels (100.0%) differ\n"
            "Comparing {} and {}:\n"
            "  Pictures are identical\n"
            "Summary: 2 identical, 1 different\n"
        ).format(
            os.path.join(da, "a_pic_0.raw"),
            os.path.join(db, "b_pic_0.raw"),
            os.path.join(da, "a_pic_1.raw"),
            os.path.join(db, "b_pic_1.raw"),
            os.path.join(da, "a_pic_2.raw"),
            os.path.join(db, "b_pic_2.raw"),
        )
