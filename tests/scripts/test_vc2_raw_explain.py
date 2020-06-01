import pytest

import os

from fractions import Fraction

import subprocess

import shlex

import numpy as np

from PIL import Image

from vc2_data_tables import (
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    ColorDifferenceSamplingFormats,
    PictureCodingModes,
    SourceSamplingModes,
)

from vc2_conformance.pseudocode.video_parameters import VideoParameters

from vc2_conformance.file_format import write

from vc2_conformance.picture_generators import linear_ramps, moving_sprite

from vc2_conformance.scripts.vc2_raw_explain import (
    is_rgb_color,
    PICTURE_COMPONENT_NAMES,
    COLOR_DIFF_FORMAT_NAMES,
    CommandExplainer,
    explain_interleaving,
    explain_component_order_and_sampling,
    explain_component_sizes,
    explain_color_model,
    explain_pixel_aspect_ratio,
    UnsupportedPictureFormat,
    example_ffmpeg_command,
    example_imagemagick_command,
    explain_ffmpeg_command,
    explain_imagemagick_command,
    main,
)


def test_is_rgb_color():
    for matrix_index in PresetColorMatrices:
        expected = matrix_index == PresetColorMatrices.rgb
        vp = VideoParameters(color_matrix_index=matrix_index)
        assert is_rgb_color(vp) is expected


def test_all_component_names_listed():
    for matrix_index in PresetColorMatrices:
        assert matrix_index in PICTURE_COMPONENT_NAMES


def test_all_color_diff_format_names_listed():
    for format_index in ColorDifferenceSamplingFormats:
        assert format_index in COLOR_DIFF_FORMAT_NAMES


@pytest.mark.parametrize(
    "picture_coding_mode,source_sampling_mode,top_field_first,expected",
    [
        # Straight-forward modes where pictures correspond with the temporally
        # displayed blocks of image
        (
            PictureCodingModes.pictures_are_frames,
            SourceSamplingModes.progressive,
            True,
            "Each raw picture contains a whole frame.",
        ),
        (
            PictureCodingModes.pictures_are_fields,
            SourceSamplingModes.interlaced,
            True,
            "Each raw picture contains a single field. The top field comes first.",
        ),
        # Bottom-field first
        (
            PictureCodingModes.pictures_are_fields,
            SourceSamplingModes.interlaced,
            False,
            "Each raw picture contains a single field. The bottom field comes first.",
        ),
        # Contradictory picture coding and source sampling modes
        (
            PictureCodingModes.pictures_are_fields,
            SourceSamplingModes.progressive,
            True,
            "Each raw picture contains a single field (though the underlying video is progressive). The top field comes first.",
        ),
        (
            PictureCodingModes.pictures_are_frames,
            SourceSamplingModes.interlaced,
            True,
            "Each raw picture contains a whole frame (though the underlying video is interlaced). The top field comes first.",
        ),
    ],
)
def test_explain_interleaving(
    picture_coding_mode, source_sampling_mode, top_field_first, expected
):
    assert (
        explain_interleaving(
            VideoParameters(
                source_sampling=source_sampling_mode, top_field_first=top_field_first,
            ),
            picture_coding_mode,
        )
        == expected
    )


@pytest.mark.parametrize(
    "matrix,color_diff_format,expected",
    [
        (
            PresetColorMatrices.hdtv,
            ColorDifferenceSamplingFormats.color_4_4_4,
            "Pictures contain three planar components: Y, Cb and Cr, in that order, which are 4:4:4 subsampled.",
        ),
        (
            PresetColorMatrices.rgb,
            ColorDifferenceSamplingFormats.color_4_2_0,
            "Pictures contain three planar components: G, R and B, in that order, which are 4:2:0 subsampled.",
        ),
    ],
)
def test_explain_component_order_and_sampling(matrix, color_diff_format, expected):
    assert (
        explain_component_order_and_sampling(
            VideoParameters(
                color_matrix_index=matrix, color_diff_format_index=color_diff_format,
            ),
            PictureCodingModes.pictures_are_frames,
        )
        == expected
    )


