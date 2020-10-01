"""
The :py:mod:`vc2_conformance.file_format` module contains functions for reading
and writing raw pictures and their metadata as files.

Picture and metadata files must come in pairs with the raw planar picture data
file having the extension '.raw' and the metadata file having the extension
'.json'. See :ref:`file-format` for a description of the file format.

..
    NB: If you're reading this the 'file-format' reference above probably isn't
    clickable :). It points to the documentation in
    ``docs/source/user_guide/file_format.rst``.

The following functions may be used to read and write picture/metadata files:

.. autofunction:: read

.. autofunction:: write

The above functions are just wrappers around the following functions which read
and write picture and metadata files in isolation:

.. autofunction:: read_metadata

.. autofunction:: read_picture

.. autofunction:: write_metadata

.. autofunction:: write_picture

Finally, the following function may be used to get the filenames for both parts
of a picture/metadata file pair:

.. autofunction:: get_metadata_and_picture_filenames

"""

import os
import re
import json

import numpy as np

from vc2_data_tables import (
    ColorDifferenceSamplingFormats,
    PictureCodingModes,
    SourceSamplingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
)

from vc2_conformance.pseudocode.video_parameters import VideoParameters

from vc2_conformance.dimensions_and_depths import compute_dimensions_and_depths


__all__ = [
    "read",
    "write",
    "get_metadata_and_picture_filenames",
    "read_metadata",
    "read_picture",
    "write_metadata",
    "write_picture",
]


def get_metadata_and_picture_filenames(filename):
    """
    Given either the filename of a saved picture (.raw) or metadata file
    (.json), return a (metadata_filename, picture_filename) tuple with the
    names of the two corresponding files.
    """
    base_name = os.path.splitext(filename)[0]
    return (
        "{}.json".format(base_name),
        "{}.raw".format(base_name),
    )


def get_picture_filename_pattern(filename):
    """
    Given the filename of a picture file (*.raw), return a version with the
    number replaced with '%d'.
    """
    return re.sub(
        r"(.*)_[0-9]+\.raw",
        r"\1_%d.raw",
        filename,
    )


def write(picture, video_parameters, picture_coding_mode, filename):
    """
    Write a picture to a data and metadata file.

    Convenience wrapper around :py:func:`write_picture` and
    :py:func:`write_metadata`.

    Parameters
    ==========
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    filename : str
        The filename of either the picture data file (.raw) or metadata file
        (.json). The name of the other file will be inferred automatically.
    """
    metadata_filename, picture_filename = get_metadata_and_picture_filenames(filename)

    with open(metadata_filename, "wb") as f:
        write_metadata(picture, video_parameters, picture_coding_mode, f)

    with open(picture_filename, "wb") as f:
        write_picture(picture, video_parameters, picture_coding_mode, f)


def read(filename):
    """
    Read a picture from a data and metadata file.

    Convenience wrapper around :py:func:`read_picture` and
    :py:func:`read_metadata`.

    Parameters
    ==========
    filename : str
        The filename of either the picture data file (.raw) or metadata file
        (.json). The name of the other file will be inferred automatically.

    Returns
    =======
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    """
    metadata_filename, picture_filename = get_metadata_and_picture_filenames(filename)

    with open(metadata_filename, "rb") as f:
        (
            video_parameters,
            picture_coding_mode,
            picture_number,
        ) = read_metadata(f)

    with open(picture_filename, "rb") as f:
        picture = read_picture(
            video_parameters,
            picture_coding_mode,
            picture_number,
            f,
        )

    return (picture, video_parameters, picture_coding_mode)


