"""
The :py:mod:`vc2_conformance.picture_generators` module contains routines for
generating video sequences for arbitrary VC-2 video formats.

The picture generators in this module are used to generate encoder and decoder
test cases (:py:mod:`vc2_conformance.test_cases`).

All picture generator functions take a
:py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`, and
:py:class:`~vc2_data_tables.PictureCodingModes` as their arguments, defining the
desired VC-2 video format. They then yield a sequence of ``{"Y": [[int, ...],
...], "C1": [[int, ...], ...], "C2": [[int, ...], ...], "pic_num": int}``
dictionaries containing integer picture component values, ready for encoding or
writing to a file.

The following picture generators are provided.

.. autofunction:: moving_sprite

.. autofunction:: static_sprite

.. autofunction:: mid_gray

.. autofunction:: white_noise

.. autofunction:: linear_ramps

Longer sequences may be produced by repeating the pictures produced by the
above generators:

.. autofunction:: repeat_pictures

.. note::

    Where the picture coding mode indicates that pictures represents fields
    (not frames), an even number of pictures (i.e. a whole number of frames) is
    always generated. This means that, for example, a single-frame picture
    generator will generate *two* pictures for these formats.

"""

import functools

from copy import deepcopy

from itertools import cycle

from fractions import Fraction

import math

import numpy as np

from PIL import Image

from vc2_conformance.file_format import read

from vc2_conformance.dimensions_and_depths import compute_dimensions_and_depths

from vc2_data_tables import (
    PictureCodingModes,
    SourceSamplingModes,
)

from vc2_conformance.color_conversion import (
    LINEAR_RGB_TO_XYZ,
    to_xyz,
    from_xyz,
    matmul_colors,
    swap_primaries,
)

from vc2_conformance_data import (
    POINTER_SPRITE_FILENAME,
    NATURAL_PICTURES_FILENAMES,
)


__all__ = [
    "moving_sprite",
    "static_sprite",
    "mid_gray",
    "white_noise",
    "linear_ramps",
    "repeat_pictures",
]


def read_as_xyz(filename):
    """
    Read a VC-2 raw image (see :py:mod:`vc2_conformance.file_format`) into a
    floating point CIE XYZ color 3D array.

    Returns
    =======
    xyz : :py:class:`numpy.array`
        A (height, width, 3) array containing the loaded picture, upsampled to
        4:4:4 color subsampling and converted to CIE XYZ color values.
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    """
    picture, video_parameters, picture_coding_mode = read(filename)

    xyz = to_xyz(
        np.array(picture["Y"]),
        np.array(picture["C1"]),
        np.array(picture["C2"]),
        video_parameters,
    )

    return xyz, video_parameters, picture_coding_mode


def resize(im, width, height):
    """
    Resize a linear-light 3D image.
    """
    # Here we use PIL's resize function with a reasonably high-quality LANCZOS
    # filter. Since PIL only supports single-channel floating point images, we
    # must process each channel separately.
    return np.stack(
        [
            Image.fromarray(im[:, :, channel]).resize((width, height), Image.LANCZOS)
            for channel in range(3)
        ],
        axis=-1,
    )


def read_as_xyz_to_fit(filename, width, height, pixel_aspect_ratio=1):
    """
    Read a VC-2 raw image (see :py:mod:`vc2_conformance.file_format`) into a
    floating point CIE XYZ color 3D array, sized to fit the desired picture
    size, aspect ratio and pixel aspect ratio.

    Parameters
    ==========
    filename : str
        Filename to read from.
    width : int
    height : int
        Width and height of the desired output image.
    pixel_aspect_ratio : :py:class:`Fraction`
        The pixel aspect ratio of the output image.
    """
    image, image_video_parameters, image_picture_coding_mode = read_as_xyz(filename)
    assert image_video_parameters["pixel_aspect_ratio_numer"] == 1
    assert image_video_parameters["pixel_aspect_ratio_denom"] == 1

    im_height, im_width, _ = image.shape

    # Stretch original image to correct for the target pixel aspect ratio
    if pixel_aspect_ratio.numerator != pixel_aspect_ratio.denominator:
        im_width *= pixel_aspect_ratio.denominator
        im_width //= pixel_aspect_ratio.numerator

    im_aspect = Fraction(im_width, im_height)
    out_aspect = Fraction(width, height)

    if im_aspect > out_aspect:
        # Image wider than output, squash so height fits then crop width
        im_height = height
        im_width = int(math.ceil(im_height * im_aspect))
    else:
        # Image taller than output, squash so width fits then crop height
        im_width = width
        im_height = int(math.ceil(im_width / im_aspect))

    image = resize(image, im_width, im_height)

    # Crop to output shape
    x_excess = im_width - width
    y_excess = im_height - height
    return image[
        y_excess // 2 : (y_excess // 2) + height,
        x_excess // 2 : (x_excess // 2) + width,
        :,
    ]


