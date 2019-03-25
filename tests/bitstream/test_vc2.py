"""
The tests in this class are currently of the sanity-check flavour. More
detailed cross-checking of these structures with the VC-2 reference decoder
will be taken care of elsewhere.
"""

import pytest

from mock import Mock

from io import BytesIO

from vc2_conformance import bitstream

from vc2_conformance import tables


def test_parse_info():
    p = bitstream.ParseInfo()
    
    # The parse_info structure is defined as being 13 bytes long (10.5.1)
    assert p.length == 13 * 8


@pytest.mark.parametrize("T", [bitstream.AuxiliaryData, bitstream.Padding])
def test_aux_and_padding(T):
    b = T(10)
    
    assert b.length == 10 * 8


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

def test_pixel_aspect_ratio():
    r = bitstream.PixelAspectRatio()
    assert r.length == 1
    
    r["custom_pixel_aspect_ratio_flag"].value = True
    # flag=1, index=3 bits
    assert r.length == 4
    
    assert str(r) == (
        "pixel_aspect_ratio:\n"
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
    c["color_primaries"]["index"].value = tables.PresetColorPrimaries.d_cinema
    c["color_matrix"]["custom_color_matrix_flag"].value = True
    c["color_matrix"]["index"].value = tables.PresetColorMatrices.reversible
    c["transfer_function"]["custom_transfer_function_flag"].value = True
    assert c.length == 1 + 1 + 1 + 5 + 1 + 3 + 1 + 1
    
    assert str(c) == (
        "color_spec:\n"
        "  custom_color_spec_flag: True\n"
        "  index: custom (0)\n"
        "  color_primaries:\n"
        "    custom_color_primaries_flag: True\n"
        "    index: d_cinema (3)\n"
        "  color_matrix:\n"
        "    custom_color_matrix_flag: True\n"
        "    index: reversible (2)\n"
        "  transfer_function:\n"
        "    custom_transfer_function_flag: True\n"
        "    index: tv_gamma (0)"
    )

def test_source_parameters():
    s = bitstream.SourceParameters()
    assert str(s) == (
        "source_parameters:\n"
        "  frame_size:\n"
        "    custom_dimensions_flag: False\n"
        "  color_diff_sampling_format:\n"
        "    custom_color_diff_format_flag: False\n"
        "  scan_format:\n"
        "    custom_scan_format_flag: False\n"
        "  frame_rate:\n"
        "    custom_frame_rate_flag: False\n"
        "  pixel_aspect_ratio:\n"
        "    custom_pixel_aspect_ratio_flag: False\n"
        "  clean_area:\n"
        "    custom_clean_area_flag: False\n"
        "  signal_range:\n"
        "    custom_signal_range_flag: False\n"
        "  color_spec:\n"
        "    custom_color_spec_flag: False"
    )

def test_transform_parameters():
    p = bitstream.TransformParameters(
        parse_code=tables.ParseCodes.low_delay_picture,
        major_version=2,
    )
    
    # Non-extended, low-delay version, default matrix
    assert str(p) == (
        "transform_parameters:\n"
        "  wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "  dwt_depth: 0\n"
        "  slice_parameters:\n"
        "    slices_x: 1\n"
        "    slices_y: 1\n"
        "    slice_bytes_numerator: 0\n"
        "    slice_bytes_denominator: 1\n"
        "  quant_matrix:\n"
        "    custom_quant_matrix: False"
    )
    
    # Extended, high-quality version with custom matrix and HO-transform
    p.parse_code = tables.ParseCodes.high_quality_picture
    p.major_version = 3
    p["dwt_depth"].value = 1
    p["extended_transform_parameters"]["asym_transform_flag"].value = True
    p["extended_transform_parameters"]["dwt_depth_ho"].value = 2
    p["quant_matrix"]["custom_quant_matrix"].value = True
    assert p.dwt_depth == 1
    assert p.dwt_depth_ho == 2
    assert str(p) == (
        "transform_parameters:\n"
        "  wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "  dwt_depth: 1\n"
        "  extended_transform_parameters:\n"
        "    asym_transform_index_flag: False\n"
        "    asym_transform_flag: True\n"
        "    dwt_depth_ho: 2\n"
        "  slice_parameters:\n"
        "    slices_x: 1\n"
        "    slices_y: 1\n"
        "    slice_prefix_bytes: 0\n"
        "    slice_size_scaler: 1\n"
        "  quant_matrix:\n"
        "    custom_quant_matrix: True\n"
        "    matrix:\n"
        "      Level 0: L: 0\n"
        "      Level 1: H: 0\n"
        "      Level 2: H: 0\n"
        "      Level 3: HL: 0, LH: 0, HH: 0"
    )
    
    # Disabling the asym_transform_flag or decrementing the version number
    # should force the dwt_depth_ho to 0
    p["extended_transform_parameters"]["asym_transform_flag"].value = False
    assert p.dwt_depth == 1
    assert p.dwt_depth_ho == 0
    p["extended_transform_parameters"]["asym_transform_flag"].value = True
    p.major_version = 2
    assert p.dwt_depth == 1
    assert p.dwt_depth_ho == 0


def test_transform_data():
    t = bitstream.TransformData(
        slices_x=2,
        slices_y=1,
        dwt_depth=0,
        dwt_depth_ho=0,
        luma_dimensions=(2, 1),
        color_diff_dimensions=(2, 1),
        parse_code=tables.ParseCodes.high_quality_picture,
    )
    
    assert str(t) == (
        "(y=0, x=0):\n"
        "  slice(sx=0, sy=0):\n"
        "    hq_slice:\n"
        "      qindex: 0\n"
        "      slice_y_length: 0\n"
        "      y_transform: Level 0: DC: slice_band x=[0, 1) y=[0, 1): 0\n"
        "      slice_c1_length: 0\n"
        "      c1_transform: Level 0: DC: slice_band x=[0, 1) y=[0, 1): 0\n"
        "      slice_c2_length: 0\n"
        "      c2_transform: Level 0: DC: slice_band x=[0, 1) y=[0, 1): 0\n"
        "(y=0, x=1):\n"
        "  slice(sx=1, sy=0):\n"
        "    hq_slice:\n"
        "      qindex: 0\n"
        "      slice_y_length: 0\n"
        "      y_transform: Level 0: DC: slice_band x=[1, 2) y=[0, 1): 0\n"
        "      slice_c1_length: 0\n"
        "      c1_transform: Level 0: DC: slice_band x=[1, 2) y=[0, 1): 0\n"
        "      slice_c2_length: 0\n"
        "      c2_transform: Level 0: DC: slice_band x=[1, 2) y=[0, 1): 0"
    )


class TestFragmentParse(object):
    
    def test_slices_received(self):
        pfsr = Mock(return_value=None)
        f = bitstream.FragmentParse(previous_fragment_slices_received=pfsr)
        
        # None should be passed through if input has no slices
        pfsr.return_value = None
        f["fragment_header"]["fragment_slice_count"].value = 10
        assert f.fragment_slices_received is None
        
        # If a start-of-picture, this counter should be reset
        f["fragment_header"]["fragment_slice_count"].value = 0
        assert f.fragment_slices_received == 0
        
        # The summation should be passed through if input does have slices
        pfsr.return_value = 100
        f["fragment_header"]["fragment_slice_count"].value = 10
        assert f.fragment_slices_received == 110
        
        # If a start-of-picture set of fragments, should pass through 0
        f["fragment_header"]["fragment_slice_count"].value = 0
        assert f.fragment_slices_received == 0
    
    def test_str(self):
        f = bitstream.FragmentParse(
            parse_code=tables.ParseCodes.high_quality_picture,
            previous_slices_x=10,
            previous_slices_y=5,
            previous_dwt_depth=0,
            previous_dwt_depth_ho=0,
            luma_dimensions=(10, 5),
            color_diff_dimensions=(10, 5),
            previous_fragment_slices_received=111,
        )
        f["fragment_header"]["fragment_slice_count"].value = 2
        f["fragment_header"]["fragment_x_offset"].value = 9
        f["fragment_header"]["fragment_y_offset"].value = 1
        
        # NB: The slice, picture and wavelet transform sizes above were chosen
        # to ensure there is exactly one pixel in every component of every
        # slice.
        
        assert str(f) == (
            "fragment_parse:\n"
            "  fragment_header:\n"
            "    picture_number: 0\n"
            "    fragment_data_length: 0\n"
            "    fragment_slice_count: 2\n"
            "    fragment_x_offset: 9\n"
            "    fragment_y_offset: 1\n"
            "  fragment_data (112th - 113th slices received):\n"
            "    slice(sx=9, sy=1):\n"
            "      hq_slice:\n"
            "        qindex: 0\n"
            "        slice_y_length: 0\n"
            "        y_transform: Level 0: DC: slice_band x=[9, 10) y=[1, 2): 0\n"
            "        slice_c1_length: 0\n"
            "        c1_transform: Level 0: DC: slice_band x=[9, 10) y=[1, 2): 0\n"
            "        slice_c2_length: 0\n"
            "        c2_transform: Level 0: DC: slice_band x=[9, 10) y=[1, 2): 0\n"
            "    slice(sx=0, sy=2):\n"
            "      hq_slice:\n"
            "        qindex: 0\n"
            "        slice_y_length: 0\n"
            "        y_transform: Level 0: DC: slice_band x=[0, 1) y=[2, 3): 0\n"
            "        slice_c1_length: 0\n"
            "        c1_transform: Level 0: DC: slice_band x=[0, 1) y=[2, 3): 0\n"
            "        slice_c2_length: 0\n"
            "        c2_transform: Level 0: DC: slice_band x=[0, 1) y=[2, 3): 0"
        )


class TestLDSlice(object):

    def test_length_computation(self):
        s = bitstream.LDSlice(
            sx=0,
            sy=0,
            slices_x=4,
            slices_y=2,
            slice_bytes_numerator=7,
            slice_bytes_denominator=3,
            dwt_depth_ho=1,
            dwt_depth=2,
            luma_dimensions=(64, 16),
            color_diff_dimensions=(32, 16),  # 4:2:2 style
        )
        
        # The desired slice length is 7/3 bytes (i.e. 2 1/3rd bytes each). This
        # means that depending on the slice index, the slice will either be 2
        # or 3 bytes long.
        #
        # For 2-byte slices, the length field will be 4 bits long.
        # For 3-byte slices, the length field will be 5 bits long.
        #
        # This means that the total available bits for transform data will be
        # 5 for 2-byte slices and 12 for 3-byte slices.
        for i in range(4 * 2):
            s.sx = i % 4
            s.sy = i // 4
            assert s["slice_y_length"].length == 4 if (i % 3) != 2 else 5
            assert s["y_transform"].length + s["c_transform"].length == (
                5 if (i % 3) != 2 else 12
            )

    def test_most_functions(self):
        # The following test should be relatively comprehensive since all values
        # must be passed through correctly to produce the correct final string
        # representation.
        s = bitstream.LDSlice(
            sx=2,
            sy=0,
            slices_x=4,
            slices_y=2,
            slice_bytes_numerator=7,
            slice_bytes_denominator=3,
            dwt_depth_ho=1,
            dwt_depth=2,
            luma_dimensions=(64, 16),
            color_diff_dimensions=(32, 16),  # 4:2:2 style
        )
        
        # This slice will be 3 bytes long with 12 bits available for luma and
        # chroma values in total (see test_length_computation).
        #
        # In this case lets assign 8 of the total bits to luma values (leaving
        # 4 bits for chroma)
        s["slice_y_length"].value = 8
        
        # Perform a write so the values past the bounded blocks become
        # highlighted allowing us to verify the bounded blocks are sized
        # correctly.
        w = bitstream.BitstreamWriter(BytesIO())
        s.write(w)
        
        # NB: For the specified number of slices and picture dimensions, the
        # slices will contain 16x8 blocks of the luma component and 8x8 blocks
        # of chroma components. After division into subbands, the band sizes
        # will thus be:
        # * Level 3: Luma: (8, 4) Chroma (4, 4)  (2D)
        # * Level 2: Luma: (4, 2) Chroma (2, 2)  (2D)
        # * Level 1: Luma: (2, 2) Chroma (1, 2)  (Horizontal Only)
        # * Level 0: Luma: (2, 2) Chroma (1, 2)  (DC)
        
        assert str(s) == (
            "ld_slice:\n"
            "  qindex: 0\n"
            "  slice_y_length: 8\n"
            "  y_transform:\n"
            "    Level 0:\n"
            "      L:\n"
            "        slice_band x=[4, 6) y=[0, 2):\n"
            "          0  0\n"
            "          0  0\n"
            "    Level 1:\n"
            "      H:\n"
            "        slice_band x=[4, 6) y=[0, 2):\n"
            "          0  0\n"
            "          0  0\n"
            # NB: At this point the specified 8 bits have been spent on this
            # part of the slice so the remaining bits should be past the end of
            # the bounded block.
            "    Level 2:\n"
            "      HL:\n"
            "        slice_band x=[8, 12) y=[0, 2):\n"
            "          0*  0*  0*  0*\n"
            "          0*  0*  0*  0*\n"
            "      LH:\n"
            "        slice_band x=[8, 12) y=[0, 2):\n"
            "          0*  0*  0*  0*\n"
            "          0*  0*  0*  0*\n"
            "      HH:\n"
            "        slice_band x=[8, 12) y=[0, 2):\n"
            "          0*  0*  0*  0*\n"
            "          0*  0*  0*  0*\n"
            "    Level 3:\n"
            "      HL:\n"
            "        slice_band x=[16, 24) y=[0, 4):\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "      LH:\n"
            "        slice_band x=[16, 24) y=[0, 4):\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "      HH:\n"
            "        slice_band x=[16, 24) y=[0, 4):\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "          0*  0*  0*  0*  0*  0*  0*  0*\n"
            "  c_transform:\n"
            "    Level 0:\n"
            "      L:\n"
            "        color_diff_slice_band x=[2, 3) y=[0, 2):\n"
            "          (0, 0)\n"
            "          (0, 0)\n"
            # NB: 4 bits sent, remaining bits are past end of bounded block
            "    Level 1:\n"
            "      H:\n"
            "        color_diff_slice_band x=[2, 3) y=[0, 2):\n"
            "          (0*, 0*)\n"
            "          (0*, 0*)\n"
            "    Level 2:\n"
            "      HL:\n"
            "        color_diff_slice_band x=[4, 6) y=[0, 2):\n"
            "          (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)\n"
            "      LH:\n"
            "        color_diff_slice_band x=[4, 6) y=[0, 2):\n"
            "          (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)\n"
            "      HH:\n"
            "        color_diff_slice_band x=[4, 6) y=[0, 2):\n"
            "          (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)\n"
            "    Level 3:\n"
            "      HL:\n"
            "        color_diff_slice_band x=[8, 12) y=[0, 4):\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "      LH:\n"
            "        color_diff_slice_band x=[8, 12) y=[0, 4):\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "      HH:\n"
            "        color_diff_slice_band x=[8, 12) y=[0, 4):\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "          (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)"
        )


def test_hq_slice():
    # The following test should be relatively comprehensive since all values
    # must be passed through correctly to produce the correct final string
    # representation.
    s = bitstream.HQSlice(
        sx=2,
        sy=1,
        slices_x=4,
        slices_y=2,
        slice_prefix_bytes=2,
        slice_size_scaler=2,
        dwt_depth_ho=1,
        dwt_depth=2,
        luma_dimensions=(64, 16),
        color_diff_dimensions=(32, 16),  # 4:2:2 style
    )
    
    # Set non-zero sizes for bounded blocks
    for i, component in enumerate(["y", "c1", "c2"]):
        s["slice_{}_length".format(component)].value = i + 1
    
    # Perform a write so the values past the bounded blocks become highlighted
    # allowing us to verify the bounded blocks are sized correctly.
    w = bitstream.BitstreamWriter(BytesIO())
    s.write(w)
    
    # NB: For the specified number of slices and picture dimensions, the slices
    # will contain 16x8 blocks of the luma component and 8x8 blocks of chroma
    # components. After division into subbands, the band sizes will thus be:
    # * Level 3: Luma: (8, 4) Chroma (4, 4)  (2D)
    # * Level 2: Luma: (4, 2) Chroma (2, 2)  (2D)
    # * Level 1: Luma: (2, 2) Chroma (1, 2)  (Horizontal Only)
    # * Level 0: Luma: (2, 2) Chroma (1, 2)  (DC)
    
    assert str(s) == (
        "hq_slice:\n"
        "  slice_prefix_bytes: 0x00 0x00\n"
        "  qindex: 0\n"
        "  slice_y_length: 1\n"  # 1 * 2 * 8 = 16 bits
        "  y_transform:\n"
        "    Level 0:\n"
        "      L:\n"
        "        slice_band x=[4, 6) y=[2, 4):\n"
        "          0  0\n"
        "          0  0\n"
        "    Level 1:\n"
        "      H:\n"
        "        slice_band x=[4, 6) y=[2, 4):\n"
        "          0  0\n"
        "          0  0\n"
        "    Level 2:\n"
        "      HL:\n"
        "        slice_band x=[8, 12) y=[2, 4):\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        # NB: At this point the specified 16 bits have been spent on this part
        # of the slice so the remaining bits should be past the end of the
        # bounded block.
        "      LH:\n"
        "        slice_band x=[8, 12) y=[2, 4):\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "      HH:\n"
        "        slice_band x=[8, 12) y=[2, 4):\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "    Level 3:\n"
        "      HL:\n"
        "        slice_band x=[16, 24) y=[4, 8):\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "      LH:\n"
        "        slice_band x=[16, 24) y=[4, 8):\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "      HH:\n"
        "        slice_band x=[16, 24) y=[4, 8):\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "          0*  0*  0*  0*  0*  0*  0*  0*\n"
        "  slice_c1_length: 2\n"  # 2 * 2 * 8 = 32 bits
        "  c1_transform:\n"
        "    Level 0:\n"
        "      L:\n"
        "        slice_band x=[2, 3) y=[2, 4):\n"
        "          0\n"
        "          0\n"
        "    Level 1:\n"
        "      H:\n"
        "        slice_band x=[2, 3) y=[2, 4):\n"
        "          0\n"
        "          0\n"
        "    Level 2:\n"
        "      HL:\n"
        "        slice_band x=[4, 6) y=[2, 4):\n"
        "          0  0\n"
        "          0  0\n"
        "      LH:\n"
        "        slice_band x=[4, 6) y=[2, 4):\n"
        "          0  0\n"
        "          0  0\n"
        "      HH:\n"
        "        slice_band x=[4, 6) y=[2, 4):\n"
        "          0  0\n"
        "          0  0\n"
        "    Level 3:\n"
        "      HL:\n"
        "        slice_band x=[8, 12) y=[4, 8):\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        # NB: 32 bits sent, remaining bits are past end of bounded block
        "      LH:\n"
        "        slice_band x=[8, 12) y=[4, 8):\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "      HH:\n"
        "        slice_band x=[8, 12) y=[4, 8):\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "  slice_c2_length: 3\n"  # 3 * 2 * 8 = 48 bits
        "  c2_transform:\n"
        "    Level 0:\n"
        "      L:\n"
        "        slice_band x=[2, 3) y=[2, 4):\n"
        "          0\n"
        "          0\n"
        "    Level 1:\n"
        "      H:\n"
        "        slice_band x=[2, 3) y=[2, 4):\n"
        "          0\n"
        "          0\n"
        "    Level 2:\n"
        "      HL:\n"
        "        slice_band x=[4, 6) y=[2, 4):\n"
        "          0  0\n"
        "          0  0\n"
        "      LH:\n"
        "        slice_band x=[4, 6) y=[2, 4):\n"
        "          0  0\n"
        "          0  0\n"
        "      HH:\n"
        "        slice_band x=[4, 6) y=[2, 4):\n"
        "          0  0\n"
        "          0  0\n"
        "    Level 3:\n"
        "      HL:\n"
        "        slice_band x=[8, 12) y=[4, 8):\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        "      LH:\n"
        "        slice_band x=[8, 12) y=[4, 8):\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        "          0  0  0  0\n"
        # NB: 48 bits sent, remaining bits are past end of bounded block
        "      HH:\n"
        "        slice_band x=[8, 12) y=[4, 8):\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*\n"
        "          0*  0*  0*  0*"
    )


class TestSliceBand():
    
    def test_single_slice_per_picture_no_transform(self):
        s = bitstream.SliceBand(
            sx=0,
            sy=0,
            slices_x=1,
            slices_y=1,
            level=0,
            dwt_depth_ho=0,
            dwt_depth=0,
            component_dimensions=(11, 5),
        )
        
        # With no transform and exactly one slice, should support arbitrary
        # dimensions exactly
        assert str(s) == (
            "slice_band x=[0, 11) y=[0, 5):\n"
            "  0  0  0  0  0  0  0  0  0  0  0\n"
            "  0  0  0  0  0  0  0  0  0  0  0\n"
            "  0  0  0  0  0  0  0  0  0  0  0\n"
            "  0  0  0  0  0  0  0  0  0  0  0\n"
            "  0  0  0  0  0  0  0  0  0  0  0"
        )
    
    def test_slice_sizes(self):
        s = bitstream.SliceBand(
            sx=0,
            sy=0,
            slices_x=3,
            slices_y=2,
            level=0,
            dwt_depth_ho=0,
            dwt_depth=0,
            component_dimensions=(11, 5),
        )
        
        assert s.subband_width == 11
        assert s.subband_height == 5
        
        # Slices should be consecutive and vary in length to eventually reach
        # the correct total width.
        s.sx = 0
        assert s.slice_left == 0
        assert s.slice_right == 3
        s.sx = 1
        assert s.slice_left == 3
        assert s.slice_right == 7
        s.sx = 2
        assert s.slice_left == 7
        assert s.slice_right == 11
        
        s.sy = 0
        assert s.slice_top == 0
        assert s.slice_bottom == 2
        s.sy = 1
        assert s.slice_top == 2
        assert s.slice_bottom == 5
        
        # Make sure the string representation follows along too...
        assert str(s) == (
            "slice_band x=[7, 11) y=[2, 5):\n"
            "  0  0  0  0\n"
            "  0  0  0  0\n"
            "  0  0  0  0"
        )
    
    def test_subband_dimensions(self):
        s = bitstream.SliceBand(
            sx=0,
            sy=0,
            slices_x=1,
            slices_y=1,
            level=0,
            dwt_depth_ho=0,
            dwt_depth=0,
            component_dimensions=(11, 5),
        )
        
        # Horizontal-only
        s.dwt_depth_ho = 1
        s.level = 1
        assert s.subband_width == 12//2  # Must be upped to be divisioble by 2
        assert s.subband_height == 5  # Unchanged
        
        s.dwt_depth_ho = 2
        s.level = 2
        assert s.subband_width == 12//2  # Must be upped to be divisioble by 4
        assert s.subband_height == 5  # Unchanged
        
        s.dwt_depth_ho = 3
        s.level = 3
        assert s.subband_width == 16//2  # Must be upped to be divisioble by 8
        assert s.subband_height == 5  # Unchanged
        
        # Going down the levels
        s.level = 2
        assert s.subband_width == 16//4
        assert s.subband_height == 5
        
        s.level = 1
        assert s.subband_width == 16//8
        assert s.subband_height == 5
        
        # We've hit DC
        s.level = 0
        assert s.subband_width == 16//8
        assert s.subband_height == 5
        
        # 2D too
        s.dwt_depth = 1
        s.level = 4
        assert s.subband_width == 16//2  # Must be upped to be divisioble by 16
        assert s.subband_height == 6//2  # Must be upped to be divisible by 2
        
        s.dwt_depth = 2
        s.level = 5
        assert s.subband_width == 32//2  # Must be upped to be divisioble by 32
        assert s.subband_height == 8//2  # Must be upped to be divisible by 4
        
        s.dwt_depth = 3
        s.level = 6
        assert s.subband_width == 64//2  # Must be upped to be divisioble by 64
        assert s.subband_height == 8//2  # Must be upped to be divisible by 8
        
        # Going down the levels
        s.level = 5
        assert s.subband_width == 64//4
        assert s.subband_height == 8//4
        
        s.level = 4
        assert s.subband_width == 64//8
        assert s.subband_height == 8//8
        
        # We've hit horizontal-only
        s.level = 3
        assert s.subband_width == 64//16
        assert s.subband_height == 8//8
        
        s.level = 2
        assert s.subband_width == 64//32
        assert s.subband_height == 8//8
        
        s.level = 1
        assert s.subband_width == 64//64
        assert s.subband_height == 8//8
        
        # We've hit DC
        s.level = 0
        assert s.subband_width == 64//64
        assert s.subband_height == 8//8
    
    def test_out_of_range_slices_no_crash(self):
        s = bitstream.SliceBand(
            sx=100,
            sy=100,
            slices_x=3,
            slices_y=2,
            level=0,
            dwt_depth_ho=0,
            dwt_depth=0,
            component_dimensions=(11, 5),
        )
        str(s)
    
    @pytest.mark.parametrize("slices_x,slices_y", [(-1, -1), (0, 0), (1, 1)])
    @pytest.mark.parametrize("level", [-1, 0, 1, 2])
    @pytest.mark.parametrize("dwt_depth_ho", [-1, 0, 1])
    @pytest.mark.parametrize("dwt_depth", [-1, 0, 1])
    @pytest.mark.parametrize("w,h", [(-1, -1), (0, 0), (1, 1)])
    def test_negative_or_zero_values_dont_crash(
            self, slices_x, slices_y, level, dwt_depth_ho, dwt_depth, w, h):
        s = bitstream.SliceBand(
            sx=0,
            sy=0,
            slices_x=slices_x,
            slices_y=slices_y,
            level=level,
            dwt_depth_ho=dwt_depth_ho,
            dwt_depth=dwt_depth,
            component_dimensions=(w, h),
        )
        str(s)


def test_color_diff_slice_band():
    # NB: Only the string output is checked since almost all implementation is
    # shared with SliceBand
    s = bitstream.ColorDiffSliceBand(
        sx=0,
        sy=0,
        slices_x=1,
        slices_y=1,
        level=0,
        dwt_depth_ho=0,
        dwt_depth=0,
        component_dimensions=(8, 5),
    )
    
    assert str(s) == (
        "color_diff_slice_band x=[0, 8) y=[0, 5):\n"
        "  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)\n"
        "  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)\n"
        "  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)\n"
        "  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)\n"
        "  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)  (0, 0)"
    )

def test_picture_parse():
    p = bitstream.PictureParse(
        parse_code=tables.ParseCodes.high_quality_picture,
        major_version=3,
        luma_dimensions=(4, 2),
        color_diff_dimensions=(2, 2),
    )
    
    assert str(p) == (
        "picture_parse:\n"
        "  picture_header:\n"
        "    picture_number: 0\n"
        "  wavelet_transform:\n"
        "    transform_parameters:\n"
        "      wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "      dwt_depth: 0\n"
        "      extended_transform_parameters:\n"
        "        asym_transform_index_flag: False\n"
        "        asym_transform_flag: False\n"
        "      slice_parameters:\n"
        "        slices_x: 1\n"
        "        slices_y: 1\n"
        "        slice_prefix_bytes: 0\n"
        "        slice_size_scaler: 1\n"
        "      quant_matrix:\n"
        "        custom_quant_matrix: False\n"
        "    transform_data:\n"
        "      (y=0, x=0):\n"
        "        slice(sx=0, sy=0):\n"
        "          hq_slice:\n"
        "            qindex: 0\n"
        "            slice_y_length: 0\n"
        "            y_transform:\n"
        "              Level 0:\n"
        "                DC:\n"
        "                  slice_band x=[0, 4) y=[0, 2):\n"
        "                    0  0  0  0\n"
        "                    0  0  0  0\n"
        "            slice_c1_length: 0\n"
        "            c1_transform:\n"
        "              Level 0:\n"
        "                DC:\n"
        "                  slice_band x=[0, 2) y=[0, 2):\n"
        "                    0  0\n"
        "                    0  0\n"
        "            slice_c2_length: 0\n"
        "            c2_transform:\n"
        "              Level 0:\n"
        "                DC:\n"
        "                  slice_band x=[0, 2) y=[0, 2):\n"
        "                    0  0\n"
        "                    0  0"
    )


class TestDataUnit(object):
    
    @pytest.mark.parametrize("parse_code,expected_chosen_unit,expected_is_fn", [
        (
            tables.ParseCodes.sequence_header,
            "sequence_header",
            "is_sequence_header",
        ),
        (
            tables.ParseCodes.end_of_sequence,
            None,
            None,
        ),
        (
            tables.ParseCodes.auxiliary_data,
            "auxiliary_data",
            "is_auxiliary_data",
        ),
        (
            tables.ParseCodes.padding_data,
            "padding",
            "is_padding",
        ),
        (
            tables.ParseCodes.low_delay_picture,
            "picture_parse",
            "is_picture_parse",
        ),
        (
            tables.ParseCodes.high_quality_picture,
            "picture_parse",
            "is_picture_parse",
        ),
        (
            tables.ParseCodes.low_delay_picture_fragment,
            "fragment_parse",
            "is_fragment_parse",
        ),
        (
            tables.ParseCodes.high_quality_picture_fragment,
            "fragment_parse",
            "is_fragment_parse",
        ),
    ])
    def test_chosen_unit(self,
            parse_code, expected_chosen_unit, expected_is_fn):
        d = bitstream.DataUnit(parse_code=parse_code)
        assert d.chosen_unit == expected_chosen_unit
        for is_fn in ["is_sequence_header",
                      "is_picture_parse",
                      "is_fragment_parse",
                      "is_auxiliary_data",
                      "is_padding"]:
            value = getattr(d, is_fn)()
            if is_fn == expected_is_fn:
                assert value is True
            else:
                assert value is False
        assert d.chosen_unit == expected_chosen_unit
    
    def test_end_of_sequence(self):
        d = bitstream.DataUnit(
            parse_code=tables.ParseCodes.end_of_sequence,
        )
        
        assert d.length == 0
        assert str(d) == ""
    
    def test_sequence_header(self):
        d = bitstream.DataUnit(
            parse_code=tables.ParseCodes.sequence_header,
            previous_major_version=0,
        )
        
        # Changed to match the data stream
        assert d.major_version == 3
        assert d.luma_dimensions == (640, 480)
        assert d.color_diff_dimensions == (320, 240)
    
    def test_picture_parse(self):
        d = bitstream.DataUnit(
            parse_code=tables.ParseCodes.high_quality_picture,
            previous_major_version=3,
            previous_luma_dimensions=(4, 2),
            previous_color_diff_dimensions=(2, 2),
        )
        
        # Unchanged
        assert d.major_version == 3
        assert d.luma_dimensions == (4, 2)
        assert d.color_diff_dimensions == (2, 2)
    
    def test_fragment_parse(self):
        # Fragment Header
        d = bitstream.DataUnit(
            parse_code=tables.ParseCodes.high_quality_picture_fragment,
            previous_major_version=3,
            previous_luma_dimensions=(4, 2),
            previous_color_diff_dimensions=(2, 2),
            previous_fragment_slices_received=-1,
            previous_slices_x=-1,
            previous_slices_y=-1,
            previous_slice_bytes_numerator=-1,
            previous_slice_bytes_denominator=-1,
            previous_slice_prefix_bytes=-1,
            previous_slice_size_scaler=-1,
            previous_dwt_depth=-1,
            previous_dwt_depth_ho=-1,
        )
        d["fragment_parse"]["fragment_header"]["fragment_slice_count"].value = 0
        
        # Reset slice count
        assert d.fragment_slices_received == 0
        
        # Other parameters set from header
        assert d.slices_x == 1
        assert d.slices_y == 1
        assert d.slice_bytes_numerator == 0
        assert d.slice_bytes_denominator == 1
        assert d.slice_prefix_bytes == 0
        assert d.slice_size_scaler == 1
        assert d.dwt_depth == 0
        assert d.dwt_depth_ho == 0
        
        # Other values passed through unchanged
        assert d.major_version == 3
        assert d.luma_dimensions == (4, 2)
        assert d.color_diff_dimensions == (2, 2)
        
        # Fragment Data
        d = bitstream.DataUnit(
            parse_code=tables.ParseCodes.high_quality_picture_fragment,
            previous_major_version=3,
            previous_luma_dimensions=(4, 2),
            previous_color_diff_dimensions=(2, 2),
            previous_fragment_slices_received=1,
            previous_slices_x=2,
            previous_slices_y=3,
            previous_slice_bytes_numerator=1,
            previous_slice_bytes_denominator=2,
            previous_slice_prefix_bytes=3,
            previous_slice_size_scaler=4,
            previous_dwt_depth=5,
            previous_dwt_depth_ho=6,
        )
        d["fragment_parse"]["fragment_header"]["fragment_slice_count"].value = 1
        
        # Incremented slice count passed through
        assert d.fragment_slices_received == 2
        
        # Other values passed through unchanged
        assert d.major_version == 3
        assert d.luma_dimensions == (4, 2)
        assert d.color_diff_dimensions == (2, 2)
        assert d.slices_x == 2
        assert d.slices_y == 3
        assert d.slice_bytes_numerator == 1
        assert d.slice_bytes_denominator == 2
        assert d.slice_prefix_bytes == 3
        assert d.slice_size_scaler == 4
        assert d.dwt_depth == 5
        assert d.dwt_depth_ho == 6
    
    def test_auxiliary_data(self):
        d = bitstream.DataUnit(
            parse_code=tables.ParseCodes.auxiliary_data,
            length_bytes=10,
        )
        assert d.length == 8 * 10
    
    def test_padding(self):
        d = bitstream.DataUnit(
            parse_code=tables.ParseCodes.padding_data,
            length_bytes=10,
        )
        assert d.length == 8 * 10
