import math

import logging

from sentinels import Sentinel

from attr import attrs, attrib

from fractions import Fraction

from collections import defaultdict

from vc2_conformance.tables import *


L = Sentinel("L")
H = Sentinel("H")
"""Named variables for horizontal-only wavelet subbands."""

LL = Sentinel("LL")
HL = Sentinel("HL")
LH = Sentinel("LH")
HH = Sentinel("HH")
"""Named variables for 2D wavelet subbands."""

Y = Sentinel("Y")
C1 = Sentinel("C1")
C2 = Sentinel("C2")
"""(13.2.3) Named picture components."""

pic_num = Sentinel("pic_num")
"""(15.2) Used as a key in state.current_picture."""


@attrs
class State(object):
    
    def __attrs_post_init__(self):
        # (A.2.1) Load the first byte on startup ('A decoder is deemed to
        # maintain a copy of the current byte').
        read_byte(self)
    
    ################################################################################
    # (A) Low-level data (de)coding definitions
    ################################################################################
    
    stream = attrib()
    """
    (Non-standard) The current stream as an open Python file object, open in
    binary read mode.
    """
    
    current_byte = attrib(default=None)
    """
    (A.2.1) Current byte being processed (as uint)
    """
    
    next_bit = attrib(default=None)
    """
    (A.2.1) Next bit to be used from the current byte (7=MSB of current_byte, 0
    means LSB of current_byte).
    """
    
    bits_left = attrib(default=None)
    """
    (A.4.2) The number of remaining bits in the current bounded block.
    """
    
    ################################################################################
    # (10) Stream decoding
    ################################################################################
    
    parse_code = attrib(default=None)
    """
    (10.5.1). One of the parse codes from (Table 10.1), as defined in
    the ParseCodes enum.
    """
    
    next_parse_offset = attrib(default=None)
    """
    (10.5.1). The offset (in bytes) from the first byte of the
    current parse info header to the first byte of the next parse info header.
    May be 0 if the next block is a picture or the end of the stream.
    """
    
    previous_parse_offset = attrib(default=None)
    """
    (10.5.1). The offset (in bytes) from the first byte of the current parse
    info header to the first byte of the previous parse info header. May be 0
    if the start of the stream.
    """
    
    fragmented_picture_done = attrib(default=None)
    """
    (14.4) Has the current fragment been completely read?
    """
    
    ################################################################################
    # (11) Sequence header parsing
    ################################################################################
    
    major_version = attrib(default=None)
    """(11.2.2) VC-2 Version number component."""
    
    minor_version = attrib(default=None)
    """(11.2.2) VC-2 Version number component."""
    
    profile = attrib(default=None)
    """(11.2.3) VC-2 profile number."""
    
    level = attrib(default=None)
    """(11.2.3) VC-2 level number."""
    
    luma_width = attrib(default=None)
    luma_height = attrib(default=None)
    """(11.6.2) dimensions of luma part of pictures"""
    
    color_diff_width = attrib(default=None)
    color_diff_height = attrib(default=None)
    """(11.6.2) dimensions of chroma part of pictures"""
    
    luma_depth = attrib(default=None)
    color_diff_depth = attrib(default=None)
    """(11.6.3) bit-depths of pictures"""
    
    ################################################################################
    # (12) Picture syntax
    ################################################################################
    
    picture_number = attrib(default=None)
    """(12.2) The picture number of the picture being decoded (32-bit uint)."""
    
    wavelet_index = attrib(default=None)
    """(21.4.1) The index of the inverse wavelet transform to use."""
    
    dwt_depth = attrib(default=None)
    """(21.4.1) The inverse wavelet transform depth to use."""
    
    wavelet_index_ho = attrib(default=None)
    """
    (21.4.1) The index of the inverse wavelet transform to use for
    horizontal-only components.
    """
    
    dwt_depth_ho = attrib(default=None)
    """
    (21.4.1) The inverse wavelet transform depth to use for horizontal-only
    components.
    """
    
    slices_x = attrib(default=None)
    slices_y = attrib(default=None)
    """(12.4.5.2) Number of slices horizontally/vertically."""
    
    slice_bytes_numerator = attrib(default=None)
    slice_bytes_denominator = attrib(default=None)
    """(12.4.5.2) Number of bytes per low-delay picture slice."""
    
    slice_prefix_bytes = attrib(default=None)
    slice_size_scaler = attrib(default=None)
    """(12.4.5.2) High-quality picture slice parameters."""
    
    quant_matrix = attrib(factory=lambda: defaultdict(dict))
    """
    (12.4.5.3) The current quantisation matrix. This is a dictionary {level:
    {subband: value, ...}, ...}. The default value is a defaultdict of dicts
    for convenience but may be replaced with a regular dict of dicts.
    """
    
    ################################################################################
    # (13) Transform data syntax
    ################################################################################
    
    y_transform = attrib(default=None)
    c1_transform = attrib(default=None)
    c2_transform = attrib(default=None)
    """
    (13.1) Wavelet coefficient data for the luma and color difference
    components.
    """
    
    quantizer = attrib(factory=lambda: defaultdict(dict))
    """
    (13.5.5) The quantisation index for each level/subband of the current
    slice. This is a dictionary {level: {subband: value, ...}, ...}. The
    default value is a defaultdict of dicts for convenience but may be replaced
    with a regular dict of dicts.
    """
    
    ################################################################################
    # (14) Fragment syntax
    ################################################################################
    
    fragment_data_length = attrib(default=None)
    """(14.2)"""
    
    fragment_slice_count = attrib(default=None)
    """(14.2)"""
    
    fragment_x_offset = attrib(default=None)
    fragment_y_offset = attrib(default=None)
    """(14.2)"""
    
    fragment_slices_received = attrib(default=None)
    """(14.3)"""
    
    fragment_picture_done = attrib(default=None)
    """(14.3)"""
    
    ################################################################################
    # (15) Picture decoding
    ################################################################################
    
    current_picture = attrib(default=None)
    """
    (15.2) A dict with four keys: pic_num, Y, C1 and C2. The pic_num entry
    contains the current picture_number and the Y, C1 and C2 components contain
    arrays of pixel data.
    """


################################################################################
# (5.5.3) Integer functions/operators
################################################################################

def intlog2(n):
    """(5.5.3)"""
    return int(math.ceil(math.log(n, 2)))

def sign(n):
    """(5.5.3)"""
    if n < 0:
        return -1
    elif n == 0:
        return 0
    elif n > 0:
        return 1

def clip(a, b, t):
    """(5.5.3)"""
    return min(max(a, b), t)

