import pytest

from io import BytesIO

from bitarray import bitarray

from vc2_conformance import tables

from vc2_conformance.state import State
from vc2_conformance.video_parameters import VideoParameters

from vc2_conformance.bitstream import BitstreamWriter, Serialiser

from vc2_conformance.bitstream import vc2


# This test file attempts to check that:
#
# * Every non-slice-specific VC-2 bitstream parsing function produces sensible,
#   non-crashing output for in-range and out-of-range values
# * Every VC-2 bitstream structured dict has defaults which produce a valid
#   bitstream.


@pytest.fixture
def f():
    return BytesIO()

@pytest.fixture
def w(f):
    return BitstreamWriter(f)


def test_parse_info(w):
    pi_in = vc2.ParseInfo()
    with Serialiser(w, pi_in) as serdes:
        vc2.parse_info(serdes, State())
    pi = serdes.context
    assert str(pi) == (
        "ParseInfo:\n"
        "  padding: 0b\n"
        "  parse_info_prefix: Correct (0x42424344)\n"
        "  parse_code: end_of_sequence (0x10)\n"
        "  next_parse_offset: 0\n"
        "  previous_parse_offset: 0"
    )


@pytest.mark.parametrize("T,func", [
    (vc2.AuxiliaryData, vc2.auxiliary_data),
    (vc2.Padding, vc2.padding),
])
def test_auxiliary_data_and_padding(w, T, func):
    ad_in = T()
    with Serialiser(w, ad_in) as serdes:
        func(serdes, State(next_parse_offset=13))
    ad = serdes.context
    assert str(ad) == (
        "{}:\n"
        "  padding: 0b\n"
        "  bytes: 0x"
    ).format(T.__name__)
    
    # With some data and padding
    w.seek(0, 3)
    ad_in = T(padding=bitarray("1010"), bytes=b"\x11\x22\x33")
    with Serialiser(w, ad_in) as serdes:
        func(serdes, State(next_parse_offset=13+3))
    ad = serdes.context
    assert str(ad) == (
        "{}:\n"
        "  padding: 0b1010\n"
        "  bytes: 0x11_22_33"
    ).format(T.__name__)


@pytest.mark.parametrize("sh_before,string", [
    # Default value
    (vc2.SequenceHeader(), "custom_format (0)"),
    # Integer value
    (vc2.SequenceHeader(base_video_format=0), "custom_format (0)"),
    # Enum value
    (vc2.SequenceHeader(base_video_format=tables.BaseVideoFormats.hd1080p_50), "hd1080p_50 (14)"),
    # Invalid value
    (vc2.SequenceHeader(base_video_format=123456), "123456"),
])
def test_sequence_header(w, sh_before, string):
    # Try with several video formats -- mustn't crash when presented with
    # invalid values
    with Serialiser(w, sh_before) as serdes:
        vc2.sequence_header(serdes, State())
    sh = serdes.context
    assert str(sh) == (
        "SequenceHeader:\n"
        "  padding: 0b\n"
        "  parse_parameters: ParseParameters:\n"
        "    major_version: 3\n"
        "    minor_version: 0\n"
        "    profile: high_quality (3)\n"
        "    level: 0\n"
        "  base_video_format: {}\n"
        "  video_parameters: SourceParameters:\n"
        "    frame_size: FrameSize:\n"
        "      custom_dimensions_flag: False\n"
        "    color_diff_sampling_format: ColorDiffSamplingFormat:\n"
        "      custom_color_diff_format_flag: False\n"
        "    scan_format: ScanFormat:\n"
        "      custom_scan_format_flag: False\n"
        "    frame_rate: FrameRate:\n"
        "      custom_frame_rate_flag: False\n"
        "    pixel_aspect_ratio: PixelAspectRatio:\n"
        "      custom_pixel_aspect_ratio_flag: False\n"
        "    clean_area: CleanArea:\n"
        "      custom_clean_area_flag: False\n"
        "    signal_range: SignalRange:\n"
        "      custom_signal_range_flag: False\n"
        "    color_spec: ColorSpec:\n"
        "      custom_color_spec_flag: False\n"
        "  picture_coding_mode: pictures_are_frames (0)"
    ).format(string)


