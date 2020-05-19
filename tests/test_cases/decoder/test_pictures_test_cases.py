import pytest

import logging

from bitarray import bitarray

from copy import deepcopy

from io import BytesIO

from collections import defaultdict

from itertools import islice

from vc2_data_tables import (
    Profiles,
    ParseCodes,
    WaveletFilters,
    ColorDifferenceSamplingFormats,
    PictureCodingModes,
)

from vc2_conformance.bitstream.exp_golomb import signed_exp_golomb_length

from vc2_conformance.pseudocode.state import State

from vc2_conformance.bitstream import (
    Serialiser,
    MonitoredSerialiser,
    BitstreamWriter,
    BitstreamReader,
    vc2_default_values,
    to_bit_offset,
    HQSlice,
    LDSlice,
    hq_slice,
    ld_slice,
    autofill_and_serialise_stream,
    parse_stream,
)

from vc2_conformance import decoder

from sample_codec_features import MINIMAL_CODEC_FEATURES

from vc2_conformance.test_cases.decoder.pictures import (
    generate_filled_padding,
    fill_hq_slice_padding,
    fill_ld_slice_padding,
    generate_exp_golomb_with_ascending_lengths,
    slice_padding_data,
    UnsatisfiableBlockSizeError,
    generate_exp_golomb_with_length,
    DanglingTransformValueType,
    generate_dangling_transform_values,
    cut_off_value_at_end_of_hq_slice,
    cut_off_value_at_end_of_ld_slice,
    dangling_bounded_block_data,
)


class TestGenerateFiledPadding(object):
    def test_empty(self):
        assert generate_filled_padding(0, b"\x00", 0) == bitarray()
        assert generate_filled_padding(0, b"\x00", 1) == bitarray()

    def test_partial_filler_copy(self):
        assert generate_filled_padding(12, b"\xAA\xFF") == bitarray("10101010" "1111")

    def test_full_filler_copy(self):
        assert generate_filled_padding(16, b"\xAA\xFF") == bitarray(
            "10101010" "11111111"
        )

    def test_multiple_filler_copies(self):
        assert generate_filled_padding(32, b"\xAA\xFF") == bitarray(
            "10101010" "11111111" "10101010" "11111111"
        )

    def test_multiple_partial_filler_copies(self):
        assert generate_filled_padding(40, b"\xAA\xFF") == bitarray(
            "10101010" "11111111" "10101010" "11111111" "10101010"
        )
        assert generate_filled_padding(44, b"\xAA\xFF") == bitarray(
            "10101010" "11111111" "10101010" "11111111" "10101010" "1111"
        )

    def test_byte_alignment_not_required(self):
        assert generate_filled_padding(32, b"\xAA\xFF", 8) == bitarray(
            "10101010" "11111111" "10101010" "11111111"
        )

    def test_byte_alignment_required(self):
        assert generate_filled_padding(32, b"\xAA\xFF", 14) == bitarray(
            # Byte align
            "00"
            # Filler
            "10101010"
            "11111111"
            "10101010"
            "111111"  # Truncated
        )


