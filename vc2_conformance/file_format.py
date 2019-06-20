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

Picture metadata is stored as an ASCII encoded JSON object. This JSON object
with the following fields:

* ``video_parameters``: A
  :py:class:`vc2_conformance.video_parameters.VideoParameters` object.
* ``picture_coding_mode``: The picture coding mode (11.5)
* ``picture_number``: The picture number (12.2) (14.2)

The dimensions and depth of the picture components in an associated picture
data file can be computed using the procedure defined in set_coding_parameters
(11.6.1).
"""

import json
import os

from collections import OrderedDict

from vc2_conformance.vc2_math import intlog2
from vc2_conformance.arrays import new_array

from vc2_conformance.state import State
from vc2_conformance.video_parameters import VideoParameters, set_coding_parameters


def write(picture, video_parameters, picture_coding_mode, filename):
    """
    Write a picture to a data and metadata file.
    
    Convenience wrapper around :py:func:`write_picture` and
    :py:func:`write_metadata`.
    
    Parameters
    ==========
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_conformance.tables.PictureCodingModes`
    filename : str
        The filename of either the picture data file (.raw) or metadata file
        (.json). The name of the other file will be inferred automatically.
    """
    base_name = os.path.splitext(filename)[0]
    
    with open("{}.json".format(base_name), "w") as f:
        write_metadata(picture, video_parameters, picture_coding_mode, f)
    with open("{}.raw".format(base_name), "wb") as f:
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
    picture_coding_mode : :py:class:`~vc2_conformance.tables.PictureCodingModes`
    """
    base_name = os.path.splitext(filename)[0]
    
    with open("{}.json".format(base_name), "r") as f:
        (
            video_parameters,
            picture_coding_mode,
            picture_number,
        ) = read_metadata(f)
    
    with open("{}.raw".format(base_name), "rb") as f:
        picture = read_picture(
            video_parameters,
            picture_coding_mode,
            picture_number,
            f,
        )
    
    return (picture, video_parameters, picture_coding_mode)


def compute_dimensions_and_depths(video_parameters, picture_coding_mode):
    """
    Compute the dimensions, bit depth and bytes-per-sample of a picture.
    
    Parameters
    ==========
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_conformance.tables.PictureCodingModes`
    
    Returns
    =======
    OrderedDict
        An ordered dictionary mapping from component name ("Y", "C1" and "C2")
        to a (width, height, depth_bits, bytes_per_sample) tuple.
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
        
        out[component] = (width, height, depth_bits, bytes_per_sample)
    
    return out


def write_picture(picture, video_parameters, picture_coding_mode, file):
    """
    Write a decoded picture to a file as a planar image.
    
    Parameters
    ==========
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_conformance.tables.PictureCodingModes`
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
    picture_coding_mode : :py:class:`~vc2_conformance.tables.PictureCodingModes`
    file : :py:class:`file`
        A file open for string (not binary) writing.
    """
    json.dump(
        {
            "video_parameters": video_parameters,
            "picture_coding_mode": picture_coding_mode,
            "picture_number": picture["pic_num"],
        },
        file,
    )


def read_metadata(file):
    """
    Read a JSON picture etadata file.
    
    Parameters
    ==========
    file : :py:class:`file`
        A file open for string (not binary) reading.
    
    Returns
    =======
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_conformance.tables.PictureCodingModes`
    picture_number : int
    """
    metadata = json.load(file)
    
    return (
        metadata["video_parameters"],
        metadata["picture_coding_mode"],
        metadata["picture_number"],
    )


def read_picture(video_parameters, picture_coding_mode, picture_number, file):
    """
    Read a picture from a file.
    
    Parameters
    ==========
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_conformance.tables.PictureCodingModes`
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
