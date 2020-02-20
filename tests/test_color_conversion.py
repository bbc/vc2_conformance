import pytest

import numpy as np

from vc2_data_tables import (
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    ColorDifferenceSamplingFormats,
)

from vc2_conformance.video_parameters import VideoParameters

from vc2_conformance.vc2_math import intlog2

from vc2_conformance.color_conversion import (
    PrimaryChromacities,
    xy_to_xyz,
    primary_chromacities_to_matrix,
    LINEAR_RGB_TO_XYZ,
    XYZ_TO_LINEAR_RGB,
    TRANSFER_FUNCTIONS,
    INVERSE_TRANSFER_FUNCTIONS,
    COLOR_MATRICES,
    INVERSE_COLOR_MATRICES,
    int_to_float,
    float_to_int,
    from_444,
    to_444,
    to_xyz,
    from_xyz,
)


# Used by various tests
REC709 = PrimaryChromacities(
    xw=0.3127,
    yw=0.3290,
    xr=0.640,
    yr=0.330,
    xg=0.300,
    yg=0.600,
    xb=0.150,
    yb=0.060,
)

def test_xy_to_xyz():
    X = 10
    Y = 20
    Z = 30
    
    x = X / (X + Y + Z)
    y = Y / (X + Y + Z)
    
    X2, Y2, Z2 = xy_to_xyz(x, y)
    
    assert np.isclose(X / Y, X2)
    assert np.isclose(Y / Y, Y2)
    assert np.isclose(Z / Y, Z2)


def test_primary_chromacities_to_matrix():
    # Test the the resulting matrix has all of the properties expected of it
    m = primary_chromacities_to_matrix(REC709)
    
    X, Y, Z = np.matmul(m, [1, 0, 0])
    assert np.isclose(X / (X + Y + Z), REC709.xr)
    assert np.isclose(Y / (X + Y + Z), REC709.yr)
    
    X, Y, Z = np.matmul(m, [0, 1, 0])
    assert np.isclose(X / (X + Y + Z), REC709.xg)
    assert np.isclose(Y / (X + Y + Z), REC709.yg)
    
    X, Y, Z = np.matmul(m, [0, 0, 1])
    assert np.isclose(X / (X + Y + Z), REC709.xb)
    assert np.isclose(Y / (X + Y + Z), REC709.yb)
    
    X, Y, Z = np.matmul(m, [1, 1, 1])
    assert np.isclose(X / (X + Y + Z), REC709.xw)
    assert np.isclose(Y / (X + Y + Z), REC709.yw)


@pytest.mark.parametrize("index", PresetColorPrimaries)
def test_primary_conversions(index):
    # Check that every supported set of primaries has a pair of matching
    # matrices
    
    to_xyz = LINEAR_RGB_TO_XYZ[index]
    from_xyz = XYZ_TO_LINEAR_RGB[index]
    
    assert np.all(np.isclose(np.matmul(to_xyz, from_xyz), np.eye(3)))


@pytest.mark.parametrize("index", PresetTransferFunctions)
def test_transfer_functions(index):
    # Check that every supported transfer function is defined (in the forward
    # direction) and that it is plausible
    f = TRANSFER_FUNCTIONS[index]
    
    # Run a sweep which includes under and overshoots and at a resolution where
    # the region 0 to +1 is sampled at at least as finely as a 16-bit signal
    linear = np.linspace(-1.0, +2.0, 1<<18)
    non_linear = f(linear)
    
    slope = non_linear[1:] - non_linear[:-1]
    
    # Check that the function is monotonic, non-monotonicity might indicate
    # that 'joins' in piecewise functions are not defined exactly enough
    monotonic = np.all((slope) >= 0.0)
    assert monotonic

@pytest.mark.parametrize("index", INVERSE_TRANSFER_FUNCTIONS)
def test_inverse_transfer_functions(index):
    # Check that inverses actually work
    f = TRANSFER_FUNCTIONS[index]
    f_inv = INVERSE_TRANSFER_FUNCTIONS[index]
    
    # At least as fine as 16-bit color
    linear = np.linspace(0.0, 1.0, 1<<16)
    non_linear = f(linear)
    linear2 = f_inv(non_linear)
    
    # NB: Numerical precision may be somewhat limited at extremes of the
    # function, hence the loose tolerance here
    assert np.all(np.isclose(linear, linear2, rtol=1e-2))


@pytest.mark.parametrize("index", PresetColorMatrices)
def test_matrix_conversions(index):
    # Check that every supported set of matrices has a pair of matching
    # matrices
    
    to_yc1c2 = COLOR_MATRICES[index]
    from_yc1c2 = INVERSE_COLOR_MATRICES[index]
    
    assert np.all(np.isclose(np.matmul(to_yc1c2, from_yc1c2), np.eye(3)))