class TestFillHQSlicePadding(object):
    def sanity_check(self, slice_size_scaler, slice):
        """
        Checks that the provided slice serializes correctly.
        """
        slice.setdefault("prefix_bytes", bytes())
        slice.setdefault("y_block_padding", bitarray())
        slice.setdefault("c1_block_padding", bitarray())
        slice.setdefault("c2_block_padding", bitarray())

        f = BytesIO()
        with Serialiser(BitstreamWriter(f), slice) as ser:
            hq_slice(
                ser,
                State(
                    slice_prefix_bytes=0,
                    slice_size_scaler=slice_size_scaler,
                    dwt_depth=0,
                    dwt_depth_ho=0,
                    luma_width=len(slice["y_transform"]),
                    luma_height=1,
                    color_diff_width=len(slice["c1_transform"]),
                    color_diff_height=1,
                    slices_x=1,
                    slices_y=1,
                ),
                0,
                0,
            )

    @pytest.mark.parametrize("slice_size_scaler", [1, 10])
    @pytest.mark.parametrize(
        "transform_data",
        [
            ([], [], []),
            ([0, 0, 0, 0, 0, 0], [0, 0, 0], [0, 0, 0]),
            ([1, 2, 3, 4, 5, 6], [1, 2, 3], [4, 5, 6]),
        ],
    )
    @pytest.mark.parametrize("component", ["Y", "C1", "C2"])
    @pytest.mark.parametrize("byte_align", [True, False])
    def test_zero_size_slice(
        self, slice_size_scaler, transform_data, byte_align, component,
    ):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=0,
            slice_c1_length=0,
            slice_c2_length=0,
            y_transform=transform_data[0],
            c1_transform=transform_data[1],
            c2_transform=transform_data[2],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=slice_size_scaler),
            0,
            0,
            hq_slice,
            component,
            b"\xAA\xBB",
            byte_align,
        )

        assert hq_slice["slice_y_length"] == 0
        assert hq_slice["slice_c1_length"] == 0
        assert hq_slice["slice_c2_length"] == 0

        if all(transform_data):
            assert hq_slice["y_transform"] == [0] * 6
            assert hq_slice["c1_transform"] == [0] * 3
            assert hq_slice["c2_transform"] == [0] * 3
        else:
            assert hq_slice["y_transform"] == []
            assert hq_slice["c1_transform"] == []
            assert hq_slice["c2_transform"] == []

        assert hq_slice.get("y_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()

        self.sanity_check(slice_size_scaler, hq_slice)

    def test_clears_transform_coeffs(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[1, 2, 3, 4, 5, 6],
            c1_transform=[7, 8, 9],
            c2_transform=[0, 1, 2],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=1), 0, 0, hq_slice, "Y", b"\x00",
        )

        assert hq_slice["y_transform"] == [0, 0, 0, 0, 0, 0]
        assert hq_slice["c1_transform"] == [0, 0, 0]
        assert hq_slice["c2_transform"] == [0, 0, 0]

        self.sanity_check(1, hq_slice)

    @pytest.mark.parametrize("slice_size_scaler", [1, 10])
    @pytest.mark.parametrize("component", ["Y", "C1", "C2"])
    def test_sums_lengths(self, slice_size_scaler, component):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=slice_size_scaler),
            0,
            0,
            hq_slice,
            component,
            b"\x00",
        )

        if component == "Y":
            assert hq_slice["slice_y_length"] == 1 + 2 + 3
        else:
            assert hq_slice["slice_y_length"] == 0

        if component == "C1":
            assert hq_slice["slice_c1_length"] == 1 + 2 + 3
        else:
            assert hq_slice["slice_c1_length"] == 0

        if component == "C2":
            assert hq_slice["slice_c2_length"] == 1 + 2 + 3
        else:
            assert hq_slice["slice_c2_length"] == 0

        self.sanity_check(slice_size_scaler, hq_slice)

    def test_fill_unaligned(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=1), 0, 0, hq_slice, "Y", b"\x00\xFF\xAA",
        )

        assert hq_slice["y_block_padding"] == bitarray(
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00000000"
            "11111111"
            "10"  # Truncated
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()

        self.sanity_check(1, hq_slice)

    def test_fill_aligned(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=1), 0, 0, hq_slice, "Y", b"\x00\xFF\xAA", True,
        )

        assert hq_slice["y_block_padding"] == bitarray(
            # Byte align
            "00"
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00000000"
            "11111111"
            # Trunacated!
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()

        self.sanity_check(1, hq_slice)

    def test_fill_already_aligned(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0, 0],
            c2_transform=[0, 0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=1), 0, 0, hq_slice, "Y", b"\x00\xFF\xAA", True,
        )

        assert hq_slice["y_block_padding"] == bitarray(
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00000000"
            "11111111"
            # Trunacated!
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()

        self.sanity_check(1, hq_slice)

    def test_slice_size_scaler(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=2), 0, 0, hq_slice, "Y", b"\x00\xFF\xAA", True,
        )

        assert hq_slice["y_block_padding"] == bitarray(
            # Byte align
            "00"
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two...
            "00000000"
            "11111111"
            "10101010"
            # Repeat three...
            "00000000"
            "11111111"
            "10101010"
            # Repeat four
            "00000000"
            "11111111"
            # Trunacated!
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()

        self.sanity_check(2, hq_slice)

    def test_min_length(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=2), 0, 0, hq_slice, "Y", b"\x00\xFF\xAA", True, 7,
        )

        assert hq_slice["slice_y_length"] == 7
        assert hq_slice["slice_c1_length"] == 0
        assert hq_slice["slice_c2_length"] == 0

        assert hq_slice["y_block_padding"] == bitarray(
            # Byte align
            "00"
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two...
            "00000000"
            "11111111"
            "10101010"
            # Repeat three...
            "00000000"
            "11111111"
            "10101010"
            # Repeat four...
            "00000000"
            "11111111"
            "10101010"
            # Repeat five
            "00000000"
            # Truncated
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()

        self.sanity_check(2, hq_slice)


class TestFillLDSlicePadding(object):
    def make_state(self):
        return State(
            slice_bytes_numerator=6, slice_bytes_denominator=1, slices_x=1, slices_y=1,
        )

    @pytest.fixture
    def state(self):
        return self.make_state()

    def sanity_check(self, slice):
        """
        Checks that the provided slice serializes correctly.
        """
        slice.setdefault("y_block_padding", bitarray())
        slice.setdefault("c_block_padding", bitarray())

        f = BytesIO()
        state = self.make_state()
        state.update(
            State(
                dwt_depth=0,
                dwt_depth_ho=0,
                luma_width=len(slice["y_transform"]),
                luma_height=1,
                color_diff_width=len(slice["c_transform"]) // 2,
                color_diff_height=1,
            )
        )
        with Serialiser(BitstreamWriter(f), slice) as ser:
            ld_slice(ser, state, 0, 0)

    def test_clears_transform_coeffs(self, state):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=1,
            y_transform=[1, 2, 3, 4, 5, 6],
            c_transform=[7, 8, 9, 10],
        )
        fill_ld_slice_padding(
            state, 0, 0, ld_slice, "Y", b"\x00",
        )

        assert ld_slice["y_transform"] == [0, 0, 0, 0, 0, 0]
        assert ld_slice["c_transform"] == [0, 0, 0, 0]

        self.sanity_check(ld_slice)

    @pytest.mark.parametrize("component", ["Y", "C"])
    def test_sums_lengths(self, component, state):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=1,
            y_transform=[0, 0, 0, 0, 0, 0],
            c_transform=[0, 0, 0, 0],
        )
        fill_ld_slice_padding(
            state, 0, 0, ld_slice, component, b"\x00",
        )

        if component == "Y":
            assert ld_slice["slice_y_length"] == (6 * 8) - 7 - 6
        else:
            assert ld_slice["slice_y_length"] == 0

        self.sanity_check(ld_slice)

    @pytest.mark.parametrize("component", ["Y", "C"])
    def test_fill_unaligned(self, state, component):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=1,
            y_transform=[0, 0, 0, 0, 0, 0],
            c_transform=[0, 0, 0, 0],
        )
        fill_ld_slice_padding(
            state, 0, 0, ld_slice, component, b"\x00\xFF\xAA",
        )

        # 35 - 6 = 29 bits to fill
        expected = bitarray(
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00000"  # Truncated
        )
        if component == "Y":
            assert ld_slice["y_block_padding"] == expected
            assert ld_slice.get("c_block_padding", bitarray()) == bitarray()
        else:
            assert ld_slice.get("y_block_padding", bitarray()) == bitarray()
            # Extra bits of filler due to two fewer transform components
            assert ld_slice["c_block_padding"] == expected + bitarray("00")

        self.sanity_check(ld_slice)

    @pytest.mark.parametrize("component", ["Y", "C"])
    def test_fill_aligned(self, state, component):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=1,
            y_transform=[0, 0, 0, 0, 0, 0],
            c_transform=[0, 0, 0, 0],
        )
        fill_ld_slice_padding(
            state, 0, 0, ld_slice, component, b"\x00\xFF\xAA", True,
        )

        # 7 + 6 = 13 bits of header so 3 bits required for byte alignment
        # 35 - 6 - 3 = 25 bits to fill
        expected = bitarray(
            # Byte alignment bits
            "000"
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00"  # Truncated
        )
        if component == "Y":
            assert ld_slice["y_block_padding"] == expected
            assert ld_slice.get("c_block_padding", bitarray()) == bitarray()
        else:
            assert ld_slice.get("y_block_padding", bitarray()) == bitarray()
            # Extra bits of filler due to two fewer transform components
            assert ld_slice["c_block_padding"] == expected + bitarray("00")

        self.sanity_check(ld_slice)


