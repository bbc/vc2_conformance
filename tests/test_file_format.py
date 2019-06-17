import pytest

from io import BytesIO

import struct

import json

from vc2_conformance import tables

from vc2_conformance.file_format import (
    write_picture,
    read_picture,
    InvalidMagicWordError,
    InvalidComponentNumberError,
)


def test_write_picture():
    picture = {
        "pic_num": 0xDEADBEEF,
        # Different sized components, different sized dimensions
        "Y": [[1, 2, 3], [4, 5, 6]],
        "C1": [[7, 8]],
        "C2": [[9, 10]],
    }
    video_parameters = {
        # Not a whole number of bytes and not nearest to a power-of-two bytes
        "luma_excursion": (1<<23) - 1,
        # An exact number of bytes
        "color_diff_excursion": 255,
    }
    f = BytesIO()
    
    write_picture(picture, video_parameters, f)
    
    f.seek(0)
    
    # Magic word
    assert f.read(4) == b"\x56\x43\x32\x43"
    
    # Picture Number
    assert f.read(4) == b"\xEF\xBE\xAD\xDE"
    
    # Video parameters
    (json_length, ) = struct.unpack("<I", f.read(4))
    assert json.loads(f.read(json_length).decode("utf-8")) == video_parameters
    
    # Luma component
    assert f.read(4) == b"\x00\x00\x00\x00"  # Component num (0)
    assert f.read(4) == b"\x03\x00\x00\x00"  # Width (3)
    assert f.read(4) == b"\x02\x00\x00\x00"  # Height (2)
    assert f.read(4) == b"\x17\x00\x00\x00"  # Depth (23)
    assert f.read(4) == b"\x00\x02\x00\x00"  # Sample (1 << 9)
    assert f.read(4) == b"\x00\x04\x00\x00"  # Sample (2 << 9)
    assert f.read(4) == b"\x00\x06\x00\x00"  # Sample (3 << 9)
    assert f.read(4) == b"\x00\x08\x00\x00"  # Sample (4 << 9)
    assert f.read(4) == b"\x00\x0A\x00\x00"  # Sample (5 << 9)
    assert f.read(4) == b"\x00\x0C\x00\x00"  # Sample (6 << 9)
    
    # Color difference component 1
    assert f.read(4) == b"\x01\x00\x00\x00"  # Component num (1)
    assert f.read(4) == b"\x02\x00\x00\x00"  # Width (2)
    assert f.read(4) == b"\x01\x00\x00\x00"  # Height (1)
    assert f.read(4) == b"\x08\x00\x00\x00"  # Depth (8)
    assert f.read(1) == b"\x07"  # Sample (7)
    assert f.read(1) == b"\x08"  # Sample (8)
    
    # Color difference component 2
    assert f.read(4) == b"\x02\x00\x00\x00"  # Component num (2)
    assert f.read(4) == b"\x02\x00\x00\x00"  # Width (2)
    assert f.read(4) == b"\x01\x00\x00\x00"  # Height (1)
    assert f.read(4) == b"\x08\x00\x00\x00"  # Depth (8)
    assert f.read(1) == b"\x09"  # Sample (9)
    assert f.read(1) == b"\x0A"  # Sample (10)


class TestReadPicture(object):
    
    def test_roundtrip(self):
        picture = {
            "pic_num": 0xDEADBEEF,
            # Different sized components, different sized dimensions
            "Y": [[1, 2, 3], [4, 5, 6]],
            "C1": [[7, 8]],
            "C2": [[9, 10]],
        }
        video_parameters = {
            # Not a whole number of bytes and not nearest to a power-of-two bytes
            "luma_excursion": (1<<23) - 1,
            # An exact number of bytes
            "color_diff_excursion": 255,
        }
        f = BytesIO()
        write_picture(picture, video_parameters, f)
        
        f.seek(0)
        picture_out, video_parameters_out = read_picture(f)
        
        picture_out["Y"] = picture_out["Y"].tolist()
        picture_out["C1"] = picture_out["C1"].tolist()
        picture_out["C2"] = picture_out["C2"].tolist()
        assert picture == picture_out
        
        assert video_parameters == video_parameters_out
    
    def test_invalid_magic_word(self):
        picture = {
            "pic_num": 0xDEADBEEF,
            # Different sized components, different sized dimensions
            "Y": [[1, 2, 3], [4, 5, 6]],
            "C1": [[7, 8]],
            "C2": [[9, 10]],
        }
        video_parameters = {
            # Not a whole number of bytes and not nearest to a power-of-two bytes
            "luma_excursion": (1<<23) - 1,
            # An exact number of bytes
            "color_diff_excursion": 255,
        }
        f = BytesIO()
        write_picture(picture, video_parameters, f)
        
        # Corrupt magic word
        f.seek(0)
        f.write(b"\xFF")
        
        f.seek(0)
        with pytest.raises(InvalidMagicWordError):
            read_picture(f)
    
    def test_invalid_component_number(self):
        picture = {
            "pic_num": 0xDEADBEEF,
            # Different sized components, different sized dimensions
            "Y": [[1, 2, 3], [4, 5, 6]],
            "C1": [[7, 8]],
            "C2": [[9, 10]],
        }
        video_parameters = {
            # Not a whole number of bytes and not nearest to a power-of-two bytes
            "luma_excursion": (1<<23) - 1,
            # An exact number of bytes
            "color_diff_excursion": 255,
        }
        f = BytesIO()
        write_picture(picture, video_parameters, f)
        
        # Corrupt component number
        f.seek(8)
        f.seek(12 + struct.unpack("<I", f.read(4))[0])
        f.write(b"\xFF")
        
        f.seek(0)
        with pytest.raises(InvalidComponentNumberError):
            read_picture(f)