@pytest.mark.parametrize("a_int,a_float,offset,excursion", [
    # Full-range 8-bit Y signal
    (
        [0, 51, 204, 255],
        [0.0, 0.2, 0.8, 1.0],
        0,
        255,
    ),
    # Full-range 8-bit Cx signal
    (
        [26, 128, 230],
        [-0.4, 0.0, 0.4],
        128,
        255,
    ),
    # Video-range 10-bit Y signal
    (
        [64, 283, 502, 721, 940],
        [0.0, 0.25, 0.5, 0.75, 1.0],
        64,
        876,
    ),
    # Video-range 10-bit Cx signal
    (
        [64, 288, 512, 736, 960],
        [-0.5, -0.25, 0.0, 0.25, 0.5],
        512,
        896,
    ),
])
def test_int_to_float_and_float_to_int(a_int, a_float, offset, excursion):
    a_float2 = int_to_float(a_int, offset, excursion)
    assert a_float2.dtype == np.float
    assert np.array_equal(a_float2, a_float)
    
    a_int2 = float_to_int(a_float, offset, excursion)
    assert a_int2.dtype == np.int
    assert np.array_equal(a_int2, a_int)


@pytest.mark.parametrize("a_float,a_int,offset,excursion", [
    # Check rounding
    ([0.5], [128], 0, 255),
    ([-0.5, 0.5], [0, 255], 128, 255),
    # Check clamping: 8 bit full range Y signal
    (
        [-2.0, -0.01, 0.0, 1.0, 1.01, 2.0],
        [0, 0, 0, 255, 255, 255],
        0,
        255,
    ),
    # Check clamping: 8 bit full range Cx signal
    (
        [-2.0, -0.51, -0.5, 0.5, 0.51, 2.0],
        [0, 0, 0, 255, 255, 255],
        128,
        255,
    ),
    # Check clamping: 10 bit video range Y signal
    (
        [-2.0, -0.0731, 0.0, 1.0, 1.0947, 2.0],
        [0, 0, 64, 940, 1023, 1023],
        64,
        876,
    ),
])
def test_float_to_int(a_float, a_int, offset, excursion):
    # Test the rounding and clipping behaviour of the float to ind conversion
    a_int2 = float_to_int(a_float, offset, excursion)
    assert a_int2.dtype == np.int
    assert np.array_equal(a_int2, a_int)


def test_from_444_to_444():
    a = np.arange(6 * 4, dtype=float).reshape(6, 4)
    assert np.array_equal(from_444(a, ColorDifferenceSamplingFormats.color_4_4_4), a)


def test_from_444_to_422():
    a = np.array([
        [1010, 2010, 3010, 4010, 5010, 6010],
        [1020, 2020, 3020, 4020, 5020, 6020],
        [1030, 2030, 3030, 4030, 5030, 6030],
        [1040, 2040, 3040, 4040, 5040, 6040],
    ], dtype=float)
    a_exp = np.array([
        [1510, 3510, 5510],
        [1520, 3520, 5520],
        [1530, 3530, 5530],
        [1540, 3540, 5540],
    ], dtype=float)
    assert np.array_equal(from_444(a, ColorDifferenceSamplingFormats.color_4_2_2), a_exp)


def test_from_444_to_420():
    a = np.array([
        [1010, 2010, 3010, 4010, 5010, 6010],
        [1020, 2020, 3020, 4020, 5020, 6020],
        [1030, 2030, 3030, 4030, 5030, 6030],
        [1040, 2040, 3040, 4040, 5040, 6040],
    ], dtype=float)
    a_exp = np.array([
        [1515, 3515, 5515],
        [1535, 3535, 5535],
    ], dtype=float)
    assert np.array_equal(from_444(a, ColorDifferenceSamplingFormats.color_4_2_0), a_exp)


@pytest.mark.parametrize("format", ColorDifferenceSamplingFormats)
def test_from_444_all_formats_supported(format):
    a = np.arange(6 * 4, dtype=float).reshape(6, 4)
    assert from_444(a, format) is not None


@pytest.mark.parametrize("format", ColorDifferenceSamplingFormats)
def test_to_444(format):
    a = np.arange(6 * 4, dtype=float).reshape(6, 4)
    
    if format == ColorDifferenceSamplingFormats.color_4_4_4:
        assert np.array_equal(to_444(a, format), a)
    else:
        with pytest.raises(NotImplementedError):
            to_444(a, format)