@pytest.mark.parametrize("sign", [+1, -1])
def test_generate_exp_golomb_numbers_with_ascending_lengths(sign):
    for length, number in islice(
        generate_exp_golomb_with_ascending_lengths(sign), 128,
    ):
        # Use a known-good implementation of a signed exp-golmb encoder and
        # check length is correct.
        f = BytesIO()
        w = BitstreamWriter(f)
        w.write_sint(number)
        actual_length = to_bit_offset(*w.tell())
        assert actual_length == length

        # Check sign of number
        if sign < 0:
            assert number <= 0
        else:
            assert number >= 0


@pytest.mark.parametrize(
    "num_values,required_length,expected",
    [
        # Special case: 0-bits can only be achieved by zero items
        (0, 0, []),
        (1, 0, None),
        (2, 0, None),
        # Special case singleton
        (1, 0, None),
        (1, 1, [0]),
        (1, 2, None),
        (1, 3, None),
        (1, 4, [1]),
        (1, 5, None),
        (1, 6, [3]),
        (1, 7, None),
        (1, 8, [7]),
        # Pair of numbers should be simillarly sized, add flexibility and alternate
        # in signs.
        (2, 0, None),
        (2, 1, None),
        (2, 2, [0, 0]),
        (2, 3, None),
        (2, 4, None),
        (2, 5, [1, 0]),
        (2, 6, None),
        (2, 7, [3, 0]),
        (2, 8, [1, -1]),
        (2, 9, [7, 0]),
        # Triple of numbers, may end up with last one or two values being fixed at
        # zero
        (3, 0, None),
        (3, 1, None),
        (3, 2, None),
        (3, 3, [0, 0, 0]),
        (3, 4, None),
        (3, 5, None),
        (3, 6, [1, 0, 0]),
        (3, 7, None),
        (3, 8, [3, 0, 0]),
        (3, 9, [1, -1, 0]),
        (3, 10, [7, 0, 0]),
        (3, 11, [3, -1, 0]),
        (3, 12, [1, -1, 1]),
        (3, 13, [3, -3, 0]),
        (3, 14, [3, -1, 1]),
    ],
)
def test_generate_exp_golomb_with_length(num_values, required_length, expected):
    if expected is not None:
        out = generate_exp_golomb_with_length(num_values, required_length)
        assert out == expected
        # Sanity check our model answer!
        assert sum(signed_exp_golomb_length(n) for n in out) == required_length
    else:
        with pytest.raises(UnsatisfiableBlockSizeError):
            generate_exp_golomb_with_length(num_values, required_length)