def frames_to_samples(video_parameters, frames):
    """
    Convert a number of seconds into a number of samples (frames for
    progressive video, fields for interlaced video).

    Returns a (num_samples, relative_rate) pair. The 'relative_rate' value
    gives the relative sample rate to the frame rate and is 1 for progressive
    and 2 for interlaced formats.
    """
    if video_parameters["source_sampling"] == SourceSamplingModes.interlaced:
        relative_rate = 2
    else:
        relative_rate = 1

    num_samples = frames * relative_rate

    return (num_samples, relative_rate)


def progressive_to_interlaced(video_parameters, picture_coding_mode, pictures):
    """
    Given a sequence of frames, produces a sequence of half-height fields.
    There is a 1:1 mapping between incoming progressive frames and outgoing
    interlaced fields with half of the incoming lines being dropped from each
    frame.
    """
    first_row_indices = [0, 1] if video_parameters["top_field_first"] else [1, 0]

    for first_row, picture in zip(cycle(first_row_indices), pictures):
        yield picture[first_row::2, :, :]


def progressive_to_split_fields(video_parameters, picture_coding_mode, pictures):
    """
    Given a sequence of frames, produces a series of half-height fields. Each
    frame is turned into a pair of successive fields.
    """
    first_row_indices = [0, 1] if video_parameters["top_field_first"] else [1, 0]

    for picture in pictures:
        for first_row in first_row_indices:
            yield picture[first_row::2, :, :]


def interleave_fields(video_parameters, picture_coding_mode, pictures):
    """
    Given a sequence of fields, interleave those fields into frames. Each
    successive pair of fields will be interleaved into a single output frame.
    """
    it = iter(pictures)
    for field_pair in zip(it, it):
        if not video_parameters["top_field_first"]:
            field_pair = field_pair[::-1]

        top, bottom = field_pair

        interleaved = np.empty((top.shape[0] * 2, top.shape[1], 3), dtype=top.dtype)
        interleaved[0::2, :, :] = top
        interleaved[1::2, :, :] = bottom

        yield interleaved


def progressive_to_pictures(video_parameters, picture_coding_mode, pictures):
    """
    Given a sequence of frames, produce a series of pictures for the current
    source sampling and picture coding modes.

    When interlacing is used, successive pictures will be vertically subsampled
    effectively reducing the frame rate by half.
    """
    pictures_are_frames = picture_coding_mode == PictureCodingModes.pictures_are_frames
    progressive = video_parameters["source_sampling"] == SourceSamplingModes.progressive

    if pictures_are_frames:
        if progressive:
            pass  # Nothing to do
        else:  # interlaced
            # Interlace and combine two fields to a picture
            pictures = progressive_to_interlaced(
                video_parameters, picture_coding_mode, pictures
            )
            pictures = interleave_fields(
                video_parameters, picture_coding_mode, pictures
            )
    else:  # pictures are fields
        if progressive:
            # Split each frame across two pictures
            pictures = progressive_to_split_fields(
                video_parameters, picture_coding_mode, pictures
            )
        else:  # interlaced
            # Interlaced, one field per picture
            pictures = progressive_to_interlaced(
                video_parameters, picture_coding_mode, pictures
            )

    return pictures


def xyz_to_native(video_parameters, picture_coding_mode, pictures):
    """
    Given a sequence of CIE XYZ pictures as 3D arrays, produce a corresponding
    sequence of dictionaries for the specified video format of the form::

        {
            "Y": [[int, ...], ...],
            "C1": [[int, ...], ...],
            "C2": [[int, ...], ...],
            "pic_num": int,
        }

    As constructed by the VC-2 pseudocode.

    Picture numbers are assigned starting from zero.
    """
    for pic_num, picture in enumerate(pictures):
        y, c1, c2 = from_xyz(picture, video_parameters)
        yield {
            "Y": y.tolist(),
            "C1": c1.tolist(),
            "C2": c2.tolist(),
            "pic_num": pic_num,
        }