def test_parse_parameters(w):
    pp_before = vc2.ParseParameters()
    with Serialiser(w, pp_before) as serdes:
        vc2.parse_parameters(serdes, State())
    pp = serdes.context
    assert str(pp) == (
        "ParseParameters:\n"
        "  major_version: 3\n"
        "  minor_version: 0\n"
        "  profile: high_quality (3)\n"
        "  level: 0"
    )


def test_source_parameters(w):
    sp_before = vc2.SourceParameters()
    with Serialiser(w, sp_before) as serdes:
        vc2.source_parameters(serdes, State(), 0)
    sp = serdes.context
    assert str(sp) == (
        "SourceParameters:\n"
        "  frame_size: FrameSize:\n"
        "    custom_dimensions_flag: False\n"
        "  color_diff_sampling_format: ColorDiffSamplingFormat:\n"
        "    custom_color_diff_format_flag: False\n"
        "  scan_format: ScanFormat:\n"
        "    custom_scan_format_flag: False\n"
        "  frame_rate: FrameRate:\n"
        "    custom_frame_rate_flag: False\n"
        "  pixel_aspect_ratio: PixelAspectRatio:\n"
        "    custom_pixel_aspect_ratio_flag: False\n"
        "  clean_area: CleanArea:\n"
        "    custom_clean_area_flag: False\n"
        "  signal_range: SignalRange:\n"
        "    custom_signal_range_flag: False\n"
        "  color_spec: ColorSpec:\n"
        "    custom_color_spec_flag: False"
    )


def test_frame_size(w):
    # Default (with flag clear)
    fs_before = vc2.FrameSize()
    with Serialiser(w, fs_before) as serdes:
        vc2.frame_size(serdes, State(), VideoParameters())
    fs = serdes.context
    assert str(fs) == (
        "FrameSize:\n"
        "  custom_dimensions_flag: False"
    )
    
    # With flag set
    fs_before = vc2.FrameSize(
        custom_dimensions_flag=True,
        frame_width=100,
        frame_height=200,
    )
    with Serialiser(w, fs_before) as serdes:
        vc2.frame_size(serdes, State(), VideoParameters())
    fs = serdes.context
    assert str(fs) == (
        "FrameSize:\n"
        "  custom_dimensions_flag: True\n"
        "  frame_width: 100\n"
        "  frame_height: 200"
    )