def write_picture(picture, video_parameters, picture_coding_mode, file):
    """
    Write a decoded picture to a file as a planar image.

    Parameters
    ==========
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    file : :py:class:`file`
        A file open for binary writing.
    """
    dims_and_depths = compute_dimensions_and_depths(
        video_parameters, picture_coding_mode
    )

    for (
        component,
        (width, height, depth_bits, bytes_per_sample),
    ) in dims_and_depths.items():
        # We use native Python integers in a dtype=object array to ensure we
        # can support arbitrary bit depths.
        #
        # NB: we make a copy as we will mutate later.
        values = np.array(picture[component], dtype=object)

        # Write as little-endian representation (NB: this rather explicit
        # expansion supports arbitrary depth values beyond those natively
        # supported by Numpy).
        out = np.zeros((height, width, bytes_per_sample), dtype=np.uint8)
        for byte in range(bytes_per_sample):
            out[:, :, byte] = values & 0xFF
            if byte != bytes_per_sample - 1:
                values >>= 8

        file.write(out.tobytes())


def write_metadata(picture, video_parameters, picture_coding_mode, file):
    """
    Write the metadata associated with a decoded picture to a file as JSON.

    Parameters
    ==========
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    file : :py:class:`file`
        A file open for binary writing.
    """

    # Conversion below is necessary under Python 2.x where IntEnum values are
    # not correctly serialised as integers but instead into invalid JSON.
    file.write(
        json.dumps(
            {
                "video_parameters": {
                    key: int(value)
                    if (isinstance(value, int) and not isinstance(value, bool))
                    else value
                    for key, value in video_parameters.items()
                },
                "picture_coding_mode": int(picture_coding_mode),
                "picture_number": str(picture["pic_num"]),
            }
        ).encode("utf-8")
    )


def read_metadata(file):
    """
    Read a JSON picture metadata file.

    Parameters
    ==========
    file : :py:class:`file`
        A file open for binary reading.

    Returns
    =======
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    picture_number : int
    """
    metadata = json.loads(file.read().decode("utf-8"))

    video_parameters = VideoParameters(metadata["video_parameters"])

    # Convert back into native types
    for name, int_enum_type in [
        ("color_diff_format_index", ColorDifferenceSamplingFormats),
        ("source_sampling", SourceSamplingModes),
        ("color_primaries_index", PresetColorPrimaries),
        ("color_matrix_index", PresetColorMatrices),
        ("transfer_function_index", PresetTransferFunctions),
    ]:
        video_parameters[name] = int_enum_type(video_parameters[name])

    picture_coding_mode = PictureCodingModes(metadata["picture_coding_mode"])

    picture_number = int(metadata["picture_number"])

    return (video_parameters, picture_coding_mode, picture_number)


def read_picture(video_parameters, picture_coding_mode, picture_number, file):
    """
    Read a picture from a file.

    Parameters
    ==========
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    picture_number : int
    file : :py:class:`file`
        A file open for binary reading.

    Returns
    =======
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    """
    picture = {"pic_num": picture_number}

    dims_and_depths = compute_dimensions_and_depths(
        video_parameters, picture_coding_mode
    )
    for (
        component,
        (width, height, depth_bits, bytes_per_sample),
    ) in dims_and_depths.items():
        data = np.frombuffer(
            file.read(height * width * bytes_per_sample),
            dtype=np.uint8,
        ).reshape(height, width, bytes_per_sample)

        # Mask off just the intended bits
        msb_byte = ((depth_bits + 7) // 8) - 1
        if msb_byte < bytes_per_sample:
            data = np.require(data, requirements="W")
            data[:, :, msb_byte + 1 :] = 0
        if depth_bits % 8 != 0:
            data = np.require(data, requirements="W")
            data[:, :, msb_byte] &= (1 << (depth_bits % 8)) - 1

        # We use a dtype=object array so that we can use Python's arbitrary
        # precision integers in order to support arbitrary bit depths
        values = np.zeros((height, width), dtype=object)

        # Read little endian (NB, this method supports arbitrary width values)
        for byte in reversed(range(bytes_per_sample)):
            if byte != bytes_per_sample - 1:
                values <<= 8
            values += data[:, :, byte]

        picture[component] = values.tolist()

    return picture
