import pytest

import numpy as np

from vc2_data_tables import (
    BaseVideoFormats,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    ColorDifferenceSamplingFormats,
)

from vc2_conformance.pseudocode.video_parameters import (
    VideoParameters,
    set_source_defaults,
)

from vc2_conformance.pseudocode.vc2_math import intlog2

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
    float_to_int_clipped,
    from_444,
    to_444,
    to_xyz,
    from_xyz,
    matmul_colors,
    swap_primaries,
    ColorParametersSanity,
    sanity_check_video_parameters,
)


# Used by various tests
REC709 = PrimaryChromacities(
    xw=0.3127, yw=0.3290, xr=0.640, yr=0.330, xg=0.300, yg=0.600, xb=0.150, yb=0.060,
)


def test_xy_to_xyz():
    X = 10.0
    Y = 20.0
    Z = 30.0

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
    linear = np.linspace(-1.0, +2.0, 1 << 18)
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
    linear = np.linspace(0.0, 1.0, 1 << 16)
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


@pytest.mark.parametrize(
    "a_int,a_float,offset,excursion",
    [
        # Full-range 8-bit Y signal
        ([0, 51, 204, 255], [0.0, 0.2, 0.8, 1.0], 0, 255,),
        # Full-range 8-bit Cx signal
        ([26, 128, 230], [-0.4, 0.0, 0.4], 128, 255,),
        # Video-range 10-bit Y signal
        ([64, 283, 502, 721, 940], [0.0, 0.25, 0.5, 0.75, 1.0], 64, 876,),
        # Video-range 10-bit Cx signal
        ([64, 288, 512, 736, 960], [-0.5, -0.25, 0.0, 0.25, 0.5], 512, 896,),
        # Out of range values shouldn't be clipped
        ([-255, 0, 255, 510], [-1.0, 0.0, 1.0, 2.0], 0, 255,),
    ],
)
def test_int_to_float_and_float_to_int(a_int, a_float, offset, excursion):
    a_float2 = int_to_float(a_int, offset, excursion)
    assert a_float2.dtype == np.float
    assert np.array_equal(a_float2, a_float)

    a_int2 = float_to_int(a_float, offset, excursion)
    assert a_int2.dtype == np.int
    assert np.array_equal(a_int2, a_int)


@pytest.mark.parametrize(
    "a_float,a_int,offset,excursion",
    [
        # Check rounding
        ([0.5], [128], 0, 255),
        ([-0.5, 0.5], [0, 255], 128, 255),
        # Check clamping: 8 bit full range Y signal
        ([-2.0, -0.01, 0.0, 1.0, 1.01, 2.0], [0, 0, 0, 255, 255, 255], 0, 255,),
        # Check clamping: 8 bit full range Cx signal
        ([-2.0, -0.51, -0.5, 0.5, 0.51, 2.0], [0, 0, 0, 255, 255, 255], 128, 255,),
        # Check clamping: 10 bit video range Y signal
        ([-2.0, -0.0731, 0.0, 1.0, 1.0947, 2.0], [0, 0, 64, 940, 1023, 1023], 64, 876,),
    ],
)
def test_float_to_int_clipped(a_float, a_int, offset, excursion):
    # Test the rounding and clipping behaviour of the float to ind conversion
    a_int2 = float_to_int_clipped(a_float, offset, excursion)
    assert a_int2.dtype == np.int
    assert np.array_equal(a_int2, a_int)


def test_from_444_to_444():
    a = np.arange(6 * 4, dtype=float).reshape(6, 4)
    assert np.array_equal(from_444(a, ColorDifferenceSamplingFormats.color_4_4_4), a)


def test_from_444_to_422():
    a = np.array(
        [
            [1010, 2010, 3010, 4010, 5010, 6010],
            [1020, 2020, 3020, 4020, 5020, 6020],
            [1030, 2030, 3030, 4030, 5030, 6030],
            [1040, 2040, 3040, 4040, 5040, 6040],
        ],
        dtype=float,
    )
    a_exp = np.array(
        [
            [1510, 3510, 5510],
            [1520, 3520, 5520],
            [1530, 3530, 5530],
            [1540, 3540, 5540],
        ],
        dtype=float,
    )
    assert np.array_equal(
        from_444(a, ColorDifferenceSamplingFormats.color_4_2_2), a_exp
    )


