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


class TestParseInfo(object):
    
    def test_str(self):
        p = bitstream.ParseInfo()
        
        # The parse_info structure is defined as being 13 bytes long (10.5.1)
        assert p.length == 13 * 8
        
        assert str(p) == (
            "parse_info:\n"
            "  parse_info_prefix: Correct (0x42424344)\n"
            "  parse_code: end_of_sequence (0x10)\n"
            "  next_parse_offset: 0\n"
            "  previous_parse_offset: 0"
        )
    
    def test_data_length(self):
        p = bitstream.ParseInfo()
        
        d = p.data_length
        
        # The parse_info structure is defined as being 13 bytes long (10.5.1)
        p["next_parse_offset"].value = 13 + 123
        assert d.value == 123
    
    def test_is_low_delay_and_high_quality(self):
        p = bitstream.ParseInfo()
        
        is_low_delay = p.is_low_delay
        is_high_quality = p.is_high_quality
        
        p["parse_code"].value = tables.ParseCodes.end_of_sequence
        assert is_low_delay.value is False
        assert is_high_quality.value is False
        
        p["parse_code"].value = tables.ParseCodes.low_delay_picture
        assert is_low_delay.value is True
        assert is_high_quality.value is False
        
        p["parse_code"].value = tables.ParseCodes.high_quality_picture_fragment
        assert is_low_delay.value is False
        assert is_high_quality.value is True


