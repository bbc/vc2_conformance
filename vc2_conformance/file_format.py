"""
:py:mod:`vc2_conformance.file_format`: Image File Format
========================================================

This module contains functions for reading and writing pictures and their
display metadata as files.

Picture and metadata files must come in pairs with the picture data file having
the extension '.raw' and the metadata file having the extension '.json'.


Picture Data Format
-------------------

Pictures are stored as raw planar data, i.e.::

    +---+---+-- --+---+---+---+-- --+---+---+---+-- --+---+
    | Y | Y | ... | Y | Cb| Cb| ... | Cb| Cr| Cr| ... | Cr|
    +---+---+-- --+---+---+---+-- --+---+---+---+-- --+---+

Sample values for each component are stored in raster-scan order.

Sample values are stored in the smallest possible power-of-two number of bytes.
For example:

* 6 or 8 bit-per-sample values are stored as one byte per sample
* 10 or 16 bit-per-sample values are stored as two bytes per sample
* 17, 24 or 32 bit-per-sample values are stored as four bytes per sample

Sample values are MSB aligned and zero padded. For example, 10 bit values will
be stored left-shifted by 6 places.

Multi-byte values are stored with big-endian byte ordering (the first byte of a
value in the file contains the most significant 8 bits).

The dimensions and bit depth of each component is not encoded in the picture
data file and must be obtained from an associated metadata file.


Metadata Format
---------------

Picture metadata is stored as an UTF-8 encoded JSON object. This JSON object
with the following fields:

* ``video_parameters``: A
  :py:class:`vc2_conformance.video_parameters.VideoParameters` object.
* ``picture_coding_mode``: The picture coding mode (11.5)
* ``picture_number``: The picture number as a string (in base 10) because JSON
  always uses floats. (12.2) (14.2)
* ``informative_picture_parameters``: An informative entry giving the
  dimensions and bit depths of each picture component, for convenience.  For
  normative purposes, this data should be computed using the procedure defined
  in set_coding_parameters (11.6.1). Contains an object with keys "Y", "C1" and
  "C2" containing objects with the following keys:
  * ``width`` and ``height``: The dimensions of the picture component.
  * ``depth_bits``: The number of bits per pixel.
  * ``bytes_per_sample``: The number of bytes used to store each pixel.

"""

import json
import os

from collections import OrderedDict, namedtuple

from vc2_conformance.vc2_math import intlog2
from vc2_conformance.arrays import new_array

from vc2_data_tables import (
    ColorDifferenceSamplingFormats,
    PictureCodingModes,
)

from vc2_conformance.state import State
from vc2_conformance.video_parameters import VideoParameters, set_coding_parameters


__all__ = [
    "read",
    "write",
    "get_metadata_and_picture_filenames",
    "compute_dimensions_and_depths",
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


def write(picture, video_parameters, picture_coding_mode, filename):
    """
    Write a picture to a data and metadata file.
    
    Convenience wrapper around :py:func:`write_picture` and
    :py:func:`write_metadata`.
    
    Parameters
    ==========
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
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
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
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


DimensionsAndDepths = namedtuple(
    "DimensionsAndDepths",
    "width,height,depth_bits,bytes_per_sample",
)
"""
A set of picture component dimensions and bit depths.

Parameters
==========
width, height : int
    The dimensions of the picture.
depth_bits : int
    The number of bits per pixel.
bytes_per_sample : int
    The number of bytes used to store each pixel value.
"""


def compute_dimensions_and_depths(video_parameters, picture_coding_mode):
    """
    Compute the dimensions, bit depth and bytes-per-sample of a picture.
    
    Parameters
    ==========
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    
    Returns
    =======
    OrderedDict
        An ordered dictionary mapping from component name ("Y", "C1" and "C2")
        to a :py:class:`DimensionsAndDepths`(width, height, depth_bits,
        bytes_per_sample) namedtuple.
    """
    state = State()
    set_coding_parameters(state, video_parameters, picture_coding_mode)
    
    out = OrderedDict()
    
    for component in ["Y", "C1", "C2"]:
        if component == "Y":
            width = state["luma_width"]
            height = state["luma_height"]
            depth_bits = state["luma_depth"]
        else:
            width = state["color_diff_width"]
            height = state["color_diff_height"]
            depth_bits = state["color_diff_depth"]
        
        bytes_per_sample = (depth_bits + 7) // 8  # Round up to whole number of bytes
        bytes_per_sample = 1 << intlog2(bytes_per_sample)  # Round up to power of two
        
        out[component] = DimensionsAndDepths(width, height, depth_bits, bytes_per_sample)
    
    return out


def write_picture(picture, video_parameters, picture_coding_mode, file):
    """
    Write a decoded picture to a file as a planar image.
    
    Parameters
    ==========
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    file : :py:class:`file`
        A file open for binary writing.
    """
    dims_and_depths = compute_dimensions_and_depths(video_parameters, picture_coding_mode)
    
    for component, (width, height, depth_bits, bytes_per_sample) in dims_and_depths.items():
        shift = (bytes_per_sample*8) - depth_bits
        
        for row in picture[component]:
            for value in row:
                value <<= shift
                file.write(bytearray(
                    (value >> (n*8)) & 0xFF
                    for n in range(bytes_per_sample - 1, -1, -1)
                ))


def write_metadata(picture, video_parameters, picture_coding_mode, file):
    """
    Write the metadata associated with a decoded picture to a file as JSON.
    
    Parameters
    ==========
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    file : :py:class:`file`
        A file open for binary writing.
    """
    
    # Conversion below is necessary under Python 2.x where IntEnum values are
    # not correctly serialised as integers but instead into invalid JSON.
    file.write(json.dumps(
        {
            "video_parameters": {
                key: int(value) if isinstance(value, int) else value
                for key, value in video_parameters.items()
            },
            "picture_coding_mode": int(picture_coding_mode),
            "picture_number": str(picture["pic_num"]),
            "informative_picture_parameters": {
                component: params._asdict()
                for component, params in compute_dimensions_and_depths(
                    video_parameters,
                    picture_coding_mode,
                ).items()
            }
        }
    ).encode("utf-8"))


def read_metadata(file):
    """
    Read a JSON picture etadata file.
    
    Parameters
    ==========
    file : :py:class:`file`
        A file open for binary reading.
    
    Returns
    =======
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    picture_number : int
    """
    metadata = json.loads(file.read().decode("utf-8"))
    
    return (
        metadata["video_parameters"],
        metadata["picture_coding_mode"],
        int(metadata["picture_number"]),
    )


def read_picture(video_parameters, picture_coding_mode, picture_number, file):
    """
    Read a picture from a file.
    
    Parameters
    ==========
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    picture_number : int
    file : :py:class:`file`
        A file open for binary reading.
    
    Returns
    =======
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    """
    picture = {"pic_num": picture_number}
    
    dims_and_depths = compute_dimensions_and_depths(video_parameters, picture_coding_mode)
    for component, (width, height, depth_bits, bytes_per_sample) in dims_and_depths.items():
        picture[component] = new_array(width, height)
        
        shift = (bytes_per_sample*8) - depth_bits
        
        for row in range(height):
            row_values = picture[component][row]
            
            for col in range(width):
                value = 0
                for b in bytearray(file.read(bytes_per_sample)):
                    value = (value << 8) | b
                
                value >>= shift
                
                row_values[col] = value
    
    return picture