def pipe(next_function):
    """
    Turn a function of the form::

        f(video_parameters, iterable) -> iterable

    Into a decorator for processing the outputs of video sequence generator
    functions of the form::

        g(video_parameters, ...) -> iterable

    For example::

        >>> def repeat_pictures(video_parameters, picture_coding_mode, iterable):
        ...     for picture in iterable:
        ...         yield picture
        ...         yield picture

        >>> @pipe(repeat_pictures)
        ... def picture_generator(video_parameters, picture_coding_mode, num_frames):
        ...     for frame in range(num_frames):
        ...         picture = something(...)
        ...         yield picture

    In this example, the ``picture_generator`` generator function will generate a
    series of repeated pictures.

    Note that the first argument (``video_parameters``) to the decorated
    function is also passed to ``next_function``.
    """

    @functools.wraps(next_function)
    def decorator(video_sequence_generator):
        @functools.wraps(video_sequence_generator)
        def wrapper(video_parameters, picture_coding_mode, *args, **kwargs):
            iterator = video_sequence_generator(
                video_parameters, picture_coding_mode, *args, **kwargs
            )
            return next_function(video_parameters, picture_coding_mode, iterator)

        return wrapper

    return decorator


def read_and_adapt_pointer_sprite(video_parameters):
    """
    Read the :py:data:`vc2_conformance_data.POINTER_SPRITE_FILENAME` sprite,
    correcting to match the pixel aspect ratio and color primaries specified in
    the provided ``video_parameters``.

    Returns a CIE-XYZ image.
    """
    sprite, sprite_video_parameters, _ = read_as_xyz(POINTER_SPRITE_FILENAME)

    # This sprite has been designed with the intention that 'white', 'red',
    # 'green', and 'blue' in the sprite's color model should be transformed
    # into the native primaries of the output format. As a consequence, we swap
    # the color primaries here.
    sprite = swap_primaries(sprite, sprite_video_parameters, video_parameters)

    sprite_width = sprite_video_parameters["frame_width"]
    sprite_height = sprite_video_parameters["frame_height"]
    assert sprite_video_parameters["pixel_aspect_ratio_numer"] == 1
    assert sprite_video_parameters["pixel_aspect_ratio_denom"] == 1

    # Make sprite square under all pixel aspect ratios
    if (
        video_parameters["pixel_aspect_ratio_numer"]
        != video_parameters["pixel_aspect_ratio_denom"]
    ):
        sprite_width *= video_parameters["pixel_aspect_ratio_denom"]
        sprite_width //= video_parameters["pixel_aspect_ratio_numer"]
        sprite = resize(sprite, sprite_width, sprite_height)

    return sprite


def repeat_pictures(pictures, count):
    """
    Repeat a sequence of pictures produced by a picture generator to produce a
    longer sequence.
    """
    for pic_num, picture in enumerate(list(pictures) * count):
        picture = deepcopy(picture)
        picture["pic_num"] = pic_num
        yield picture


@pipe(xyz_to_native)
@pipe(progressive_to_pictures)
def real_pictures(video_parameters, picture_coding_mode):
    """
    A video sequence containing a series of real pictures.

    This image sequence is provided as an easy visual sanity checking measure
    for decoders and a basic performance check for encoders.
    """
    for filename in NATURAL_PICTURES_FILENAMES:
        picture = read_as_xyz_to_fit(
            filename,
            video_parameters["frame_width"],
            video_parameters["frame_height"],
            Fraction(
                video_parameters["pixel_aspect_ratio_numer"],
                video_parameters["pixel_aspect_ratio_denom"],
            ),
        )

        # NB: Repeat pictures for interlaced modes so each frame is made up of
        # two fields containing the same picture content
        yield picture
        if video_parameters["source_sampling"] == SourceSamplingModes.interlaced:
            yield picture


