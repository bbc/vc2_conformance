import pytest

from io import BytesIO

from bitarray import bitarray

from vc2_conformance import tables

from vc2_conformance.state import State
from vc2_conformance.video_parameters import VideoParameters

from vc2_conformance.bitstream import (
    BitstreamReader,
    BitstreamWriter,
    Deserialiser,
    Serialiser,
)

from vc2_conformance.bitstream import vc2


# This test file attepts to check only the behaviour of the slice-reading parts
# of the VC-2 bitstream serialisation/deserialisation processes.
#
# Note that all non-trivial behaviours of the LDSliceArray/HQSliceArray
# fixeddict classes is tested separately.


class TestLowDelay(object):
    
    @pytest.fixture
    def bitstream(self):
        """
        A hand-made low-delay bitstream containing two slices as follows:
        
        * Slice size: 127/2 bytes, so:
          * Slice 0 will be 63 bytes (504 bits)
          * Slice 1 will be 64 bytes (512 bits)
        * Data dimensions (no transform)
          * 4 x 4 luma data per slice
          * 2 x 2 color-diff data per slice
        * qindex = 10 for slice 0, 11 for slice 1
        * slice_y_length is chosen such that in slice 0 the luma data will not
          fit in the allocated space and in slice 1, the color diff data will
          not fit. This field is 9 bits long in both slices. Accounting for the
          qindex and slice_y_length field, 488 bits remain for data in slice 0
          and 496 remain in slice 1.
          * In slice 0: slice_y_length = 5 (leaving 483 for color diff)
          * In slice 1: slice_y_length = 487 (leaving 9 for color diff)
        * Luma data
          * Slice 0: '1' in first sample, '0' in rest
          * Slice 1: '1' in all samples
        * Color diff data
          * Slice 0: '2' in c1, and '-2' in c2 for all samples
          * Slice 1: '2' in c1, and '-2' in c2 for first samples, '0' in rest
        * Padding data in bounded blocks will be set to a binary string
          0b1000....0001 which fills the remaining space. Specifically:
          * Slice 0: Luma: No padding, Color-diff: 483-(2*2*4*2)=451 bits of padding
          * Slice 1: Luma: 487-(4*4*4)=423 bits of padding, Color-diff: No padding
        """
        out = b""
        
        # Slice 0 qindex and slice_y_length
        # 0d_____10________5
        # 0b0001010000000101
        # 0x___1___4___0___5
        out += b"\x14\x05"
        
        # Slice 0 luma and color-diff samples
        #    Luma          Color Diff                  Padding
        #     |                |                          |
        #    ,--, ,---------------------------,           |
        #    1  0 2  -2   2  -2   2  -2   2  -2           |
        #    |  | |   |   |   |   |   |   |   |           |
        #   ,--,|,--,,--,,--,,--,,--,,--,,--,,--,,------------------,
        # 0b00101011001110110011101100111011001111000000 ... 00000001
        # 0x___2___B___3___B___3___B___3___B___3___C___0 ... ___0___1
        out += b"\x2B\x3B\x3B\x3B\x3C" + (b"\x00"*55) + b"\x01"
        
        # Slice 1 qindex and slice_y_length
        # 0d_____11______487
        # 0b0001011111100111
        # 0x___1___7___E___7
        out += b"\x17\xE7"
        
        # Slice 1 luma and color-diff samples
        #       Luma             Padding      Color Diff
        #         |                 |             |
        #    ,----------,           |          ,-----,
        #    1   1  ... 1           |          2  -2 0
        #    |   |  +13 |           |          |   | |
        #   ,--,,--,   ,--,,----------------,,--,,--,|
        # 0b00100010...001010000000...0000001011001111
        # 0x___2___2...___2___8___0...___0___2___C___F
        out += (b"\x22"*8) + b"\x80" + (b"\x00"*51) + b"\x02\xCF"
        
        # Sanity check
        assert len(out) == 127
        
        return out
    
    @pytest.fixture
    def slice_array(self):
        """
        A hand-made :py:class:`LDSliceArray` contianing the same values encoded by
        the bitstream fixture.
        """
        return vc2.LDSliceArray(
            _parameters=vc2.SliceArrayParameters(
                slices_x=2,
                slices_y=1,
                start_sx=0,
                start_sy=0,
                slice_count=2,
                dwt_depth=0,
                dwt_depth_ho=0,
                luma_width=8,
                luma_height=4,
                color_diff_width=4,
                color_diff_height=2,
            ),
            _slice_bytes_numerator=127,
            _slice_bytes_denominator=2,
            qindex=[10, 11],
            slice_y_length=[5, 487],
            y_transform=([1] + [0]*15 + [1]*16),
            c1_transform=([2]*4 + [2] + [0]*3),
            c2_transform=([-2]*4 + [-2] + [0]*3),
            y_block_padding=[
                bitarray(),
                bitarray("1" + "0"*421 + "1"),
            ],
            c_block_padding=[
                bitarray("1" + "0"*449 + "1"),
                bitarray(),
            ],
        )
    
    @pytest.fixture
    def state(self):
        """
        A state object for a the VC-2 pseudo-code suitable for the
        bitstream fixture (above).
        """
        return State(
            parse_code=tables.ParseCodes.low_delay_picture,
            dwt_depth=0,
            dwt_depth_ho=0,
            luma_width=8,
            luma_height=4,
            color_diff_width=4,
            color_diff_height=2,
            slices_x=2,
            slices_y=1,
            slice_bytes_numerator=127,
            slice_bytes_denominator=2,
        )
    
    def test_serialise_transform_data(self, bitstream, state, slice_array):
        f = BytesIO()
        w = BitstreamWriter(f)
        with Serialiser(w, {"ld_slice_array": slice_array}) as serdes:
            vc2.transform_data(serdes, state)
        
        assert serdes.context == {"ld_slice_array": slice_array}
        assert f.getvalue() == bitstream
    
    def test_deserialise_transform_data(self, bitstream, state, slice_array):
        # NB: Deserialisation is also tested to assure correctness of the
        # hand-computed values in this test. The deserialiser's correctness is
        # implied by serialiser's correctness, tested above.
        r = BitstreamReader(BytesIO(bitstream))
        with Deserialiser(r) as serdes:
            vc2.transform_data(serdes, state)
        
        assert set(serdes.context) == set(["ld_slice_array"])
        
        sa = serdes.context["ld_slice_array"]
        assert sa == slice_array
    
    def test_deserialise_fragment_data(self, bitstream, state, slice_array):
        r = BitstreamReader(BytesIO(bitstream*2))
        
        slice_arrays = []
        
        for x_offset, y_offset, slice_count in [(0, 0, 1), (1, 0, 1), (0, 0, 2)]:
            state["fragment_x_offset"] = x_offset
            state["fragment_y_offset"] = y_offset
            state["fragment_slice_count"] = slice_count
            with Deserialiser(r) as serdes:
                vc2.fragment_data(serdes, state)
            slice_arrays.append(serdes.context.pop("ld_slice_array"))
            assert serdes.context == {}
        
        assert slice_arrays[2] == slice_array