class TestGenerateDanglingTransformValues(object):
    @pytest.mark.parametrize(
        "block_bits,num_values,magnitude",
        [
            # A lower-bound for 'reasonable' slice sizes would certainly be well
            # above 4-values per slice. In our test cases we also use 8 (and
            # possibly n*8 for small n) bit slices. Make sure these should work.
            (8, 4, 1),
            (16, 4, 1),
            # Should be able to fit larger numbers into a larger block
            (16, 4, 4),
            # More values than bits (can always pad the start with zeros)
            (8, 10, 1),
            # More bits than values (must use non-zero values at start to fill
            # required space)
            (16, 4, 1),
        ],
    )
    def test_happy_cases(self, block_bits, num_values, magnitude):
        value_sets = {
            dangle_type: generate_dangling_transform_values(
                block_bits, num_values, dangle_type, magnitude,
            )
            for dangle_type in DanglingTransformValueType
        }

        values_and_bits_beyond_ends = {}
        for description, values in value_sets.items():
            # Should all have required number of values
            assert len(values) == num_values

            # Should correctly encode into bounded block
            f = BytesIO()
            w = BitstreamWriter(f)
            w.bounded_block_begin(block_bits)
            for value in values:
                w.write_sint(value)

            # Should completely fill the block
            length_used = to_bit_offset(*w.tell())
            assert length_used == block_bits

            # Check we actually wrote 'beyond' the end of the block
            assert w.bits_remaining < 0

            # Work out which value and which bits actually first crossed the
            # end-of-block boundary (we'll later check that these actually
            # match our expectations later)
            w.flush()
            f.seek(0)
            r = BitstreamReader(f)
            r.bounded_block_begin(block_bits)
            value_beyond_end = None
            bits_beyond_end = None
            while r.bits_remaining >= 0:
                value_beyond_end = r.read_sint()
                bits_beyond_end = -r.bits_remaining
            values_and_bits_beyond_ends[description] = (
                value_beyond_end,
                bits_beyond_end,
            )

        # Check that the dangling value dangles in the expected way
        v, b = values_and_bits_beyond_ends[DanglingTransformValueType.zero_dangling]
        assert v == 0
        assert b == 1

        v, b = values_and_bits_beyond_ends[DanglingTransformValueType.sign_dangling]
        assert v != 0
        assert (-v).bit_length() == magnitude
        assert b == 1

        v, b = values_and_bits_beyond_ends[
            DanglingTransformValueType.stop_and_sign_dangling
        ]
        assert v != 0
        assert (-v).bit_length() == magnitude
        assert b == 2

        v, b = values_and_bits_beyond_ends[
            DanglingTransformValueType.lsb_stop_and_sign_dangling
        ]
        assert v != 0
        # NB: Larger due to exp-golmb code needing to end in 1
        assert (-v).bit_length() == magnitude + 1
        assert b == 3

    @pytest.mark.parametrize(
        "block_bits,num_values,magnitude,exp_cases",
        [
            # No values or bits; can't fit anything in
            (0, 0, 1, set([])),
            # No bits; can only fit the zero-past-end case
            (0, 1, 1, set(["zero_dangling"])),
            (0, 3, 1, set(["zero_dangling"])),
            # Single bit
            (1, 4, 1, set(["zero_dangling", "lsb_stop_and_sign_dangling"])),
            # Two bits
            (
                2,
                10,
                1,
                set(
                    [
                        "lsb_stop_and_sign_dangling",
                        "stop_and_sign_dangling",
                        "zero_dangling",
                    ]
                ),
            ),
            (2, 2, 1, set(["lsb_stop_and_sign_dangling", "stop_and_sign_dangling"])),
            (2, 1, 1, set(["stop_and_sign_dangling"])),
            # Three bits
            (
                3,
                10,
                1,
                set(
                    [
                        "lsb_stop_and_sign_dangling",
                        "stop_and_sign_dangling",
                        "sign_dangling",
                        "zero_dangling",
                    ]
                ),
            ),
            (3, 2, 1, set(["stop_and_sign_dangling", "sign_dangling"])),
            (3, 1, 1, set(["sign_dangling"])),
            # Special oddball case: single value with 4 bits (arguably could be
            # fulfilled for the stop+sign dangling case by having the overflowing
            # value take up 6 bits, but this is not worth the effort to
            # implement...)
            (4, 1, 1, set([])),
            # Larger values may not fit into smaller arrays
            (8, 2, 2, set(["zero_dangling", "stop_and_sign_dangling"])),
        ],
    )
    def test_degenerate_cases(self, block_bits, num_values, magnitude, exp_cases):
        out = {}
        for dangle_type in DanglingTransformValueType:
            try:
                out[dangle_type.name] = generate_dangling_transform_values(
                    block_bits, num_values, dangle_type, magnitude,
                )
            except UnsatisfiableBlockSizeError:
                continue

        assert set(out) == exp_cases

        # Assert cases are all of the correct length (a bug more likely for
        # these degenerate cases)
        for values in out.values():
            assert len(values) == num_values


