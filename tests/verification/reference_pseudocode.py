"""
Verbatim Python implementations of the reference VC-2 pseudocode snippets.

The :py:mod:`verification` test suite compares these implementations against
those used in :py:mod:`vc2_conformance` for equivalence. As such, these
implementations *must* be kept consistent with the VC-2 specification.
"""

# The following general differences apply (which make the pseudocode not Python)
# * missing 'def' prefix for function defintions
# * for i = n to m syntax replaced with for i in range(n, m+1)
# * missing quotes on dictionary keys
# * state is a global variable (passed as needed as first argument here)
# * Replace `if x == True(False)` with `if (not) x`
# * Replace `length` with `len`
# * Replace `elif` with `elif`
# * Replace `for each x in a, b, c` with `for x in [a, b, c]`
# * Replace long-dash with `-` in arithmetic
# * Replace constant sentinels with strings (e.g. LL -> "LL")
# * Replace '1d_synthesis' with 'oned_synthesis'
# * Replace superscripts with '**'


################################################################################
# 5: VC-2 Conventions
################################################################################

# Errata: Expressed as if/else sequence rather than postfixed 'if' conditions
def sign(a):
    """(5.5.3)"""
    if a>0:
        return 1
    elif a==0:  # Errata: '=' in spec
        return 0
    elif a<0:
        return -1

def clip(a, b, t):
    """(5.5.3)"""
    return min(max(a,b),t)


################################################################################
# 10: VC-2 Stream
################################################################################

# Errata: 'state' is created internally as an empty dict in the spec, not
# passed in as an argument
def parse_sequence(state):
    """(10.4.1)"""
    # state = {}  # Errata: see above
    parse_info(state)
    while(not is_end_of_sequence(state)):
        if (is_seq_header(state)):
            sequence_header(state)
        elif (is_picture(state)):
            picture_parse(state)
        elif (is_fragment(state)):
            # Errata: is 'fragment' in the spec
            fragment_parse(state)
        elif (is_auxiliary_data(state)):
            auxiliary_data(state)
        elif (is_padding_data(state)):  # Errata: is 'is_padding' in the spec
            padding(state)
        parse_info(state)


# Errata: missing '_' in name
def auxiliary_data(state):
    """(10.4.4)"""
    byte_align(state)
    for i in range(state["next_parse_offset"]-13):
        # Errata: is 'read_byte' in the spec
        read_uint_lit(state, 1)


def padding(state):
    """(10.4.5)"""
    byte_align(state)
    for i in range(state["next_parse_offset"]-13):
        # Errata: is 'read_byte' in the spec
        read_uint_lit(state, 1)


def parse_info(state):
    """(10.5.1)"""
    byte_align(state)  # Errata: missing in spec
    read_uint_lit(state, 4)
    state["parse_code"] = read_uint_lit(state, 1)  # Errata: 'read_byte' in spec
    state["next_parse_offset"] = read_uint_lit(state, 4)
    state["previous_parse_offset"] = read_uint_lit(state, 4)


def is_seq_header(state):
    """(Table 10.2)"""
    return (state["parse_code"] == 0x00)

def is_end_of_sequence(state):
    """(Table 10.2)"""
    return (state["parse_code"] == 0x10)

def is_auxiliary_data(state):
    """(Table 10.2)"""
    return ((state["parse_code"]&0xF8) == 0x20)

def is_padding_data(state):
    """(Table 10.2)"""
    return (state["parse_code"] == 0x30)

# Errata: is_picture also returns True for fragments in the spec.
def is_picture(state):
    """(Table 10.2)"""
    return ((state["parse_code"]&0x8C) == 0x88)

# Errata: is_ld_picture also returns True for LD fragments in the spec.
def is_ld_picture(state):
    """(Table 10.2)"""
    return ((state["parse_code"]&0xFC) == 0xC8)

# Errata: is_hq_picture also returns True for HQ fragments in the spec.
def is_hq_picture(state):
    """(Table 10.2)"""
    return ((state["parse_code"]&0xFC) == 0xE8)

def is_fragment(state):
    """(Table 10.2)"""
    return ((state["parse_code"]&0x0C) == 0x0C)

def is_ld_fragment(state):
    """(Table 10.2)"""
    return ((state["parse_code"]&0xFC) == 0xCC)

def is_hq_fragment(state):
    """(Table 10.2)"""
    return ((state["parse_code"]&0xFC) == 0xEC)