def test_from_444_to_420():
    a = np.array(
        [
            [1010, 2010, 3010, 4010, 5010, 6010],
            [1020, 2020, 3020, 4020, 5020, 6020],
            [1030, 2030, 3030, 4030, 5030, 6030],
            [1040, 2040, 3040, 4040, 5040, 6040],
        ],
        dtype=float,
    )
    a_exp = np.array([[1515, 3515, 5515], [1535, 3535, 5535]], dtype=float)
    assert np.array_equal(
        from_444(a, ColorDifferenceSamplingFormats.color_4_2_0), a_exp
    )


@pytest.mark.parametrize("format", ColorDifferenceSamplingFormats)
def test_from_444_all_formats_supported(format):
    a = np.arange(6 * 4, dtype=float).reshape(6, 4)
    assert from_444(a, format) is not None


@pytest.mark.parametrize("format", ColorDifferenceSamplingFormats)
def test_to_444(format):
    a = np.arange(6 * 4, dtype=float).reshape(6, 4)

    upsampled = to_444(a, format)
    downsampled = from_444(upsampled, format)

    assert np.array_equal(a, downsampled)


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
        color_primaries_index=PresetColorPrimaries.hdtv,
        color_matrix_index=PresetColorMatrices.rgb,
        transfer_function_index=PresetTransferFunctions.tv_gamma,
    )

    # Find XYZ coordinates for White, black, red green and blue
    test_colors_rgb = np.array(
        [
            [1.0, 0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 1.0, 0.0],
            [1.0, 0.0, 0.0, 0.0, 1.0],
        ]
    )
    test_colors_xyz = np.matmul(
        LINEAR_RGB_TO_XYZ[video_parameters["color_primaries_index"]], test_colors_rgb,
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
    # * Row 0: Fully saturated colors in pairs of pixels
    # * Row 1: Colors paired with black (which after 4:2:2 subsampling will
    #   result in darker colors (at least with the low-pass filter used here)
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

    test_picture_xyz = np.stack([row_0, row_1, row_2, row_3], axis=0)

    # Colors should come out as expected RGB values in GBR order
    g, b, r = from_xyz(test_picture_xyz, video_parameters,)

    # First row: solid colors
    #                            Wht      Blk    Red     Grn       Blu
    assert np.allclose(r[0], [255, 0, 255, 0, 0], atol=1)
    assert np.allclose(g[0], [255, 255, 0, 0, 0, 0, 255, 255, 0, 0], atol=1)
    assert np.allclose(b[0], [255, 0, 0, 0, 255], atol=1)

    # Second row, dimmed R and B channels
    #                            Wht    Blk    Red     Grn     Blu
    assert np.allclose(r[1], [128, 0, 128, 0, 0], atol=1)
    assert np.allclose(g[1], [255, 0, 0, 0, 0, 0, 255, 0, 0, 0], atol=1)
    assert np.allclose(b[1], [128, 0, 0, 0, 128], atol=1)

    # Third row: all-white
    assert np.allclose(r[2], [255, 255, 255, 255, 255], atol=1)
    assert np.allclose(g[2], [255, 255, 255, 255, 255, 255, 255, 255, 255, 255], atol=1)
    assert np.allclose(b[2], [255, 255, 255, 255, 255], atol=1)

    # Fourth row: all-black
    assert np.allclose(r[3], [0, 0, 0, 0, 0], atol=1)
    assert np.allclose(g[3], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], atol=1)
    assert np.allclose(b[3], [0, 0, 0, 0, 0], atol=1)