@pytest.mark.parametrize(
    "video_parameters,expected",
    [
        # Sizes match, components all the same and match the bit width used in the
        # file format.
        (
            VideoParameters(
                frame_width=200,
                frame_height=100,
                color_matrix_index=PresetColorMatrices.rgb,
                color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
                luma_offset=0,
                luma_excursion=255,
                color_diff_offset=0,
                color_diff_excursion=255,
            ),
            "Each component consists of 200x50 8 bit values. Values run from 0 (video level 0.00) to 255 (video level 1.00).",
        ),
        # Components differ in size
        (
            VideoParameters(
                frame_width=200,
                frame_height=100,
                color_matrix_index=PresetColorMatrices.rgb,
                color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_0,
                luma_offset=0,
                luma_excursion=255,
                color_diff_offset=0,
                color_diff_excursion=255,
            ),
            (
                "The G component consists of 200x50 8 bit values. "
                "Values run from 0 (video level 0.00) to 255 (video level 1.00)."
                "\n\n"
                "The R and B components consist of 100x25 8 bit values. "
                "Values run from 0 (video level 0.00) to 255 (video level 1.00)."
            ),
        ),
        # Components differ in range
        (
            VideoParameters(
                frame_width=200,
                frame_height=100,
                color_matrix_index=PresetColorMatrices.hdtv,
                color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
                luma_offset=0,
                luma_excursion=255,
                color_diff_offset=128,
                color_diff_excursion=255,
            ),
            (
                "The Y component consists of 200x50 8 bit values. "
                "Values run from 0 (video level 0.00) to 255 (video level 1.00)."
                "\n\n"
                "The Cb and Cr components consist of 200x50 8 bit values. "
                "Values run from 0 (video level -0.50) to 255 (video level 0.50)."
            ),
        ),
        # Padded into larger bit depth
        (
            VideoParameters(
                frame_width=200,
                frame_height=100,
                color_matrix_index=PresetColorMatrices.hdtv,
                color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
                luma_offset=0,
                luma_excursion=1023,
                color_diff_offset=512,
                color_diff_excursion=1023,
            ),
            (
                "The Y component consists of 200x50 10 bit values "
                "stored as 16 bit (2 byte) values (with the 6 most "
                "significant bits set to 0) in little-endian byte order. "
                "Values run from 0 (video level 0.00) to 1023 (video level 1.00)."
                "\n\n"
                "The Cb and Cr components consist of 200x50 10 bit values "
                "stored as 16 bit (2 byte) values (with the 6 most "
                "significant bits set to 0) in little-endian byte order. "
                "Values run from 0 (video level -0.50) to 1023 (video level 0.50)."
            ),
        ),
        # Video-range signals
        (
            VideoParameters(
                frame_width=200,
                frame_height=100,
                color_matrix_index=PresetColorMatrices.hdtv,
                color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
                luma_offset=16,
                luma_excursion=219,
                color_diff_offset=128,
                color_diff_excursion=224,
            ),
            (
                "The Y component consists of 200x50 8 bit values. "
                "Values run from 0 (video level -0.07) to 255 (video level 1.09)."
                "\n\n"
                "The Cb and Cr components consist of 200x50 8 bit values. "
                "Values run from 0 (video level -0.57) to 255 (video level 0.57)."
            ),
        ),
    ],
)
def test_explain_component_sizes(video_parameters, expected):
    assert (
        explain_component_sizes(
            video_parameters, PictureCodingModes.pictures_are_fields,
        )
        == expected
    )


def test_explain_color_model():
    assert explain_color_model(
        VideoParameters(
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.hdtv,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
        ),
        PictureCodingModes.pictures_are_fields,
    ) == (
        "The color model uses the 'hdtv' primaries (ITU-R BT.709), "
        "the 'hdtv' color matrix (ITU-R BT.709) "
        "and the 'tv_gamma' transfer function (ITU-R BT.2020)."
    )


def test_explain_pixel_aspect_ratio():
    assert explain_pixel_aspect_ratio(
        VideoParameters(pixel_aspect_ratio_numer=4, pixel_aspect_ratio_denom=3,),
        PictureCodingModes.pictures_are_fields,
    ) == (
        "The pixel aspect ratio is 4:3 (not to be confused with the frame aspect ratio)."
    )