class TestSequenceHeader(object):
    
    def test_str(self):
        s = bitstream.SequenceHeader()
        
        assert str(s) == (
            "sequence_header:\n"
            "  parse_parameters:\n"
            "    major_version: 3\n"
            "    minor_version: 0\n"
            "    profile: high_quality (3)\n"
            "    level: 0\n"
            "  base_video_format: custom_format (0)\n"
            "  video_parameters:\n"
            "    source_parameters:\n"
            "      frame_size:\n"
            "        custom_dimensions_flag: False\n"
            "      color_diff_sampling_format:\n"
            "        custom_color_diff_format_flag: False\n"
            "      scan_format:\n"
            "        custom_scan_format_flag: False\n"
            "      frame_rate:\n"
            "        custom_frame_rate_flag: False\n"
            "      pixel_aspect_ratio:\n"
            "        custom_pixel_aspect_ratio_flag: False\n"
            "      clean_area:\n"
            "        custom_clean_area_flag: False\n"
            "      signal_range:\n"
            "        custom_signal_range_flag: False\n"
            "      color_spec:\n"
            "        custom_color_spec_flag: False\n"
            "  picture_coding_mode: pictures_are_frames (0)"
        )
    
    def test_dimensions_properties(self):
        s = bitstream.SequenceHeader()
        
        s["base_video_format"].value = tables.BaseVideoFormats.hd1080p_50
        
        # Purely from the base spec
        assert s.luma_dimensions.value == (1920, 1080)
        assert s.color_diff_dimensions.value == (1920//2, 1080)  # 4:2:2
        
        # Override size
        frame_size = s["video_parameters"]["frame_size"]
        frame_size["custom_dimensions_flag"].value = True
        frame_size["frame_width"].value = 1000
        frame_size["frame_height"].value = 600
        
        assert s.luma_dimensions.value == (1000, 600)
        assert s.color_diff_dimensions.value == (1000//2, 600)  # 4:2:2
        
        # Override color-diff sampling
        cdiff_sampling_format = s["video_parameters"]["color_diff_sampling_format"]
        cdiff_sampling_format["custom_color_diff_format_flag"].value = True
        cdiff_sampling_format["color_diff_format_index"].value = \
            tables.ColorDifferenceSamplingFormats.color_4_2_0
        
        assert s.luma_dimensions.value == (1000, 600)
        assert s.color_diff_dimensions.value == (1000//2, 600//2)  # 4:2:0
        
        # Change picture coding mode
        s["picture_coding_mode"].value = tables.PictureCodingModes.pictures_are_fields
        
        assert s.luma_dimensions.value == (1000, 600//2)
        assert s.color_diff_dimensions.value == (1000//2, 600//2//2)  # 4:2:0
        
        # Base video format is invalid, but everything else is overridden so
        # things should still come out valid
        s["base_video_format"].value = -1
        
        assert s.luma_dimensions.value == (1000, 600//2)
        assert s.color_diff_dimensions.value == (1000//2, 600//2//2)  # 4:2:0


def test_parse_parameters():
    p = bitstream.ParseParameters()
    
    assert str(p) == (
        "parse_parameters:\n"
        "  major_version: 3\n"
        "  minor_version: 0\n"
        "  profile: high_quality (3)\n"
        "  level: 0"
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


def test_frame_size():
    f = bitstream.FrameSize()
    assert str(f) == (
        "frame_size:\n"
        "  custom_dimensions_flag: False"
    )
    
    f["custom_dimensions_flag"].value = True
    assert str(f) == (
        "frame_size:\n"
        "  custom_dimensions_flag: True\n"
        "  frame_width: 1\n"
        "  frame_height: 1"
    )


def test_color_diff_sampling_format():
    c = bitstream.ColorDiffSamplingFormat()
    assert str(c) == (
        "color_diff_sampling_format:\n"
        "  custom_color_diff_format_flag: False"
    )
    
    c["custom_color_diff_format_flag"].value = True
    assert str(c) == (
        "color_diff_sampling_format:\n"
        "  custom_color_diff_format_flag: True\n"
        "  color_diff_format_index: color_4_4_4 (0)"
    )


def test_scan_format():
    s = bitstream.ScanFormat()
    assert str(s) == (
        "scan_format:\n"
        "  custom_scan_format_flag: False"
    )
    
    s["custom_scan_format_flag"].value = True
    assert str(s) == (
        "scan_format:\n"
        "  custom_scan_format_flag: True\n"
        "  source_sampling: progressive (0)"
    )


def test_frame_rate():
    f = bitstream.FrameRate()
    assert str(f) == (
        "frame_rate:\n"
        "  custom_frame_rate_flag: False"
    )
    
    f["custom_frame_rate_flag"].value = True
    assert str(f) == (
        "frame_rate:\n"
        "  custom_frame_rate_flag: True\n"
        "  index: 0\n"
        "  frame_rate_numer: 0\n"
        "  frame_rate_denom: 1"
    )
    
    f["index"].value = tables.PresetFrameRates.fps_24_over_1_001
    assert str(f) == (
        "frame_rate:\n"
        "  custom_frame_rate_flag: True\n"
        "  index: 24000/1001 fps (1)"
    )


def test_pixel_aspect_ratio():
    p = bitstream.PixelAspectRatio()
    assert str(p) == (
        "pixel_aspect_ratio:\n"
        "  custom_pixel_aspect_ratio_flag: False"
    )
    
    p["custom_pixel_aspect_ratio_flag"].value = True
    assert str(p) == (
        "pixel_aspect_ratio:\n"
        "  custom_pixel_aspect_ratio_flag: True\n"
        "  index: 0\n"
        "  pixel_aspect_ratio_numer: 1\n"
        "  pixel_aspect_ratio_denom: 1"
    )
    
    p["index"].value = tables.PresetPixelAspectRatios.ratio_4_3
    assert str(p) == (
        "pixel_aspect_ratio:\n"
        "  custom_pixel_aspect_ratio_flag: True\n"
        "  index: 4:3 (6)"
    )


def test_clean_area():
    c = bitstream.CleanArea()
    assert str(c) == (
        "clean_area:\n"
        "  custom_clean_area_flag: False"
    )
    
    c["custom_clean_area_flag"].value = True
    assert str(c) == (
        "clean_area:\n"
        "  custom_clean_area_flag: True\n"
        "  clean_width: 1\n"
        "  clean_height: 1\n"
        "  left_offset: 0\n"
        "  top_offset: 0"
    )


def test_signal_range():
    s = bitstream.SignalRange()
    assert str(s) == (
        "signal_range:\n"
        "  custom_signal_range_flag: False"
    )
    
    s["custom_signal_range_flag"].value = True
    assert str(s) == (
        "signal_range:\n"
        "  custom_signal_range_flag: True\n"
        "  index: 0\n"
        "  luma_offset: 0\n"
        "  luma_excursion: 1\n"
        "  color_diff_offset: 0\n"
        "  color_diff_excursion: 1"
    )
    
    s["index"].value = tables.PresetSignalRanges.range_8_bit_video
    assert str(s) == (
        "signal_range:\n"
        "  custom_signal_range_flag: True\n"
        "  index: range_8_bit_video (2)"
    )


def test_color_spec():
    s = bitstream.ColorSpec()
    assert str(s) == (
        "color_spec:\n"
        "  custom_color_spec_flag: False"
    )
    
    s["custom_color_spec_flag"].value = True
    assert str(s) == (
        "color_spec:\n"
        "  custom_color_spec_flag: True\n"
        "  index: custom (0)\n"
        "  color_primaries:\n"
        "    custom_color_primaries_flag: False\n"
        "  color_matrix:\n"
        "    custom_color_matrix_flag: False\n"
        "  transfer_function:\n"
        "    custom_transfer_function_flag: False"
    )
    
    s["index"].value = tables.PresetColorSpecs.hdtv
    assert str(s) == (
        "color_spec:\n"
        "  custom_color_spec_flag: True\n"
        "  index: hdtv (3)"
    )


def test_color_primaries():
    c = bitstream.ColorPrimaries()
    assert str(c) == (
        "color_primaries:\n"
        "  custom_color_primaries_flag: False"
    )
    
    c["custom_color_primaries_flag"].value = True
    assert str(c) == (
        "color_primaries:\n"
        "  custom_color_primaries_flag: True\n"
        "  index: hdtv (0)"
    )


def test_color_matrix():
    c = bitstream.ColorMatrix()
    assert str(c) == (
        "color_matrix:\n"
        "  custom_color_matrix_flag: False"
    )
    
    c["custom_color_matrix_flag"].value = True
    assert str(c) == (
        "color_matrix:\n"
        "  custom_color_matrix_flag: True\n"
        "  index: hdtv (0)"
    )


def test_transfer_function():
    c = bitstream.TransferFunction()
    assert str(c) == (
        "transfer_function:\n"
        "  custom_transfer_function_flag: False"
    )
    
    c["custom_transfer_function_flag"].value = True
    assert str(c) == (
        "transfer_function:\n"
        "  custom_transfer_function_flag: True\n"
        "  index: tv_gamma (0)"
    )


@pytest.mark.parametrize("T", [bitstream.AuxiliaryData, bitstream.Padding])
def test_auxiliary_data_and_padding(T):
    p = bitstream.ParseInfo()
    a = T(p)
    
    assert a.parse_info is p
    
    p["next_parse_offset"].value = 13 + 5
    assert a.length == 5 * 8
    assert str(a) == "0x00 0x00 0x00 0x00 0x00"


class TestTransformParameters(object):
    
    def test_construct(self):
        p = bitstream.ParseInfo()
        s = bitstream.SequenceHeader()
        t = bitstream.TransformParameters(p, s)
        
        assert t.parse_info is p
        assert t.sequence_header is s
    
    def test_extended(self):
        t = bitstream.TransformParameters()
        
        t.sequence_header["parse_parameters"]["major_version"].value = 3
        assert t.extended.value is True
        
        t.sequence_header["parse_parameters"]["major_version"].value = 2
        assert t.extended.value is False
    
    def test_dwt_depth(self):
        t = bitstream.TransformParameters()
        
        t["dwt_depth"].value = 0
        assert t.dwt_depth.value == 0
        
        t["dwt_depth"].value = 123
        assert t.dwt_depth.value == 123
    
    def test_dwt_depth_ho(self):
        t = bitstream.TransformParameters()
        
        # Always zero for < v3
        t.sequence_header["parse_parameters"]["major_version"].value = 2
        assert t.dwt_depth_ho.value == 0
        
        # Always zero when asym_transform_flag is False
        t.sequence_header["parse_parameters"]["major_version"].value = 3
        t["extended_transform_parameters"]["asym_transform_flag"].value = False
        assert t.dwt_depth_ho.value == 0
        
        # Takes required value when asym_transform_flag is True
        t["extended_transform_parameters"]["asym_transform_flag"].value = True
        
        t["extended_transform_parameters"]["dwt_depth_ho"].value = 0
        assert t.dwt_depth_ho.value == 0
        
        t["extended_transform_parameters"]["dwt_depth_ho"].value = 123
        assert t.dwt_depth_ho.value == 123
    
    def test_str(self):
        t = bitstream.TransformParameters()
        
        t.parse_info["parse_code"].value = tables.ParseCodes.high_quality_picture
        
        # Not-extended
        t.sequence_header["parse_parameters"]["major_version"].value = 2
        assert str(t) == (
            "transform_parameters:\n"
            "  wavelet_index: deslauriers_dubuc_9_7 (0)\n"
            "  dwt_depth: 0\n"
            "  slice_parameters:\n"
            "    slices_x: 1\n"
            "    slices_y: 1\n"
            "    slice_prefix_bytes: 0\n"
            "    slice_size_scaler: 1\n"
            "  quant_matrix:\n"
            "    custom_quant_matrix: False"
        )
        
        # Extended
        t.sequence_header["parse_parameters"]["major_version"].value = 3
        assert str(t) == (
            "transform_parameters:\n"
            "  wavelet_index: deslauriers_dubuc_9_7 (0)\n"
            "  dwt_depth: 0\n"
            "  extended_transform_parameters:\n"
            "    asym_transform_index_flag: False\n"
            "    asym_transform_flag: False\n"
            "  slice_parameters:\n"
            "    slices_x: 1\n"
            "    slices_y: 1\n"
            "    slice_prefix_bytes: 0\n"
            "    slice_size_scaler: 1\n"
            "  quant_matrix:\n"
            "    custom_quant_matrix: False"
        )

def test_extended_transform_parameters():
    e = bitstream.ExtendedTransformParameters()
    
    assert str(e) == (
        "extended_transform_parameters:\n"
        "  asym_transform_index_flag: False\n"
        "  asym_transform_flag: False"
    )
    
    e["asym_transform_index_flag"].value = True
    assert str(e) == (
        "extended_transform_parameters:\n"
        "  asym_transform_index_flag: True\n"
        "  wavelet_index_ho: deslauriers_dubuc_9_7 (0)\n"
        "  asym_transform_flag: False"
    )
    
    e["asym_transform_flag"].value = True
    assert str(e) == (
        "extended_transform_parameters:\n"
        "  asym_transform_index_flag: True\n"
        "  wavelet_index_ho: deslauriers_dubuc_9_7 (0)\n"
        "  asym_transform_flag: True\n"
        "  dwt_depth_ho: 0"
    )


def test_slice_parameters():
    p = bitstream.ParseInfo()
    s = bitstream.SliceParameters(p)
    
    assert s.parse_info is p
    
    p["parse_code"].value = tables.ParseCodes.low_delay_picture
    assert str(s) == (
        "slice_parameters:\n"
        "  slices_x: 1\n"
        "  slices_y: 1\n"
        "  slice_bytes_numerator: 1\n"
        "  slice_bytes_denominator: 1"
    )
    
    p["parse_code"].value = tables.ParseCodes.high_quality_picture
    assert str(s) == (
        "slice_parameters:\n"
        "  slices_x: 1\n"
        "  slices_y: 1\n"
        "  slice_prefix_bytes: 0\n"
        "  slice_size_scaler: 1"
    )

def test_quant_matrix():
    dwt_depth = bitstream.ConstantValue(1)
    dwt_depth_ho = bitstream.ConstantValue(2)
    q = bitstream.QuantMatrix(dwt_depth, dwt_depth_ho)
    
    assert q.dwt_depth is dwt_depth
    assert q.dwt_depth_ho is dwt_depth_ho
    
    assert str(q) == (
        "quant_matrix:\n"
        "  custom_quant_matrix: False"
    )
    
    q["custom_quant_matrix"].value = True
    assert str(q) == (
        "quant_matrix:\n"
        "  custom_quant_matrix: True\n"
        "  matrix:\n"
        "    Level 0: L: 0\n"
        "    Level 1: H: 0\n"
        "    Level 2: H: 0\n"
        "    Level 3: HL: 0, LH: 0, HH: 0"
    )


def test_picture_parse():
    parse_info = bitstream.ParseInfo()
    sequence_header = bitstream.SequenceHeader()
    
    parse_info["parse_code"].value = tables.ParseCodes.high_quality_picture
    
    # Set custom (small) frame size to avoid allocating large amounts of memory
    sequence_header["video_parameters"]["frame_size"]["custom_dimensions_flag"].value = True
    sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 8
    sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 4
    
    p = bitstream.PictureParse(parse_info, sequence_header)
    
    assert p.parse_info is parse_info
    assert p.sequence_header is sequence_header
    
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
        "    hq_transform_data: <HQSliceArray start_sx=0 start_sy=0 slice_count=1>"
    )


def test_picture_header():
    p = bitstream.PictureHeader()
    
    p["picture_number"].value = 123
    
    assert str(p) == (
        "picture_header:\n"
        "  picture_number: 123"
    )


def test_wavelet_transform():
    parse_info = bitstream.ParseInfo()
    sequence_header = bitstream.SequenceHeader()
    
    # Set custom (small) frame size to avoid allocating large amounts of memory
    sequence_header["video_parameters"]["frame_size"]["custom_dimensions_flag"].value = True
    sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 8
    sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 4
    
    w = bitstream.WaveletTransform(parse_info, sequence_header)
    
    assert w.parse_info is parse_info
    assert w.sequence_header is sequence_header
    
    w["transform_parameters"]["slice_parameters"]["slices_x"].value = 3
    w["transform_parameters"]["slice_parameters"]["slices_y"].value = 2
    
    parse_info["parse_code"].value = tables.ParseCodes.low_delay_picture
    assert str(w) == (
        "wavelet_transform:\n"
        "  transform_parameters:\n"
        "    wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "    dwt_depth: 0\n"
        "    extended_transform_parameters:\n"
        "      asym_transform_index_flag: False\n"
        "      asym_transform_flag: False\n"
        "    slice_parameters:\n"
        "      slices_x: 3\n"
        "      slices_y: 2\n"
        "      slice_bytes_numerator: 1\n"
        "      slice_bytes_denominator: 1\n"
        "    quant_matrix:\n"
        "      custom_quant_matrix: False\n"
        "  ld_transform_data: <LDSliceArray start_sx=0 start_sy=0 slice_count=6>"
    )
    
    parse_info["parse_code"].value = tables.ParseCodes.high_quality_picture
    assert str(w) == (
        "wavelet_transform:\n"
        "  transform_parameters:\n"
        "    wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "    dwt_depth: 0\n"
        "    extended_transform_parameters:\n"
        "      asym_transform_index_flag: False\n"
        "      asym_transform_flag: False\n"
        "    slice_parameters:\n"
        "      slices_x: 3\n"
        "      slices_y: 2\n"
        "      slice_prefix_bytes: 0\n"
        "      slice_size_scaler: 1\n"
        "    quant_matrix:\n"
        "      custom_quant_matrix: False\n"
        "  hq_transform_data: <HQSliceArray start_sx=0 start_sy=0 slice_count=6>"
    )