def test_color_diff_sampling_format(w):
    # Default (with flag clear)
    cd_before = vc2.ColorDiffSamplingFormat()
    with Serialiser(w, cd_before) as serdes:
        vc2.color_diff_sampling_format(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "ColorDiffSamplingFormat:\n"
        "  custom_color_diff_format_flag: False"
    )
    
    # With flag set
    cd_before = vc2.ColorDiffSamplingFormat(
        custom_color_diff_format_flag=True,
        color_diff_format_index=0,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.color_diff_sampling_format(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "ColorDiffSamplingFormat:\n"
        "  custom_color_diff_format_flag: True\n"
        "  color_diff_format_index: color_4_4_4 (0)"
    )


def test_scan_format(w):
    # Default (with flag clear)
    cd_before = vc2.ScanFormat()
    with Serialiser(w, cd_before) as serdes:
        vc2.scan_format(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "ScanFormat:\n"
        "  custom_scan_format_flag: False"
    )
    
    # With flag set
    cd_before = vc2.ScanFormat(
        custom_scan_format_flag=True,
        source_sampling=0,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.scan_format(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "ScanFormat:\n"
        "  custom_scan_format_flag: True\n"
        "  source_sampling: progressive (0)"
    )


def test_frame_rate(w):
    # Default (with flag clear)
    cd_before = vc2.FrameRate()
    with Serialiser(w, cd_before) as serdes:
        vc2.frame_rate(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "FrameRate:\n"
        "  custom_frame_rate_flag: False"
    )
    
    # With flag set and preset value
    cd_before = vc2.FrameRate(
        custom_frame_rate_flag=True,
        index=1,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.frame_rate(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "FrameRate:\n"
        "  custom_frame_rate_flag: True\n"
        "  index: fps_24_over_1_001 (1)"
    )
    
    # With flag set and invalid preset value
    cd_before = vc2.FrameRate(
        custom_frame_rate_flag=True,
        index=1234,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.frame_rate(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "FrameRate:\n"
        "  custom_frame_rate_flag: True\n"
        "  index: 1234"
    )
    
    # With flag set and custom value
    cd_before = vc2.FrameRate(
        custom_frame_rate_flag=True,
        index=0,
        frame_rate_numer=1,
        frame_rate_denom=2,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.frame_rate(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "FrameRate:\n"
        "  custom_frame_rate_flag: True\n"
        "  index: 0\n"
        "  frame_rate_numer: 1\n"
        "  frame_rate_denom: 2"
    )


def test_pixel_aspect_ratio(w):
    # Default (with flag clear)
    cd_before = vc2.PixelAspectRatio()
    with Serialiser(w, cd_before) as serdes:
        vc2.pixel_aspect_ratio(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "PixelAspectRatio:\n"
        "  custom_pixel_aspect_ratio_flag: False"
    )
    
    # With flag set and preset value
    cd_before = vc2.PixelAspectRatio(
        custom_pixel_aspect_ratio_flag=True,
        index=1,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.pixel_aspect_ratio(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "PixelAspectRatio:\n"
        "  custom_pixel_aspect_ratio_flag: True\n"
        "  index: ratio_1_1 (1)"
    )
    
    # With flag set and invalid preset value
    cd_before = vc2.PixelAspectRatio(
        custom_pixel_aspect_ratio_flag=True,
        index=1234,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.pixel_aspect_ratio(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "PixelAspectRatio:\n"
        "  custom_pixel_aspect_ratio_flag: True\n"
        "  index: 1234"
    )
    
    # With flag set and custom value
    cd_before = vc2.PixelAspectRatio(
        custom_pixel_aspect_ratio_flag=True,
        index=0,
        pixel_aspect_ratio_numer=1,
        pixel_aspect_ratio_denom=2,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.pixel_aspect_ratio(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "PixelAspectRatio:\n"
        "  custom_pixel_aspect_ratio_flag: True\n"
        "  index: 0\n"
        "  pixel_aspect_ratio_numer: 1\n"
        "  pixel_aspect_ratio_denom: 2"
    )


def test_clean_area(w):
    # Default (with flag clear)
    cd_before = vc2.CleanArea()
    with Serialiser(w, cd_before) as serdes:
        vc2.clean_area(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "CleanArea:\n"
        "  custom_clean_area_flag: False"
    )
    
    # With flag set
    cd_before = vc2.CleanArea(
        custom_clean_area_flag=True,
        clean_width=10,
        clean_height=20,
        left_offset=30,
        top_offset=40,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.clean_area(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "CleanArea:\n"
        "  custom_clean_area_flag: True\n"
        "  clean_width: 10\n"
        "  clean_height: 20\n"
        "  left_offset: 30\n"
        "  top_offset: 40"
    )


def test_signal_range(w):
    # Default (with flag clear)
    cd_before = vc2.SignalRange()
    with Serialiser(w, cd_before) as serdes:
        vc2.signal_range(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "SignalRange:\n"
        "  custom_signal_range_flag: False"
    )
    
    # With flag set and preset value
    cd_before = vc2.SignalRange(
        custom_signal_range_flag=True,
        index=1,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.signal_range(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "SignalRange:\n"
        "  custom_signal_range_flag: True\n"
        "  index: range_8_bit_full_range (1)"
    )
    
    # With flag set and invalid value
    cd_before = vc2.SignalRange(
        custom_signal_range_flag=True,
        index=1234,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.signal_range(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "SignalRange:\n"
        "  custom_signal_range_flag: True\n"
        "  index: 1234"
    )
    
    # With flag set and custom value
    cd_before = vc2.SignalRange(
        custom_signal_range_flag=True,
        index=0,
        luma_offset=1,
        luma_excursion=2,
        color_diff_offset=3,
        color_diff_excursion=4,
    )
    with Serialiser(w, cd_before) as serdes:
        vc2.signal_range(serdes, State(), VideoParameters())
    cd = serdes.context
    assert str(cd) == (
        "SignalRange:\n"
        "  custom_signal_range_flag: True\n"
        "  index: 0\n"
        "  luma_offset: 1\n"
        "  luma_excursion: 2\n"
        "  color_diff_offset: 3\n"
        "  color_diff_excursion: 4"
    )


def test_color_spec(w):
    # Default (with flag clear)
    cs_before = vc2.ColorSpec()
    with Serialiser(w, cs_before) as serdes:
        vc2.color_spec(serdes, State(), VideoParameters())
    cs = serdes.context
    assert str(cs) == (
        "ColorSpec:\n"
        "  custom_color_spec_flag: False"
    )
    
    # With flag set and preset value
    cs_before = vc2.ColorSpec(
        custom_color_spec_flag=True,
        index=1,
    )
    with Serialiser(w, cs_before) as serdes:
        vc2.color_spec(serdes, State(), VideoParameters())
    cs = serdes.context
    assert str(cs) == (
        "ColorSpec:\n"
        "  custom_color_spec_flag: True\n"
        "  index: sdtv_525 (1)"
    )
    
    # With flag set and invalid value
    cs_before = vc2.ColorSpec(
        custom_color_spec_flag=True,
        index=1234,
    )
    with Serialiser(w, cs_before) as serdes:
        vc2.color_spec(serdes, State(), VideoParameters())
    cs = serdes.context
    assert str(cs) == (
        "ColorSpec:\n"
        "  custom_color_spec_flag: True\n"
        "  index: 1234"
    )
    
    # With flag set and custom value
    cs_before = vc2.ColorSpec(
        custom_color_spec_flag=True,
        index=0,
        color_primaries=vc2.ColorPrimaries(),
        color_matrix=vc2.ColorMatrix(),
        transfer_function=vc2.TransferFunction(),
    )
    with Serialiser(w, cs_before) as serdes:
        vc2.color_spec(serdes, State(), VideoParameters())
    cs = serdes.context
    assert str(cs) == (
        "ColorSpec:\n"
        "  custom_color_spec_flag: True\n"
        "  index: custom (0)\n"
        "  color_primaries: ColorPrimaries:\n"
        "    custom_color_primaries_flag: False\n"
        "  color_matrix: ColorMatrix:\n"
        "    custom_color_matrix_flag: False\n"
        "  transfer_function: TransferFunction:\n"
        "    custom_transfer_function_flag: False"
    )


def test_color_primaries(w):
    # Default (with flag clear)
    cp_before = vc2.ColorPrimaries()
    with Serialiser(w, cp_before) as serdes:
        vc2.color_primaries(serdes, State(), VideoParameters())
    cp = serdes.context
    assert str(cp) == (
        "ColorPrimaries:\n"
        "  custom_color_primaries_flag: False"
    )
    
    # With flag set and preset value
    cp_before = vc2.ColorPrimaries(
        custom_color_primaries_flag=True,
        index=1,
    )
    with Serialiser(w, cp_before) as serdes:
        vc2.color_primaries(serdes, State(), VideoParameters())
    cp = serdes.context
    assert str(cp) == (
        "ColorPrimaries:\n"
        "  custom_color_primaries_flag: True\n"
        "  index: sdtv_525 (1)"
    )
    
    # With flag set and invalid value
    cp_before = vc2.ColorPrimaries(
        custom_color_primaries_flag=True,
        index=1234,
    )
    with Serialiser(w, cp_before) as serdes:
        vc2.color_primaries(serdes, State(), VideoParameters())
    cp = serdes.context
    assert str(cp) == (
        "ColorPrimaries:\n"
        "  custom_color_primaries_flag: True\n"
        "  index: 1234"
    )


def test_color_matrix(w):
    # Default (with flag clear)
    cp_before = vc2.ColorMatrix()
    with Serialiser(w, cp_before) as serdes:
        vc2.color_matrix(serdes, State(), VideoParameters())
    cp = serdes.context
    assert str(cp) == (
        "ColorMatrix:\n"
        "  custom_color_matrix_flag: False"
    )
    
    # With flag set and preset value
    cp_before = vc2.ColorMatrix(
        custom_color_matrix_flag=True,
        index=1,
    )
    with Serialiser(w, cp_before) as serdes:
        vc2.color_matrix(serdes, State(), VideoParameters())
    cp = serdes.context
    assert str(cp) == (
        "ColorMatrix:\n"
        "  custom_color_matrix_flag: True\n"
        "  index: sdtv (1)"
    )
    
    # With flag set and invalid value
    cp_before = vc2.ColorMatrix(
        custom_color_matrix_flag=True,
        index=1234,
    )
    with Serialiser(w, cp_before) as serdes:
        vc2.color_matrix(serdes, State(), VideoParameters())
    cp = serdes.context
    assert str(cp) == (
        "ColorMatrix:\n"
        "  custom_color_matrix_flag: True\n"
        "  index: 1234"
    )


def test_transfer_function(w):
    # Default (with flag clear)
    cp_before = vc2.TransferFunction()
    with Serialiser(w, cp_before) as serdes:
        vc2.transfer_function(serdes, State(), VideoParameters())
    cp = serdes.context
    assert str(cp) == (
        "TransferFunction:\n"
        "  custom_transfer_function_flag: False"
    )
    
    # With flag set and preset value
    cp_before = vc2.TransferFunction(
        custom_transfer_function_flag=True,
        index=1,
    )
    with Serialiser(w, cp_before) as serdes:
        vc2.transfer_function(serdes, State(), VideoParameters())
    cp = serdes.context
    assert str(cp) == (
        "TransferFunction:\n"
        "  custom_transfer_function_flag: True\n"
        "  index: extended_gamut (1)"
    )
    
    # With flag set and invalid value
    cp_before = vc2.TransferFunction(
        custom_transfer_function_flag=True,
        index=1234,
    )
    with Serialiser(w, cp_before) as serdes:
        vc2.transfer_function(serdes, State(), VideoParameters())
    cp = serdes.context
    assert str(cp) == (
        "TransferFunction:\n"
        "  custom_transfer_function_flag: True\n"
        "  index: 1234"
    )


def test_picture_parse(w):
    # A minimum state for a 1x1 coefficient HQ picture
    state = State(
        major_version=3,
        minor_version=0,
        parse_code=tables.ParseCodes.high_quality_picture,
        luma_width=1,
        luma_height=1,
        color_diff_width=1,
        color_diff_height=1,
    )
    
    # Set all values which cannot have sensible defaults (e.g. because values
    # depend on earlier bitstream values)
    pp_before = vc2.PictureParse(
        wavelet_transform=vc2.WaveletTransform(
            transform_parameters=vc2.TransformParameters(
                slice_parameters=vc2.SliceParameters(
                    slice_prefix_bytes=0,
                    slice_size_scaler=0,
                )
            ),
            # The length of this padding field may change if the proceeding
            # bitstream values do.
            padding=bitarray("0000000"),
            hq_slice_array=vc2.HQSliceArray(),
        )
    )
    with Serialiser(w, pp_before) as serdes:
        vc2.picture_parse(serdes, state)
    pp = serdes.context
    assert str(pp) == (
        "PictureParse:\n"
        "  padding1: 0b\n"
        "  picture_header: PictureHeader:\n"
        "    picture_number: 0\n"
        "  padding2: 0b\n"
        "  wavelet_transform: WaveletTransform:\n"
        "    transform_parameters: TransformParameters:\n"
        "      wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "      dwt_depth: 0\n"
        "      extended_transform_parameters: ExtendedTransformParameters:\n"
        "        asym_transform_index_flag: False\n"
        "        asym_transform_flag: False\n"
        "      slice_parameters: SliceParameters:\n"
        "        slices_x: 0\n"
        "        slices_y: 0\n"
        "        slice_prefix_bytes: 0\n"
        "        slice_size_scaler: 0\n"
        "      quant_matrix: QuantMatrix:\n"
        "        custom_quant_matrix: False\n"
        "    padding: 0b0000000\n"
        "    hq_slice_array: <HQSliceArray with 0 slices>"
    )

def test_picture_header(w):
    ph_before = vc2.PictureHeader()
    with Serialiser(w, ph_before) as serdes:
        vc2.picture_header(serdes, State())
    ph = serdes.context
    assert str(ph) == (
        "PictureHeader:\n"
        "  picture_number: 0"
    )


def test_wavelet_transform(w):
    # A minimum state for a 1x1 coefficient HQ picture
    state = State(
        major_version=3,
        minor_version=0,
        parse_code=tables.ParseCodes.high_quality_picture,
        luma_width=1,
        luma_height=1,
        color_diff_width=1,
        color_diff_height=1,
    )
    
    # Set all values which cannot have sensible defaults (e.g. because values
    # depend on earlier bitstream values)
    wt_before = vc2.WaveletTransform(
        transform_parameters=vc2.TransformParameters(
            slice_parameters=vc2.SliceParameters(
                slice_prefix_bytes=0,
                slice_size_scaler=0,
            )
        ),
        # The length of this padding field may change if the proceeding
        # bitstream values do.
        padding=bitarray("0000000"),
        hq_slice_array=vc2.HQSliceArray(),
    )
    with Serialiser(w, wt_before) as serdes:
        vc2.wavelet_transform(serdes, state)
    wt = serdes.context
    assert str(wt) == (
        "WaveletTransform:\n"
        "  transform_parameters: TransformParameters:\n"
        "    wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "    dwt_depth: 0\n"
        "    extended_transform_parameters: ExtendedTransformParameters:\n"
        "      asym_transform_index_flag: False\n"
        "      asym_transform_flag: False\n"
        "    slice_parameters: SliceParameters:\n"
        "      slices_x: 0\n"
        "      slices_y: 0\n"
        "      slice_prefix_bytes: 0\n"
        "      slice_size_scaler: 0\n"
        "    quant_matrix: QuantMatrix:\n"
        "      custom_quant_matrix: False\n"
        "  padding: 0b0000000\n"
        "  hq_slice_array: <HQSliceArray with 0 slices>"
    )


def test_transform_parameters(w):
    # A minimum state for a HQ picture
    state = State(
        major_version=3,
        minor_version=0,
        parse_code=tables.ParseCodes.high_quality_picture,
    )
    
    # Set all values which cannot have sensible defaults (e.g. because values
    # depend on earlier bitstream values)
    wt_before = vc2.TransformParameters(
        slice_parameters=vc2.SliceParameters(
            slice_prefix_bytes=0,
            slice_size_scaler=0,
        ),
    )
    with Serialiser(w, wt_before) as serdes:
        vc2.transform_parameters(serdes, state)
    wt = serdes.context
    assert str(wt) == (
        "TransformParameters:\n"
        "  wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "  dwt_depth: 0\n"
        "  extended_transform_parameters: ExtendedTransformParameters:\n"
        "    asym_transform_index_flag: False\n"
        "    asym_transform_flag: False\n"
        "  slice_parameters: SliceParameters:\n"
        "    slices_x: 0\n"
        "    slices_y: 0\n"
        "    slice_prefix_bytes: 0\n"
        "    slice_size_scaler: 0\n"
        "  quant_matrix: QuantMatrix:\n"
        "    custom_quant_matrix: False"
    )


def test_transform_parameters(w):
    # A minimum state for a HQ picture
    state = State(
        major_version=3,
        minor_version=0,
        parse_code=tables.ParseCodes.high_quality_picture,
    )
    
    # Set all values which cannot have sensible defaults (e.g. because values
    # depend on earlier bitstream values)
    wt_before = vc2.TransformParameters(
        slice_parameters=vc2.SliceParameters(
            slice_prefix_bytes=0,
            slice_size_scaler=0,
        ),
    )
    with Serialiser(w, wt_before) as serdes:
        vc2.transform_parameters(serdes, state)
    wt = serdes.context
    assert str(wt) == (
        "TransformParameters:\n"
        "  wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "  dwt_depth: 0\n"
        "  extended_transform_parameters: ExtendedTransformParameters:\n"
        "    asym_transform_index_flag: False\n"
        "    asym_transform_flag: False\n"
        "  slice_parameters: SliceParameters:\n"
        "    slices_x: 0\n"
        "    slices_y: 0\n"
        "    slice_prefix_bytes: 0\n"
        "    slice_size_scaler: 0\n"
        "  quant_matrix: QuantMatrix:\n"
        "    custom_quant_matrix: False"
    )


def test_extended_transform_parameters(w):
    # A minimum state for a v3 bitstream
    state = State(
        major_version=3,
        minor_version=0,
    )
    
    # Neither flag set
    ep_before = vc2.ExtendedTransformParameters()
    with Serialiser(w, ep_before) as serdes:
        vc2.extended_transform_parameters(serdes, state)
    ep = serdes.context
    assert str(ep) == (
        "ExtendedTransformParameters:\n"
        "  asym_transform_index_flag: False\n"
        "  asym_transform_flag: False"
    )
    
    # Both flags set
    ep_before = vc2.ExtendedTransformParameters(
        asym_transform_index_flag=True,
        wavelet_index_ho=4,
        asym_transform_flag=True,
        dwt_depth_ho=0,
    )
    with Serialiser(w, ep_before) as serdes:
        vc2.extended_transform_parameters(serdes, state)
    ep = serdes.context
    assert str(ep) == (
        "ExtendedTransformParameters:\n"
        "  asym_transform_index_flag: True\n"
        "  wavelet_index_ho: haar_with_shift (4)\n"
        "  asym_transform_flag: True\n"
        "  dwt_depth_ho: 0"
    )
    
    # Both flags set, out of range wavelet
    ep_before = vc2.ExtendedTransformParameters(
        asym_transform_index_flag=True,
        wavelet_index_ho=1234,
        asym_transform_flag=True,
        dwt_depth_ho=0,
    )
    with Serialiser(w, ep_before) as serdes:
        vc2.extended_transform_parameters(serdes, state)
    ep = serdes.context
    assert str(ep) == (
        "ExtendedTransformParameters:\n"
        "  asym_transform_index_flag: True\n"
        "  wavelet_index_ho: 1234\n"
        "  asym_transform_flag: True\n"
        "  dwt_depth_ho: 0"
    )


def test_slice_parmeters(w):
    # A LD picture
    state = State(
        major_version=3,
        minor_version=0,
        parse_code=tables.ParseCodes.low_delay_picture,
    )
    sp_before = vc2.SliceParameters(
        slice_bytes_numerator=0,
        slice_bytes_denominator=0,
    )
    with Serialiser(w, sp_before) as serdes:
        vc2.slice_parameters(serdes, state)
    sp = serdes.context
    assert str(sp) == (
        "SliceParameters:\n"
        "  slices_x: 0\n"
        "  slices_y: 0\n"
        "  slice_bytes_numerator: 0\n"
        "  slice_bytes_denominator: 0"
    )
    
    # A HQ picture
    state = State(
        major_version=3,
        minor_version=0,
        parse_code=tables.ParseCodes.high_quality_picture,
    )
    sp_before = vc2.SliceParameters(
        slice_prefix_bytes=0,
        slice_size_scaler=0,
    )
    with Serialiser(w, sp_before) as serdes:
        vc2.slice_parameters(serdes, state)
    sp = serdes.context
    assert str(sp) == (
        "SliceParameters:\n"
        "  slices_x: 0\n"
        "  slices_y: 0\n"
        "  slice_prefix_bytes: 0\n"
        "  slice_size_scaler: 0"
    )


def test_quant_matrix(w):
    # Use default quantisation matrix
    qm_before = vc2.QuantMatrix()
    with Serialiser(w, qm_before) as serdes:
        vc2.quant_matrix(serdes, State())
    qm = serdes.context
    assert str(qm) == (
        "QuantMatrix:\n"
        "  custom_quant_matrix: False"
    )
    
    # Use custom quantisation matrix (DC only)
    state = State(dwt_depth=0, dwt_depth_ho=0)
    qm_before = vc2.QuantMatrix(
        custom_quant_matrix=True,
        quant_matrix=[0],
    )
    with Serialiser(w, qm_before) as serdes:
        vc2.quant_matrix(serdes, state)
    qm = serdes.context
    assert str(qm) == (
        "QuantMatrix:\n"
        "  custom_quant_matrix: True\n"
        "  quant_matrix: [0]"
    )
    
    # Use custom quantisation matrix (HO only)
    state = State(dwt_depth=0, dwt_depth_ho=2)
    qm_before = vc2.QuantMatrix(
        custom_quant_matrix=True,
        quant_matrix=[0]*(1+2),
    )
    with Serialiser(w, qm_before) as serdes:
        vc2.quant_matrix(serdes, state)
    qm = serdes.context
    assert str(qm) == (
        "QuantMatrix:\n"
        "  custom_quant_matrix: True\n"
        "  quant_matrix: [0, 0, 0]"
    )
    
    # Use custom quantisation matrix (2D only)
    state = State(dwt_depth=1, dwt_depth_ho=0)
    qm_before = vc2.QuantMatrix(
        custom_quant_matrix=True,
        quant_matrix=[0]*(1+3),
    )
    with Serialiser(w, qm_before) as serdes:
        vc2.quant_matrix(serdes, state)
    qm = serdes.context
    assert str(qm) == (
        "QuantMatrix:\n"
        "  custom_quant_matrix: True\n"
        "  quant_matrix: [0, 0, 0, 0]"
    )
    
    # Use custom quantisation matrix (2D + HO)
    state = State(dwt_depth=1, dwt_depth_ho=2)
    qm_before = vc2.QuantMatrix(
        custom_quant_matrix=True,
        quant_matrix=[0]*(1+2+3),
    )
    with Serialiser(w, qm_before) as serdes:
        vc2.quant_matrix(serdes, state)
    qm = serdes.context
    assert str(qm) == (
        "QuantMatrix:\n"
        "  custom_quant_matrix: True\n"
        "  quant_matrix: [0, 0, 0, 0, 0, 0]"
    )


def test_fragment_parse(w):
    # First fragment in picture
    state = State(
        major_version=3,
        minor_version=0,
        parse_code=tables.ParseCodes.high_quality_picture,
    )
    fp_before = vc2.FragmentParse(
        transform_parameters=vc2.TransformParameters(
            slice_parameters=vc2.SliceParameters(
                slice_prefix_bytes=0,
                slice_size_scaler=0,
            )
        )
    )
    with Serialiser(w, fp_before) as serdes:
        vc2.fragment_parse(serdes, state)
    fp = serdes.context
    assert str(fp) == (
        "FragmentParse:\n"
        "  padding1: 0b\n"
        "  fragment_header: FragmentHeader:\n"
        "    picture_number: 0\n"
        "    fragment_data_length: 0\n"
        "    fragment_slice_count: 0\n"
        "  padding2: 0b\n"
        "  transform_parameters: TransformParameters:\n"
        "    wavelet_index: deslauriers_dubuc_9_7 (0)\n"
        "    dwt_depth: 0\n"
        "    extended_transform_parameters: ExtendedTransformParameters:\n"
        "      asym_transform_index_flag: False\n"
        "      asym_transform_flag: False\n"
        "    slice_parameters: SliceParameters:\n"
        "      slices_x: 0\n"
        "      slices_y: 0\n"
        "      slice_prefix_bytes: 0\n"
        "      slice_size_scaler: 0\n"
        "    quant_matrix: QuantMatrix:\n"
        "      custom_quant_matrix: False"
    )
    
    # Slice-containing fragment
    w.seek(0, 7)
    state = State(
        major_version=3,
        minor_version=0,
        parse_code=tables.ParseCodes.high_quality_picture,
        slices_x=2,
        slices_y=2,
        dwt_depth=0,
        dwt_depth_ho=0,
        luma_width=0,
        luma_height=0,
        color_diff_width=0,
        color_diff_height=0,
        slice_prefix_bytes=0,
        slice_size_scaler=0,
    )
    fp_before = vc2.FragmentParse(
        fragment_header=vc2.FragmentHeader(
            fragment_slice_count=1,
            fragment_x_offset=0,
            fragment_y_offset=0,
        ),
        hq_slice_array=vc2.HQSliceArray(
            prefix_bytes=[b""],
            qindex=[0],
            slice_y_length=[0],
            slice_c1_length=[0],
            slice_c2_length=[0],
            y_block_padding=[bitarray()],
            c1_block_padding=[bitarray()],
            c2_block_padding=[bitarray()],
        ),
    )
    with Serialiser(w, fp_before) as serdes:
        vc2.fragment_parse(serdes, state)
    fp = serdes.context
    assert str(fp) == (
        "FragmentParse:\n"
        "  padding1: 0b\n"
        "  fragment_header: FragmentHeader:\n"
        "    picture_number: 0\n"
        "    fragment_data_length: 0\n"
        "    fragment_slice_count: 1\n"
        "    fragment_x_offset: 0\n"
        "    fragment_y_offset: 0\n"
        "  padding2: 0b\n"
        "  hq_slice_array: <HQSliceArray with 1 slice>"
    )


def test_fragment_header(w):
    # Count = 0
    fh_before = vc2.FragmentHeader()
    with Serialiser(w, fh_before) as serdes:
        vc2.fragment_header(serdes, State())
    fh = serdes.context
    assert str(fh) == (
        "FragmentHeader:\n"
        "  picture_number: 0\n"
        "  fragment_data_length: 0\n"
        "  fragment_slice_count: 0"
    )
    
    # Count != 0
    fh_before = vc2.FragmentHeader(
        fragment_slice_count=2,
        fragment_x_offset=0,
        fragment_y_offset=0,
    )
    with Serialiser(w, fh_before) as serdes:
        vc2.fragment_header(serdes, State())
    fh = serdes.context
    assert str(fh) == (
        "FragmentHeader:\n"
        "  picture_number: 0\n"
        "  fragment_data_length: 0\n"
        "  fragment_slice_count: 2\n"
        "  fragment_x_offset: 0\n"
        "  fragment_y_offset: 0"
    )