class TestCommandExplainer(object):
    def test_empty(self):
        c = CommandExplainer()
        assert c.command == ""
        assert c.explain() == ""

    def test_no_notes(self):
        c = CommandExplainer()
        c.append("foo bar")
        c.append("baz")
        assert c.command == "foo barbaz"
        assert c.explain() == "    foo barbaz"

    def test_note(self):
        c = CommandExplainer()
        c.append("foo bar")
        c.append(" baz", "an argument")
        assert c.command == "foo bar baz"
        assert c.explain() == (
            "    foo bar baz\n" "\n" "Where:\n" "\n" "* `baz` = an argument"
        )

    def test_strip(self):
        c = CommandExplainer()
        c.append("foo")
        c.append(" no strip ", "no strip", strip=False)
        c.append("|")
        c.append(" with strip ", "with strip", strip=True)
        c.append("| bar")
        assert c.command == "foo no strip | with strip | bar"
        assert c.explain() == (
            "    foo no strip | with strip | bar\n"
            "\n"
            "Where:\n"
            "\n"
            "* ` no strip ` = no strip\n"
            "* `with strip` = with strip"
        )


def write_pictures_to_dir(
    picture_generator, video_parameters, picture_coding_mode, dirname,
):
    """
    Take a set of pictures generated by ``picture_generator`` and write
    them as raw images to the specified directory.
    """
    for i, picture in enumerate(picture_generator):
        write(
            picture,
            video_parameters,
            picture_coding_mode,
            os.path.join(dirname, "picture_{}.raw".format(i),),
        )


