import pytest

from bitarray import bitarray

from vc2_conformance.bitstream.vc2.fixeddicts.slice_arrays import (
    LDSliceArray,
    HQSliceArray,
)

from vc2_conformance.bitstream.vc2.fixeddicts.slice_arrays_views import (
    SliceArrayParameters,
    BaseSliceView,
    ComponentView,
    ComponentSubbandView,
    LDSliceView,
    HQSliceView,
    component_views_str,
)

from vc2_conformance.exp_golomb import signed_exp_golomb_length
    


class TestSliceArrayParameters(object):
    
    def test_to_slice_index(self):
        p = SliceArrayParameters(slices_x=4, slices_y=3,
                                 start_sx=2, start_sy=1, slice_count=6)
        
        assert p.to_slice_index(2, 1) == 0
        assert p.to_slice_index(3, 1) == 1
        assert p.to_slice_index(0, 2) == 2
        assert p.to_slice_index(1, 2) == 3
        assert p.to_slice_index(2, 2) == 4
        assert p.to_slice_index(3, 2) == 5
    
    def test_from_slice_index(self):
        p = SliceArrayParameters(slices_x=4, slices_y=3,
                                 start_sx=2, start_sy=1, slice_count=6)
        
        assert p.from_slice_index(0) == (2, 1)
        assert p.from_slice_index(1) == (3, 1)
        assert p.from_slice_index(2) == (0, 2)
        assert p.from_slice_index(3) == (1, 2)
        assert p.from_slice_index(4) == (2, 2)
        assert p.from_slice_index(5) == (3, 2)

    def test_subband_dimensions_dc(self):
        p = SliceArrayParameters(dwt_depth=0, dwt_depth_ho=0)
        assert p.subband_dimensions(11, 5, level=0) == (11, 5)
    
    def test_subband_dimensions_ho(self):
        # Horizontal only
        assert SliceArrayParameters(dwt_depth=0, dwt_depth_ho=1).subband_dimensions(11, 5, level=1) == (
            12//2,  # Changed to become divisible by two
            5,
        )
        
        assert SliceArrayParameters(dwt_depth=0, dwt_depth_ho=2).subband_dimensions(11, 5, level=2) == (
            12//2,  # Changed to become divisible by four
            5,
        )
        
        assert SliceArrayParameters(dwt_depth=0, dwt_depth_ho=3).subband_dimensions(11, 5, level=3) == (
            16//2,  # Changed to become divisible by eight
            5,
        )
        
        # Working down the horizontal-only levels
        assert SliceArrayParameters(dwt_depth=0, dwt_depth_ho=3).subband_dimensions(11, 5, level=2) == (
            16//4,
            5,
        )
        assert SliceArrayParameters(dwt_depth=0, dwt_depth_ho=3).subband_dimensions(11, 5, level=1) == (
            16//8,
            5,
        )
        # DC Again
        assert SliceArrayParameters(dwt_depth=0, dwt_depth_ho=3).subband_dimensions(11, 5, level=0) == (
            16//8,
            5,
        )
    
    def test_subband_dimensions_2d_and_ho(self):
        # Starting from the HO level from above
        assert SliceArrayParameters(dwt_depth=1, dwt_depth_ho=3).subband_dimensions(11, 5, level=4) == (
            16//2,  # Changed to become divisible by sixteen
            6//2, # Changed to become divisible by two
        )
        
        assert SliceArrayParameters(dwt_depth=2, dwt_depth_ho=3).subband_dimensions(11, 5, level=5) == (
            32//2,  # Changed to become divisible by thirty-two
            8//2, # Changed to become divisible by four
        )
        
        assert SliceArrayParameters(dwt_depth=3, dwt_depth_ho=3).subband_dimensions(11, 5, level=6) == (
            64//2,  # Changed to become divisible by sixty-four
            8//2, # Changed to become divisible by eight
        )
        
        # Working down the levels
        assert SliceArrayParameters(dwt_depth=3, dwt_depth_ho=3).subband_dimensions(11, 5, level=5) == (
            64//4,
            8//4,
        )
        assert SliceArrayParameters(dwt_depth=3, dwt_depth_ho=3).subband_dimensions(11, 5, level=4) == (
            64//8,
            8//8,
        )
        
        # Hit horizontal only
        assert SliceArrayParameters(dwt_depth=3, dwt_depth_ho=3).subband_dimensions(11, 5, level=3) == (
            64//16,
            8//8,
        )
        assert SliceArrayParameters(dwt_depth=3, dwt_depth_ho=3).subband_dimensions(11, 5, level=2) == (
            64//32,
            8//8,
        )
        assert SliceArrayParameters(dwt_depth=3, dwt_depth_ho=3).subband_dimensions(11, 5, level=1) == (
            64//64,
            8//8,
        )
        
        # Hit DC
        assert SliceArrayParameters(dwt_depth=3, dwt_depth_ho=3).subband_dimensions(11, 5, level=0) == (
            64//64,
            8//8,
        )
    @pytest.mark.parametrize("sx,sy,x1,y1,x2,y2", [
        # Check consecutive and complete in X-axis
        (0, 0,  0, 0,  3, 2),
        (1, 0,  3, 0,  7, 2),
        (2, 0,  7, 0,  11, 2),
        # And then again on the Y-axis
        (0, 1,  0, 2,  3, 5),
        (1, 1,  3, 2,  7, 5),
        (2, 1,  7, 2,  11, 5),
    ])
    def test_slice_subband_bounds(self, sx, sy, x1, y1, x2, y2):
        p = SliceArrayParameters(slices_x=3, slices_y=2)
        assert p.slice_subband_bounds(
            sx, sy,
            subband_width=11, subband_height=5,
        ) == (x1, y1, x2, y2)
    
    def test_to_coeff_index_index_order(self):
        # Check this function produces correct indices for a sample scenario
        p = SliceArrayParameters(start_sx=1, start_sy=0, slices_x=3, slices_y=2)
        
        # Widths and heights were chosen arbitrarily to achieve
        # * subband_index=0 has subband slices with no entries
        # * subband_index=1 has subband slices with different sizes
        # * subband_index=2 has subband slices with equal sizes (10x10)
        subband_dimensions = [(2, 1), (11, 5), (30, 20)]
        
        # Iterate over the subband samples in what should be index order
        indices = []
        for sy in range(p["slices_y"] + 1):  # NB: Also test we can go beyond slices_y
            for sx in range(p["slices_x"]):
                # NB We start from sx=1, sy=0
                if sx == 0 and sy == 0:
                    continue
                
                for subband_index, (subband_width, subband_height) in enumerate(
                        subband_dimensions):
                    x1, y1, x2, y2 = p.slice_subband_bounds(
                        sx, sy,
                        subband_width, subband_height,
                    )
                    subband_slice_width = x2 - x1
                    subband_slice_height = y2 - y1
                    for y in range(subband_slice_height):
                        for x in range(subband_slice_width):
                            indices.append(p.to_coeff_index(
                                subband_dimensions,
                                sx, sy,
                                subband_index,
                                x, y,
                            ))
        
        assert indices == list(range(len(indices)))
    
    @pytest.mark.parametrize("sx,sy,subband_index,x,y", [
        # sx is out of range
        (-2, 0, 0, 0, 0),
        (-1, 0, 0, 0, 0),
        (3, 0, 0, 0, 0),
        (4, 0, 0, 0, 0),
        # subband_index is out of range
        (0, 0, -2, 0, 0),
        (0, 0, -1, 0, 0),
        (0, 0, 3, 0, 0),
        (0, 0, 4, 0, 0),
        # 'x' is out of range (because a zero-sized subband slice)
        (0, 0, 0, -2, 0),
        (0, 0, 0, -1, 0),
        (0, 0, 0, 1, 0),
        (0, 0, 0, 2, 0),
        # 'x' is out of range (because a smaller than usual subband slice)
        (0, 0, 1, -2, 0),
        (0, 0, 1, -1, 0),
        (0, 0, 1, 3, 0),
        (0, 0, 1, 4, 0),
        # 'y' is out of range (because of a zero-sized subband slice)
        (0, 0, 0, 0, -2),
        (0, 0, 0, 0, -1),
        (0, 0, 0, 0, 1),
        (0, 0, 0, 0, 2),
        # 'y' is out of range (because of a smaller than usual subband slice)
        (0, 0, 1, 0, -2),
        (0, 0, 1, 0, -1),
        (0, 0, 1, 0, 2),
        (0, 0, 1, 0, 3),
    ])
    def test_to_coeff_index_out_of_range_errors(self, sx, sy, subband_index, x, y):
        p = SliceArrayParameters(slices_x=3, slices_y=2)
        
        # Chosen carefully such that:
        # * subband_index=0 has subband slices with no entries
        # * subband_index=1 has subband slices with different sizes
        # * subband_index=2 has subband slices with equal sizes (10x10)
        subband_dimensions = [(2, 1), (11, 5), (30, 20)]
        
        with pytest.raises(IndexError):
            p.to_coeff_index(
                subband_dimensions,
                sx, sy,
                subband_index,
                x, y,
            )
    
    def test_to_num_subbands_and_levels(self):
        p = SliceArrayParameters(dwt_depth=0, dwt_depth_ho=0)
        
        assert p.num_subbands == 1
        assert p.num_subband_levels == 1
        
        p["dwt_depth"] = 3
        assert p.num_subbands == 1 + 3 + 3 + 3
        assert p.num_subband_levels == 1 + 3
        
        p["dwt_depth_ho"] = 2
        assert p.num_subbands == 1 + 1 + 1 + 3 + 3 + 3
        assert p.num_subband_levels == 1 + 2 + 3
    
    def test_luma_and_color_diff_subband_dimensions(self):
        p = SliceArrayParameters(
            luma_width=256,
            luma_height=128,
            color_diff_width=256//2,
            color_diff_height=128//2,
            slices_x=4,
            slices_y=4,
            dwt_depth=2,
            dwt_depth_ho=1,
        )
        assert p.luma_subband_dimensions == (
            (256//8, 128//4),  # Level 0: L
            (256//8, 128//4),  # Level 1: H
            (256//4, 128//4),  # Level 2: HL
            (256//4, 128//4),  # Level 2: LH
            (256//4, 128//4),  # Level 2: HH
            (256//2, 128//2),  # Level 3: HL
            (256//2, 128//2),  # Level 3: LH
            (256//2, 128//2),  # Level 3: HH
        )
        assert p.color_diff_subband_dimensions == (
            (256//2//8, 128//2//4),  # Level 0: L
            (256//2//8, 128//2//4),  # Level 1: H
            (256//2//4, 128//2//4),  # Level 2: HL
            (256//2//4, 128//2//4),  # Level 2: LH
            (256//2//4, 128//2//4),  # Level 2: HH
            (256//2//2, 128//2//2),  # Level 3: HL
            (256//2//2, 128//2//2),  # Level 3: LH
            (256//2//2, 128//2//2),  # Level 3: HH
        )


class TestBaseSliceView(object):
    
    @pytest.fixture(params=[LDSliceArray, HQSliceArray])
    def a(self, request):
        T = request.param
        return T(
            _parameters=SliceArrayParameters(
                slices_x=10,
                slices_y=5,
            ),
        )
    
    @pytest.fixture()
    def v(self, a):
        return BaseSliceView(a, 1, 2)
    
    def test_constructor(self, v):
        assert v.sx == 1
        assert v.sy == 2
        assert v.slice_index == 21
    
    def test_qindex(self, a, v):
        a["qindex"] = [0]*10*5
        
        # Get
        v.qindex = 123
        assert a["qindex"][10*2 + 1] == 123
        
        # Set
        a["qindex"][10*2 + 1] = 321
        assert v.qindex == 321
    
    def test_coeffs(self, v):
        for component in ["y", "c1", "c2"]:
            coeffs_view = getattr(v, "{}_transform".format(component))
            assert isinstance(coeffs_view, ComponentView)
            assert coeffs_view.component == component


class TestLDSliceArray(object):
    
    def test_lengths(self):
        a = LDSliceArray(
            _parameters=SliceArrayParameters(
                luma_width=16,
                luma_height=8,
                color_diff_width=8,
                color_diff_height=4,
                slices_x=4,
                slices_y=2,
            ),
            _slice_bytes_numerator=127,
            _slice_bytes_denominator=2,
            y_transform=[0]*16*8,
            c1_transform=[0]*8*4,
            c2_transform=[0]*8*4,
            slice_y_length=[0]*4*2,
            y_block_padding=[bitarray()]*4*2,
            c_block_padding=[bitarray()]*4*2,
        )
        
        assert a[0].length == 63*8
        assert a[1].length == 64*8
        
        assert a[0].header_length == 7 + 9
        assert a[1].header_length == 7 + 9
        
        a[0].slice_y_length = 0
        a[1].slice_y_length = 0
        assert a[0].true_slice_y_length == 0
        assert a[1].true_slice_y_length == 0
        assert a[0].slice_c_length == 63*8 - (7 + 9)
        assert a[1].slice_c_length == 64*8 - (7 + 9)
        
        a[0].slice_y_length = 123
        a[1].slice_y_length = 321
        assert a[0].true_slice_y_length == 123
        assert a[1].true_slice_y_length == 321
        assert a[0].slice_c_length == 63*8 - (7 + 9) - 123
        assert a[1].slice_c_length == 64*8 - (7 + 9) - 321
        
        # Clamp to maximum size
        a[0].slice_y_length = 100000
        a[1].slice_y_length = 100000
        assert a[0].true_slice_y_length == 63*8 - (7 + 9)
        assert a[1].true_slice_y_length == 64*8 - (7 + 9)
        assert a[0].slice_c_length == 0
        assert a[1].slice_c_length == 0


class TestComponentView(object):
    
    @pytest.fixture()
    def p(self):
        return SliceArrayParameters(
            slices_x=10,
            slices_y=5,
        )
    
    @pytest.fixture(params=[LDSliceArray, HQSliceArray])
    def a(self, request, p):
        T = request.param
        return T(_parameters=p)
    
    @pytest.fixture()
    def v(self, a):
        return a[1, 2].y_transform
    
    def test_constructor(self, a, v):
        assert v.component == "y"
    
    def test_len(self, p, v):
        p["dwt_depth"] = 0
        p["dwt_depth_ho"] = 0
        assert len(v) == 1
        
        p["dwt_depth"] = 1
        p["dwt_depth_ho"] = 2
        assert len(v) == 1 + 2 + 3
    
    def test_iter(self, p, v):
        p["dwt_depth"] = 0
        p["dwt_depth_ho"] = 0
        assert [sv.subband_index for sv in v] == [0]
        
        p["dwt_depth"] = 1
        p["dwt_depth_ho"] = 2
        assert [sv.subband_index for sv in v] == list(range(1 + 2 + 3))
    
    def test_items(self, p, v):
        p["dwt_depth"] = 0
        p["dwt_depth_ho"] = 0
        assert [(l, s, sv.subband_index) for l, s, sv in v.items()] == [(0, "DC", 0)]
        
        p["dwt_depth"] = 1
        p["dwt_depth_ho"] = 2
        assert [(l, s, sv.subband_index) for l, s, sv in v.items()] == [
            (0, "L", 0),
            (1, "H", 1),
            (2, "H", 2),
            (3, "HL", 3),
            (3, "LH", 4),
            (3, "HH", 5),
        ]
    
    def test_getitem(self, p, v):
        p["dwt_depth"] = 0
        p["dwt_depth_ho"] = 0
        assert v[0].subband_index == 0
        assert v[0, "DC"].subband_index == 0
        
        p["dwt_depth"] = 1
        p["dwt_depth_ho"] = 2
        for i, (l, s) in enumerate([(0, "L"), (1, "H"), (2, "H"),
                                    (3, "HL"), (3, "LH"), (3, "HH")]):
            assert v[i].subband_index == i
            assert v[l, s].subband_index == i


class TestComponentSubbandView(object):
    
    @pytest.fixture()
    def p(self):
        return SliceArrayParameters(
            slices_x=10,
            slices_y=5,
            luma_width=200,
            luma_height=50,
        )
    
    @pytest.fixture(params=[LDSliceArray, HQSliceArray])
    def a(self, request, p):
        T = request.param
        return T(_parameters=p)
    
    @pytest.fixture()
    def v(self, a):
        return a[1, 2].y_transform[0]
    
    def test_constructor(self, a, v):
        assert v.subband_index == 0
        assert v.subband == (0, "DC")
    
    def test_bounds(self, v):
        assert v.bounds == (20, 20, 40, 30)
    
    def test_dimensions(self, v):
        assert v.dimensions == (20, 10)
    
    def test_len(self, v):
        assert len(v) == 20 * 10
    
    def test_normalise_key(self, p, v):
        p["start_sx"] = 0
        p["start_sy"] = 0
        
        base = ((10*2)*200) + (20*10)
        assert v._normalise_key(0) == base
        assert v._normalise_key(20) == base + 20
        
        assert v._normalise_key((0, 0)) == base
        assert v._normalise_key((10, 0)) == base + 10
        assert v._normalise_key((0, 5)) == base + (5*20)
        assert v._normalise_key((1, 5)) == base + (5*20) + 1
        
        p["start_sx"] = 1
        p["start_sy"] = 2
        assert v._normalise_key(0) == 0
        assert v._normalise_key((0, 0)) == 0
    
    def test_start_and_end_indices(self, v):
        base = ((10*2)*200) + (20*10)
        assert v.start_index == base
        assert v.end_index == base + len(v)
    
    def test_get_and_set(self, p, a, v):
        p["start_sx"] = 1
        p["start_sy"] = 2
        for _ in range(20*10):
            a["y_transform"].append(0)
        
        v[0, 1] = 123
        assert a["y_transform"][20] == 123
        
        a["y_transform"][20] = 321
        assert v[0, 1] == 321
    
    def test_iter(self, p, a, v):
        p["start_sx"] = 1
        p["start_sy"] = 2
        for i in range(20*10):
            a["y_transform"].append(i)
        
        assert list(iter(v)) == list(range(20*10))
    
    def test_items(self, p, a, v):
        p["start_sx"] = 1
        p["start_sy"] = 2
        for i in range(20*10):
            a["y_transform"].append(i)
        
        assert list(v.items()) == [
            (i%20, i//20, i)
            for i in range(20*10)
        ]


class TestComponentViewsStr(object):
    
    # The following fixtures define structures with the following dimensions
    #
    # 4:2:0 colour sampling -> 128x16 luma, 64x8 color-diff
    # 4x2 slices -> 32x8 luma, 16x4 color-diff dimensions
    # One horizontal only transform level and two 2D transform levels ->
    #   Level 0, L: 4x2 luma, 2x1 color-diff
    #   Level 1, H: 4x2 luma, 2x1 color-diff
    #   Level 2: HL, LH, HH: 8x2 luma, 4x1 color-diff
    #   Level 3: HL, LH, HH: 16x4 luma, 8x2 color-diff
    
    @pytest.fixture
    def p(self):
        return SliceArrayParameters(
            slices_x=4,
            slices_y=2,
            luma_width=128,
            luma_height=16,
            color_diff_width=64,
            color_diff_height=8,
            dwt_depth=2,
            dwt_depth_ho=1,
            start_sx=2,
            start_sy=1,
            slice_count=2,
        )
    
    @pytest.fixture(params=[LDSliceArray, HQSliceArray])
    def a(self, request, p):
        T = request.param
        a = T(_parameters=p)
        
        if T is LDSliceArray:
            a["slice_y_length"] = [0] * 128*16
            a["y_block_padding"] = [bitarray()] * 128*16
            a["c_block_padding"] = [bitarray()] * 64*8
        else:
            a["slice_y_length"] = [0] * 128*16
            a["slice_c1_length"] = [0] * 64*8
            a["slice_c2_length"] = [0] * 64*8
            
            a["y_block_padding"] = [bitarray()] * 128*16
            a["c1_block_padding"] = [bitarray()] * 64*8
            a["c2_block_padding"] = [bitarray()] * 64*8
        
        a["y_transform"] = [0] * 128*16
        a["c1_transform"] = [0] * 64*8
        a["c2_transform"] = [0] * 64*8
        
        return a
    
    def test_with_padding(self, a):
        c1_transform = a[0].c1_transform
        c2_transform = a[0].c2_transform
        
        # Pre-populate the color samples with increasing integers
        i = 0
        num_bits = 0
        for subband_index in range(len(c1_transform)):
            c1_subband = c1_transform[subband_index]
            c2_subband = c2_transform[subband_index]
            for value_index in range(len(c1_subband)):
                c1_subband[value_index] = i
                c2_subband[value_index] = i + 1
                num_bits += signed_exp_golomb_length(i)
                num_bits += signed_exp_golomb_length(i+1)
                i += 2
        
        assert component_views_str(
            num_bits + 4,
            bitarray("0101"),
            c1_transform,
            c2_transform,
        ) == (
            "Level 0, L:\n"
            "  (0, 1)  (2, 3)\n"
            "Level 1, H:\n"
            "  (4, 5)  (6, 7)\n"
            "Level 2, HL:\n"
            "  (8, 9)  (10, 11)  (12, 13)  (14, 15)\n"
            "Level 2, LH:\n"
            "  (16, 17)  (18, 19)  (20, 21)  (22, 23)\n"
            "Level 2, HH:\n"
            "  (24, 25)  (26, 27)  (28, 29)  (30, 31)\n"
            "Level 3, HL:\n"
            "  (32, 33)  (34, 35)  (36, 37)  (38, 39)  (40, 41)  (42, 43)  (44, 45)  (46, 47)\n"
            "  (48, 49)  (50, 51)  (52, 53)  (54, 55)  (56, 57)  (58, 59)  (60, 61)  (62, 63)\n"
            "Level 3, LH:\n"
            "  (64, 65)  (66, 67)  (68, 69)  (70, 71)  (72, 73)  (74, 75)  (76, 77)  (78, 79)\n"
            "  (80, 81)  (82, 83)  (84, 85)  (86, 87)  (88, 89)  (90, 91)  (92, 93)  (94, 95)\n"
            "Level 3, HH:\n"
            "    (96, 97)    (98, 99)  (100, 101)  (102, 103)  (104, 105)  (106, 107)  (108, 109)  (110, 111)\n"
            "  (112, 113)  (114, 115)  (116, 117)  (118, 119)  (120, 121)  (122, 123)  (124, 125)  (126, 127)\n"
            "4 unused bits: 0b0101"
        )
    
    def test_with_values_past_end(self, a):
        c1_transform = a[0].c1_transform
        c2_transform = a[0].c2_transform
        
        # Pre-populate the color samples with increasing integers
        i = 0
        num_bits = 0
        for subband_index in range(len(c1_transform) - 1):
            c1_subband = c1_transform[subband_index]
            c2_subband = c2_transform[subband_index]
            for value_index in range(len(c1_subband)):
                c1_subband[value_index] = i
                c2_subband[value_index] = i + 1
                num_bits += signed_exp_golomb_length(i)
                num_bits += signed_exp_golomb_length(i+1)
                i += 2
        
        assert component_views_str(
            num_bits + 1,
            0,
            c1_transform,
            c2_transform,
        ) == (
            "Level 0, L:\n"
            "  (0, 1)  (2, 3)\n"
            "Level 1, H:\n"
            "  (4, 5)  (6, 7)\n"
            "Level 2, HL:\n"
            "  (8, 9)  (10, 11)  (12, 13)  (14, 15)\n"
            "Level 2, LH:\n"
            "  (16, 17)  (18, 19)  (20, 21)  (22, 23)\n"
            "Level 2, HH:\n"
            "  (24, 25)  (26, 27)  (28, 29)  (30, 31)\n"
            "Level 3, HL:\n"
            "  (32, 33)  (34, 35)  (36, 37)  (38, 39)  (40, 41)  (42, 43)  (44, 45)  (46, 47)\n"
            "  (48, 49)  (50, 51)  (52, 53)  (54, 55)  (56, 57)  (58, 59)  (60, 61)  (62, 63)\n"
            "Level 3, LH:\n"
            "  (64, 65)  (66, 67)  (68, 69)  (70, 71)  (72, 73)  (74, 75)  (76, 77)  (78, 79)\n"
            "  (80, 81)  (82, 83)  (84, 85)  (86, 87)  (88, 89)  (90, 91)  (92, 93)  (94, 95)\n"
            "Level 3, HH:\n"
            "   (0, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)"
        )
    
    def test_with_single_coefficient_set(self, a):
        y_transform = a[0].y_transform
        
        # Pre-populate the color samples with increasing integers
        i = 0
        num_bits = 0
        for subband_index in range(len(y_transform) - 1):
            y_subband = y_transform[subband_index]
            for value_index in range(len(y_subband)):
                y_subband[value_index] = i
                num_bits += signed_exp_golomb_length(i)
                i += 1
        
        assert component_views_str(
            num_bits + 1,
            0,
            y_transform,
        ) == (
            "Level 0, L:\n"
            "  0  1  2  3\n"
            "  4  5  6  7\n"
            "Level 1, H:\n"
            "   8   9  10  11\n"
            "  12  13  14  15\n"
            "Level 2, HL:\n"
            "  16  17  18  19  20  21  22  23\n"
            "  24  25  26  27  28  29  30  31\n"
            "Level 2, LH:\n"
            "  32  33  34  35  36  37  38  39\n"
            "  40  41  42  43  44  45  46  47\n"
            "Level 2, HH:\n"
            "  48  49  50  51  52  53  54  55\n"
            "  56  57  58  59  60  61  62  63\n"
            "Level 3, HL:\n"
            "   64   65   66   67   68   69   70   71   72   73   74   75   76   77   78   79\n"
            "   80   81   82   83   84   85   86   87   88   89   90   91   92   93   94   95\n"
            "   96   97   98   99  100  101  102  103  104  105  106  107  108  109  110  111\n"
            "  112  113  114  115  116  117  118  119  120  121  122  123  124  125  126  127\n"
            "Level 3, LH:\n"
            "  128  129  130  131  132  133  134  135  136  137  138  139  140  141  142  143\n"
            "  144  145  146  147  148  149  150  151  152  153  154  155  156  157  158  159\n"
            "  160  161  162  163  164  165  166  167  168  169  170  171  172  173  174  175\n"
            "  176  177  178  179  180  181  182  183  184  185  186  187  188  189  190  191\n"
            "Level 3, HH:\n"
            "   0  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*\n"
            "  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*\n"
            "  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*\n"
            "  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*"
        )