def using_dc_prediction(state):
    """(Table 10.2)"""
    return ((state["parse_code"]&0x28) == 0x08)


def decode_sequence():
    """(10.6.1)"""
    state = {}
    video_parameters = {}
    decoded_pictures = {}
    parse_info(state)
    while(not is_end_of_sequence(state)):
        if (is_seq_header(state)):
            video_parameters = sequence_header(state)
        if(is_picture(state)):
            if (is_fragment(state)):
                fragment_parse(state)
                if (state["fragmented_picture_done"]):
                    decoded_pictures[len(decoded_pictures)] = picture_decode(state)
            else:
                picture_parse(state)
                decoded_pictures[len(decoded_pictures)] = picture_decode(state)
        parse_info(state)
    
    # Errata: Returns a set (curly-bracketed pair) not a 2-array
    return [video_parameters, decoded_pictures]


################################################################################
# 11: Sequence Header
################################################################################

def sequence_header(state):
    """(11.1)"""
    byte_align(state)
    parse_parameters(state)
    base_video_format = read_uint(state)
    video_parameters = source_parameters(state, base_video_format)
    picture_coding_mode = read_uint(state)
    set_coding_parameters(state, video_parameters, picture_coding_mode)
    return video_parameters


def parse_parameters(state):
    """(11.2.1)"""
    state["major_version"] = read_uint(state)
    state["minor_version"] = read_uint(state)
    state["profile"] = read_uint(state)
    state["level"] = read_uint(state)


# Errata: argument is 'video_format' in the spec
def source_parameters(state, base_video_format):
    """(11.4.1)"""
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


def frame_size(state, video_parameters):
    """(11.4.3)"""
    custom_dimensions_flag = read_bool(state)
    # Errata: missing ':'
    if(custom_dimensions_flag):
        video_parameters["frame_width"] = read_uint(state)
        video_parameters["frame_height"] = read_uint(state)


def color_diff_sampling_format(state, video_parameters):
    """(11.4.4)"""
    custom_color_diff_format_flag = read_bool(state)
    # Errata: missing ':'
    if(custom_color_diff_format_flag):
        video_parameters["color_diff_format_index"] = read_uint(state)


def scan_format(state, video_parameters):
    """(11.4.5)"""
    custom_scan_format_flag = read_bool(state)
    if(custom_scan_format_flag):
        video_parameters["source_sampling"] = read_uint(state)


def frame_rate(state, video_parameters):
    """(11.4.6)"""
    custom_frame_rate_flag = read_bool(state)
    if(custom_frame_rate_flag):
        index = read_uint(state)
        if(index == 0):
            video_parameters["frame_rate_numer"] = read_uint(state)
            video_parameters["frame_rate_denom"] = read_uint(state)
        else:
            preset_frame_rate(video_parameters, index)


# Errata: called 'aspect_ratio' in spec
def pixel_aspect_ratio(state, video_parameters):
    """(11.4.7)"""
    custom_pixel_aspect_ratio_flag = read_bool(state)
    if(custom_pixel_aspect_ratio_flag):
        index = read_uint(state)
        if(index == 0):
            video_parameters["pixel_aspect_ratio_numer"] = read_uint(state)
            video_parameters["pixel_aspect_ratio_denom"] = read_uint(state)
        else:
            # Errata: called 'preset_aspect_ratio' in spec
            preset_pixel_aspect_ratio(video_parameters, index)


def clean_area(state, video_parameters):
    """(11.4.8)"""
    custom_clean_area_flag = read_bool(state)
    if(custom_clean_area_flag):
        video_parameters["clean_width"] = read_uint(state)
        video_parameters["clean_height"] = read_uint(state)
        video_parameters["left_offset"] = read_uint(state)
        video_parameters["top_offset"] = read_uint(state)


def signal_range(state, video_parameters):
    """(11.4.9)"""
    custom_signal_range_flag = read_bool(state)
    if(custom_signal_range_flag):
        index = read_uint(state)
        if(index == 0):
            video_parameters["luma_offset"] = read_uint(state)
            video_parameters["luma_excursion"] = read_uint(state)
            video_parameters["color_diff_offset"] = read_uint(state)
            video_parameters["color_diff_excursion"] = read_uint(state)
        else:
            preset_signal_range(video_parameters, index)