@pipe(xyz_to_native)
@pipe(progressive_to_pictures)
def moving_sprite(video_parameters, picture_coding_mode, num_frames=10):
    """
    A video sequence containing a simple moving synthetic image.

    This sequence consists of a 128 by 128 pixel sprite (shown below) on a
    black background which traverses the screen from left-to-right moving 16
    pixels to the right every frame (or 8 every field). By default the sequence
    is 10 frames long.

    .. image:: /_static/test_images/pointer.png

    This test sequence may be used to verify that interlacing, pixel aspect
    ratio and frame-rate metadata is being correctly reported by a codec for
    display purposes.

    For interlaced formats (see ``scan_format`` (11.4.5)), sequential fields
    will contain the sprite at different horizontal positions, regardless of
    whether pictures are fields or frames (see picture coding mode (11.5)). As
    a result, when frames are viewed as a set of raw interleaved fields, ragged
    edges will be visible.

    Conversely, for progressive formats, sequential fields contain alternate
    lines from the same moment in time and when interleaved should produce
    smooth edges, regardless of the picture coding mode.

    In the very first field of the sequence, the left edge of the white
    triangle will touch the edge of the frame.  In interlaced formats, the top
    line of white pixels in the sprite will always be located on the top field.
    As a result, the line immediately below should always appear shifted to the
    right when top-field-first field order is used and shifted to the left when
    bottom-field-first order is used (see 'top field first parameter' (11.3)).

    The sprite should be square with the white triangle having equal height and
    length and the hypotenuse lying at an angle of 45 degrees. The circular
    cut-out should be a perfect circle. This verifies that the pictures are
    displayed with the correct pixel aspect ratio (11.4.7).

    The text in the sprite is provided to check that the correct picture
    orientation has been used.

    The colors of the characters 'V', 'C' and '2' are colored saturated
    primary red, green, and blue for the color primaries used (11.4.10.2). This
    provides a basic verification that the color components have been provided
    to the display system and decoded correctly.
    """
    sprite = read_and_adapt_pointer_sprite(video_parameters)

    frame_width = video_parameters["frame_width"]
    frame_height = video_parameters["frame_height"]
    sprite_height, sprite_width, _ = sprite.shape

    # Generate frames
    num_samples, relative_rate = frames_to_samples(video_parameters, num_frames)
    x_step_size = 16 // relative_rate
    for px in np.arange(num_samples, dtype=np.int64) * x_step_size:
        # For bizarre, tiny picture formats too small for the sprite, clip the
        # sprite to fit
        sw = min(frame_width, sprite_width)
        sh = min(frame_height, sprite_height)

        # Clip sprite at edge of screen
        sx = 0
        if px < 0:
            sw += px
            sx -= px
            px -= px

        # Clip sprite at right edge of screen
        if px + sw > frame_width:
            sw -= (px + sw) - frame_width
            # Special case: picture is off edge of display. Sould only occur
            # with absurdly small (e.g. < 8 px wide) frame sizes.
            sw = max(0, sw)

        # Blit the sprite onto an otherwise empty frame
        picture = np.zeros((frame_height, frame_width, 3))
        picture[:sh, px : px + sw, :] = sprite[:sh, sx : sx + sw, :]

        yield picture


@pipe(xyz_to_native)
@pipe(progressive_to_pictures)
def static_sprite(video_parameters, picture_coding_mode):
    """
    A video sequence containing a exactly one frame containing a synthetic
    image.

    This sequence consists of a 128 by 128 pixel sprite (shown below) located
    at the top-left corner of the frame on a black background.

    .. image:: /_static/test_images/pointer.png

    This test sequence may be used to verify that interlacing, pixel aspect
    ratio and frame-rate metadata is being correctly reported by a codec for
    display purposes.

    For if incorrect field ordering is specified, edges will appear ragged and
    not smooth.

    The sprite should be square with the white triangle having equal height and
    length and the hypotenuse lying at an angle of 45 degrees. The circular
    cut-out should be a perfect circle. This verifies that the pictures are
    displayed with the correct pixel aspect ratio (11.4.7).

    The text in the sprite is provided to check that the correct picture
    orientation has been used.

    The colors of the characters 'V', 'C' and '2' are colored saturated
    primary red, green, and blue for the color primaries used (11.4.10.2). This
    provides a basic verification that the color components have been provided
    to the display system and decoded correctly.
    """
    sprite = read_and_adapt_pointer_sprite(video_parameters)

    frame_width = video_parameters["frame_width"]
    frame_height = video_parameters["frame_height"]
    sprite_height, sprite_width, _ = sprite.shape

    # For bizarre, tiny picture formats too small for the sprite, clip the
    # sprite to fit
    sw = min(frame_width, sprite_width)
    sh = min(frame_height, sprite_height)

    # Blit the sprite onto an otherwise empty frame
    picture = np.zeros((frame_height, frame_width, 3))
    picture[:sh, :sw, :] = sprite[:sh, :sw, :]

    yield picture
    if video_parameters["source_sampling"] == SourceSamplingModes.interlaced:
        yield picture