class TestCutOffValueAtEndOfHQSlice(object):
    def sanity_check(self, slice_size_scaler, slice):
        """
        Checks that the provided slice serializes correctly.
        """
        f = BytesIO()
        with Serialiser(BitstreamWriter(f), slice, vc2_default_values) as ser:
            hq_slice(
                ser,
                State(
                    slice_prefix_bytes=0,
                    slice_size_scaler=slice_size_scaler,
                    dwt_depth=0,
                    dwt_depth_ho=0,
                    luma_width=len(slice["y_transform"]),
                    luma_height=1,
                    color_diff_width=len(slice["c1_transform"]),
                    color_diff_height=1,
                    slices_x=1,
                    slices_y=1,
                ),
                0,
                0,
            )

    @pytest.mark.parametrize("component", ["Y", "C1", "C2"])
    @pytest.mark.parametrize("dangle_type", DanglingTransformValueType)
    def test_component_selection(self, component, dangle_type):
        slice_size_scaler = 2
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[1, 2, 3, 4, 5, 6],
            c1_transform=[7, 8, 9],
            c2_transform=[0, 1, 2],
        )
        cut_off_value_at_end_of_hq_slice(
            State(slice_size_scaler=slice_size_scaler),
            0,
            0,
            hq_slice,
            component,
            dangle_type,
            magnitude=1,
        )

        # Check other components are zeroed out
        for other_component in ["Y", "C1", "C2"]:
            if other_component != component:
                values = hq_slice["{}_transform".format(other_component.lower())]
                for value in values:
                    assert value == 0
                if other_component == "Y":
                    assert len(values) == 6
                else:
                    assert len(values) == 3

        # Check target component is not zeroed out (NB: this test will only
        # work for the dangling zeros case if the total number of values is <
        # 2*8*slice_size_scaler)
        values = hq_slice["{}_transform".format(component.lower())]
        if component == "Y":
            assert len(values) == 6
            assert values != [0, 0, 0, 0, 0, 0]
        else:
            assert len(values) == 3
            assert values != [0, 0, 0]

        # Check that the components do write beyond the end of the slice
        component_bits = (
            slice_size_scaler
            * hq_slice["slice_{}_length".format(component.lower())]
            * 8
        )
        actual_bits = sum(map(signed_exp_golomb_length, values))
        if dangle_type != DanglingTransformValueType.zero_dangling:
            for n in reversed(values):
                if n == 0:
                    actual_bits -= 1
                else:
                    break
        assert actual_bits > component_bits

        self.sanity_check(slice_size_scaler, hq_slice)

    @pytest.mark.parametrize("component", ["Y", "C1", "C2"])
    @pytest.mark.parametrize("dangle_type", DanglingTransformValueType)
    def test_min_length(self, component, dangle_type):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        cut_off_value_at_end_of_hq_slice(
            State(slice_size_scaler=2),
            0,
            0,
            hq_slice,
            component,
            dangle_type,
            magnitude=1,
            min_length=7,
        )

        assert (
            hq_slice["slice_y_length"]
            + hq_slice["slice_c1_length"]
            + hq_slice["slice_c2_length"]
        ) == 7

        self.sanity_check(2, hq_slice)

    def test_magnitude(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        cut_off_value_at_end_of_hq_slice(
            State(slice_size_scaler=2),
            0,
            0,
            hq_slice,
            "Y",
            DanglingTransformValueType.sign_dangling,
            magnitude=3,
        )

        for value in reversed(hq_slice["y_transform"]):
            if value != 0:
                break

        assert value.bit_length() == 3

        self.sanity_check(2, hq_slice)


class TestCutOffValueAtEndOfLDSlice(object):
    def sanity_check(self, slice):
        """
        Checks that the provided slice serializes correctly.
        """
        f = BytesIO()
        with Serialiser(BitstreamWriter(f), slice, vc2_default_values) as ser:
            ld_slice(
                ser,
                State(
                    slice_bytes_numerator=4,
                    slice_bytes_denominator=1,
                    dwt_depth=0,
                    dwt_depth_ho=0,
                    luma_width=len(slice["y_transform"]),
                    luma_height=1,
                    color_diff_width=len(slice["c_transform"]),
                    color_diff_height=1,
                    slices_x=1,
                    slices_y=1,
                ),
                0,
                0,
            )

    @pytest.mark.parametrize("component", ["Y", "C"])
    @pytest.mark.parametrize("dangle_type", DanglingTransformValueType)
    def test_component_selection(self, component, dangle_type):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=16,
            y_transform=[1, 2, 3, 4, 5, 6],
            c_transform=[7, 8, 9, 0, 1, 2],
        )
        cut_off_value_at_end_of_ld_slice(
            State(
                slice_bytes_numerator=4,
                slice_bytes_denominator=1,
                slices_x=1,
                slices_y=1,
            ),
            0,
            0,
            ld_slice,
            component,
            dangle_type,
            magnitude=1,
        )

        # Check other components are zeroed out
        for other_component in ["Y", "C"]:
            if other_component != component:
                values = ld_slice["{}_transform".format(other_component.lower())]
                for value in values:
                    assert value == 0
                assert len(values) == 6

        # Check target component is not zeroed out (NB: this test will only
        # work for the dangling zeros case if the total number of values is <
        # 16)
        values = ld_slice["{}_transform".format(component.lower())]
        assert len(values) == 6
        assert values != [0, 0, 0, 0, 0, 0]

        # Check that the components do write beyond the end of the slice
        if component == "Y":
            component_bits = ld_slice["slice_y_length"]
        else:
            component_bits = (
                # Slice size
                (4 * 8)
                -
                # Qindex
                7
                -
                # 5 bit size
                5
            ) - ld_slice["slice_y_length"]
        actual_bits = sum(map(signed_exp_golomb_length, values))
        if dangle_type != DanglingTransformValueType.zero_dangling:
            for n in reversed(values):
                if n == 0:
                    actual_bits -= 1
                else:
                    break
        assert actual_bits > component_bits

        self.sanity_check(ld_slice)

    def test_min_length(self):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=16,
            y_transform=[0, 0, 0, 0, 0, 0],
            c_transform=[0, 0, 0, 0, 0, 0],
        )
        cut_off_value_at_end_of_ld_slice(
            State(
                slice_bytes_numerator=4,
                slice_bytes_denominator=1,
                slices_x=1,
                slices_y=1,
            ),
            0,
            0,
            ld_slice,
            "Y",
            DanglingTransformValueType.sign_dangling,
            magnitude=3,
        )

        for value in reversed(ld_slice["y_transform"]):
            if value != 0:
                break

        assert value.bit_length() == 3

        self.sanity_check(ld_slice)