def color_spec(state, video_parameters):
    """(11.4.10.1)"""
    custom_color_spec_flag = read_bool(state)
    if(custom_color_spec_flag):
        index = read_uint(state)
        preset_color_spec(video_parameters, index)
        if(index == 0):
            color_primaries(state, video_parameters)
            color_matrix(state, video_parameters)
            transfer_function(state, video_parameters)


def color_primaries(state, video_parameters):
    """(11.4.10.2)"""
    custom_color_primaries_flag = read_bool(state)
    if(custom_color_primaries_flag):
        index = read_uint(state)
        preset_color_primaries(video_parameters,index)


def color_matrix(state, video_parameters):
    """(11.4.10.3)"""
    custom_color_matrix_flag = read_bool(state)
    if(custom_color_matrix_flag):
        index = read_uint(state)
        preset_color_matrix(video_parameters, index)


def transfer_function(state, video_parameters):
    """(11.4.10.4)"""
    custom_transfer_function_flag = read_bool(state)
    if(custom_transfer_function_flag):
        index = read_uint(state)
        preset_transfer_function(video_parameters ,index)


def set_coding_parameters(state, video_parameters, picture_coding_mode):
    """(11.6.1)"""
    picture_dimensions(state, video_parameters, picture_coding_mode)
    video_depth(state, video_parameters)


def picture_dimensions(state, video_parameters, picture_coding_mode):
    """(11.6.2)"""
    state["luma_width"] = video_parameters["frame_width"]
    state["luma_height"] = video_parameters["frame_height"]
    state["color_diff_width"] = state["luma_width"]
    state["color_diff_height"] = state["luma_height"]
    color_diff_format_index = video_parameters["color_diff_format_index"]
    if (color_diff_format_index == 1):
        state["color_diff_width"] //= 2
    if (color_diff_format_index == 2):
        state["color_diff_width"] //= 2
        state["color_diff_height"] //= 2
    if (picture_coding_mode == 1):
        state["luma_height"] //= 2
        state["color_diff_height"] //= 2


def video_depth(state, video_parameters):
    """(11.6.3)"""
    state["luma_depth"] = intlog2(video_parameters["luma_excursion"]+1)
    state["color_diff_depth"] = intlog2(video_parameters["color_diff_excursion"]+1)


################################################################################
# 12: Picture syntax
################################################################################

def picture_parse(state):
    """(12.1)"""
    byte_align(state)
    picture_header(state)
    byte_align(state)
    wavelet_transform(state)


def picture_header(state):
    """(12.2)"""
    state["picture_number"] = read_uint_lit(state, 4)


def wavelet_transform(state):
    """(12.3)"""
    transform_parameters(state)
    byte_align(state)
    transform_data(state)


# Errata: add missing '_' to name
def transform_parameters(state):
    """(12.4.1)"""
    state["wavelet_index"] = read_uint(state)
    state["dwt_depth"] = read_uint(state)
    state["wavelet_index_ho"] = state["wavelet_index"]
    state["dwt_depth_ho"] = 0
    if (state["major_version"] >= 3):
        extended_transform_parameters(state)
    slice_parameters(state)
    quant_matrix(state)


def extended_transform_parameters(state):
    """(12.4.4.1)"""
    asym_transform_index_flag = read_bool(state)
    if (asym_transform_index_flag):
        state["wavelet_index_ho"] = read_uint(state)
    asym_transform_flag = read_bool(state)
    if (asym_transform_flag):
        state["dwt_depth_ho"] = read_uint(state)


def slice_parameters(state):
    """(12.4.5.2)"""
    state["slices_x"] = read_uint(state)
    state["slices_y"] = read_uint(state)
    # Errata: just uses 'is_ld_picture' and 'is_hq_picture' in spec but should
    # check fragment types too
    if is_ld_picture(state) or is_ld_fragment(state):
        state["slice_bytes_numerator"] = read_uint(state)
        state["slice_bytes_denominator"] = read_uint(state)
    if is_hq_picture(state) or is_hq_fragment(state):
        state["slice_prefix_bytes"] = read_uint(state)
        state["slice_size_scaler"] = read_uint(state)


def quant_matrix(state):
    """(12.4.5.3)"""
    custom_quant_matrix = read_bool(state)
    if(custom_quant_matrix):
        if (state["dwt_depth_ho"] == 0):
            state["quant_matrix"][0]["LL"] = read_uint(state)
        else:
            state["quant_matrix"][0]["L"] = read_uint(state)
            for level in range(1, state["dwt_depth_ho"] + 1):
                state["quant_matrix"][level]["H"] = read_uint(state)
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            state["quant_matrix"][level]["HL"] = read_uint(state)
            state["quant_matrix"][level]["LH"] = read_uint(state)
            state["quant_matrix"][level]["HH"] = read_uint(state)
    else:
        set_quant_matrix(state)