class TestHighQuality(object):
    
    @pytest.fixture
    def bitstream(self):
        """
        A hand-made high-quality bitstream containing two slices as follows:
        
        * Slice prefixes: 2 bytes long
          * Slice 0 will have prefix bytes 0xDE 0xAD
          * Slice 1 will have prefix bytes 0xBE 0xEF
        * Data dimensions (no transform)
          * 4 x 4 luma data per slice
          * 2 x 2 color-diff data per slice
        * qindex = 10 for slice 0, 11 for slice 1
        * transform coefficients:
          * slice 0: all coefficients set to 1, 7 and -7 for Y, C1 and C2 (respectively)
          * slice 1: all coefficients set to 0 for all components
        * length: Set to be the samllest size large enough to fit the
          coefficients (slice scaler = 3)
          * slice 0: 
            * Y: Coeffs = 4*16bits = 8 bytes. Length field = 3. Length = 3*3=9 Bytes
            * C1: Coeffs = 8*4bits = 4 bytes. Length field = 2. Length = 2*3=6 Bytes
            * C2: Coeffs = 8*4bits = 4 bytes. Length field = 2. Length = 2*3=6 Bytes
          * slice 1: length field = 0
        * padding a binary string 0b100...001 filling any remaining space
          * slice 0:
            * Y: 0x81 (8 bits)
            * C1: 0x8001 (16 bits)
            * C2: 0x7FFE (16 bits)  (inverted bits to make distinct from C1)
        """
        out = b""
        
        # Slice 0 prefix bytes
        out += b"\xDE\xAD"
        
        # Slice 0 qindex
        out += b"\x0A"
        
        # Slice 0 slice_y_length
        out += b"\x03"
        
        # Slice 0 y_coeffs
        #     1   1 ...  1  Padding
        #     |   | +13  |    |
        #   ,--,,--,...,--,,------,
        # 0b00100010   001010000001
        # 0x___2___2...___2___8___1
        out += (b"\x22"*8) + b"\x81"
        
        # Slice 0 slice_c1_length
        out += b"\x02"
        
        # Slice 0 c1_coeffs
        #      7       7       7       7        Padding
        #      |       |       |       |           |
        #   ,------,,------,,------,,------,,--------------,
        # 0b000000100000001000000010000000101000000000000001
        # 0x___0___2___0___2___0___2___0___2___8___0___0___1
        out += (b"\x02"*4) + b"\x80\x01"
        
        # Slice 0 slice_c2_length
        out += b"\x02"
        
        # Slice 0 c2_coeffs
        #     -7      -7      -7      -7        Padding
        #      |       |       |       |           |
        #   ,------,,------,,------,,------,,--------------,
        # 0b000000110000001100000011000000110111111111111110
        # 0x___0___3___0___3___0___3___0___3___7___F___F___E
        out += (b"\x03"*4) + b"\x7F\xFE"
        
        # Slice 1 prefix bytes
        out += b"\xBE\xEF"
        
        # Slice 1 qindex
        out += b"\x0B"
        
        # Slice 1 slice_*_length
        out += b"\x00\x00\x00"
        
        return out
    
    @pytest.fixture
    def slice_array(self):
        """
        A hand-made :py:class:`HQSliceArray` contianing the same values encoded by
        the bitstream fixture.
        """
        return vc2.HQSliceArray(
            _parameters=vc2.SliceArrayParameters(
                slices_x=2,
                slices_y=1,
                start_sx=0,
                start_sy=0,
                slice_count=2,
                dwt_depth=0,
                dwt_depth_ho=0,
                luma_width=8,
                luma_height=4,
                color_diff_width=4,
                color_diff_height=2,
            ),
            _slice_prefix_bytes=2,
            _slice_size_scaler=3,
            prefix_bytes=[b"\xDE\xAD", b"\xBE\xEF"],
            qindex=[10, 11],
            slice_y_length=[3, 0],
            slice_c1_length=[2, 0],
            slice_c2_length=[2, 0],
            y_transform=([1]*16 + [0]*16),
            c1_transform=([7]*4 + [0]*4),
            c2_transform=([-7]*4 + [0]*4),
            y_block_padding=[
                bitarray("1" + "0"*6 + "1"),
                bitarray(),
            ],
            c1_block_padding=[
                bitarray("1" + "0"*14 + "1"),
                bitarray(),
            ],
            c2_block_padding=[
                bitarray("0" + "1"*14 + "0"),
                bitarray(),
            ],
        )
    
    @pytest.fixture
    def state(self):
        """
        A state object for a the VC-2 pseudo-code suitable for the
        bitstream fixture (above).
        """
        return State(
            parse_code=tables.ParseCodes.high_quality_picture,
            dwt_depth=0,
            dwt_depth_ho=0,
            luma_width=8,
            luma_height=4,
            color_diff_width=4,
            color_diff_height=2,
            slices_x=2,
            slices_y=1,
            slice_prefix_bytes=2,
            slice_size_scaler=3,
        )
    
    def test_serialise_transform_data(self, bitstream, state, slice_array):
        f = BytesIO()
        w = BitstreamWriter(f)
        with Serialiser(w, {"hq_slice_array": slice_array}) as serdes:
            vc2.transform_data(serdes, state)
        
        assert serdes.context == {"hq_slice_array": slice_array}
        assert f.getvalue() == bitstream
    
    def test_deserialise_transform_data(self, bitstream, state, slice_array):
        # NB: Deserialisation is also tested to assure correctness of the
        # hand-computed values in this test. The deserialiser's correctness is
        # implied by serialiser's correctness, tested above.
        r = BitstreamReader(BytesIO(bitstream))
        with Deserialiser(r) as serdes:
            vc2.transform_data(serdes, state)
        
        assert set(serdes.context) == set(["hq_slice_array"])
        
        sa = serdes.context["hq_slice_array"]
        assert sa == slice_array
    
    def test_deserialise_fragment_data(self, bitstream, state, slice_array):
        r = BitstreamReader(BytesIO(bitstream*2))
        
        slice_arrays = []
        
        for x_offset, y_offset, slice_count in [(0, 0, 1), (1, 0, 1), (0, 0, 2)]:
            state["fragment_x_offset"] = x_offset
            state["fragment_y_offset"] = y_offset
            state["fragment_slice_count"] = slice_count
            with Deserialiser(r) as serdes:
                vc2.fragment_data(serdes, state)
            slice_arrays.append(serdes.context.pop("hq_slice_array"))
            assert serdes.context == {}
        
        assert slice_arrays[2] == slice_array