@pytest.mark.parametrize(
    "profile,lossless",
    [
        (Profiles.high_quality, False),
        (Profiles.high_quality, True),
        (Profiles.low_delay, False),
    ],
)
def test_slice_padding_data(profile, lossless):
    # Check that the expected padding data for each picture component makes it
    # into the stream

    codec_features = MINIMAL_CODEC_FEATURES.copy()
    codec_features["profile"] = profile
    codec_features["lossless"] = lossless
    if lossless:
        codec_features["picture_bytes"] = None

    # The first 10 bytes of padding data for each component
    # {padding_field_name: set([bitarray, ...]), ...}
    component_padding_first_16_bits = defaultdict(set)

    # The number of times "BBCD" appears (byte aligned) in the bitstream
    end_of_sequence_counts = []

    def find_slice_padding_bytes(d):
        if isinstance(d, dict):
            for key, value in d.items():
                if key.endswith("_block_padding"):
                    component_padding_first_16_bits[key].add(value[:16].to01())
                else:
                    find_slice_padding_bytes(value)
        elif isinstance(d, list):
            for v in d:
                find_slice_padding_bytes(v)

    for test_case in slice_padding_data(codec_features):
        find_slice_padding_bytes(test_case.value)
        f = BytesIO()

        autofill_and_serialise_stream(f, test_case.value)

        end_of_sequence = b"BBCD" + bytearray([ParseCodes.end_of_sequence])
        end_of_sequence_counts.append(f.getvalue().count(end_of_sequence))

    if profile == Profiles.high_quality:
        components = ["Y", "C1", "C2"]
    elif profile == Profiles.low_delay:
        components = ["Y", "C"]

    # Check that the non-aligned padding values appear as expected
    for component in components:
        key = "{}_block_padding".format(component.lower())
        assert "0000000000000000" in component_padding_first_16_bits[key]
        assert "1111111111111111" in component_padding_first_16_bits[key]
        assert "1010101010101010" in component_padding_first_16_bits[key]
        assert "0101010101010101" in component_padding_first_16_bits[key]

    # Check the final test cases insert extra (byte aligned!) end-of-sequence
    # blocks in the padding data (NB: we don't test that they appear in the
    # right places... but hey...)
    for count in end_of_sequence_counts[: -len(components)]:
        assert count == 1
    for count in end_of_sequence_counts[-len(components) :]:
        assert count > 1