################################################################################
# 13: Transform Data Syntax
################################################################################

# Errata: Not given as function in spec (given as wordy description)
def subband_width(state, level, comp):
    """(13.2.3)"""
    if comp == "Y":
        w = state["luma_width"]
    else:
        w = state["color_diff_width"]
    
    scale_w = 2**(state["dwt_depth_ho"] + state["dwt_depth"])
    
    pw = scale_w * ( (w+scale_w-1) //scale_w)
    
    if level == 0:
        return pw // 2**(state["dwt_depth_ho"] + state["dwt_depth"])
    else:  # Errata: two equivalent else-if branches in spec
        return pw // 2**(state["dwt_depth_ho"] + state["dwt_depth"] - level + 1)


# Errata: Not given as function in spec (given as wordy description)
def subband_height(state, level, comp):
    """(13.2.3)"""
    if comp == "Y":
        w = state["luma_height"]
    else:
        w = state["color_diff_height"]
    
    scale_h = 2**(state["dwt_depth"])
    
    ph = scale_h * ( (h+scale_h-1) //scale_h)
    
    if level <= state["dwt_depth_ho"]:
        return ph // 2**(state["dwt_depth"])
    else:  # Errata: two equivalent else-if branches in spec
        return ph // 2**(state["dwt_depth_ho"] + state["dwt_depth"] - level + 1)


def inverse_quant(quantized_coeff, quant_index):
    """(13.3.1)"""
    # Errata: bars used in spec, should be 'abs()'
    magnitude = abs(quantized_coeff)
    if(magnitude != 0):
        magnitude *= quant_factor(quant_index)
        magnitude += quant_offset(quant_index)
        magnitude += 2
        magnitude //= 4
    return sign(quantized_coeff) * magnitude


def quant_factor(index):
    """(13.3.2)"""
    base = 2**(index//4)
    if((index%4) == 0):
        return (4 * base)
    elif((index%4) == 1):
        return(((503829 * base) + 52958) // 105917)
    elif((index%4) == 2):
        return(((665857 * base) + 58854) // 117708)
    elif((index%4) == 3):
        return(((440253 * base) + 32722) // 65444)


def quant_offset(index):
    """(13.3.2)"""
    if(index == 0):
        offset = 1
    elif(index == 1):
        offset = 2
    else:
        offset = (quant_factor(index) + 1)//2
    return offset


def dc_prediction(band):
    """(13.4)"""
    for y in range(0, height(band)):
        for x in range(0, width(band)):
            # Errata: 'If' not 'if' in spec
            if(x > 0 and y > 0):
                prediction = mean(band[y][x-1], band[y-1][x-1], band[y-1][x])
            elif (x > 0 and y == 0):
                prediction = band[0][x - 1]
            elif (x == 0 and y > 0):
                prediction = band[y - 1][0]
            else:
                prediction = 0
            band[y][x] += prediction


def transform_data(state):
    """(13.5.2)"""
    state["y_transform"] = initialize_wavelet_data(state, "Y")
    state["c1_transform"] = initialize_wavelet_data(state, "C1")
    state["c2_transform"] = initialize_wavelet_data(state, "C2")
    for sy in range(state["slices_y"]):
        for sx in range(state["slices_x"]):
            slice(state, sx, sy)
    if (using_dc_prediction(state)):  # Errata: '= True' in spec, should be '== True'
        if (state["dwt_depth_ho"] == 0):
            dc_prediction(state["y_transform"][0]["LL"])
            dc_prediction(state["c1_transform"][0]["LL"])
            dc_prediction(state["c2_transform"][0]["LL"])
        else:
            dc_prediction(state["y_transform"][0]["L"])
            dc_prediction(state["c1_transform"][0]["L"])
            dc_prediction(state["c2_transform"][0]["L"])


def slice(state, sx, sy):
    """(13.5.2)"""
    # Errata: In the spec the if/elif conditions below had mismatched brackets
    #
    # Errata: In the spec the if/elif conditions only tested for picture types,
    # not pictures and fragments.
    #
    # Errata: In the spec the if/elif condition function names were missing a
    # leading 'is_'.
    if is_ld_picture(state) or is_ld_fragment(state):
        ld_slice(state, sx, sy)
    elif is_hq_picture(state) or is_hq_fragment(state):
        hq_slice(state, sx, sy)


def ld_slice(state, sx, sy):
    """(13.5.3.1)"""
    slice_bits_left = 8*slice_bytes(state, sx, sy)
    qindex = read_nbits(state, 7)
    slice_bits_left -= 7
    slice_quantizers(state, qindex)
    length_bits = intlog2(8*slice_bytes(state, sx, sy)-7)
    slice_y_length = read_nbits(state, length_bits)
    slice_bits_left -= length_bits
    state["bits_left"] = slice_y_length
    if (state["dwt_depth_ho"] == 0):
        # Errata: called 'luma_slice_band' in spec and missing "y_transform"
        # argument.
        slice_band(state, "y_transform", 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                slice_band(state, "y_transform", level, orient, sx, sy)
    else:
        # Errata: called 'luma_slice_band' in spec and missing "y_transform"
        # argument.
        slice_band(state, "y_transform", 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            slice_band(state, "y_transform", level, "H", sx, sy)
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                slice_band(state, "y_transform", level, orient, sx, sy)
    flush_inputb(state)
    slice_bits_left -= slice_y_length
    state["bits_left"] = slice_bits_left
    # Errata: in spec, the HO/2D cases are not handled correctly (the new
    # code below is based on the code above for the luma case
    if (state["dwt_depth_ho"] == 0):
        color_diff_slice_band(state, 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(state, level, orient, sx, sy)
    else:
        color_diff_slice_band(state, 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            color_diff_slice_band(state, level, "H", sx, sy)
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(state, level, orient, sx, sy)
    flush_inputb(state)


def slice_bytes(state, sx, sy):
    """(13.5.3.2)"""
    slice_number = sy*state["slices_x"] + sx
    bytes = ((slice_number+1)*state["slice_bytes_numerator"])// state["slice_bytes_denominator"]
    bytes -= (slice_number*state["slice_bytes_numerator"])// state["slice_bytes_denominator"]
    return bytes


def hq_slice(state, sx, sy):
    """(13.5.4)"""
    read_uint_lit(state, state["slice_prefix_bytes"])
    qindex = read_uint_lit(state, 1)
    slice_quantizers(state, qindex)
    for transform in ["y_transform", "c1_transform", "c2_transform"]:
        length = state["slice_size_scaler"]* read_uint_lit(state, 1)
        state["bits_left"] = 8*length
        if (state["dwt_depth_ho"] == 0):
            slice_band(state, transform, 0, "LL", sx, sy)
            for level in range(1, state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(state, transform, level, orient, sx, sy)
        else:
            slice_band(state, transform, 0, "L", sx, sy)
            for level in range(1, state["dwt_depth_ho"] + 1):
                slice_band(state, transform, level, "H", sx, sy)
            for level in range(state["dwt_depth_ho"] + 1,
                               state["dwt_depth_ho"] + state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(state, transform, level, orient, sx, sy)
        flush_inputb(state)


def slice_quantizers(state, qindex):
    """(13.5.5)"""
    if (state["dwt_depth_ho"] == 0) :
        state["quantizer"][0]["LL"] = max(qindex - state["quant_matrix"][0]["LL"], 0)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                qval = max(qindex - state["quant_matrix"][level][orient], 0)
                state["quantizer"][level][orient] = qval
    else :
        state["quantizer"][0]["L"] = max(qindex - state["quant_matrix"][0]["L"], 0)
        for level in range(1, state["dwt_depth_ho"] + 1):
            qval = max(qindex - state["quant_matrix"][level]["H"], 0)
            state["quantizer"][level]["H"] = qval
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                qval = max(qindex - state["quant_matrix"][level][orient], 0)
                state["quantizer"][level][orient] = qval


def slice_left(state, sx,c,level):
    """(13.5.6.2)"""
    return (subband_width(state, level,c) * sx)//state["slices_x"]

def slice_right(state, sx,c,level):
    """(13.5.6.2)"""
    return (subband_width(state, level,c) * (sx + 1))//state["slices_x"]

def slice_top(state, sy,c,level):
    """(13.5.6.2)"""
    return (subband_height(state, level,c) * sy)//state["slices_y"]

def slice_bottom(state, sy,c,level):
    """(13.5.6.2)"""
    return (subband_height(state, level,c) * (sy + 1))//state["slices_y"]


def slice_band(state, transform, level, orient, sx, sy):
    """(13.5.6.3)"""
    # Errata: 'Y' is always used in the spec but should respect whatever
    # transform is specified.
    comp = "Y" if transform.startswith("y") else "C1"
    
    for y in range(slice_top(state, sy,comp,level), slice_bottom(state, sy,comp,level)):
        for x in range(slice_left(state, sx,comp,level), slice_right(state, sx,comp,level)):
            val = read_sintb(state)
            qi = state["quantizer"][level][orient]
            state[transform][level][orient][y][x] = inverse_quant(val, qi)


def color_diff_slice_band(state, level, orient, sx, sy):
    """(13.5.6.4)"""
    # Errata: the following line is not necessary
    #qi = state["quantizer"][level][orient]
    
    for y in range(slice_top(state,sy,"C1",level), slice_bottom(state,sy,"C1",level)):
        for x in range(slice_left(state,sx,"C1",level), slice_right(state,sx,"C1",level)):
            qi = state["quantizer"][level][orient]
            val = read_sintb(state)
            state["c1_transform"][level][orient][y][x] = inverse_quant(val, qi)
            val = read_sintb(state)
            state["c2_transform"][level][orient][y][x] = inverse_quant(val, qi)

################################################################################
# 14: Fragment Syntax
################################################################################

def fragment_parse (state):
    """(14.1)"""
    byte_align(state)
    fragment_header(state)
    if (state["fragment_slice_count"] == 0):
        byte_align(state)
        transform_parameters(state)
        initialize_fragment_state(state)
    else:
        byte_align(state)
        fragment_data(state)


def fragment_header (state):
    """(14.2)"""
    state["picture_number"] = read_uint_lit(state, 4)
    state["fragment_data_length"] = read_uint_lit(state, 2)
    state["fragment_slice_count"] = read_uint_lit(state, 2)
    if (state["fragment_slice_count"] != 0):
        state["fragment_x_offset"] = read_uint_lit(state, 2)
        state["fragment_y_offset"] = read_uint_lit(state, 2)


def initialize_fragment_state (state):
    """(14.3)"""
    state["y_transform"] = initialize_wavelet_data("Y")
    state["c1_transform"] = initialize_wavelet_data("C1")
    state["c2_transform"] = initialize_wavelet_data("C2")
    state["fragment_slices_received"] = 0
    state["fragment_picture_done"] = False


def fragment_data(state):
    """(14.4)"""
    # Errata: In the spec this loop goes from 0 to fragment_slice_count
    # inclusive but should be fragment_slice_count *exclusive* (as below)
    for s in range(0, state["fragment_slice_count"]):
        state["slice_x"] = (state["fragment_y_offset"]*state["slices_x"] + state["fragment_x_offset"] + s)%state["slices_x"]
        state["slice_y"] = (state["fragment_y_offset"]*state["slices_x"] + state["fragment_x_offset"] + s)//state["slices_x"]
        slice(state, state["slice_x"], state["slice_y"])
        state["fragment_slices_received"] += 1
        if (state["fragment_slices_received"] == state["slice_x"]*state["slice_y"]):
            state["fragmented_picture_done"] = True
            if (using_dc_prediction(state)):
                if (state["dwt_depth_ho"] == 0):
                    dc_prediction(state["y_transform"][0]["LL"])
                    dc_prediction(state["c1_transform"][0]["LL"])
                    dc_prediction(state["c2_transform"][0]["LL"])
                else:
                    dc_prediction(state["y_transform"][0]["L"])
                    dc_prediction(state["c1_transform"][0]["L"])
                    dc_prediction(state["c2_transform"][0]["L"])


################################################################################
# 15: Picture Decoding
################################################################################

def picture_decode(state):
    """(15.2)"""
    state["current_picture"] = {}
    state["current_picture"]["pic_num"] = state["picture_number"]
    inverse_wavelet_transform(state)
    clip_picture(state, state["current_picture"])
    offset_picture(state, state["current_picture"])
    return state["current_picture"]


def inverse_wavelet_transform(state):
    """(15.3)"""
    state["current_picture"]["Y"] = idwt(state, state["y_transform"])
    state["current_picture"]["C1"] = idwt(state, state["c1_transform"])
    state["current_picture"]["C2"] = idwt(state, state["c2_transform"])
    for c in ["Y", "C1", "C2"]:  # Errata: Should be 'for each' in spec
        idwt_pad_removal(state, state["current_picture"][c], c )


def idwt(state, coeff_data):
    """(15.4.1)"""
    if (state["dwt_depth_ho"] == 0):
        DC_band = coeff_data[0]["LL"]
    else:
        DC_band = coeff_data[0]["L"]
    for n in range(1, state["dwt_depth_ho"] + 1):
        new_DC_band = h_synthesis(state, DC_band, coeff_data[n]["H"])
        DC_band = new_DC_band
    for n in range(state["dwt_depth_ho"] + 1,
                   state["dwt_depth_ho"] + state["dwt_depth"] + 1):
        new_DC_band = vh_synthesis(state, DC_band, coeff_data[n]["HL"],
                                   coeff_data[n]["LH"],coeff_data[n]["HH"])
        DC_band = new_DC_band
    return DC_band


# Errata: Expressed as prose, not a single function in spec
def h_synthesis(state, L_data, H_data):
    """(15.4.2)"""
    # Step 1.
    #
    # Errata: 'new_array' not part of spec but the need for the function is
    # described in prose.
    #
    # Errata: the 'width(L_data)' etc. parts of the lines below refer to
    # 'LL_data' in the spec.
    synth = new_array(height(L_data), 2 * width(L_data))
    
    # Step 2.
    for y in range(0, (height(synth))):
        for x in range(0, (width(synth)//2)):
            # Errata: 2*x is '2x' in spec
            synth[y][2*x] = L_data[y][x]
            synth[y][(2*x) + 1] = H_data[y][x]
    
    # Step 3.
    for y in range(0, height(synth)):
        oned_synthesis(row(synth, y), state["wavelet_index_ho"])
    
    # Step 4.
    shift = filter_bit_shift(state)
    if((shift > 0)):  # Errata: 'If' in spec should be 'if'
        for y in range(0, height(synth)):
            for x in range(0, width(synth)):
                synth[y][x] = (synth[y][x] + (1 << (shift - 1))) >> shift
    
    return synth


# Errata: Expressed as prose, not a single function in spec
def vh_synthesis(state, LL_data, HL_data, LH_data, HH_data):
    """(15.4.3)"""
    # Step 1.
    #
    # Errata: 'new_array' not part of spec but the need for the function is
    # described in prose.
    synth = new_array(2 * height(LL_data), 2 * width(LL_data))
    
    # Step 2.
    for y in range(0, (height(synth)//2)):
        for x in range(0, (width(synth)//2)):
            # Errata: 2*x is '2x' in spec (etc.)
            synth[2*y][2*x] = LL_data[y][x]
            synth[2*y][2*x + 1] = HL_data[y][x]
            synth[2*y + 1][2*x] = LH_data[y][x]
            synth[2*y + 1][2*x + 1] = HH_data[y][x]
    
    # Step 3.
    for x in range(0, width(synth)):
        oned_synthesis(column(synth, x), state["wavelet_index"])
    for y in range(0, height(synth)):
        oned_synthesis(row(synth, y), state["wavelet_index_ho"])
    
    # Step 4.
    shift = filter_bit_shift(state)
    if((shift > 0) == True):  # Errata: 'If' in spec should be 'if'
        for y in range(0, height(synth)):
            for x in range(0, width(synth)):
                synth[y][x] = (synth[y][x] + (1 << (shift - 1))) >> shift
    
    return synth


def lift1(A, L, D, taps, S):
    """(15.4.4.1)"""
    for n in range(0, (length(A)//2)):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i) - 1
            pos = min(pos, length(A) - 1)
            pos = max(pos, 1)
            sum += taps[i-D]* A[pos]
        if((S>0)):  # Errata: 'If' in spec should be 'if'
            sum += (1<<(S - 1))
        A[2*n] += (sum >> S)


def lift2(A, L, D, taps, S):
    """(15.4.4.1)"""
    for n in range(0, (length(A)//2)):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i) - 1
            pos = min(pos, length(A) - 1)
            pos = max(pos, 1)
            sum += taps[i-D] * A[pos]
        if((S>0)) :  # Errata: 'If' in spec should be 'if'
            sum += (1<<(S - 1))
        A[2*n] -= (sum >> S)


def lift3(A, L, D, taps, S):
    """(15.4.4.1)"""
    for n in range(0, (length(A)//2)):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i)
            pos = min(pos, length(A) - 2)
            pos = max(pos, 0)
            sum += taps[i-D] * A[pos]
        if (S>0):  # Errata: 'If' in spec should be 'if'
            sum += (1<<(S - 1))
        A[2*n + 1] += (sum >> S)


def lift4(A, L, D, taps, S):
    """(15.4.4.1)"""
    for n in range(0, (length(A)//2)):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i)
            pos = min(pos, length(A) - 2)
            pos = max(pos, 0)
            sum += t[i-D] * A[pos]
        if (S>0):  # Errata: 'If' in spec should be 'if'
            sum += (1<<(S - 1))
        A[2*n + 1] -= (sum >> S)


# Errata: Expressed as prose, not a single function in spec
def idwt_pad_removal(state, pic, c):
    """(15.4.5)"""
    if(c == "Y"):
        width = state["luma_width"]
        height = state["luma_height"]
    elif((c == "C1") or (c == "C2")):
        width = state["color_diff_width"]
        height = state["color_diff_height"]
    
    # Errata: Implementation of the following not given in spec
    del pic[height:, :]
    del pic[:, width:]


def clip_picture(state, current_picture):
    """(15.5)"""
    for c in ["Y", "C1", "C2"]:
        clip_component(state, current_picture[c], c)


def clip_component(state, comp_data, c):
    """(15.5)"""
    for y in range(0, height(comp_data)):
        for x in range(0, width(comp_data)):
            if (c=="Y"):
                clip(comp_data[y][x], -(2**(state["luma_depth"]-1)), 2**(state["luma_depth"]-1) -1)
            else:
                clip(comp_data[y][x], -(2**(state["color_diff_depth"]-1)), 2**(state["color_diff_depth"]-1) -1)


def offset_picture(state, current_picture):
    """(15.5)"""
    for c in ["Y", "C1", "C2"]:
        offset_component(state, current_picture[c], c)


def offset_component(state, comp_data, c):
    """(15.5)"""
    for y in range(0, height(comp_data)):
        for x in range(0, width(comp_data)):
            if (c=="Y"):
                comp_data[y][x] += 2**(state["luma_depth"]-1)
            else:
                comp_data[y][x] += 2**(state["color_diff_depth"]-1)


################################################################################
# A: VC-2 Data Coding Definitions
################################################################################

def read_bit(state):
    """(A.2.3)"""
    bit = (state["current_byte"] >> state["next_bit"])&1
    state["next_bit"] -= 1
    if(state["next_bit"] < 0):
        state["next_bit"] = 7
        read_byte(state)
    return bit


def byte_align(state):
    """(A.2.4)"""
    if(state["next_bit"] != 7):
        read_byte(state)


def read_bool(state):
    """(A.3.2)"""
    if(read_bit(state) == 1):
        return True
    else:
        return False

def read_nbits(state, n):
    """(A.3.3)"""
    val = 0
    for i in range(0, n):
        val <<= 1
        val += read_bit(state)
    return val

def read_uint_lit(state, n):
    """(A.3.4)"""
    # Errata: also performs a byte alignment in spec (now refactored out into
    # byte_align calls wherever read_uint_lit is used and the stream may be
    # unaligned)
    return read_nbits(state, 8*n)


def read_bitb(state):
    """(A.4.2)"""
    if(state["bits_left"] == 0):
        return 1
    else:
        state["bits_left"] -= 1
        return read_bit(state)


def read_boolb(state):
    """(A.4.2)"""
    if(read_bitb(state) == 1):
        return True
    else:
        return False


def flush_inputb(state):
    """(A.4.2)"""
    while(state["bits_left"] > 0):
        read_bit(state)
        state["bits_left"] -= 1


def read_uint(state):
    """(A.4.3)"""
    value = 1
    while(read_bit(state) == 0):
        value <<= 1
        if(read_bit(state) == 1):
            value += 1
    value -= 1
    return value


def read_uintb(state):
    """(A.4.3)"""
    value = 1
    while(read_bitb(state) == 0):
        value <<= 1
        # Errata: In spec 'read_bitb()' is compared with True but returns 0 or 1
        if(read_bitb(state)):
            value += 1
    value -= 1
    return value


def read_sint(state):
    """(A.4.4)"""
    value = read_uint(state)
    if(value != 0):
        if(read_bit(state) == 1):
            value = -value
    return value


def read_sintb(state):
    """(A.4.4)"""
    value = read_uintb(state)
    if(value != 0):
        if(read_bitb(state) == 1):
            value = -value
    return value