def mid_gray(video_parameters, picture_coding_mode):
    """
    A video sequence containing exactly one empty mid-gray frame.

    'Mid gray' is defined as having each color component set to the integer
    value exactly half-way along its range. When encoded using VC-2 all
    transform coefficients will be zero.

    The actual color will differ depending on the color model used and the
    signal offsets specified, though typically a gray color is produced.
    """

    dd = compute_dimensions_and_depths(video_parameters, picture_coding_mode)

    y = np.full(
        (dd["Y"].height, dd["Y"].width),
        1 << (dd["Y"].depth_bits - 1),
    )
    c1 = np.full(
        (dd["C1"].height, dd["C1"].width),
        1 << (dd["C1"].depth_bits - 1),
    )
    c2 = np.full(
        (dd["C2"].height, dd["C2"].width),
        1 << (dd["C2"].depth_bits - 1),
    )

    yield {
        "Y": y.tolist(),
        "C1": c1.tolist(),
        "C2": c2.tolist(),
        "pic_num": 0,
    }
    if picture_coding_mode == PictureCodingModes.pictures_are_fields:
        yield {
            "Y": y.tolist(),
            "C1": c1.tolist(),
            "C2": c2.tolist(),
            "pic_num": 1,
        }


def white_noise(video_parameters, picture_coding_mode, num_frames=1, seed=0):
    """
    A video sequence containing uniformly distributed pseudo-random full-range
    signal values.

    .. note::

        Because all picture components are filled with noise, the resulting
        pictures will contain 'color' noise rather than black-and-white noise.
        This may include out-of-gamut signals.

    By default a single frame is produced, but the ``num_frames`` argument may
    be used to specify more.

    By default a fixed seed is used, but alternative seeds may be provided in
    the ``seed`` argument.
    """
    if picture_coding_mode == PictureCodingModes.pictures_are_fields:
        num_pictures = num_frames * 2
    else:
        num_pictures = num_frames

    dd = compute_dimensions_and_depths(video_parameters, picture_coding_mode)

    rand = np.random.RandomState(seed)

    for pic_num in range(num_pictures):
        picture = {"pic_num": pic_num}

        for component in ["Y", "C1", "C2"]:
            picture[component] = rand.randint(
                0,
                1 << dd[component].depth_bits,
                (dd[component].height, dd[component].width),
                # NB: int on Windows is only 32 bits, hence forced 64 bit width
                # here
                dtype=np.int64,
            ).tolist()

        yield picture


@pipe(xyz_to_native)
@pipe(progressive_to_pictures)
def linear_ramps(video_parameters, picture_coding_mode):
    """
    An video sequence containing exactly one frame with a series of linear
    color ramps (illustrated below).

    .. image:: /_static/test_images/linear_ramps.png

    The frame is split into horizontal bands which contain, top to bottom:

    * A black-to-white linear ramp
    * A black-to-red linear ramp
    * A black-to-green linear ramp
    * A black-to-blue linear ramp

    The color ramps are linear in intensity. For most color formats (using
    a non-linear transfer function) this produces a non-linear ramp in coded
    pixel values. Further, the ramp will not be perceptually linear since human
    vision does not have a linear response.

    This is provided for the purposes of checking that metadata related to
    color is correctly passed through for display purposes.
    """

    width = video_parameters["frame_width"]
    height = video_parameters["frame_height"]

    ramps_rgb = np.zeros((4, width, 3))

    ramps_rgb[0, :, :] = np.repeat(np.linspace(0.0, 1.0, width), 3).reshape(-1, 3)
    ramps_rgb[1, :, 0] = np.linspace(0.0, 1.0, width)
    ramps_rgb[2, :, 1] = np.linspace(0.0, 1.0, width)
    ramps_rgb[3, :, 2] = np.linspace(0.0, 1.0, width)

    ramps_xyz = matmul_colors(
        LINEAR_RGB_TO_XYZ[video_parameters["color_primaries_index"]],
        ramps_rgb,
    )

    frame_xyz = np.repeat(ramps_xyz, (height + 3) // 4, axis=0)[:height, :, :]

    yield frame_xyz
    if video_parameters["source_sampling"] == SourceSamplingModes.interlaced:
        yield frame_xyz