def mean(S):
    """(5.5.3)"""
    n = len(S)
    return (sum(S) + (n//2)) // n

def array(width, height, initial_value=0):
    """
    Not from spec. Makes a 2D array out of nested lists with the outer list
    having 'height' entries and each inner list having 'width' entries,
    initially set to initial_value.
    """
    return [
        [initial_value] * width
        for _ in range(height)
    ]


def width(a):
    """(5.5.4)"""
    # NB: This will fail for arrays with 0 height... but we shouldn't encounter
    # those... right...?
    return len(a[0])


def height(a):
    """(5.5.4)"""
    return len(a)


################################################################################
# (A) Low-level data (de)coding definitions
################################################################################

def read_byte(state):
    """(A.2.2) Read the next byte in the stream into the buffer"""
    # NB: The test here is added beyond the scope of the test since the spec
    # assumes an infinate length file while in practice the file will not have
    # infinite length.
    byte = state.stream.read(1)
    if len(byte) == 1:
        state.current_byte = bytearray(byte)[0]
        state.next_bit = 7
    else:
        # End of file (these values should cause any future reads to fail)
        state.current_byte = None
        state.next_bit = None


def read_bit(state):
    """(A.2.3) Read and return the next bit in the stream."""
    assert state.current_byte is not None
    assert state.next_bit is not None
    bit = (state.current_byte >> state.next_bit) & 1
    state.next_bit -= 1
    
    # Roll on to next byte if required
    if state.next_bit < 0:
        state.next_bit = 7
        read_byte(state)
    
    return bit


def byte_align(state):
    """(A.2.4) Align read pointer to next byte boundary."""
    assert state.next_bit is not None
    if state.next_bit != 7:
        read_byte(state)


def read_bool(state):
    """(A.3.2)"""
    return bool(read_bit(state))


def read_nbits(state, n):
    """(A.3.3) Read an unaligned n-bit unsigned integer."""
    val = 0
    for i in range(n):
        val <<= 1
        val += read_bit(state)
    return val


def read_uint_lit(state, n):
    """(A.3.4) Read an aligned n-byte unsigned integer."""
    byte_align(state)
    return read_nbits(state, 8 * n)


def read_bitb(state):
    """(A.4.2) Read bit from current bounded block."""
    assert state.bits_left is not None
    if state.bits_left == 0:
        return 1
    else:
        state.bits_left -= 1
        return read_bit(state)


def read_boolb(state):
    """(A.4.2) Read bool from current bounded block."""
    return bool(read_bitb(state))


def flush_inputb(state):
    """(A.4.2) Flush all remaining bits in the current bounded block."""
    assert state.bits_left is not None
    while state.bits_left > 0:
        read_bit(state)
        state.bits_left -= 1


def read_uint(state):
    """(A.4.3) Read an unsigned interleaved exp-Golomb code."""
    value = 1
    while read_bit(state) == 0:
        value <<= 1
        if read_bit(state) == 1:
            value += 1
    value -= 1
    return value

def read_uintb(state):
    """
    (A.4.3) Read an unsigned interleaved exp-Golomb code from the current
    bounded block.
    """
    value = 1
    while read_bitb(state) == 0:
        value <<= 1
        if read_bitb(state) == 1:
            value += 1
    value -= 1
    return value


def read_sint(state):
    """(A.4.4) Read a signed interleaved exp-Golomb code."""
    value = read_uint(state)
    if value != 0:
        if read_bit(state) == 1:
            value = -value
    return value


def read_sintb(state):
    """
    (A.4.4) Read a signed interleaved exp-Golomb code from the current bounded
    block.
    """
    value = read_uintb(state)
    if value != 0:
        if read_bitb(state) == 1:
            value = -value
    return value


################################################################################
# (10) Stream decoding
################################################################################

def parse_sequence(stream):
    """
    (10.4.1) Parse a whole VC-2 sequence (i.e. file), discarding the contents.
    Given as a specification of the data structure, not an actually useful
    parsing loop.
    """
    state = State(stream=stream)
    parse_info(state)
    while not is_end_of_sequence(state):
        if is_seq_header(state):
            sequence_header(state)
        elif is_picture(state):
            picture_parse(state)
        elif is_fragment(state):
            fragment(state)
        elif is_auxiliary_data(state):
            auxiliary_data(state)
        elif is_padding_data(state):  # Erata: listed as 'is_padding' in standard
            padding(state)
        parse_info(state)


PARSE_INFO_HEADER_BYTES = 13
"""(15.5.1) The number of bytes in the parse_info header."""


def auxiliary_data(state):
    """(10.4.4) Read an auxiliary data block."""
    byte_align(state)
    for i in range(state.next_parse_offset - PARSE_INFO_HEADER_BYTES):
        # Erata: is eroneously 'read_byte' in the spec
        read_uint_lit(state, 1)


def padding(state):
    """(10.4.5) Read a padding data block."""
    byte_align(state)
    for i in range(state.next_parse_offset - PARSE_INFO_HEADER_BYTES):
        # Erata: is eroneously 'read_byte' in the spec
        read_uint_lit(state, 1)


def parse_info(state):
    """(10.5.1) Read a parse_info header."""
    magic_word = read_uint_lit(state, 4)
    state.parse_code = read_uint_lit(state, 1)
    state.next_parse_offset = read_uint_lit(state, 4)
    state.previous_parse_offset = read_uint_lit(state, 4)
    
    logging.debug("parse_info: magic_word = 0x%08X", magic_word)
    logging.debug("parse_info: parse_code = %d", state.parse_code)
    logging.debug("parse_info: next_parse_offset = %d", state.next_parse_offset)
    logging.debug("parse_info: previous_parse_offset = %d", state.previous_parse_offset)
    
    assert magic_word == 0x42424344  # 'BBCD'


def is_seq_header(state):
    """(10.5.2) (Table 10.2)"""
    return state.parse_code == ParseCodes.sequence_header.value


def is_end_of_sequence(state):
    """(10.5.2) (Table 10.2)"""
    return state.parse_code == ParseCodes.end_of_sequence.value


def is_auxiliary_data(state):
    """(10.5.2) (Table 10.2)"""
    return (state.parse_code & 0xF8) == ParseCodes.auxiliary_data.value


def is_padding_data(state):
    """(10.5.2) (Table 10.2)"""
    return state.parse_code == ParseCodes.auxiliary_data.value


def is_picture(state):
    """(10.5.2) (Table 10.2) NB: Includes fragments."""
    return (state.parse_code & 0x88) == 0x88


def is_ld_picture(state):
    """(10.5.2) (Table 10.2) NB: Includes low-delay fragments."""
    return (state.parse_code & 0xF8) == ParseCodes.low_delay_picture.value


def is_hq_picture(state):
    """(10.5.2) (Table 10.2) NB: Includes high-quality fragments."""
    return (state.parse_code & 0xF8) == ParseCodes.high_quality_picture.value


def is_fragment(state):
    """(10.5.2) (Table 10.2)"""
    return (state.parse_code & 0x0C) == 0x0C


def is_ld_fragment(state):
    """(10.5.2) (Table 10.2)"""
    return (state.parse_code & 0xFC) == ParseCodes.low_delay_picture_fragment.value


def is_hq_fragment(state):
    """(10.5.2) (Table 10.2)"""
    return (state.parse_code & 0xFC) == ParseCodes.high_quality_picture_fragment.value


def using_dc_prediction(state):
    """(10.5.2) (Table 10.2) a.k.a. is low-delay"""
    return (state.parse_code & 0x28) == 0x08


def decode_sequence(stream):
    """
    (10.6.1) Informative. Stream decode loop (a 'useful' alternative to
    parse_sequence()).
    """
    state = State(stream=stream)
    video_parameters = None
    decoded_pictures = []
    
    parse_info(state)
    while not is_end_of_sequence(state):
        if is_seq_header(state):
            logging.debug("decode_sequence: Sequence Header")
            new_video_parameters = sequence_header(state)
            assert (video_parameters is None or
                new_video_parameters == video_parameters)
            video_parameters = new_video_parameters
        elif is_picture(state):
            if is_fragment(state):
                logging.debug("decode_sequence: Fragment")
                fragment_parse(state)
                if state.fragmented_picture_done:
                    decoded_pictures.append(picture_decode(state))
            else:
                logging.debug("decode_sequence: Picture")
                picture_parse(state)
                decoded_pictures.append(picture_decode(state))
        elif is_auxiliary_data(state):  # Excluded in spec pseudo code
            logging.debug("decode_sequence: Auxiliary Data")
            auxiliary_data(state)
        elif is_padding_data(state):  # Excluded in spec pseudo code
            logging.debug("decode_sequence: Padding")
            padding(state)
        parse_info(state)
    
    return video_parameters, decoded_pictures


################################################################################
# (11) Sequence header parsing
################################################################################


def sequence_header(state):
    """(11.1) Parse a sequence header returning a VideoParameters object."""
    byte_align(state)
    
    parse_parameters(state)
    
    base_video_format = read_uint(state)
    video_parameters = source_parameters(state, base_video_format)
    
    picture_coding_mode = read_uint(state)
    set_coding_parameters(state, video_parameters, picture_coding_mode)
    
    return video_parameters


def parse_parameters(state):
    """(11.2.1)"""
    major_version = read_uint(state)
    minor_version = read_uint(state)
    profile = read_uint(state)
    level = read_uint(state)
    
    # (11.2.1) Values must be byte-for-byte identical in every parse parameters
    # block read.
    assert state.major_version is None or state.major_version == major_version
    state.major_version = major_version
    
    assert state.minor_version is None or state.minor_version == minor_version
    state.minor_version = minor_version
    
    assert state.profile is None or state.profile == profile
    state.profile = profile
    
    assert state.level is None or state.level == level
    state.level = level


def source_parameters(state, base_video_format):
    """
    (11.4.1) Parse the video source parameters. Returns a VideoParameters
    object.
    """
    video_parameters = set_source_defaults(base_video_format)
    
    frame_size(state, video_parameters)
    color_diff_sampling_format(state, video_parameters)
    scan_format(state, video_parameters)
    frame_rate(state, video_parameters)
    pixel_aspect_ratio(state, video_parameters)
    clean_area(state, video_parameters)
    signal_range(state, video_parameters)
    color_spec(state, video_parameters)
    
    return video_parameters


@attrs
class VideoParameters(object):
    """(11.4) Video parameters struct."""
    
    frame_width = attrib()
    frame_height = attrib()
    """(11.4.3)"""
    
    color_diff_format_index = attrib()
    """
    (11.4.4) An index in the enum ColorDifferenceSamplingFormats (e.g. 1 for
    '4:2:2').
    """
    
    source_sampling = attrib()
    """
    (11.4.5) An index in the enum SourceSamplingModes (e.g. progressive/interlaced).
    """
    
    top_field_first = attrib()
    """
    (11.4.5) Bool.
    """
    
    frame_rate_numer = attrib()
    frame_rate_denom = attrib()
    """(11.4.6)"""
    
    pixel_aspect_ratio_numer = attrib()
    pixel_aspect_ratio_denom = attrib()
    """(11.4.7)"""
    
    clean_width = attrib()
    clean_height = attrib()
    left_offset = attrib()
    top_offset = attrib()
    """(11.4.8)"""
    
    luma_offset = attrib()
    luma_excursion = attrib()
    color_diff_offset = attrib()
    color_diff_excursion = attrib()
    """(11.4.9)"""
    
    color_primaries = attrib()
    """(11.4.10.2) A ColorPrimaries object."""
    
    color_matrix = attrib()
    """(11.4.10.3) A ColorMatrix object."""
    
    transfer_function = attrib()
    """(11.4.10.4) A TransferFunction object."""


def set_source_defaults(base_video_format):
    """
    (11.4.2) Create a VideoParameters object with the parameters specified in a
    base video format.
    """
    base = BASE_VIDEO_FORMAT_PARAMETERS[BaseVideoFormats(base_video_format)]
    return VideoParameters(
        frame_width=base.frame_width,
        frame_height=base.frame_height,
        color_diff_format_index=base.color_diff_format_index,
        source_sampling=base.source_sampling,
        top_field_first=base.top_field_first,
        frame_rate_numer=PRESET_FRAME_RATES[base.frame_rate_index].numerator,
        frame_rate_denom=PRESET_FRAME_RATES[base.frame_rate_index].denominator,
        pixel_aspect_ratio_numer=PRESET_PIXEL_ASPECT_RATIOS[base.pixel_aspect_ratio_index].numerator,
        pixel_aspect_ratio_denom=PRESET_PIXEL_ASPECT_RATIOS[base.pixel_aspect_ratio_index].denominator,
        clean_width=base.clean_width,
        clean_height=base.clean_height,
        left_offset=base.left_offset,
        top_offset=base.top_offset,
        luma_offset=PRESET_SIGNAL_RANGES[base.signal_range_index].luma_offset,
        luma_excursion=PRESET_SIGNAL_RANGES[base.signal_range_index].luma_excursion,
        color_diff_offset=PRESET_SIGNAL_RANGES[base.signal_range_index].color_diff_offset,
        color_diff_excursion=PRESET_SIGNAL_RANGES[base.signal_range_index].color_diff_excursion,
        color_primaries=PRESET_COLOR_PRIMARIES[PRESET_COLOR_SPECS[base.color_spec_index].color_primaries_index],
        color_matrix=PRESET_COLOR_MATRICES[PRESET_COLOR_SPECS[base.color_spec_index].color_matrix_index],
        transfer_function=PRESET_TRANSFER_FUNCTIONS[PRESET_COLOR_SPECS[base.color_spec_index].transfer_function_index],
    )

def frame_size(state, video_parameters):
    """(11.4.3) Override video parameter."""
    custom_dimensions_flag = read_bool(state)
    if custom_dimensions_flag:
        video_parameters.frame_width = read_uint(state)
        video_parameters.frame_height = read_uint(state)

def color_diff_sampling_format(state, video_parameters):
    """(11.4.4) Override color sampling parameter."""
    custom_color_diff_format_flag = read_bool(state)
    if custom_color_diff_format_flag:
        video_parameters.color_diff_format_index = read_uint(state)

def scan_format(state, video_parameters):
    """(11.4.5) Override source sampling parameter."""
    custom_scan_format_flag = read_bool(state)
    if custom_scan_format_flag:
        video_parameters.source_sampling = read_uint(state)

def frame_rate(state, video_parameters):
    """(11.4.6) Override frame-rate parameter."""
    custom_frame_rate_flag = read_bool(state)
    if custom_frame_rate_flag:
        index = read_uint(state)
        if index == 0:
            video_parameters.frame_rate_numer = read_uint(state)
            video_parameters.frame_rate_denom = read_uint(state)
        else:
            preset_frame_rate(video_parameters, index)

def pixel_aspect_ratio(state, video_parameters):  # Erata: called 'aspect_ratio' in spec
    """(11.4.7) Override pixel aspect ratio parameter."""
    custom_pixel_aspect_ratio_flag = read_bool(state)
    if custom_pixel_aspect_ratio_flag:
        index = read_uint(state)
        if index == 0:
            video_parameters.pixel_aspect_ratio_numer = read_uint(state)
            video_parameters.pixel_aspect_ratio_denom = read_uint(state)
        else:
            preset_pixel_aspect_ratio(video_parameters, index)

def clean_area(state, video_parameters):
    """(11.4.8) Override clean area parameter."""
    custom_clean_area_flag = read_bool(state)
    if custom_clean_area_flag:
        video_parameters.clean_width = read_uint(state)
        video_parameters.clean_height = read_uint(state)
        video_parameters.left_offset = read_uint(state)
        video_parameters.top_offset = read_uint(state)

def signal_range(state, video_parameters):
    """(11.4.9) Override signal parameter."""
    custom_signal_range_flag = read_bool(state)
    if custom_signal_range_flag:
        index = read_uint(state)
        if index == 0:
            video_parameters.luma_offset = read_uint(state)
            video_parameters.luma_excursion = read_uint(state)
            video_parameters.color_diff_offset = read_uint(state)
            video_parameters.color_diff_excursion = read_uint(state)
        else:
            preset_signal_range(video_parameters, index)

def color_spec(state, video_parameters):
    """(11.4.10.1) Override color specification parameter."""
    custom_color_spec_flag = read_bool(state)
    if custom_color_spec_flag:
        index = read_uint(state)
        preset_color_spec(video_parameters, index)
        if index == 0:
            color_primaries(state, video_parameters)
            color_matrix(state, video_parameters)
            transfer_function(state, video_parameters)

def color_primaries(state, video_parameters):
    """(11.4.10.2) Override color primaries parameter."""
    custom_color_primaries_flag = read_bool(state)
    if custom_color_primaries_flag:
        index = read_uint(state)
        preset_color_primaries(video_parameters, index)

def color_matrix(state, video_parameters):
    """(11.4.10.3) Override color matrix parameter."""
    custom_color_matrix_flag = read_bool(state)
    if custom_color_matrix_flag:
        index = read_uint(state)
        preset_color_matrix(video_parameters, index)

def transfer_function(state, video_parameters):
    """(11.4.10.4) Override color transfer function parameter."""
    custom_transfer_function_flag = read_bool(state)
    if custom_transfer_function_flag:
        index = read_uint(state)
        preset_transfer_function(video_parameters, index)

def set_coding_parameters(state, video_parameters, picture_coding_mode):
    """(11.6.1) Set picture coding mode parameter."""
    picture_dimensions(state, video_parameters, picture_coding_mode)
    video_depth(state, video_parameters)

def picture_dimensions(state, video_parameters, picture_coding_mode):
    """(11.6.2) Compute the picture component dimensions in global state."""
    state.luma_width = video_parameters.frame_width
    state.luma_height = video_parameters.frame_height
    state.color_diff_width = state.luma_width
    state.color_diff_height = state.luma_height
    
    color_diff_format_index = video_parameters.color_diff_format_index
    if color_diff_format_index == ColorDifferenceSamplingFormats.color_4_2_2.value:
        state.color_diff_width //= 2
    if color_diff_format_index == ColorDifferenceSamplingFormats.color_4_2_0.value:
        state.color_diff_width //= 2
        state.color_diff_height //= 2
    
    if picture_coding_mode == PictureCodingModes.pictures_are_fields.value:
        state.luma_height //= 2
        state.color_diff_height //= 2

def video_depth(state, video_parameters):
    """(11.6.3) Compute the bits-per-sample for the decoded video."""
    state.luma_depth = intlog2(video_parameters.luma_excursion + 1)
    state.color_diff_depth = intlog2(video_parameters.color_diff_excursion + 1)

def preset_frame_rate(video_parameters, index):
    """(11.4.6) Set frame rate from preset."""
    preset = PRESET_FRAME_RATES[PresetFrameRates(index)]
    video_parameters.frame_rate_numer = preset.numerator
    video_parameters.frame_rate_denom = preset.denominator


def preset_pixel_aspect_ratio(video_parameters, index):  # Erata: called 'preset_aspect_ratio' in spec
    """(11.4.7) Set pixel aspect ratio from preset."""
    preset = PRESET_PIXEL_ASPECT_RATIOS[PresetPixelAspectRatios(index)]
    video_parameters.pixel_aspect_ratio_numer = preset.numerator
    video_parameters.pixel_aspect_ratio_denom = preset.denominator

def preset_signal_range(video_parameters, index):
    """(11.4.7) Set signal range from preset."""
    preset = PRESET_SIGNAL_RANGES[PresetSignalRanges(index)]
    video_parameters.luma_offset = preset.luma_offset
    video_parameters.luma_excursion = preset.luma_excursion
    video_parameters.color_diff_offset = preset.color_diff_offset
    video_parameters.color_diff_excursion = preset.color_diff_excursion


def preset_color_primaries(video_parameters, index):
    """(11.4.10.2) Set the color primaries parameter from a preset."""
    video_parameters.color_primaries = PRESET_COLOR_PRIMARIES[PresetColorPrimaries(index)]

def preset_color_matrix(video_parameters, index):
    """(11.4.10.3) Set the color matrix parameter from a preset."""
    video_parameters.color_matrix = PRESET_COLOR_MATRICES[PresetColorMatrices(index)]


def preset_transfer_function(video_parameters, index):
    """(11.4.10.4) Set the transfer function parameter from a preset."""
    video_parameters.transfer_function = PRESET_TRANSFER_FUNCTIONS[PresetTransferFunctions(index)]


def preset_color_spec(video_parameters, index):
    """(11.4.10.1) Load a preset colour specification."""
    preset = PRESET_COLOR_SPECS[PresetColorSpecs(index)]
    preset_color_primaries(video_parameters, preset.color_primaries_index)
    preset_color_matrix(video_parameters, preset.color_matrix_index)
    preset_transfer_function(video_parameters, preset.transfer_function_index)





################################################################################
# (ST 2042-2) Levels
################################################################################

# TODO


################################################################################
# (12) Picture syntax
################################################################################

def picture_parse(state):
    """(12.1)"""
    byte_align(state)
    picture_header(state)
    byte_align(state)
    wavelet_transform(state)

def picture_header(state):
    """(12.2)"""
    state.picture_number = read_uint_lit(state, 4)

def wavelet_transform(state):
    """(12.3)"""
    transform_parameters(state)
    byte_align(state)
    transform_data(state)

def transform_parameters(state):
    """(12.4.1) Read transform parameters."""
    state.wavelet_index = read_uint(state)
    state.dwt_depth = read_uint(state)
    
    state.wavelet_index_ho = state.wavelet_index
    state.dwt_depth_ho = 0
    if state.major_version >= 3:
        extended_transform_parameters(state)
    
    slice_parameters(state)
    quant_matrix(state)
    
    logging.debug("transform_parameters: Wavelet: %d depth %d",
        state.wavelet_index, state.dwt_depth)
    logging.debug("transform_parameters: Horizontal-Only Wavelet: %d depth %d",
        state.wavelet_index_ho, state.dwt_depth_ho)

def extended_transform_parameters(state):
    """(12.4.4.1) Read horizontal only transform parameters."""
    asym_transform_index_flag = read_bool(state)
    if asym_transform_index_flag:
        state.wavelet_index_ho = read_uint(state)
    
    asym_transform_flag = read_bool(state)
    if asym_transform_flag:
        state.dwt_depth_ho = read_uint(state)

def slice_parameters(state):
    """(12.4.5.2) Read slice parameters"""
    state.slices_x = read_uint(state)
    state.slices_y = read_uint(state)
    
    if is_ld_picture(state):
        state.slice_bytes_numerator = read_uint(state)
        state.slice_bytes_denominator = read_uint(state)
    if is_hq_picture(state):
        state.slice_prefix_bytes = read_uint(state)
        state.slice_size_scaler = read_uint(state)
    
    logging.debug("slice_parameters: %d x-slices, %d y-slices",
        state.slices_x, state.slices_y)
    if is_ld_picture(state):
        logging.debug("slice_parameters: slice_bytes = %d/%d",
            state.slice_bytes_numerator,
            state.slice_bytes_denominator)
    if is_hq_picture(state):
        logging.debug("slice_parameters: slice_prefix_bytes = %d",
            state.slice_prefix_bytes)
        logging.debug("slice_parameters: slice_size_scaler = %d",
            state.slice_size_scaler)

def quant_matrix(state):
    """(12.4.5.3) Read quantisation matrix"""
    custom_quant_matrix = read_bool(state)
    if custom_quant_matrix:
        if state.dwt_depth_ho == 0:
            state.quant_matrix[0][LL] = read_uint(state)
        else:
            # Read horizontal-only part
            state.quant_matrix[0][L] = read_uint(state)
            for level in range(1, state.dwt_depth_ho + 1):
                state.quant_matrix[level][H] = read_uint(state)
        
        # Read 2D part
        for level in range(state.dwt_depth_ho + 1,
                           state.dwt_depth_ho + state.dwt_depth + 1):
            state.quant_matrix[level][HL] = read_uint(state)
            state.quant_matrix[level][LH] = read_uint(state)
            state.quant_matrix[level][HH] = read_uint(state)
    else:
        set_quant_matrix(state)
    
    for level, entries in sorted(state.quant_matrix.items()):
        logging.debug("quant_matrix: Level %d: %s",
            level,
            ", ".join("{}: {}".format(
                key._name, value) for key, value in entries.items()),
        )


def set_quant_matrix(state):
    """
    (12.4.5.3) Load a default quantisation matrix from the values specified
    in (D).
    """
    state.quant_matrix = DEFAULT_QUANTISATION_MATRICES[(
        state.wavelet_index_ho,
        state.wavelet_index,
    )][(
        state.dwt_depth_ho,
        state.dwt_depth,
    )]

################################################################################
# (13) Transform data syntax
################################################################################

def subband_width(state, level, comp):
    """(13.2.3)"""
    if comp is Y:
        w = state.luma_width
    elif comp is C1 or comp is C2:
        w = state.color_diff_width
    
    # Round up (pad) the picture width to the nearest multiple of the scale
    # width
    scale_w = 1 << (state.dwt_depth_ho + state.dwt_depth)
    pw = scale_w * ((w + scale_w - 1) // scale_w)
    
    if level == 0:
        return pw // (1 << (state.dwt_depth_ho + state.dwt_depth))
    elif level <= state.dwt_depth_ho:
        return pw // (1 << (state.dwt_depth_ho + state.dwt_depth - level + 1))
    elif level > state.dwt_depth_ho:
        return pw // (1 << (state.dwt_depth_ho + state.dwt_depth - level + 1))

def subband_height(state, level, comp):
    """(13.2.3)"""
    if comp is Y:
        h = state.luma_height
    elif comp is C1 or comp is C2:
        h = state.color_diff_height
    
    # Round up (pad) the picture height to the nearest multiple of the scale
    # height
    scale_h = 1 << state.dwt_depth
    ph = scale_h * ((h + scale_h - 1) // scale_h)
    
    if level == 0:
        return ph // (1 << state.dwt_depth)
    elif level <= state.dwt_depth_ho:
        return ph // (1 << state.dwt_depth)
    elif level > state.dwt_depth_ho:
        return ph // (1 << (state.dwt_depth_ho + state.dwt_depth - level + 1))


def inverse_quant(quantized_coeff, quant_index):
    """(13.3.1)"""
    magnitude = abs(quantized_coeff)
    if magnitude != 0:
        magnitude *= quant_factor(quant_index)
        magnitude += quant_offset(quant_index)
        
        # NB: The quant_factor is returned multiplied by four (since
        # quantisation occurs at a quarter-bit granularity). As a consequence
        # the following lines implement divide-by-four-and-round.
        magnitude += 2
        magnitude //= 4
    
    return sign(quantized_coeff) * magnitude


def quant_factor(index):
    """(13.3.2)"""
    base = 1 << (index//4)
    
    # NB: In the following, the integer fractions are 'good' (better than
    # 32 significant bits) integer approximations of:
    #
    #    (4 * 2**((index%4) / 4)) * base + 0.5
    #
    # With the additional '0.5' being added to compensate for the rounding of
    # the original quantisation values.
    if index%4 == 0:
        return 4 * base
    elif index%4 == 1:
        return ((503829 * base) + 52958) // 105917
    elif index%4 == 2:
        return ((665857 * base) + 58854) // 117708
    elif index%4 == 3:
        return ((440253 * base) + 32722) // 65444


def quant_offset(index):
    """(13.3.2)"""
    if index == 0:
        return 1
    elif index == 1:
        return 2
    else:
        return (quant_factor(index) + 1) // 2


def dc_prediction(band):
    """(13.4) Update a 2D array which makes use of DC prediction."""
    for y in range(height(band)):
        for x in range(width(band)):
            if x > 0 and y > 0:
                prediction = mean((band[y][x-1], band[y-1][x-1], band[y-1][x]))
            elif x > 0 and y == 0:
                prediction = band[0][x - 1]
            elif x == 0 and y > 0:
                prediction = band[y - 1][0]
            else:
                prediction = 0
            band[y][x] += prediction


def transform_data(state):
    """(13.5.2)"""
    state.y_transform = initialize_wavelet_data(state, Y)
    state.c1_transform = initialize_wavelet_data(state, C1)
    state.c2_transform = initialize_wavelet_data(state, C2)
    
    for sy in range(state.slices_y):
        for sx in range(state.slices_x):
            slice(state, sx, sy)
    
    if using_dc_prediction(state):
        if state.dwt_depth_ho == 0:
            dc_prediction(state.y_transform[0][LL])
            dc_prediction(state.c1_transform[0][LL])
            dc_prediction(state.c2_transform[0][LL])
        else:
            dc_prediction(state.y_transform[0][L])
            dc_prediction(state.c1_transform[0][L])
            dc_prediction(state.c2_transform[0][L])
    
    logging.debug("transform_data: read %d slices",
        state.slices_x * state.slices_y)


def initialize_wavelet_data(state, comp):
    """(13.2.2) Return a ready-to-fill datastructure."""
    out = {}
    
    if state.dwt_depth_ho == 0:
        out[0] = {LL: array(subband_width(state, 0, comp),
                            subband_height(state, 0, comp))}
    else:
        out[0] = {L: array(subband_width(state, 0, comp),
                           subband_height(state, 0, comp))}
        for level in range(1, state.dwt_depth_ho + 1):
            out[level] = {H: array(subband_width(state, level, comp),
                                   subband_height(state, level, comp))}
    
    for level in range(state.dwt_depth_ho + 1,
                       state.dwt_depth_ho + state.dwt_depth + 1):
        out[level] = {orient: array(subband_width(state, level, comp),
                                    subband_height(state, level, comp))
                      for orient in [HL, LH, HH]}
    
    return out


def slice(state, sx, sy):
    """(13.5.2)"""
    if is_ld_picture(state):
        ld_slice(state, sx, sy)
    elif is_hq_picture(state):
        hq_slice(state, sx, sy)


def ld_slice(state, sx, sy):
    """(13.5.3.1)"""
    slice_bits_left = 8*slice_bytes(state, sx, sy)
    
    qindex = read_nbits(state, 7)
    slice_bits_left -= 7
    
    slice_quantizers(state, qindex)
    
    length_bits = intlog2((8 * slice_bytes(state, sx, sy)) - 7)
    slice_y_length = read_nbits(state, length_bits)
    slice_bits_left -= length_bits
    
    state.bits_left = slice_y_length
    if state.dwt_depth_ho == 0:
        # Erata: standard says 'luma_slice_band(state, 0, LL, sx, sy)'
        slice_band(state, state.y_transform, 0, LL, sx, sy)
        for level in range(1, state.dwt_depth + 1):
            for orient in [HL, LH, HH]:
                slice_band(state, state.y_transform, level, orient, sx, sy)
    else:
        # Erata: standard says 'luma_slice_band(state, 0, L, sx, sy)'
        slice_band(state, state.y_transform, 0, L, sx, sy)
        for level in range(1, state.dwt_depth_ho + 1):
            slice_band(state, state.y_transform, level, H, sx, sy)
        for level in range(state.dwt_depth_ho + 1, 
                           state.dwt_depth_ho + state.dwt_depth + 1):
            for orient in [HL, LH, HH]:
                slice_band(state, state.y_transform, level, orient, sx, sy)
    
    flush_inputb(state)
    
    slice_bits_left -= slice_y_length
    
    state.bits_left = slice_bits_left
    color_diff_slice_band(state, 0, LL, sx, sy)
    for level in range(1, state.dwt_depth + 1):
        for orient in [HL, LH, HH]:
            color_diff_slice_band(state, level, orient, sx, sy)
    flush_inputb(state)


def slice_bytes(state, sx, sy):
    """(13.5.3.2) Compute the number of bytes in a low-delay picture slice."""
    slice_number = (sy * state.slices_x) + sx
    bytes = (((slice_number + 1) * state.slice_bytes_numerator) //
             state.slice_bytes_denominator)
    bytes -= ((slice_number * state.slice_bytes_numerator) //
              state.slice_bytes_denominator)
    return bytes


def hq_slice(state, sx, sy):
    """(13.5.4)"""
    # NB: Skip and ignore prefix bytes
    read_uint_lit(state, state.slice_prefix_bytes)
    
    qindex = read_uint_lit(state, 1)
    slice_quantizers(state, qindex)
    
    for transform in [state.y_transform,
                      state.c1_transform,
                      state.c2_transform]:
        length = state.slice_size_scaler * read_uint_lit(state, 1)
        state.bits_left = 8*length
        
        if state.dwt_depth_ho == 0:
            slice_band(state, transform, 0, LL, sx, sy)
            for level in range(1, state.dwt_depth + 1):
                for orient in [HL, LH, HH]:
                    slice_band(state, transform, level, orient, sx, sy)
        else:
            slice_band(state, transform, 0, L, sx, sy)
            for level in range(1, state.dwt_depth_ho + 1):
                slice_band(state, transform, level, H, sx, sy)
            for level in range(state.dwt_depth_ho + 1,
                               state.dwt_depth_ho + state.dwt_depth + 1):
                for orient in [HL, LH, HH]:
                    slice_band(state, transform, level, orient, sx, sy)
        flush_inputb(state)


def slice_quantizers(state, qindex):
    """
    (13.5.5) Work out the quantizer setting for each level/subband for this
    index and the current matrix.
    """
    if state.dwt_depth_ho == 0:
        state.quantizer[0][LL] = max(qindex - state.quant_matrix[0][LL], 0)
        for level in range(1, state.dwt_depth + 1):
            for orient in [HL, LH, HH]:
                state.quantizer[level][orient] = max(
                    qindex - state.quant_matrix[level][orient], 0)
    else:
        state.quantizer[0][L] = max(qindex - state.quant_matrix[0][L], 0)
        for level in range(1, state.dwt_depth_ho + 1):
            state.quantizer[level][H] = max(qindex - state.quant_matrix[level][H], 0)
        
        for level in range(state.dwt_depth_ho + 1,
                           state.dwt_depth_ho + state.dwt_depth + 1):
            for orient in [HL, LH, HH]:
                state.quantizer[level][orient] = max(
                    qindex - state.quant_matrix[level][orient], 0)


def slice_left(state, sx, c, level):
    """(13.5.6.2) Get the x coordinate of the LHS of the given slice."""
    return (subband_width(state, level, c) * sx) // state.slices_x

def slice_right(state, sx, c, level):
    """(13.5.6.2) Get the x coordinate of the RHS of the given slice."""
    return (subband_width(state, level, c) * (sx + 1)) // state.slices_x

def slice_top(state, sy, c, level):
    """(13.5.6.2) Get the y coordinate of the top of the given slice."""
    return (subband_height(state, level, c) * sy) // state.slices_y

def slice_bottom(state, sy, c, level):
    """(13.5.6.2) Get the y coordinate of the bottom of the given slice."""
    return (subband_height(state, level, c) * (sy + 1)) // state.slices_y

def slice_band(state, transform, level, orient, sx, sy):
    """(13.5.6.3) Read and dequantize a subband in a slice."""
    for y in range(slice_top(state, sy, Y, level), slice_bottom(state, sy, Y, level)):
        for x in range(slice_left(state, sx, Y, level), slice_right(state, sx, Y, level)):
            val = read_sintb(state)
            qi = state.quantizer[level][orient]
            transform[level][orient][y][x] = inverse_quant(val, qi)

def color_diff_slice_band(state, level, orient, sx, sy):
    """(13.5.6.4) Read and dequantize interleaved color difference subbands in a slice."""
    qi = state.quantizer[level][orient]
    for y in range(slice_top(state, sy, C1, level), slice_bottom(state, sy, C1, level)):
        for x in range(slice_left(state, sx, C1, level), slice_right(state, sx, C1, level)):
            qi = state.quantizer[level][orient]
            
            val = read_sintb(state)
            state.c1_transform[level][orient][y][x] = inverse_quant(val, qi)
            
            val = read_sintb(state)
            state.c2_transform[level][orient][y][x] = inverse_quant(val, qi)


################################################################################
# (14) Fragment syntax
################################################################################

def fragment_parse(state):
    """(14.1)"""
    byte_align(state)
    fragment_header(state)
    if state.fragment_slice_count == 0:
        byte_align(state)
        transform_parameters(state)
        initialize_fragment_state(state)
    else:
        byte_align(state)
        fragment_data(state)


def fragment_header(state):
    """14.2"""
    state.picture_number = read_uint_lit(state, 4)
    state.fragment_data_length = read_uint_lit(state, 2)
    state.fragment_slice_count = read_uint_lit(state, 2)
    if state.fragment_slice_count != 0:
        state.fragment_x_offset = read_uint_lit(2)
        state.fragment_y_offset = read_uint_lit(2)


def initialize_fragment_state(state):
    """(14.3)"""
    state.y_transform = initialize_wavelet_data(state, Y)
    state.c1_transform = initialize_wavelet_data(state, C1)
    state.c2_transform = initialize_wavelet_data(state, C2)
    state.fragment_slices_received = 0
    state.fragment_picture_done = False


def fragment_data(state):
    """(14.4) Unpack and dequantize transform data from a fragment."""
    for s in range(state.fragment_slice_count + 1):
        state.slice_x = (
            ((state.fragment_y_offset * state.slices_x) +
             state.fragment_x_offset + s) % state.slices_x
        )
        state.slice_y = (
            ((state.fragment_y_offset * state.slices_x) +
             state.fragment_x_offset + s) // state.slices_x
        )
        slice(state, state.slice_x, state.slice_y)
        state.fragment_slices_received += 1
        
        if state.fragment_slices_received == (state.slice_x * state.slice_y):
            state.fragmented_picture_done = True
            if using_dc_prediction(state):
                if state.dwt_depth_ho == 0:
                    dc_prediction(state.y_transform[0][LL])
                    dc_prediction(state.c1_transform[0][LL])
                    dc_prediction(state.c2_transform[0][LL])
                else:
                    dc_prediction(state.y_transform[0][L])
                    dc_prediction(state.c1_transform[0][L])
                    dc_prediction(state.c2_transform[0][L])


################################################################################
# (15) Picture decoding
################################################################################


def picture_decode(state):
    """
    (15.2) Decode (inverse wavelet transform, clip and offset) a picture and
    return it (in the same format as state.current_picture).
    """
    state.current_picture = {}
    state.current_picture[pic_num] = state.picture_number
    
    inverse_wavelet_transform(state)
    clip_picture(state, state.current_picture)
    offset_picture(state, state.current_picture)
    
    logging.debug("picture_decode: picture decoded, clipped and offset")
    
    return state.current_picture


def inverse_wavelet_transform(state):
    """(15.3)"""
    state.current_picture[Y] = idwt(state, state.y_transform)
    state.current_picture[C1] = idwt(state, state.c1_transform)
    state.current_picture[C2] = idwt(state, state.c2_transform)
    
    for c in [Y, C1, C2]:
        idwt_pad_removal(state, state.current_picture[c], c)


def row(a, k):
    """
    (15.4.1) A 1D-array-like view into a row of a (2D) nested list as returned
    by 'array()'.
    """
    # Easy case...
    return a[k]


class column(object):
    """
    (15.4.1) A 1D-array-like view into a column of a (2D) nested list as returned
    by 'array()'.
    """
    
    def __init__(self, a, k):
        self._a = a
        self._k = k
    
    def __getitem__(self, key):
        # NB: Slices not supported...
        assert isinstance(key, int)
        return self._a[key][self._k]
    
    def __setitem__(self, key, value):
        # NB: Slices not supported...
        assert isinstance(key, int)
        self._a[key][self._k] = value
    
    def __len__(self):
        return len(self._a)


def idwt(state, coeff_data):
    """(15.4.1) Actual IDWT implementation."""
    if state.dwt_depth_ho == 0:
        DC_band = coeff_data[0][LL]
    else:
        DC_band = coeff_data[0][L]
    
    for n in range(1, state.dwt_depth_ho + 1):
        new_DC_band = h_synthesis(state, DC_band, coeff_data[n][H])
        DC_band = new_DC_band
    
    for n in range(state.dwt_depth_ho + 1,
                   state.dwt_depth_ho + state.dwt_depth + 1):
        new_DC_band = vh_synthesis(state, DC_band,
                                   coeff_data[n][HL],
                                   coeff_data[n][LH],
                                   coeff_data[n][HH])
        DC_band = new_DC_band
    
    return DC_band


def h_synthesis(state, L_data, H_data):
    """(15.4.2)"""
    # Step 1
    synth = array(2 * width(L_data), height(L_data))
    
    # Step 2
    for y in range(height(synth)):
        for x in range(width(synth)//2):
            synth[y][2*x] = L_data[y][x]
            synth[y][(2*x) + 1] = H_data[y][x]
    
    # Step 3
    for y in range(height(synth)):
        oned_synthesis(row(synth, y), state.wavelet_index_ho)
    
    # Step 4
    shift = filter_bit_shift(state)
    if shift > 0:
        for y in range(height(synth)):
            for x in range(width(synth)):
                # NB: Shift rounds rather than floors.
                synth[y][x] = (synth[y][x] + (1 << (shift - 1))) >> shift
    
    return synth


def vh_synthesis(state, LL_data, HL_data, LH_data, HH_data):
    """(15.4.2)"""
    # Step 1
    synth = array(2 * width(LL_data), 2 * height(LL_data))
    
    # Step 2
    for y in range(height(synth)//2):
        for x in range(width(synth)//2):
            synth[2*y][2*x] = LL_data[y][x]
            synth[2*y][(2*x) + 1] = HL_data[y][x]
            synth[(2*y) + 1][2*x] = LH_data[y][x]
            synth[(2*y) + 1][(2*x) + 1] = HH_data[y][x]
    
    # Step 3
    for x in range(width(synth)):
        oned_synthesis(column(synth, x), state.wavelet_index)
    for y in range(height(synth)):
        oned_synthesis(row(synth, y), state.wavelet_index_ho)
    
    # Step 4
    shift = filter_bit_shift(state)
    if shift > 0:
        for y in range(height(synth)):
            for x in range(width(synth)):
                # NB: Shift rounds rather than floors.
                synth[y][x] = (synth[y][x] + (1 << (shift - 1))) >> shift
    
    return synth


def filter_bit_shift(state):
    """(15.4.2) Return the bit shift for the current horizontal-only filter."""
    filter_params = LIFTING_FILTER_PARAMETERS[state.wavelet_index_ho]
    return filter_params.filter_bit_shift


def oned_synthesis(A, filter_index):
    """(15.4.4.1) and (15.4.4.3). Acts in-place on 'A'"""
    assert len(A) % 2 == 0
    
    filter_params = LIFTING_FILTER_PARAMETERS[filter_index]
    
    for stage in filter_params.stages:
        lift_fn = LIFTING_FUNCTION_TYPES[stage.lift_type]
        lift_fn(A, stage.L, stage.D, stage.taps, stage.S)


def lift1(A, L, D, taps, S):
    """(15.4.4.1) Even add weighted odd values."""
    assert L == len(taps)
    for n in range(0, len(A)//2):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i) - 1
            pos = min(pos, len(A) - 1)
            pos = max(pos, 1)
            sum += taps[i-D] * A[pos]
        if S > 0:
            sum += (1<<(S-1))
        A[2*n] += sum >> S

def lift2(A, L, D, taps, S):
    """(15.4.4.1) Even subtract weighted odd values."""
    assert L == len(taps)
    for n in range(0, len(A)//2):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i) - 1
            pos = min(pos, len(A) - 1)
            pos = max(pos, 1)
            sum += taps[i-D] * A[pos]
        if S > 0:
            sum += (1<<(S-1))
        A[2*n] -= sum >> S

def lift3(A, L, D, taps, S):
    """(15.4.4.1) Odd add weighted even values."""
    assert L == len(taps)
    for n in range(0, len(A)//2):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i)
            pos = min(pos, len(A) - 2)
            pos = max(pos, 0)
            sum += taps[i-D] * A[pos]
        if S > 0:
            sum += (1<<(S-1))
        A[2*n + 1] += sum >> S

def lift4(A, L, D, taps, S):
    """(15.4.4.1) Odd subtract weighted even values."""
    assert L == len(taps)
    for n in range(0, len(A)//2):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i)
            pos = min(pos, len(A) - 2)
            pos = max(pos, 0)
            sum += taps[i-D] * A[pos]
        if S > 0:
            sum += (1<<(S-1))
        A[2*n + 1] -= sum >> S


LIFTING_FUNCTION_TYPES = {
    1: lift1,
    2: lift2,
    3: lift3,
    4: lift4,
}
"""A mapping from integers to their corresponding functions."""


@attrs
class LiftingStage(object):
    """
    (15.4.4.1) Definition of a lifting stage/operation in a lifting filter.
    """
    
    lift_type = attrib()
    """
    Specifies which lifting filtering operation is taking place. One
    of the indices from the LIFTING_FUNCTION_TYPES enumeration.
    """
    
    S = attrib()
    """Scale factor (right-shift applied to weighted sum)"""
    
    L = attrib()
    """Length of filter."""
    
    D = attrib()
    """Offset of filter."""
    
    taps = attrib()
    """An array of integers defining the filter coefficients."""

@attrs
class LiftingFilterParameters(object):
    """
    (15.4.4.3) The generic container for the details described by (Table 15.1
    to 15.6).
    """
    name = attrib()
    """Informative. The name of this filter."""
    
    filter_bit_shift = attrib()
    """Right-shift to apply after synthesis (or before analysis)."""
    
    stages = attrib()
    """
    A list of LiftingStage objects to be used in sequence to perform synthesis
    with this filter.
    """

LIFTING_FILTER_PARAMETERS = {
    0: LiftingFilterParameters(
        name="Deslauriers-Dubuc (9,7)",
        stages=[
            LiftingStage(lift_type=2, S=2, L=2, D=0, taps=[1, 1]),
            LiftingStage(lift_type=3, S=4, L=4, D=-1, taps=[-1, 9, 9, -1]),
        ],
        filter_bit_shift=1,
    ),
    1: LiftingFilterParameters(
        name="LeGall (5,3)",
        stages=[
            LiftingStage(lift_type=2, S=2, L=2, D=0, taps=[1, 1]),
            LiftingStage(lift_type=3, S=1, L=2, D=0, taps=[1, 1]),
        ],
        filter_bit_shift=1,
    ),
    2: LiftingFilterParameters(
        name="Deslauriers-Dubuc (13,7)",
        stages=[
            LiftingStage(lift_type=2, S=5, L=4, D=-1, taps=[-1, 9, 9, -1]),
            LiftingStage(lift_type=3, S=4, L=4, D=-1, taps=[-1, 9, 9, -1]),
        ],
        filter_bit_shift=1,
    ),
    3: LiftingFilterParameters(
        name="Haar filter with no shift",
        stages=[
            LiftingStage(lift_type=2, S=1, L=1, D=1, taps=[1]),
            LiftingStage(lift_type=3, S=0, L=1, D=0, taps=[1]),
        ],
        filter_bit_shift=0,
    ),
    4: LiftingFilterParameters(
        name="Haar filter with single shift",
        stages=[
            LiftingStage(lift_type=2, S=1, L=1, D=1, taps=[1]),
            LiftingStage(lift_type=3, S=0, L=1, D=0, taps=[1]),
        ],
        filter_bit_shift=1,
    ),
    5: LiftingFilterParameters(
        name="Fidelity filter",
        stages=[
            LiftingStage(lift_type=3, S=8, L=8, D=-3, taps=[-2, -10, -25, 81, 81, -25, 10, -2]),
            LiftingStage(lift_type=2, S=8, L=8, D=-3, taps=[-8, 21, -46, 161, 161, -46, 21, -8]),
        ],
        filter_bit_shift=0,
    ),
    6: LiftingFilterParameters(
        name="Integer lifting approximation to Daubechies (9,7)",
        stages=[
            LiftingStage(lift_type=2, S=12, L=2, D=0, taps=[1817, 1817]),
            LiftingStage(lift_type=4, S=12, L=2, D=0, taps=[3616, 3616]),
            LiftingStage(lift_type=1, S=12, L=2, D=0, taps=[217, 217]),
            LiftingStage(lift_type=3, S=12, L=2, D=0, taps=[6497, 6497]),
        ],
        filter_bit_shift=1,
    ),
}
"""
(15.4.4.3) Filter definitions taken from (Table 15.1 to 15.6) using the indices
normitively specified in (12.4.2) in (Table 12.1).
"""


def idwt_pad_removal(state, pic, c):
    """(15.4.5) Discard 'padding' values from a 2D array"""
    if c is Y:
        width = state.luma_width
        height = state.luma_height
    elif c is C1 or c is C2:
        width = state.color_diff_width
        height = state.color_diff_height
    
    del pic[height:]
    for row in pic:
        del row[width:]


def clip_picture(state, current_picture):
    """(15.5) Clip values to valid signal ranges."""
    for c in [Y, C1, C2]:
        clip_component(state, current_picture[c], c)


def clip_component(state, comp_data, c):
    """(15.5)"""
    for y in range(height(comp_data)):
        for x in range(width(comp_data)):
            if c is Y:
                comp_data[y][x] = clip(comp_data[y][x],
                                       -(1 << (state.luma_depth-1)),
                                       (1 << (state.luma_depth-1)) - 1)
            else:
                comp_data[y][x] = clip(comp_data[y][x],
                                       -(1 << (state.color_diff_depth-1)),
                                       (1 << (state.color_diff_depth-1)) - 1)


def offset_picture(state, current_picture):
    """(15.5)"""
    for c in [Y, C1, C2]:
        offset_component(state, current_picture[c], c)

def offset_component(state, comp_data, c):
    """(15.5)"""
    for y in range(height(comp_data)):
        for x in range(width(comp_data)):
            if c is Y:
                comp_data[y][x] += 1 << (state.luma_depth - 1)
            else:
                comp_data[y][x] += 1 << (state.color_diff_depth - 1)


################################################################################
# (D) Quantisation matrices
################################################################################

DEFAULT_QUANTISATION_MATRICES = {
    # (Table D.1) Deslauriers-Dubuc (9,7)
    (0, 0): {
        (0, 0): {
            0: {LL: 0},
        },
        (0, 1): {
            0: {LL: 5},
            1: {HL: 3, LH: 3, HH: 0},
        },
        (0, 2): {
            0: {LL: 5},
            1: {HL: 3, LH: 3, HH: 0},
            2: {HL: 4, LH: 4, HH: 1},
        },
        (0, 3): {
            0: {LL: 5},
            1: {HL: 3, LH: 3, HH: 0},
            2: {HL: 4, LH: 4, HH: 1},
            3: {HL: 5, LH: 5, HH: 2},
        },
        (0, 4): {
            0: {LL: 5},
            1: {HL: 3, LH: 3, HH: 0},
            2: {HL: 4, LH: 4, HH: 1},
            3: {HL: 5, LH: 5, HH: 2},
            4: {HL: 6, LH: 6, HH: 3},
        },
        (1, 0): {
            0: {L: 3},
            1: {H: 0},
        },
        (1, 1): {
            0: {L: 3},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 0},
        },
        (1, 2): {
            0: {L: 3},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 0},
            3: {HL: 4, LH: 4, HH: 1},
        },
        (1, 3): {
            0: {L: 3},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 0},
            3: {HL: 4, LH: 4, HH: 1},
            4: {HL: 5, LH: 5, HH: 2},
        },
        (1, 4): {
            0: {L: 3},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 0},
            3: {HL: 4, LH: 4, HH: 1},
            4: {HL: 5, LH: 5, HH: 2},
            5: {HL: 6, LH: 6, HH: 3},
        },
        (2, 0): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
        },
        (2, 1): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 5, LH: 5, HH: 3},
        },
        (2, 2): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 5, LH: 5, HH: 3},
            4: {HL: 6, LH: 6, HH: 4},
        },
        (2, 3): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 5, LH: 5, HH: 3},
            4: {HL: 6, LH: 6, HH: 4},
            5: {HL: 7, LH: 7, HH: 5},
        },
        (3, 0): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
        },
        (3, 1): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
            4: {HL: 8, LH: 8, HH: 5},
        },
        (3, 2): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
            4: {HL: 8, LH: 8, HH: 5},
            5: {HL: 9, LH: 9, HH: 6},
        },
        (4, 0): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
            4: {H: 8},
        },
        (4, 1): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
            4: {H: 8},
            5: {HL: 10, LH: 10, HH: 8},
        },
    },
    # (Table D.2) LeGall (5,3)
    (1, 1): {
        (0, 0): {
            0: {LL: 0},
        },
        (0, 1): {
            0: {LL: 4},
            1: {HL: 2, LH: 2, HH: 0},
        },
        (0, 2): {
            0: {LL: 4},
            1: {HL: 2, LH: 2, HH: 0},
            2: {HL: 4, LH: 4, HH: 2},
        },
        (0, 3): {
            0: {LL: 4},
            1: {HL: 2, LH: 2, HH: 0},
            2: {HL: 4, LH: 4, HH: 2},
            3: {HL: 5, LH: 5, HH: 3},
        },
        (0, 4): {
            0: {LL: 4},
            1: {HL: 2, LH: 2, HH: 0},
            2: {HL: 4, LH: 4, HH: 2},
            3: {HL: 5, LH: 5, HH: 3},
            4: {HL: 7, LH: 7, HH: 5},
        },
        (1, 0): {
            0: {L: 2},
            1: {H: 0},
        },
        (1, 1): {
            0: {L: 2},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 1},
        },
        (1, 2): {
            0: {L: 2},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 1},
            3: {HL: 4, LH: 4, HH: 2},
        },
        (1, 3): {
            0: {L: 2},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 1},
            3: {HL: 4, LH: 4, HH: 2},
            4: {HL: 6, LH: 6, HH: 4},
        },
        (1, 4): {
            0: {L: 2},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 1},
            3: {HL: 4, LH: 4, HH: 2},
            4: {HL: 6, LH: 6, HH: 4},
            5: {HL: 8, LH: 8, HH: 6},
        },
        (2, 0): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
        },
        (2, 1): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 6, LH: 6, HH: 4},
        },
        (2, 2): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 6, LH: 6, HH: 4},
            4: {HL: 7, LH: 7, HH: 5},
        },
        (2, 3): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 6, LH: 6, HH: 4},
            4: {HL: 7, LH: 7, HH: 5},
            5: {HL: 9, LH: 9, HH: 7},
        },
        (3, 0): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
        },
        (3, 1): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {HL: 8, LH: 8, HH: 6},
        },
        (3, 2): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {HL: 8, LH: 8, HH: 6},
            5: {HL: 10, LH: 10, HH: 8},
        },
        (4, 0): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {H: 8},
        },
        (4, 1): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {H: 8},
            5: {HL: 11, LH: 11, HH: 9},
        },
    },
    # (Table D.3) Deslauriers-Dubuc (13,7)
    (2, 2): {
        (0, 0): {
            0: {LL: 0},
        },
        (0, 1): {
            0: {LL: 5},
            1: {HL: 3, LH: 3, HH: 0},
        },
        (0, 2): {
            0: {LL: 5},
            1: {HL: 3, LH: 3, HH: 0},
            2: {HL: 4, LH: 4, HH: 1},
        },
        (0, 3): {
            0: {LL: 5},
            1: {HL: 3, LH: 3, HH: 0},
            2: {HL: 4, LH: 4, HH: 1},
            3: {HL: 5, LH: 5, HH: 2},
        },
        (0, 4): {
            0: {LL: 5},
            1: {HL: 3, LH: 3, HH: 0},
            2: {HL: 4, LH: 4, HH: 1},
            3: {HL: 5, LH: 5, HH: 2},
            4: {HL: 6, LH: 6, HH: 3},
        },
        (1, 0): {
            0: {L: 3},
            1: {H: 0},
        },
        (1, 1): {
            0: {L: 3},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 0},
        },
        (1, 2): {
            0: {L: 3},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 0},
            3: {HL: 4, LH: 4, HH: 1},
        },
        (1, 3): {
            0: {L: 3},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 0},
            3: {HL: 4, LH: 4, HH: 1},
            4: {HL: 5, LH: 5, HH: 2},
        },
        (1, 4): {
            0: {L: 3},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 0},
            3: {HL: 4, LH: 4, HH: 1},
            4: {HL: 5, LH: 5, HH: 2},
            5: {HL: 6, LH: 6, HH: 3},
        },
        (2, 0): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
        },
        (2, 1): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 5, LH: 5, HH: 2},
        },
        (2, 2): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 5, LH: 5, HH: 2},
            4: {HL: 6, LH: 6, HH: 4},
        },
        (2, 3): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 5, LH: 5, HH: 2},
            4: {HL: 6, LH: 6, HH: 4},
            5: {HL: 7, LH: 7, HH: 5},
        },
        (3, 0): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
        },
        (3, 1): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
            4: {HL: 8, LH: 8, HH: 5},
        },
        (3, 2): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
            4: {HL: 8, LH: 8, HH: 5},
            5: {HL: 9, LH: 9, HH: 6},
        },
        (4, 0): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
            4: {H: 8},
        },
        (4, 1): {
            0: {L: 3},
            1: {H: 0},
            2: {H: 3},
            3: {H: 5},
            4: {H: 8},
            5: {HL: 10, LH: 10, HH: 8},
        },
    },
    # (Table D.4) Haar with no shift
    (3, 3): {
        (0, 0): {
            0: {LL: 0},
        },
        (0, 1): {
            0: {LL: 8},
            1: {HL: 4, LH: 4, HH: 0},
        },
        (0, 2): {
            0: {LL: 12},
            1: {HL: 8, LH: 8, HH: 4},
            2: {HL: 4, LH: 4, HH: 0},
        },
        (0, 3): {
            0: {LL: 16},
            1: {HL: 12, LH: 12, HH: 8},
            2: {HL: 8, LH: 8, HH: 4},
            3: {HL: 4, LH: 4, HH: 0},
        },
        (0, 4): {
            0: {LL: 20},
            1: {HL: 16, LH: 16, HH: 12},
            2: {HL: 12, LH: 12, HH: 8},
            3: {HL: 8, LH: 8, HH: 4},
            4: {HL: 4, LH: 4, HH: 0},
        },
        (1, 0): {
            0: {L: 4},
            1: {H: 0},
        },
        (1, 1): {
            0: {L: 10},
            1: {H: 6},
            2: {HL: 4, LH: 4, HH: 0},
        },
        (1, 2): {
            0: {L: 14},
            1: {H: 10},
            2: {HL: 8, LH: 8, HH: 4},
            3: {HL: 4, LH: 4, HH: 0},
        },
        (1, 3): {
            0: {L: 18},
            1: {H: 14},
            2: {HL: 12, LH: 12, HH: 8},
            3: {HL: 8, LH: 8, HH: 4},
            4: {HL: 4, LH: 4, HH: 0},
        },
        (1, 4): {
            0: {L: 22},
            1: {H: 18},
            2: {HL: 16, LH: 16, HH: 12},
            3: {HL: 12, LH: 12, HH: 8},
            4: {HL: 8, LH: 8, HH: 4},
            5: {HL: 4, LH: 4, HH: 0},
        },
        (2, 0): {
            0: {L: 6},
            1: {H: 2},
            2: {H: 0},
        },
        (2, 1): {
            0: {L: 12},
            1: {H: 8},
            2: {H: 6},
            3: {HL: 4, LH: 4, HH: 0},
        },
        (2, 2): {
            0: {L: 16},
            1: {H: 12},
            2: {H: 10},
            3: {HL: 8, LH: 8, HH: 4},
            4: {HL: 4, LH: 4, HH: 0},
        },
        (2, 3): {
            0: {L: 20},
            1: {H: 16},
            2: {H: 14},
            3: {HL: 12, LH: 12, HH: 8},
            4: {HL: 8, LH: 8, HH: 4},
            5: {HL: 4, LH: 4, HH: 0},
        },
        (3, 0): {
            0: {L: 8},
            1: {H: 4},
            2: {H: 2},
            3: {H: 0},
        },
        (3, 1): {
            0: {L: 14},
            1: {H: 10},
            2: {H: 8},
            3: {H: 6},
            4: {HL: 4, LH: 4, HH: 0},
        },
        (3, 2): {
            0: {L: 18},
            1: {H: 14},
            2: {H: 12},
            3: {H: 10},
            4: {HL: 8, LH: 8, HH: 4},
            5: {HL: 4, LH: 4, HH: 0},
        },
        (4, 0): {
            0: {L: 10},
            1: {H: 6},
            2: {H: 4},
            3: {H: 2},
            4: {H: 0},
        },
        (4, 1): {
            0: {L: 16},
            1: {H: 12},
            2: {H: 10},
            3: {H: 8},
            4: {H: 6},
            5: {HL: 4, LH: 4, HH: 0},
        },
    },
    # (Table D.5) Haar with single shift per level
    (4, 4): {
        (0, 0): {
            0: {LL: 0},
        },
        (0, 1): {
            0: {LL: 8},
            1: {HL: 4, LH: 4, HH: 0},
        },
        (0, 2): {
            0: {LL: 8},
            1: {HL: 4, LH: 4, HH: 0},
            2: {HL: 4, LH: 4, HH: 0},
        },
        (0, 3): {
            0: {LL: 8},
            1: {HL: 4, LH: 4, HH: 0},
            2: {HL: 4, LH: 4, HH: 0},
            3: {HL: 4, LH: 4, HH: 0},
        },
        (0, 4): {
            0: {LL: 8},
            1: {HL: 4, LH: 4, HH: 0},
            2: {HL: 4, LH: 4, HH: 0},
            3: {HL: 4, LH: 4, HH: 0},
            4: {HL: 4, LH: 4, HH: 0},
        },
        (1, 0): {
            0: {L: 4},
            1: {H: 0},
        },
        (1, 1): {
            0: {L: 6},
            1: {H: 2},
            2: {HL: 4, LH: 4, HH: 0},
        },
        (1, 2): {
            0: {L: 6},
            1: {H: 2},
            2: {HL: 4, LH: 4, HH: 0},
            3: {HL: 4, LH: 4, HH: 0},
        },
        (1, 3): {
            0: {L: 6},
            1: {H: 2},
            2: {HL: 4, LH: 4, HH: 0},
            3: {HL: 4, LH: 4, HH: 0},
            4: {HL: 4, LH: 4, HH: 0},
        },
        (1, 4): {
            0: {L: 6},
            1: {H: 2},
            2: {HL: 4, LH: 4, HH: 0},
            3: {HL: 4, LH: 4, HH: 0},
            4: {HL: 4, LH: 4, HH: 0},
            5: {HL: 4, LH: 4, HH: 0},
        },
        (2, 0): {
            0: {L: 4},
            1: {H: 0},
            2: {H: 2},
        },
        (2, 1): {
            0: {L: 4},
            1: {H: 0},
            2: {H: 2},
            3: {HL: 4, LH: 4, HH: 0},
        },
        (2, 2): {
            0: {L: 4},
            1: {H: 0},
            2: {H: 2},
            3: {HL: 4, LH: 4, HH: 0},
            4: {HL: 4, LH: 4, HH: 0},
        },
        (2, 3): {
            0: {L: 4},
            1: {H: 0},
            2: {H: 2},
            3: {HL: 4, LH: 4, HH: 0},
            4: {HL: 4, LH: 4, HH: 0},
            5: {HL: 4, LH: 4, HH: 0},
        },
        (3, 0): {
            0: {L: 4},
            1: {H: 0},
            2: {H: 2},
            3: {H: 4},
        },
        (3, 1): {
            0: {L: 4},
            1: {H: 0},
            2: {H: 2},
            3: {H: 4},
            4: {HL: 6, LH: 6, HH: 2},
        },
        (3, 2): {
            0: {L: 4},
            1: {H: 0},
            2: {H: 2},
            3: {H: 4},
            4: {HL: 6, LH: 6, HH: 2},
            5: {HL: 6, LH: 6, HH: 2},
        },
        (4, 0): {
            0: {L: 4},
            1: {H: 0},
            2: {H: 2},
            3: {H: 4},
            4: {H: 6},
        },
        (4, 1): {
            0: {L: 4},
            1: {H: 0},
            2: {H: 2},
            3: {H: 4},
            4: {H: 6},
            5: {HL: 8, LH: 8, HH: 4},
        },
    },
    # (Table D.6) Fidelity
    (5, 5): {
        (0, 0): {
            0: {LL: 0},
        },
        (0, 1): {
            0: {LL: 0},
            1: {HL: 4, LH: 4, HH: 8},
        },
        (0, 2): {
            0: {LL: 0},
            1: {HL: 4, LH: 4, HH: 8},
            2: {HL: 8, LH: 8, HH: 12},
        },
        (0, 3): {
            0: {LL: 0},
            1: {HL: 4, LH: 4, HH: 8},
            2: {HL: 8, LH: 8, HH: 12},
            3: {HL: 13, LH: 13, HH: 17},
        },
        (0, 4): {
            0: {LL: 0},
            1: {HL: 4, LH: 4, HH: 8},
            2: {HL: 8, LH: 8, HH: 12},
            3: {HL: 13, LH: 13, HH: 17},
            4: {HL: 17, LH: 17, HH: 21},
        },
        (1, 0): {
            0: {L: 0},
            1: {H: 4},
        },
        (1, 1): {
            0: {L: 0},
            1: {H: 4},
            2: {HL: 6, LH: 6, HH: 10},
        },
        (1, 2): {
            0: {L: 0},
            1: {H: 4},
            2: {HL: 6, LH: 6, HH: 10},
            3: {HL: 11, LH: 11, HH: 15},
        },
        (1, 3): {
            0: {L: 0},
            1: {H: 4},
            2: {HL: 6, LH: 6, HH: 10},
            3: {HL: 11, LH: 11, HH: 15},
            4: {HL: 15, LH: 15, HH: 19},
        },
        (1, 4): {
            0: {L: 0},
            1: {H: 4},
            2: {HL: 6, LH: 6, HH: 10},
            3: {HL: 11, LH: 11, HH: 15},
            4: {HL: 15, LH: 15, HH: 19},
            5: {HL: 19, LH: 19, HH: 23},
        },
        (2, 0): {
            0: {L: 0},
            1: {H: 4},
            2: {H: 6},
        },
        (2, 1): {
            0: {L: 0},
            1: {H: 4},
            2: {H: 6},
            3: {HL: 8, LH: 8, HH: 12},
        },
        (2, 2): {
            0: {L: 0},
            1: {H: 4},
            2: {H: 6},
            3: {HL: 8, LH: 8, HH: 12},
            4: {HL: 13, LH: 13, HH: 17},
        },
        (2, 3): {
            0: {L: 0},
            1: {H: 4},
            2: {H: 6},
            3: {HL: 8, LH: 8, HH: 12},
            4: {HL: 13, LH: 13, HH: 17},
            5: {HL: 17, LH: 17, HH: 21},
        },
        (3, 0): {
            0: {L: 0},
            1: {H: 4},
            2: {H: 6},
            3: {H: 8},
        },
        (3, 1): {
            0: {L: 0},
            1: {H: 4},
            2: {H: 6},
            3: {H: 8},
            4: {HL: 11, LH: 11, HH: 15},
        },
        (3, 2): {
            0: {L: 0},
            1: {H: 4},
            2: {H: 6},
            3: {H: 8},
            4: {HL: 11, LH: 11, HH: 15},
            5: {HL: 15, LH: 15, HH: 19},
        },
        (4, 0): {
            0: {L: 0},
            1: {H: 4},
            2: {H: 6},
            3: {H: 8},
            4: {H: 11},
        },
        (4, 1): {
            0: {L: 0},
            1: {H: 4},
            2: {H: 6},
            3: {H: 8},
            4: {H: 11},
        },
    },
    # (Table D.7) Daubechies (9,7)
    (6, 6): {
        (0, 0): {
            0: {LL: 0},
        },
        (0, 1): {
            0: {LL: 3},
            1: {HL: 1, LH: 1, HH: 0},
        },
        (0, 2): {
            0: {LL: 3},
            1: {HL: 1, LH: 1, HH: 0},
            2: {HL: 4, LH: 4, HH: 2},
        },
        (0, 3): {
            0: {LL: 3},
            1: {HL: 1, LH: 1, HH: 0},
            2: {HL: 4, LH: 4, HH: 2},
            3: {HL: 6, LH: 6, HH: 5},
        },
        (0, 4): {
            0: {LL: 3},
            1: {HL: 1, LH: 1, HH: 0},
            2: {HL: 4, LH: 4, HH: 2},
            3: {HL: 6, LH: 6, HH: 5},
            4: {HL: 9, LH: 9, HH: 7},
        },
        (1, 0): {
            0: {L: 1},
            1: {H: 0},
        },
        (1, 1): {
            0: {L: 1},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 2},
        },
        (1, 2): {
            0: {L: 1},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 2},
            3: {HL: 6, LH: 6, HH: 4},
        },
        (1, 3): {
            0: {L: 1},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 2},
            3: {HL: 6, LH: 6, HH: 4},
            4: {HL: 8, LH: 8, HH: 7},
        },
        (1, 4): {
            0: {L: 1},
            1: {H: 0},
            2: {HL: 3, LH: 3, HH: 2},
            3: {HL: 6, LH: 6, HH: 4},
            4: {HL: 8, LH: 8, HH: 7},
            5: {HL: 11, LH: 11, HH: 9},
        },
        (2, 0): {
            0: {L: 1},
            1: {H: 0},
            2: {H: 3},
        },
        (2, 1): {
            0: {L: 1},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 6, LH: 6, HH: 5},
        },
        (2, 2): {
            0: {L: 1},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 6, LH: 6, HH: 5},
            4: {HL: 9, LH: 9, HH: 8},
        },
        (2, 3): {
            0: {L: 1},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 6, LH: 6, HH: 5},
            4: {HL: 9, LH: 9, HH: 8},
            5: {HL: 11, LH: 11, HH: 10},
        },
        (3, 0): {
            0: {L: 1},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
        },
        (3, 1): {
            0: {L: 1},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {HL: 10, LH: 10, HH: 8},
        },
        (3, 2): {
            0: {L: 1},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {HL: 10, LH: 10, HH: 8},
            5: {HL: 12, LH: 12, HH: 11},
        },
        (4, 0): {
            0: {L: 1},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {H: 10},
        },
        (4, 1): {
            0: {L: 1},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {H: 10},
        },
    },
    # (Table D.8) Horizontal Only: LeGall (5,3), Vertical Only: Haar (no shift)
    (1, 3): {
        (0, 0): {
            0: {LL: 0},
        },
        (0, 1): {
            0: {LL: 6},
            1: {HL: 4, LH: 2, HH: 0},
        },
        (0, 2): {
            0: {LL: 6},
            1: {HL: 4, LH: 2, HH: 0},
            2: {HL: 5, LH: 3, HH: 1},
        },
        (0, 3): {
            0: {LL: 6},
            1: {HL: 4, LH: 2, HH: 0},
            2: {HL: 5, LH: 3, HH: 1},
            3: {HL: 6, LH: 4, HH: 2},
        },
        (0, 4): {
            0: {LL: 6},
            1: {HL: 4, LH: 2, HH: 0},
            2: {HL: 5, LH: 3, HH: 1},
            3: {HL: 6, LH: 4, HH: 2},
            4: {HL: 6, LH: 5, HH: 2},
        },
        (1, 0): {
            0: {L: 2},
            1: {H: 0},
        },
        (1, 1): {
            0: {L: 3},
            1: {H: 1},
            2: {HL: 4, LH: 2, HH: 0},
        },
        (1, 2): {
            0: {L: 3},
            1: {H: 1},
            2: {HL: 4, LH: 2, HH: 0},
            3: {HL: 5, LH: 3, HH: 1},
        },
        (1, 3): {
            0: {L: 3},
            1: {H: 1},
            2: {HL: 4, LH: 2, HH: 0},
            3: {HL: 5, LH: 3, HH: 1},
            4: {HL: 6, LH: 4, HH: 2},
        },
        (1, 4): {
            0: {L: 3},
            1: {H: 1},
            2: {HL: 4, LH: 2, HH: 0},
            3: {HL: 5, LH: 3, HH: 1},
            4: {HL: 6, LH: 4, HH: 2},
            5: {HL: 6, LH: 5, HH: 2},
        },
        (2, 0): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
        },
        (2, 1): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 6, LH: 4, HH: 2},
        },
        (2, 2): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 6, LH: 4, HH: 2},
            4: {HL: 6, LH: 5, HH: 2},
        },
        (2, 3): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {HL: 6, LH: 4, HH: 2},
            4: {HL: 6, LH: 5, HH: 2},
            5: {HL: 7, LH: 5, HH: 3},
        },
        (3, 0): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
        },
        (3, 1): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {HL: 8, LH: 7, HH: 4},
        },
        (3, 2): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {HL: 8, LH: 7, HH: 4},
            5: {HL: 9, LH: 7, HH: 5},
        },
        (4, 0): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {H: 8},
        },
        (4, 1): {
            0: {L: 2},
            1: {H: 0},
            2: {H: 3},
            3: {H: 6},
            4: {H: 8},
            5: {HL: 11, LH: 9, HH: 7},
        },
    },
}
"""
(D.2) Default quantisation matrices. A nested lookup {(wavelet_index_ho,
wavelet_index): {(dwt_depth_ho, dwt_depth): quant_matrix, ...}, ...}.
Quantisation matrices are given in the same form as State.quant_matrix. Taken
from (Table D.1 to D.8).
"""
