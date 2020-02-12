import pytest

from io import BytesIO

import os

import struct

import json

import vc2_data_tables as tables

from vc2_conformance.video_parameters import VideoParameters, set_source_defaults

from vc2_conformance.file_format import (
    get_metadata_and_picture_filenames,
    read_metadata,
    read_picture,
    write_metadata,
    write_picture,
    read,
    write,
)


def test_get_metadata_and_picture_filenames():
    assert get_metadata_and_picture_filenames("/foo/bar/.baz.xxx") == (
        "/foo/bar/.baz.json",
        "/foo/bar/.baz.raw",
    )


@pytest.fixture
def picture():
    return {
        "pic_num": 0xDEADBEEF,
        # Different sized components, different sized dimensions
        "Y": [[1, 2, 3, 4], [5, 6, 7, 8]],
        "C1": [[9, 10]],
        "C2": [[11, 12]],
    }


@pytest.fixture
def video_parameters():
    video_parameters = set_source_defaults(tables.BaseVideoFormats.custom_format)
    
    # Low-resolution 4:2:0 format (matching the picture fixture above)
    video_parameters["frame_width"] = 4
    video_parameters["frame_height"] = 4
    video_parameters["color_diff_format_index"] = tables.ColorDifferenceSamplingFormats.color_4_2_0
    video_parameters["clean_width"] = 4
    video_parameters["clean_height"] = 4
    
    # 23-bit luma samples: Not a whole number of bytes and not nearest to a
    # power-of-two bytes
    video_parameters["luma_excursion"] = (1<<23) - 1
    # 8-bit color-diff samples: An exact number of bytes
    video_parameters["color_diff_excursion"] = 255
    
    return video_parameters


@pytest.fixture
def picture_coding_mode():
    return tables.PictureCodingModes.pictures_are_fields


def test_write_picture(picture, video_parameters, picture_coding_mode):
    picture_file = BytesIO()
    
    write_picture(picture, video_parameters, picture_coding_mode, picture_file)
    
    # Check picture data
    picture_file.seek(0)
    
    # Luma component
    assert picture_file.read(4) == b"\x00\x00\x02\x00"  # Sample (1 << 9)
    assert picture_file.read(4) == b"\x00\x00\x04\x00"  # Sample (2 << 9)
    assert picture_file.read(4) == b"\x00\x00\x06\x00"  # Sample (3 << 9)
    assert picture_file.read(4) == b"\x00\x00\x08\x00"  # Sample (4 << 9)
    assert picture_file.read(4) == b"\x00\x00\x0A\x00"  # Sample (5 << 9)
    assert picture_file.read(4) == b"\x00\x00\x0C\x00"  # Sample (6 << 9)
    assert picture_file.read(4) == b"\x00\x00\x0E\x00"  # Sample (7 << 9)
    assert picture_file.read(4) == b"\x00\x00\x10\x00"  # Sample (8 << 9)
    
    # Color difference component 1
    assert picture_file.read(1) == b"\x09"  # Sample (9)
    assert picture_file.read(1) == b"\x0A"  # Sample (10)
    
    # Color difference component 2
    assert picture_file.read(1) == b"\x0B"  # Sample (11)
    assert picture_file.read(1) == b"\x0C"  # Sample (12)
    
    # EOF
    assert picture_file.read() == b""


def test_read_picture_and_read_and_write_metadata(picture, video_parameters, picture_coding_mode):
    picture_file = BytesIO()
    metadata_file = BytesIO()
    
    write_picture(picture, video_parameters, picture_coding_mode, picture_file)
    write_metadata(picture, video_parameters, picture_coding_mode, metadata_file)
    
    metadata_file.seek(0)
    (
        new_video_parameters,
        new_picture_coding_mode,
        new_picture_number,
    ) = read_metadata(metadata_file)
    
    # Check both values and types are restored
    assert new_video_parameters == video_parameters
    assert (
        {k: type(v) for k, v in video_parameters.items()} ==
        {k: type(v) for k, v in new_video_parameters.items()}
    )
    
    assert new_picture_coding_mode == picture_coding_mode
    
    picture_file.seek(0)
    new_picture = read_picture(
        new_video_parameters,
        new_picture_coding_mode,
        new_picture_number,
        picture_file,
    )
    
    assert new_picture == picture


def test_read_and_write_convenience_functions(picture, video_parameters, picture_coding_mode, tmp_path):
    filename = os.path.join(str(tmp_path), "test_file.xxx")
    
    write(picture, video_parameters, picture_coding_mode, filename)
    
    # Correct files created
    assert set(os.listdir(str(tmp_path))) == set([
        "test_file.raw",
        "test_file.json",
    ])
    
    # Round-trip works
    assert read(filename) == (
        picture,
        video_parameters,
        picture_coding_mode,
    )