def test_to_xyz():
    # A crude samity check which verifies that the conversion steps appear to
    # work correctly
    
    # An esoteric video format which is easy to hand-evaluate and also test
    # subsampling
    video_parameters = VideoParameters(
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
        luma_offset=0,
        luma_excursion=255,
        color_diff_offset=0,
        color_diff_excursion=255,
        preset_color_primaries_index=PresetColorPrimaries.hdtv,
        preset_color_matrix_index=PresetColorMatrices.rgb,
        preset_transfer_function_index=PresetTransferFunctions.tv_gamma,
    )
    
    # Find XYZ coordinates for White, black, red green and blue
    test_colors_rgb = np.array([
        [1.0, 0.0, 1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0, 1.0, 0.0],
        [1.0, 0.0, 0.0, 0.0, 1.0],
    ])
    test_colors_xyz = np.matmul(
        LINEAR_RGB_TO_XYZ[video_parameters["preset_color_primaries_index"]],
        test_colors_rgb,
    )
    
    # The following test image is defined in the XYZ domain
    #
    #      +---+---+---+---+---+---+---+---+---+---+
    #      |Wht|Wht|Blk|Blk|Red|Red|Grn|Grn|Blu|Blu|
    #      +---+---+---+---+---+---+---+---+---+---+
    #      |Wht|Blk|Blk|Blk|Red|Blk|Grn|Blk|Blu|Blk|
    #      +---+---+---+---+---+---+---+---+---+---+
    #      |Wht|Wht|Wht|Wht|Wht|Wht|Wht|Wht|Wht|Wht|
    #      +---+---+---+---+---+---+---+---+---+---+
    #      |Blk|Blk|Blk|Blk|Blk|Blk|Blk|Blk|Blk|Blk|
    #      +---+---+---+---+---+---+---+---+---+---+
    #
    # This has the following features:
    #
    # * Row 0: Fully saturated colours in pairs of pixels
    # * Row 1: Colours paired with black (which after 4:2:2 subsampling will
    #   result in darker colours (at least with the low-pass filter used here)
    # * Row 2: All white
    # * Row 3: All black
    
    test_colors_xyz_row = test_colors_xyz.T.reshape(-1, 3)
    
    row_0 = np.repeat(test_colors_xyz_row, 2, axis=0)
    
    row_1 = row_0.copy()
    row_1[1::2, :] = 0
    
    row_2 = np.empty_like(row_0)
    row_2[:, 0] = row_0[0, 0]
    row_2[:, 1] = row_0[0, 1]
    row_2[:, 2] = row_0[0, 2]
    
    row_3 = np.empty_like(row_0)
    row_3[:, 0] = row_0[2, 0]
    row_3[:, 1] = row_0[2, 1]
    row_3[:, 2] = row_0[2, 2]
    
    test_picture_xyz = np.stack([
        row_0,
        row_1,
        row_2,
        row_3,
    ], axis=0)
    
    # Colours should come out as expected RGB values in GBR order
    g, b, r = from_xyz(
        test_picture_xyz,
        video_parameters,
    )
    
    # First row: solid colours
    #                            Wht      Blk    Red     Grn       Blu
    assert np.array_equal(r[0], [255,      0,    255,      0,        0])
    assert np.array_equal(g[0], [255, 255, 0, 0,   0, 0, 255, 255,   0, 0])
    assert np.array_equal(b[0], [255,      0,      0,      0,      255])
    
    # Second row, dimmed R and B channels
    #                            Wht    Blk    Red     Grn     Blu
    assert np.array_equal(r[1], [128,    0,    128,      0,      0])
    assert np.array_equal(g[1], [255, 0, 0, 0,   0, 0, 255, 0,   0, 0])
    assert np.array_equal(b[1], [128,    0,      0,      0,    128])
    
    # Third row: all-white
    assert np.array_equal(r[2], [255,      255,      255,      255,      255])
    assert np.array_equal(g[2], [255, 255, 255, 255, 255, 255, 255, 255, 255, 255])
    assert np.array_equal(b[2], [255,      255,      255,      255,      255])
    
    # Fourth row: all-black
    assert np.array_equal(r[3], [0,    0,    0,    0,    0])
    assert np.array_equal(g[3], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert np.array_equal(b[3], [0,    0,    0,    0,    0])


@pytest.mark.parametrize("luma_offset,luma_excursion", [(0, 255), (64, 876)])
@pytest.mark.parametrize("color_diff_offset,color_diff_excursion", [(128, 255), (512, 896)])
@pytest.mark.parametrize("primaries", PresetColorPrimaries)
@pytest.mark.parametrize("matrix", PresetColorMatrices)
@pytest.mark.parametrize("transfer_function", INVERSE_TRANSFER_FUNCTIONS)
def test_to_xyz_and_from_xyz_roundtrip(
    luma_offset,
    luma_excursion,
    color_diff_offset,
    color_diff_excursion,
    primaries,
    matrix,
    transfer_function,
):
    video_parameters = VideoParameters(
        color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
        luma_offset=luma_offset,
        luma_excursion=luma_excursion,
        color_diff_offset=color_diff_offset,
        color_diff_excursion=color_diff_excursion,
        preset_color_primaries_index=primaries,
        preset_color_matrix_index=matrix,
        preset_transfer_function_index=transfer_function,
    )
    
    luma_bits = intlog2(luma_excursion + 1)
    color_diff_bits = intlog2(color_diff_excursion + 1)
    
    w, h = 6, 4
    
    rand = np.random.RandomState(0)
    y = rand.randint(0, 2**luma_bits, (h, w))
    c1 = rand.randint(0, 2**color_diff_bits, (h, w))
    c2 = rand.randint(0, 2**color_diff_bits, (h, w))
    
    xyz = to_xyz(y, c1, c2, video_parameters)
    
    assert xyz.shape == (h, w, 3)
    
    new_y, new_c1, new_c2 = from_xyz(xyz, video_parameters)
    
    assert np.array_equal(y, new_y)
    assert np.array_equal(c1, new_c1)
    assert np.array_equal(c2, new_c2)