@pytest.mark.parametrize("luma_offset,luma_excursion", [(0, 255), (64, 876)])
@pytest.mark.parametrize(
    "color_diff_offset,color_diff_excursion", [(128, 255), (512, 896)]
)
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
        color_primaries_index=primaries,
        color_matrix_index=matrix,
        transfer_function_index=transfer_function,
    )

    luma_bits = intlog2(luma_excursion + 1)
    color_diff_bits = intlog2(color_diff_excursion + 1)

    w, h = 6, 4

    rand = np.random.RandomState(0)
    y = rand.randint(0, 2 ** luma_bits, (h, w))
    c1 = rand.randint(0, 2 ** color_diff_bits, (h, w))
    c2 = rand.randint(0, 2 ** color_diff_bits, (h, w))

    xyz = to_xyz(y, c1, c2, video_parameters)

    assert xyz.shape == (h, w, 3)

    new_y, new_c1, new_c2 = from_xyz(xyz, video_parameters)

    assert np.array_equal(y, new_y)
    assert np.array_equal(c1, new_c1)
    assert np.array_equal(c2, new_c2)


def test_matmul_colors():
    old_r = np.arange(5 * 7).reshape(5, 7)
    old_g = old_r * 10
    old_b = old_r * 100

    old_rgb = np.stack([old_r, old_g, old_b], axis=-1)

    m = np.array([[2, 0, 0], [0, 3, 0], [0, 0, 4]])

    new_rgb = matmul_colors(m, old_rgb)

    assert np.array_equal(new_rgb[:, :, 0], old_r * 2)
    assert np.array_equal(new_rgb[:, :, 1], old_g * 3)
    assert np.array_equal(new_rgb[:, :, 2], old_b * 4)


def test_swap_primaries():
    vp_before = VideoParameters(color_primaries_index=PresetColorPrimaries.hdtv,)
    vp_after = VideoParameters(color_primaries_index=PresetColorPrimaries.uhdtv,)

    linear_rgb_before = np.array(
        [[[0, 0, 0], [0.5, 0.5, 0.5], [1, 1, 1]], [[1, 0, 0], [0, 1, 0], [0, 0, 1]]]
    )

    xyz_before = matmul_colors(
        LINEAR_RGB_TO_XYZ[vp_before["color_primaries_index"]], linear_rgb_before,
    )

    xyz_after = swap_primaries(xyz_before, vp_before, vp_after,)

    linear_rgb_after = matmul_colors(
        XYZ_TO_LINEAR_RGB[vp_after["color_primaries_index"]], xyz_after,
    )

    assert not np.all(np.isclose(xyz_before, xyz_after))
    assert np.all(np.isclose(linear_rgb_before, linear_rgb_after))


class TestColorParametersSanity(object):
    def test_default(self):
        assert ColorParametersSanity()

    @pytest.mark.parametrize(
        "param",
        [
            "luma_depth_sane",
            "color_diff_depth_sane",
            "black_sane",
            "white_sane",
            "red_sane",
            "green_sane",
            "blue_sane",
            "color_diff_format_sane",
            "luma_vs_color_diff_depths_sane",
        ],
    )
    def test_params(self, param):
        # Param should be considered as part of global sanity
        cps = ColorParametersSanity(**{param: False})
        assert not cps

        # Param should be available via property
        assert getattr(cps, param) is False
        assert getattr(ColorParametersSanity(), param) is True

    def test_explain_sane(self):
        # Singular
        assert ColorParametersSanity().explain() == "Color format is sensible."

    def test_explain_depth_insane(self):
        # Singular
        cps = ColorParametersSanity(luma_depth_sane=False)
        assert cps.explain() == (
            "The luma_excursion value indicates "
            "a video format using fewer than 8 bits. Hint: The *_excursion "
            "field gives the range of legal values for a component (i.e. "
            "max_value - min_value), not a number of bits."
        )

        # Plurals
        cps = ColorParametersSanity(luma_depth_sane=False, color_diff_depth_sane=False)
        assert cps.explain() == (
            "The luma_excursion and color_diff_excursion values indicate "
            "a video format using fewer than 8 bits. Hint: The *_excursion "
            "field gives the range of legal values for a component (i.e. "
            "max_value - min_value), not a number of bits."
        )

    def test_explain_color_insane(self):
        cps = ColorParametersSanity(white_sane=False, red_sane=False, green_sane=False)
        assert cps.explain() == (
            "Some colors (e.g. white, red, green) cannot be represented "
            "in the video format specified. Hint: Check luma_offset is a "
            "near zero value, for Y C1 C2 formats check color_diff_offset "
            "is near the center of the signal range and for RGB formats it "
            "is near zero."
        )

    def test_explain_color_diff_format_insane(self):
        cps = ColorParametersSanity(color_diff_format_sane=False)
        assert cps.explain() == (
            "A color subsampling format other than 4:4:4 has been used "
            "for format using the RGB color matrix."
        )

    def test_explain_luma_vs_color_diff_depths_insane(self):
        cps = ColorParametersSanity(luma_vs_color_diff_depths_sane=False)
        assert cps.explain() == (
            "Different (luma|color_diff)_offset and/or "
            "(luma|color_diff)_excursion values have been specified for "
            "format using the RGB color matrix."
        )

    def test_combined(self):
        cps = ColorParametersSanity(
            luma_depth_sane=False,
            color_diff_depth_sane=False,
            black_sane=False,
            white_sane=False,
            red_sane=False,
            green_sane=False,
            blue_sane=False,
            color_diff_format_sane=False,
            luma_vs_color_diff_depths_sane=False,
        )
        # One of each message, with blank lines between
        assert len(list(cps.explain().split("\n"))) == 4 + 3