class TestDanglingBoundedBlockData(object):
    @pytest.mark.parametrize("profile", Profiles)
    def test_adds_dangling_data(self, profile):
        codec_features = MINIMAL_CODEC_FEATURES.copy()
        codec_features["profile"] = profile

        test_cases = list(dangling_bounded_block_data(codec_features))
        assert len(test_cases) == (4 * 3 if profile == Profiles.high_quality else 4 * 2)

        for test_case in test_cases:
            # Use a MonitoredSerialiser to log where dangling values occur and
            # make sure they occur in the right places.
            #
            # {"?_transform": set([num_dangling_bits, ...]), ...}
            dangling_values = defaultdict(set)
            last_bits_remaining = [0]

            def monitor(ser, target, value):
                if (
                    target.endswith("_transform")
                    and (last_bits_remaining[0] is None or last_bits_remaining[0] >= 0)
                    and ser.io.bits_remaining < 0
                ):
                    dangling_values[target].add(-ser.io.bits_remaining)
                last_bits_remaining[0] = ser.io.bits_remaining

            with MonitoredSerialiser(
                monitor,
                BitstreamWriter(BytesIO()),
                test_case.value,
                vc2_default_values,
            ) as ser:
                parse_stream(ser, State())

            # Check that things are as expected
            if test_case.subcase_name.startswith("zero_dangling"):
                expected_bits = 1
            elif test_case.subcase_name.startswith("sign_dangling"):
                expected_bits = 1
            elif test_case.subcase_name.startswith("stop_and_sign_dangling"):
                expected_bits = 2
            elif test_case.subcase_name.startswith("lsb_stop_and_sign_dangling"):
                expected_bits = 3

            component = test_case.subcase_name.rpartition("_")[2]
            assert dangling_values["{}_transform".format(component.lower())] == set(
                [expected_bits]
            )

    def serialise_and_decode_pictures(self, stream):
        f = BytesIO()
        autofill_and_serialise_stream(f, stream)

        pictures = []
        state = State(_output_picture_callback=lambda pic, vp: pictures.append(pic))
        f.seek(0)
        decoder.init_io(state, f)
        decoder.parse_stream(state)

        return pictures

    @pytest.mark.parametrize(
        "wavelet_index", [WaveletFilters.haar_no_shift, WaveletFilters.haar_with_shift]
    )
    @pytest.mark.parametrize("dwt_depth,dwt_depth_ho", [(0, 0), (1, 0), (0, 1), (1, 1)])
    def test_dangling_value_matters(self, wavelet_index, dwt_depth, dwt_depth_ho):
        # Here we chop off the dangling values and check that this actually
        # makes a difference in the final decoded picture. (If it didn't, you'd
        # never know if the test was successful or not...)
        codec_features = MINIMAL_CODEC_FEATURES.copy()
        codec_features["wavelet_index"] = wavelet_index
        codec_features["wavelet_index_ho"] = wavelet_index
        codec_features["dwt_depth"] = dwt_depth
        codec_features["dwt_depth_ho"] = dwt_depth_ho

        for test_case in dangling_bounded_block_data(codec_features):
            # Skip dangling zero test as replacing zero with zero won't do
            # anything anyway...
            if test_case.subcase_name.startswith("zero_dangling"):
                continue

            pictures_with_dangle = self.serialise_and_decode_pictures(
                deepcopy(test_case.value),
            )

            # Zero the last non-zero transform value in every transform
            # component
            modified_stream = deepcopy(test_case.value)
            to_visit = [modified_stream]
            while to_visit:
                d = to_visit.pop(0)
                if isinstance(d, list):
                    to_visit.extend(d)
                elif isinstance(d, dict):
                    for key, value in d.items():
                        # Zero the last non-zero transform value found (this
                        # should be the dangling value)
                        if key in (
                            "y_transform",
                            "c_transform",
                            "c1_transform",
                            "c2_transform",
                        ):
                            for i, n in reversed(list(enumerate(value))):
                                if n != 0:
                                    value[i] = 0
                                    break
                        else:
                            to_visit.append(value)

            pictures_without_dangle = self.serialise_and_decode_pictures(
                modified_stream
            )

            assert pictures_with_dangle != pictures_without_dangle

    def test_unsatisifiable_skipped(self, caplog):
        # Here we check that degenerate cases (with impractically small small
        # picture/slice sizes) don't crash but rather just skip test cases.
        #
        # In the picture below, luma components have 4 values per slice and
        # color difference components have 2 values per slice.
        codec_features = deepcopy(MINIMAL_CODEC_FEATURES)
        codec_features["video_parameters"]["frame_width"] = 4
        codec_features["video_parameters"]["frame_height"] = 2
        codec_features["video_parameters"][
            "color_diff_format_index"
        ] = ColorDifferenceSamplingFormats.color_4_2_2
        codec_features["picture_coding_mode"] = PictureCodingModes.pictures_are_frames
        codec_features["slices_x"] = 1
        codec_features["slices_y"] = 2
        codec_features["dwt_depth"] = 0
        codec_features["dwt_depth_ho"] = 0

        caplog.set_level(logging.WARNING)
        test_cases = list(dangling_bounded_block_data(codec_features))
        assert "[sign_dangling_C1]" in caplog.text
        assert "[sign_dangling_C2]" in caplog.text
        assert "[lsb_stop_and_sign_dangling_C1]" in caplog.text
        assert "[lsb_stop_and_sign_dangling_C2]" in caplog.text

        assert set(t.subcase_name for t in test_cases) == set(
            [
                # Each slice has 4 luma values which is enough to achieve any
                # required dangling values
                "zero_dangling_Y",
                "sign_dangling_Y",
                "stop_and_sign_dangling_Y",
                "lsb_stop_and_sign_dangling_Y",
                # Color diff slices have only 2 components each which means
                # anything which requires dangling by an odd number of bits is not
                # possible (with the algorithms used, at least)
                "zero_dangling_C1",
                "zero_dangling_C2",
                "stop_and_sign_dangling_C1",
                "stop_and_sign_dangling_C2",
            ]
        )
