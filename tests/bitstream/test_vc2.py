"""
The tests in this class are currently of the sanity-check flavour. More
detailed cross-checking of these structures with the VC-2 reference decoder
will be taken care of elsewhere.
"""

import pytest

from vc2_conformance import bitstream

from vc2_conformance import tables


def test_parse_info():
    p = bitstream.ParseInfo()
    
    # The parse_info structure is defined as being 13 bytes long (10.5.1)
    assert p.length == 13 * 8


def test_frame_size():
    f = bitstream.FrameSize(False)
    
    assert f.length == 1
    
    f["custom_dimensions_flag"].value = True
    assert f.length == 3


def test_color_diff_sampling_format():
    f = bitstream.ColorDiffSamplingFormat(False)
    
    assert f.length == 1
    
    f["custom_color_diff_format_flag"].value = True
    assert f.length == 2
    assert (
        f["color_diff_format_index"].value is
        tables.ColorDifferenceSamplingFormats.color_4_4_4
    )


def test_scan_format():
    f = bitstream.ScanFormat(False)
    
    assert f.length == 1
    
    f["custom_scan_format_flag"].value = True
    assert f.length == 2
    assert f["source_sampling"].value is tables.SourceSamplingModes.progressive


def test_frame_rate():
    f = bitstream.FrameRate(False)
    
    assert f.length == 1
    
    f["custom_frame_rate_flag"].value = True
    # flag=1, index=1, numer=1, dnom=3 bits
    assert f.length == 6
    
    f["index"].value = tables.PresetFrameRates.fps_24_over_1_001
    # flag=1, index=3 bits
    assert f.length == 4
    
    assert str(f) == (
        "frame_rate:\n"
        "  custom_frame_rate_flag: True\n"
        "  index: 24000/1001 fps (1)"
    )

def test_aspect_ratio():
    r = bitstream.AspectRatio()
    assert r.length == 1
    
    r["custom_pixel_aspect_ratio_flag"].value = True
    # flag=1, index=3 bits
    assert r.length == 4
    
    assert str(r) == (
        "aspect_ratio:\n"
        "  custom_pixel_aspect_ratio_flag: True\n"
        "  index: 1:1 (1)"
    )
    
    r["index"].value = 0
    r["pixel_aspect_ratio_numer"].value = 2
    r["pixel_aspect_ratio_denom"].value = 4
    # flag=1, index=1, numer=3, denom=5 bits
    assert r.length == 10

def test_clean_area():
    c = bitstream.CleanArea()
    assert c.length == 1
    c["custom_clean_area_flag"].value = True
    assert c.length == 1 + 3 + 3 + 1 + 1

def test_signal_range():
    s = bitstream.SignalRange()
    assert s.length == 1
    s["custom_signal_range_flag"].value = True
    assert s.length == 1 + 1 + 1 + 3 + 1 + 3

def test_color_spec():
    c = bitstream.ColorSpec()
    assert c.length == 1
    
    c["custom_color_spec_flag"].value = True
    c["index"].value = 1
    assert c.length == 1 + 3
    
    c["index"].value = tables.PresetColorSpecs.custom
    assert c.length == 1 + 1 + 1 + 1 + 1
    
    c["color_primaries"]["custom_color_primaries_flag"].value = True
    c["color_matrix"]["custom_color_matrix_flag"].value = True
    c["transfer_function"]["custom_transfer_function_flag"].value = True
    assert c.length == 1 + 1 + 2 + 2 + 2
    
    assert str(c) == (
        "color_spec:\n"
        "  custom_color_spec_flag: True\n"
        "  index: custom (0)\n"
        "  color_primaries:\n"
        "    custom_color_primaries_flag: True\n"
        "    index: hdtv (0)\n"
        "  color_matrix:\n"
        "    custom_color_matrix_flag: True\n"
        "    index: hdtv (0)\n"
        "  transfer_function:\n"
        "    custom_transfer_function_flag: True\n"
        "    index: tv_gamma (0)"
    )
