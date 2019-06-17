"""
:py:mod:`vc2_conformance.file_format`: Image File Format
========================================================

This module contains routines for saving, reading and converting raw planar
pictures (which may be frames or fields) and their metadata.


Picture file format
-------------------

The file format consists of a JSON video parameters object followed by a series
of planar pictures.

    +------------+------------+------------+------------+------------+------------+
    | Magic Word | Picture No | Vid. Param | Luminance  |  Chroma 1  |  Chroma 2  |
    +------------+------------+------------+------------+------------+------------+

All multi-byte values are stored in little-endian order (that is, least
significant byte first).

The first 4 bytes of the file shall be 0x56 0x43 0x32 0x43 ('VC2C' in ASCII).

    +------+------+------+------+--
    | 0x56 | 0x43 | 0x32 | 0x43 | ...
    +------+------+------+------+--

This will be followed by a 32-bit picture number.

      --+------------+--
    ... | Picture No | ...
      --+------------+--

Next is a 32-bit length field followed by 'length' bytes which must be a valid
JSON-encoded video parameters object encoded using UTF-8.

      --+------------+------------------------------+--
    ... |   length   | video parameters JSON string | ...
      --+------------+------------------------------+--

This will be followed by each picture component in turn. Each component will
begin with a 32-bit component number, 32-bit width, 32-bit height and 32-bit
depth value followed by raster scan order sample data.

      --+------------+------------+------------+------------+------------+-- --+------------+--
    ... | component  |   width    |   height   |   depth    |  sample 0  | ... | sample N-1 | ...
      --+------------+------------+------------+------------+------------+-- --+------------+--

The component should be 0 for the first (luma) component, 1 for the second
(color difference 1) component and 2 for the final (color difference 2)
component.

The 'width' and 'height' give the height and width of that picture component in
samples.

The 'depth' gives the bit depth of the samples in that picture component.

Picture samples are then stored in raster-scan order. All sample
values are unsigned integers.

The number of bytes per sample depends on the picture depth specified. The
smallest whole power-of-two number of bytes possible for that bit depth shall
be used. For example for a depth of 8 bits, samples should occupy one byte, for
10 bit images, two bytes per sample shall be used, for 20 bit samples four
bytes shall be used.

Samples shall be left-shifted and right-zero-padded such that the most
significant bit in each sample becomes the most significant bit in the stored
sequence of bytes.
"""

import struct

import json

import numpy as np

from vc2_conformance.vc2_math import intlog2

from vc2_conformance.video_parameters import VideoParameters, video_depth


def write_picture(picture, video_parameters, file):
    """
    Write a picture to a file.
    
    Parameters
    ==========
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
        The picture to be saved.
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        The associated video parameters.
    file : :py:class:`file`
        A file open for binary writing.
    """
    # Magic Word
    file.write(b"\x56\x43\x32\x43")
    
    # Picture number
    file.write(struct.pack("<I", picture["pic_num"]))
    
    # Video parameters
    video_parameters_json = json.dumps(video_parameters).encode("utf-8")
    file.write(struct.pack("<I", len(video_parameters_json)))
    file.write(video_parameters_json)
    
    # Work out bit depths
    state = {}
    video_depth(state, video_parameters)
    luma_depth = state["luma_depth"]
    color_diff_depth = state["color_diff_depth"]
    
    for comp_num, (comp_name, comp_depth) in enumerate([
        ("Y", luma_depth),
        ("C1", color_diff_depth),
        ("C2", color_diff_depth),
    ]):
        depth_min_bytes = (comp_depth + 7) // 8
        sample_bytes = 1 << intlog2(depth_min_bytes)
        
        # NB: Using Numpy here limits the bit depth to at most 64 bits per
        # sample. In practice this (should) be more than enough for anybody.
        dtype = np.dtype("<u{}".format(sample_bytes))
        a = np.array(picture[comp_name], dtype=dtype, copy=False)
        
        file.write(struct.pack("<I", comp_num))
        
        height, width = a.shape
        file.write(struct.pack("<I", width))
        file.write(struct.pack("<I", height))
        file.write(struct.pack("<I", comp_depth))
        
        file.write((a << ((sample_bytes*8) - comp_depth)).tobytes())


class InvalidMagicWordError(ValueError):
    """
    Thrown when an invalid magic word is found in a picture file.
    """

class InvalidComponentNumberError(ValueError):
    """
    Thrown when a component has the wrong component number in a picture file.
    """


def read_picture(file):
    """
    Read a picture from a file written with :py:func:`picture_to_file`.
    
    Returns
    =======
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    """
    magic_word = file.read(4)
    if magic_word != b"\x56\x43\x32\x43":
        raise InvalidMagicWordError(magic_word)
    
    picture = {}
    
    # Picture number
    picture["pic_num"] = struct.unpack("<I", file.read(4))[0]
    
    # Video parameters
    video_parameters_length = struct.unpack("<I", file.read(4))[0]
    video_parameters = VideoParameters(json.loads(file.read(video_parameters_length).decode("utf-8")))
    
    for comp_num, comp_name in enumerate(["Y", "C1", "C2"]):
        actual_comp_num, width, height, comp_depth = struct.unpack("<IIII", file.read(4*4))
        
        if actual_comp_num != comp_num:
            raise InvalidComponentNumberError(actual_comp_num)
        
        depth_min_bytes = (comp_depth + 7) // 8
        sample_bytes = 1 << intlog2(depth_min_bytes)
        
        buf = file.read(width * height * sample_bytes)
        
        dtype = np.dtype("<u{}".format(sample_bytes))
        a = np.frombuffer(buf, dtype=dtype).reshape((height, width))
        
        # Shift data back down to native significance
        picture[comp_name] = a >> ((sample_bytes*8) - comp_depth)
    
    return picture, video_parameters