class TestSanityCheckVideoParameters(object):
    @pytest.mark.parametrize("base_video_format", BaseVideoFormats)
    def test_all_base_video_formats_sensible(self, base_video_format):
        # Sanity check that all base video formats are considered to make sense
        video_parameters = set_source_defaults(base_video_format)
        assert sanity_check_video_parameters(video_parameters)

    @pytest.mark.parametrize("offset,excursion", [(0, 511), (16, 219)])
    def test_sane_rgb_mode(self, offset, excursion):
        video_parameters = VideoParameters(
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            luma_offset=offset,
            luma_excursion=excursion,
            color_diff_offset=offset,
            color_diff_excursion=excursion,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.rgb,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
        )
        assert sanity_check_video_parameters(video_parameters)

    @pytest.mark.parametrize("offset,excursion", [(0, 8), (0, 10), (0, 16)])
    def test_low_bit_depth(self, offset, excursion):
        video_parameters = VideoParameters(
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            luma_offset=offset,
            luma_excursion=excursion,
            color_diff_offset=offset,
            color_diff_excursion=excursion,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.rgb,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
        )
        sanity = sanity_check_video_parameters(video_parameters)
        assert not sanity.luma_depth_sane
        assert not sanity.color_diff_depth_sane

    @pytest.mark.parametrize(
        "color_matrix_index,color_diff_offset",
        [(PresetColorMatrices.hdtv, 0), (PresetColorMatrices.rgb, 512)],
    )
    def test_wrong_offset_for_matrix(self, color_matrix_index, color_diff_offset):
        video_parameters = VideoParameters(
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            luma_offset=0,
            luma_excursion=1023,
            color_diff_offset=color_diff_offset,
            color_diff_excursion=1023,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=color_matrix_index,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
        )
        sanity = sanity_check_video_parameters(video_parameters)
        assert not all(
            (
                sanity.white_sane,
                sanity.black_sane,
                sanity.red_sane,
                sanity.green_sane,
                sanity.blue_sane,
            )
        )

    @pytest.mark.parametrize(
        "color_diff_format_index",
        [
            ColorDifferenceSamplingFormats.color_4_2_2,
            ColorDifferenceSamplingFormats.color_4_2_0,
        ],
    )
    def test_non_444_rgb_insane(self, color_diff_format_index):
        video_parameters = VideoParameters(
            color_diff_format_index=color_diff_format_index,
            luma_offset=0,
            luma_excursion=255,
            color_diff_offset=0,
            color_diff_excursion=255,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.rgb,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
        )
        sanity = sanity_check_video_parameters(video_parameters)
        assert not sanity.color_diff_format_sane

    def test_asymmetric_444_rgb_insane(self):
        video_parameters = VideoParameters(
            color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
            luma_offset=0,
            luma_excursion=255,
            color_diff_offset=0,
            color_diff_excursion=512,
            color_primaries_index=PresetColorPrimaries.hdtv,
            color_matrix_index=PresetColorMatrices.rgb,
            transfer_function_index=PresetTransferFunctions.tv_gamma,
        )
        sanity = sanity_check_video_parameters(video_parameters)
        assert not sanity.luma_vs_color_diff_depths_sane