def assert_plausibly_linear_ramps_image(frame, transfer_function_index):
    """
    Asserts that the supplied frame could plausibly contain the linear ramps
    image.
    """
    height, width, _ = frame.shape

    # Pull out a sample of the color ramps
    strip_height = height // 4
    ramps = frame[strip_height // 2 :: strip_height, :, :] / 255.0

    ramp_w = ramps[0, :, :]
    ramp_r = ramps[1, :, :]
    ramp_g = ramps[2, :, :]
    ramp_b = ramps[3, :, :]

    # Check for plausibility.
    #
    # * The primaries are not indicated to FFMPEG so we just need to check
    #   that the chosen primaries are at least "red-ish", "green-ish" and
    #   "blue-ish" -- we'll have to be super lax about this
    # * We basically don't even bother to check if the gamma curve has been
    #   chosen plauisbly. The assumption is that anybody working with a
    #   gamma curve sufficiently far from sRGB to notice will already know
    #   what the "wrong" gamma curve looks like and will immediately
    #   understand what has happened.
    # * If the color matrix comes in an order not expected by ffmpeg, or
    #   fundamentally of the wrong type (e.g. RGB vs Y C1 C2) the colours will
    #   be wildly wrong. Otherwise, the effect of using the wrong matrix
    #   just adds to the slightly wrong primary colours.
    #
    # On the basis of the super-slack requirements for plausibility we
    # allow the expected values to be quite far off (particularly for very
    # strong transfer functions)
    if transfer_function_index in (
        PresetTransferFunctions.hybrid_log_gamma,
        PresetTransferFunctions.perceptual_quantizer,
    ):
        atol = 0.35
    else:
        atol = 0.15

    # Left of image should be black
    assert np.all(np.isclose(ramps[:, 0, :], 0.0, atol=atol))

    # Right sides of curves should be roughly the right color
    assert np.isclose(ramp_w[-1, 0], 1.0, atol=atol)
    assert np.isclose(ramp_w[-1, 1], 1.0, atol=atol)
    assert np.isclose(ramp_w[-1, 2], 1.0, atol=atol)

    assert np.isclose(ramp_r[-1, 0], 1.0, atol=atol)
    assert np.isclose(ramp_r[-1, 1], 0.0, atol=atol)
    assert np.isclose(ramp_r[-1, 2], 0.0, atol=atol)

    assert np.isclose(ramp_g[-1, 0], 0.0, atol=atol)
    assert np.isclose(ramp_g[-1, 1], 1.0, atol=atol)
    assert np.isclose(ramp_g[-1, 2], 0.0, atol=atol)

    assert np.isclose(ramp_b[-1, 0], 0.0, atol=atol)
    assert np.isclose(ramp_b[-1, 1], 0.0, atol=atol)
    assert np.isclose(ramp_b[-1, 2], 1.0, atol=atol)


class TestExampleFFMPEGCommand(object):
    @pytest.fixture
    def video_parameters(self):
        # Sensible defaults
        return VideoParameters(
            frame_width=8,
            frame_height=8,
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            source_sampling=SourceSamplingModes.progressive,
            top_field_first=True,
            frame_rate_numer=1,
            frame_rate_denom=1,
            pixel_aspect_ratio_numer=1,
            pixel_aspect_ratio_denom=1,
            clean_width=1,
            clean_height=1,
            top_offset=0,
            left_offset=0,
            luma_offset=0,
            luma_excursion=1023,
            color_diff_offset=512,
            color_diff_excursion=1023,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.hdtv,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
        )

    def ffplay_to_ffmpeg(self, ffplay_command, dirname):
        """
        Given an ffplay command generated by example_ffmpeg_command, turn it
        into an FFMPEG command which outputs PNGs to the specified directory
        with names of the form "frame_%d.png".
        """
        assert ffplay_command.startswith("ffplay ")

        just_arguments = ffplay_command[len("ffplay") :]

        ffmpeg_command = "ffmpeg {} {}".format(
            just_arguments, os.path.join(dirname, "frame_%d.png"),
        )

        return ffmpeg_command

    def read_png_frames(self, dirname):
        """
        Read all of the frame_%d.png files from the specified directory.
        Returns an array of 3D numpy arrays.
        """
        out = []

        i = 1
        while True:
            filename = os.path.join(dirname, "frame_{}.png".format(i))
            if os.path.isfile(filename):
                out.append(np.array(Image.open(filename)))
                i += 1
            else:
                return out

    @pytest.mark.parametrize("picture_coding_mode", PictureCodingModes)
    @pytest.mark.parametrize("top_field_first", [True, False])
    def test_deinterlacing(
        self, video_parameters, picture_coding_mode, top_field_first, tmpdir,
    ):
        working_dir = str(tmpdir)

        # Make wide enough to fit the sprite's movement over 3 frames (the
        # sprite moves 16 pixels per frame)
        video_parameters["frame_width"] = 64
        video_parameters["source_sampling"] = SourceSamplingModes.interlaced
        video_parameters["top_field_first"] = top_field_first

        # Generate a series of frames in the specified format to disk in raw
        # format.
        write_pictures_to_dir(
            moving_sprite(video_parameters, picture_coding_mode, num_frames=3),
            video_parameters,
            picture_coding_mode,
            working_dir,
        )

        # Transcode to PNG format frames using FFMPEG
        ffplay_command = example_ffmpeg_command(
            os.path.join(working_dir, "picture_0.raw"),
            video_parameters,
            picture_coding_mode,
        ).command
        ffmpeg_command = self.ffplay_to_ffmpeg(ffplay_command, working_dir)
        subprocess.check_call(shlex.split(ffmpeg_command.replace("\\\n", " ")))

        # Read in PNGs
        frames = self.read_png_frames(working_dir)

        # Should have decoded into 3 frames
        assert len(frames) == 3

        # Check that the edge of the sprite is always in the expected location.
        # The moving_sprite function always moves the sprite right by 8 pixels
        # per field (or 16 pixels per frame) and starts at the top-left corner.
        for frame, expected_pixel_values in zip(
            frames[:3], [[1, 1, 1, 1, 1, 1], [0, 0, 1, 1, 1, 1], [0, 0, 0, 0, 1, 1]]
        ):
            xn = len(expected_pixel_values)  # number of sample points
            xs = 8  # x-axis spacing for sample points

            sample_points = frame[
                # Select only the top few pixels (to avoid the black circle) and
                # skip the first couple of lines (to avoid deinterlacer artefacts)
                2:6,
                # Sample in the middle of the area where we expect the sprite to
                # reside
                xs // 2 : (xs // 2) + (xn * xs) : xs,
                :,
            ]

            # Colour should match sample points (an odd and even line should be
            # tested to produce more helpful errors (otherwise the 'all sample
            # points should be identical vertically' test below will find mistakes
            # due to missing deinterlacing)
            assert np.array_equal(sample_points[0, :, 0] == 255, expected_pixel_values)
            assert np.array_equal(sample_points[1, :, 0] == 255, expected_pixel_values)

            # Sample points should be identical vertically
            assert np.all((sample_points[1:, :, :] == sample_points[:-1, :, :]))

            # Colour should be either white or black so all channels should be identical
            assert np.all((sample_points[:, :, 1:] == sample_points[:, :, :-1]))

    @pytest.mark.parametrize("source_sampling_mode", SourceSamplingModes)
    @pytest.mark.parametrize("picture_coding_mode", PictureCodingModes)
    @pytest.mark.parametrize("top_field_first", [True, False])
    def test_interlace_options(
        self,
        video_parameters,
        source_sampling_mode,
        picture_coding_mode,
        top_field_first,
        tmpdir,
    ):
        working_dir = str(tmpdir)

        # Make wide enough to fit the sprite's field movement of 8 pixels
        video_parameters["frame_width"] = 16
        # One of each scan line...
        video_parameters["frame_height"] = 2

        video_parameters["source_sampling"] = source_sampling_mode
        video_parameters["top_field_first"] = top_field_first

        # Generate a frame in the specified format
        write_pictures_to_dir(
            moving_sprite(video_parameters, picture_coding_mode, num_frames=1),
            video_parameters,
            picture_coding_mode,
            working_dir,
        )

        # Get FFMPEG command
        ffplay_command = example_ffmpeg_command(
            os.path.join(working_dir, "picture_0.raw"),
            video_parameters,
            picture_coding_mode,
        ).command
        ffmpeg_command = self.ffplay_to_ffmpeg(ffplay_command, working_dir)

        # Remove deinterlacing filter, if specified, to allow us to see the
        # interlacing which has taken place
        ffmpeg_command = ffmpeg_command.replace(",yadif", "")

        # Run FFMPEG
        subprocess.check_call(shlex.split(ffmpeg_command.replace("\\\n", " ")))

        # Read in PNG (should just be one)
        frames = self.read_png_frames(working_dir)
        assert len(frames) == 1

        frame = np.array(frames[0])

        if source_sampling_mode == SourceSamplingModes.interlaced:
            if top_field_first:
                expected_frame = np.array(
                    [
                        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                        [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
                    ]
                )
            else:
                expected_frame = np.array(
                    [
                        [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
                        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    ]
                )
        else:
            expected_frame = np.array(
                [
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                ]
            )

        expected_frame = np.repeat(expected_frame * 255, 3).reshape(frame.shape)

        assert np.array_equal(frame, expected_frame)

    @pytest.mark.parametrize("pixel_aspect_ratio", [Fraction(1, 1), Fraction(4, 3)])
    def test_pixel_aspect_ratio(
        self, video_parameters, pixel_aspect_ratio, tmpdir,
    ):
        working_dir = str(tmpdir)

        # Make wide enough to fit the whole sprite
        video_parameters["frame_width"] = 180
        video_parameters["frame_height"] = 160

        video_parameters["pixel_aspect_ratio_numer"] = pixel_aspect_ratio.numerator
        video_parameters["pixel_aspect_ratio_denom"] = pixel_aspect_ratio.denominator

        picture_coding_mode = PictureCodingModes.pictures_are_frames

        # Generate a single frame (with a known-square sprite, when scaled
        # correctly)
        write_pictures_to_dir(
            moving_sprite(video_parameters, picture_coding_mode, num_frames=1),
            video_parameters,
            picture_coding_mode,
            working_dir,
        )

        # Transcode to PNG format frames using FFMPEG
        ffplay_command = example_ffmpeg_command(
            os.path.join(working_dir, "picture_0.raw"),
            video_parameters,
            picture_coding_mode,
        ).command
        ffmpeg_command = self.ffplay_to_ffmpeg(ffplay_command, working_dir)
        subprocess.check_call(shlex.split(ffmpeg_command.replace("\\\n", " ")))

        # Read in PNG
        frames = self.read_png_frames(working_dir)
        assert len(frames) == 1
        frame = frames[0]

        # Check that image size reflects altered pixel aspect ratio
        h, w, _ = frame.shape
        assert w == video_parameters["frame_width"] * pixel_aspect_ratio
        assert h == video_parameters["frame_height"]

        # Check that the sprite is square following scaling
        ys, xs = np.nonzero(np.sum(frame, axis=2))

        sprite_width = np.max(xs) - np.min(xs) + 1
        sprite_height = np.max(ys) - np.min(ys) + 1

        assert np.isclose(sprite_width / sprite_height, 1.0, atol=0.01)

    def color_plausibility_test(
        self, video_parameters, picture_coding_mode, working_dir,
    ):
        # Check that under the specified set of video parameters,
        # example_ffmpeg_command either gives plausible FFMPEG settings or
        # raises UnsupportedPictureFormat.

        # Work out the command. This may not be possible due to an unsupported
        # format combination, hence we try this first and then skip the test if
        # necessary
        try:
            ffplay_command = example_ffmpeg_command(
                os.path.join(working_dir, "picture_0.raw"),
                video_parameters,
                picture_coding_mode,
            ).command
        except UnsupportedPictureFormat:
            return

        # Generate a single frame with horizontal linear color ramps.
        write_pictures_to_dir(
            linear_ramps(video_parameters, picture_coding_mode),
            video_parameters,
            picture_coding_mode,
            working_dir,
        )

        # Transcode to PNG format frames using FFMPEG
        ffmpeg_command = self.ffplay_to_ffmpeg(ffplay_command, working_dir)
        subprocess.check_call(shlex.split(ffmpeg_command.replace("\\\n", " ")))

        # Read in PNG
        frames = self.read_png_frames(working_dir)
        assert len(frames) == 1
        frame = frames[0]

        assert_plausibly_linear_ramps_image(
            frame, video_parameters["transfer_function_index"],
        )

    @pytest.mark.parametrize("primaries", PresetColorPrimaries)
    @pytest.mark.parametrize("matrix", PresetColorMatrices)
    @pytest.mark.parametrize("transfer_function", PresetTransferFunctions)
    @pytest.mark.parametrize("color_diff_format", ColorDifferenceSamplingFormats)
    def test_color(
        self,
        video_parameters,
        primaries,
        matrix,
        transfer_function,
        color_diff_format,
        tmpdir,
    ):
        # Make tall enough and wide enough that colour subsampling doesn't
        # completely destroy the image
        video_parameters["frame_width"] = 16
        video_parameters["frame_height"] = 16

        video_parameters["color_primaries_index"] = primaries
        video_parameters["color_matrix_index"] = matrix
        video_parameters["transfer_function_index"] = transfer_function
        video_parameters["color_diff_format_index"] = color_diff_format

        if matrix == PresetColorMatrices.rgb:
            video_parameters["color_diff_offset"] = 0

        picture_coding_mode = PictureCodingModes.pictures_are_frames

        self.color_plausibility_test(
            video_parameters, picture_coding_mode, str(tmpdir),
        )

    @pytest.mark.parametrize(
        "excursion",
        [(1 << picture_bit_width) - 1 for picture_bit_width in range(1, 16)],
    )
    @pytest.mark.parametrize(
        "matrix", [PresetColorMatrices.hdtv, PresetColorMatrices.rgb]
    )
    def test_bit_depth(
        self, video_parameters, excursion, matrix, tmpdir,
    ):
        # Make tall enough and wide enough that colour subsampling doesn't
        # completely destroy the image
        video_parameters["frame_width"] = 16
        video_parameters["frame_height"] = 16

        video_parameters["color_matrix_index"] = matrix

        video_parameters["luma_offset"] = 0
        video_parameters["luma_excursion"] = excursion
        video_parameters["color_diff_offset"] = (excursion + 1) // 2
        video_parameters["color_diff_excursion"] = excursion

        if matrix == PresetColorMatrices.rgb:
            video_parameters["color_diff_offset"] = 0

        picture_coding_mode = PictureCodingModes.pictures_are_frames

        self.color_plausibility_test(
            video_parameters, picture_coding_mode, str(tmpdir),
        )


class TestExampleImageMagickCommand(object):
    @pytest.fixture
    def video_parameters(self):
        # Sensible defaults
        return VideoParameters(
            frame_width=8,
            frame_height=8,
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            source_sampling=SourceSamplingModes.progressive,
            top_field_first=True,
            frame_rate_numer=1,
            frame_rate_denom=1,
            pixel_aspect_ratio_numer=1,
            pixel_aspect_ratio_denom=1,
            clean_width=1,
            clean_height=1,
            top_offset=0,
            left_offset=0,
            luma_offset=0,
            luma_excursion=255,
            color_diff_offset=128,
            color_diff_excursion=255,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.hdtv,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
        )

    def read_png_picture(self, raw_filename):
        """
        Read the PNG file associated with the specified raw picture file.
        Returns a 3D numpy array.
        """
        name = raw_filename.rpartition(".")[0]
        png_filename = "{}.png".format(name)

        im = Image.open(png_filename)
        return np.array(im)

    @pytest.mark.parametrize("pixel_aspect_ratio", [Fraction(1, 1), Fraction(4, 3)])
    def test_pixel_aspect_ratio(
        self, video_parameters, pixel_aspect_ratio, tmpdir,
    ):
        working_dir = str(tmpdir)

        # Make wide enough to fit the whole sprite
        video_parameters["frame_width"] = 180
        video_parameters["frame_height"] = 160

        video_parameters["pixel_aspect_ratio_numer"] = pixel_aspect_ratio.numerator
        video_parameters["pixel_aspect_ratio_denom"] = pixel_aspect_ratio.denominator

        picture_coding_mode = PictureCodingModes.pictures_are_frames

        # Generate a single frame (with a known-square sprite, when scaled
        # correctly)
        write_pictures_to_dir(
            moving_sprite(video_parameters, picture_coding_mode, num_frames=1),
            video_parameters,
            picture_coding_mode,
            working_dir,
        )

        # Convert to PNG format
        filename = os.path.join(working_dir, "picture_0.raw")
        convert_command = example_imagemagick_command(
            filename, video_parameters, picture_coding_mode,
        ).command
        subprocess.check_call(shlex.split(convert_command.replace("\\\n", " ")))

        # Read in PNG
        frame = self.read_png_picture(filename)

        # Check that image size reflects altered pixel aspect ratio
        h, w, _ = frame.shape
        assert w == video_parameters["frame_width"] * pixel_aspect_ratio
        assert h == video_parameters["frame_height"]

        # Check that the sprite is square following scaling (NB: ImageMagick
        # introduces some minor errors in decoding black so we use a simple
        # threshold of 'anything less than 10' is black to work around this)
        ys, xs = np.nonzero(np.sum(frame, axis=2) > 10)

        sprite_width = np.max(xs) - np.min(xs) + 1
        sprite_height = np.max(ys) - np.min(ys) + 1

        assert np.isclose(sprite_width / sprite_height, 1.0, atol=0.01)

    def color_plausibility_test(
        self, video_parameters, picture_coding_mode, working_dir,
    ):
        # Check that under the specified set of video parameters,
        # example_ffmpeg_command either gives plausible ImageMagick settings or
        # raises UnsupportedPictureFormat.

        # Work out the command. This may not be possible due to an unsupported
        # format combination, hence we try this first and then skip the test if
        # necessary
        try:
            filename = os.path.join(working_dir, "picture_0.raw")
            convert_command = example_imagemagick_command(
                filename, video_parameters, picture_coding_mode,
            ).command
        except UnsupportedPictureFormat:
            return

        # Generate a single frame with horizontal linear color ramps.
        write_pictures_to_dir(
            linear_ramps(video_parameters, picture_coding_mode),
            video_parameters,
            picture_coding_mode,
            working_dir,
        )

        # Transcode to PNG format frames using ImageMagick
        subprocess.check_call(shlex.split(convert_command.replace("\\\n", " ")))

        # Read in PNG
        frame = self.read_png_picture(filename)

        assert_plausibly_linear_ramps_image(
            frame, video_parameters["transfer_function_index"],
        )

    @pytest.mark.parametrize("primaries", PresetColorPrimaries)
    @pytest.mark.parametrize("matrix", PresetColorMatrices)
    @pytest.mark.parametrize("transfer_function", PresetTransferFunctions)
    @pytest.mark.parametrize("color_diff_format", ColorDifferenceSamplingFormats)
    def test_color(
        self,
        video_parameters,
        primaries,
        matrix,
        transfer_function,
        color_diff_format,
        tmpdir,
    ):
        # Make tall enough and wide enough that colour subsampling doesn't
        # completely destroy the image
        video_parameters["frame_width"] = 32
        video_parameters["frame_height"] = 16

        video_parameters["color_primaries_index"] = primaries
        video_parameters["color_matrix_index"] = matrix
        video_parameters["transfer_function_index"] = transfer_function
        video_parameters["color_diff_format_index"] = color_diff_format

        if matrix == PresetColorMatrices.rgb:
            video_parameters["color_diff_offset"] = 0

        picture_coding_mode = PictureCodingModes.pictures_are_frames

        self.color_plausibility_test(
            video_parameters, picture_coding_mode, str(tmpdir),
        )

    @pytest.mark.parametrize(
        "excursion",
        [(1 << picture_bit_width) - 1 for picture_bit_width in range(1, 16)],
    )
    @pytest.mark.parametrize(
        "matrix", [PresetColorMatrices.hdtv, PresetColorMatrices.rgb]
    )
    def test_bit_depth(
        self, video_parameters, excursion, matrix, tmpdir,
    ):
        # Make tall enough and wide enough that colour subsampling doesn't
        # completely destroy the image
        video_parameters["frame_width"] = 16
        video_parameters["frame_height"] = 16

        video_parameters["color_matrix_index"] = matrix

        video_parameters["luma_offset"] = 0
        video_parameters["luma_excursion"] = excursion
        video_parameters["color_diff_offset"] = (excursion + 1) // 2
        video_parameters["color_diff_excursion"] = excursion

        if matrix == PresetColorMatrices.rgb:
            video_parameters["color_diff_offset"] = 0

        picture_coding_mode = PictureCodingModes.pictures_are_frames

        self.color_plausibility_test(
            video_parameters, picture_coding_mode, str(tmpdir),
        )


@pytest.mark.parametrize(
    "explain", [explain_ffmpeg_command, explain_imagemagick_command]
)
@pytest.mark.parametrize(
    "matrix,expect_supported",
    [(PresetColorMatrices.hdtv, True), (PresetColorMatrices.reversible, False)],
)
def test_explain_ffmpeg_and_imagemagick_commands(
    explain, matrix, expect_supported,
):
    video_parameters = VideoParameters(
        frame_width=8,
        frame_height=8,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_numer=1,
        frame_rate_denom=1,
        pixel_aspect_ratio_numer=1,
        pixel_aspect_ratio_denom=1,
        clean_width=1,
        clean_height=1,
        top_offset=0,
        left_offset=0,
        luma_offset=0,
        luma_excursion=255,
        color_diff_offset=128,
        color_diff_excursion=255,
        color_primaries_index=PresetColorPrimaries.hdtv,
        color_matrix_index=matrix,
        transfer_function_index=PresetTransferFunctions.tv_gamma,
    )

    picture_coding_mode = PictureCodingModes.pictures_are_frames

    explanation = explain("foo.raw", video_parameters, picture_coding_mode)

    if expect_supported:
        assert "$ " in explanation
        assert not explanation.startswith("No")
    else:
        assert "$ " not in explanation
        assert explanation.startswith("No")


@pytest.mark.parametrize("extension", ["raw", "json"])
def test_cli(tmpdir, capsys, extension):
    working_dir = str(tmpdir)

    # Generate a test picture
    video_parameters = VideoParameters(
        frame_width=8,
        frame_height=8,
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
        source_sampling=SourceSamplingModes.progressive,
        top_field_first=True,
        frame_rate_numer=1,
        frame_rate_denom=1,
        pixel_aspect_ratio_numer=1,
        pixel_aspect_ratio_denom=1,
        clean_width=1,
        clean_height=1,
        top_offset=0,
        left_offset=0,
        luma_offset=0,
        luma_excursion=255,
        color_diff_offset=128,
        color_diff_excursion=255,
        color_primaries_index=PresetColorPrimaries.hdtv,
        color_matrix_index=PresetColorMatrices.hdtv,
        transfer_function_index=PresetTransferFunctions.tv_gamma,
    )
    picture_coding_mode = PictureCodingModes.pictures_are_frames
    write_pictures_to_dir(
        linear_ramps(video_parameters, picture_coding_mode),
        video_parameters,
        picture_coding_mode,
        working_dir,
    )

    # Shouldn't crash...
    filename = os.path.join(working_dir, "picture_0.{}".format(extension))
    assert main([filename]) == 0

    stdout, stderr = capsys.readouterr()

    assert stderr == ""

    # Look for signs of an explanation
    assert "Each raw picture contains a whole frame." in stdout

    # Look for signs of an FFMPEG command (using the correct file)
    raw_file_pattern = os.path.join(working_dir, "picture_%d.raw")
    assert raw_file_pattern in stdout

    # Look for signs of an ImageMagick command (using the correct file)
    raw_file_filename = os.path.join(working_dir, "picture_0.raw")
    png_file_filename = os.path.join(working_dir, "picture_0.png")
    assert raw_file_filename in stdout
    assert png_file_filename in stdout
