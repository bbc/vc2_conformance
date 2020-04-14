import pytest

from bitarray import bitarray

from vc2_conformance._string_formatters import (
    Number,
    Hex,
    Dec,
    Oct,
    Bin,
    Bool,
    Bits,
    Bytes,
    Object,
    List,
    MultilineList,
)


@pytest.mark.parametrize(
    "formatter,number,expectation",
    [
        # Formatters
        (Number("d"), 123, "123"),
        (Number("d"), -123, "-123"),
        (Number("b"), 0b1001, "1001"),
        (Number("b"), -0b1001, "-1001"),
        (Number("x"), 0x1234, "1234"),
        (Number("x"), -0x1234, "-1234"),
        # Prefix
        (Number("x", prefix="0x"), 0x1234, "0x1234"),
        (Number("x", prefix="0x"), -0x1234, "-0x1234"),
        # Padding digits
        (Number("x", num_digits=8), 0x1234, "00001234"),
        (Number("x", num_digits=8), -0x1234, "-00001234"),
        (Number("x", num_digits=8, pad_digit=" "), 0x1234, "    1234"),
    ],
)
def test_number(formatter, number, expectation):
    assert formatter(number) == expectation


@pytest.mark.parametrize(
    "formatter,number,expectation",
    [
        (Hex(), 0x1234, "0x1234"),
        (Hex(8), 0x1234, "0x00001234"),
        (Hex(8, pad_digit=" "), 0x1234, "0x    1234"),
        (Hex(prefix=""), 0x1234, "1234"),
    ],
)
def test_hex(formatter, number, expectation):
    assert formatter(number) == expectation


@pytest.mark.parametrize(
    "formatter,number,expectation",
    [
        (Dec(), 1234, "1234"),
        (Dec(8), 1234, "00001234"),
        (Dec(8, pad_digit=" "), 1234, "    1234"),
        (Dec(prefix="0d"), 1234, "0d1234"),
    ],
)
def test_dec(formatter, number, expectation):
    assert formatter(number) == expectation


@pytest.mark.parametrize(
    "formatter,number,expectation",
    [
        (Oct(), 0o1234, "0o1234"),
        (Oct(8), 0o1234, "0o00001234"),
        (Oct(8, pad_digit=" "), 0o1234, "0o    1234"),
        (Oct(prefix=""), 0o1234, "1234"),
    ],
)
def test_oct(formatter, number, expectation):
    assert formatter(number) == expectation


@pytest.mark.parametrize(
    "formatter,number,expectation",
    [
        (Bin(), 0b1001, "0b1001"),
        (Bin(8), 0b1001, "0b00001001"),
        (Bin(8, pad_digit=" "), 0b1001, "0b    1001"),
        (Bin(prefix=""), 0b1001, "1001"),
    ],
)
def test_bin(formatter, number, expectation):
    assert formatter(number) == expectation


@pytest.mark.parametrize(
    "value,expectation",
    [
        (True, "True"),
        (1, "True"),
        (False, "False"),
        (0, "False"),
        (123, "True (123)"),
        (None, "False (None)"),
    ],
)
def test_bool(value, expectation):
    assert Bool()(value) == expectation


@pytest.mark.parametrize(
    "formatter,number,expectation",
    [
        # Simple cases
        (Bits(), bitarray(), "0b"),
        (Bits(), bitarray("0"), "0b0"),
        (Bits(), bitarray("1001"), "0b1001"),
        # Test prefix
        (Bits(prefix=""), bitarray("101"), "101"),
        (Bits(prefix="!"), bitarray("101"), "!101"),
        # Test ellipsisation
        (Bits(), bitarray("0" * 16), "0b0000...0000 (16 bits)"),
        (Bits(), bitarray("101" + "0" * 16 + "101"), "0b1010000...0000101 (22 bits)"),
        (Bits(), bitarray("0" * 6), "0b000000"),
        (Bits(min_length=4, context=1), bitarray("0" * 6), "0b0...0"),
        # Test show length
        (Bits(show_length=True), bitarray(), "0b (0 bits)"),
        (Bits(show_length=True), bitarray("0"), "0b0 (1 bit)"),
        (Bits(show_length=True), bitarray("00"), "0b00 (2 bits)"),
        (Bits(show_length=3), bitarray("00"), "0b00"),
        (Bits(show_length=3), bitarray("000"), "0b000 (3 bits)"),
        (Bits(show_length=False), bitarray("0" * 100), "0b0000...0000"),
    ],
)
def test_bits(formatter, number, expectation):
    assert formatter(number) == expectation


@pytest.mark.parametrize(
    "formatter,number,expectation",
    [
        # Simple cases
        (Bytes(), b"", "0x"),
        (Bytes(), b"\x00", "0x00"),
        (Bytes(), b"\xAB\xCD\xEF", "0xAB_CD_EF"),
        # Test prefix
        (Bytes(prefix=""), b"\x00", "00"),
        (Bytes(prefix="!"), b"\x00", "!00"),
        # Ellipsise
        (Bytes(), b"\x00" * 8, "0x00_00...00_00 (8 bytes)"),
        (Bytes(), b"\xAA" + b"\x00" * 8 + b"\xBB", "0xAA_00_00...00_00_BB (10 bytes)"),
        (Bytes(), b"\x00" * 3, "0x00_00_00"),
        (Bytes(context=1, min_length=1), b"\x00" * 3, "0x00...00"),
        # Show length
        (Bytes(show_length=True), b"", "0x (0 bytes)"),
        (Bytes(show_length=True), b"\x00", "0x00 (1 byte)"),
        (Bytes(show_length=True), b"\x00\x00", "0x00_00 (2 bytes)"),
        (Bytes(show_length=3), b"\x00\x00", "0x00_00"),
        (Bytes(show_length=3), b"\x00\x00\x00", "0x00_00_00 (3 bytes)"),
        (Bytes(show_length=False), b"\x00" * 100, "0x00_00...00_00"),
    ],
)
def test_bytes(formatter, number, expectation):
    assert formatter(number) == expectation


@pytest.mark.parametrize(
    "formatter,value,expectation",
    [
        # Default prefix/suffix should work
        (Object(), 123, "<int>"),
        (Object(), {}, "<dict>"),
        (Object(), Object(), "<Object>"),
        # Custom prefix/suffix should work
        (Object(prefix="(", suffix=")"), 123, "(int)"),
    ],
)
def test_object(formatter, value, expectation):
    assert formatter(value) == expectation


@pytest.mark.parametrize(
    "formatter,value,expectation",
    [
        # Empty list
        (List(), [], "[]"),
        # Singleton
        (List(), [1], "[1]"),
        # No (adjacent) repeats
        (List(), [1, 2, 3, 2, 1], "[1, 2, 3, 2, 1]"),
        # All repeats collapsed (by default)
        (List(), [0, 0, 0], "[0]*3"),
        (List(), [0, 0, 0, 0], "[0]*4"),
        # Multiple repeated values can be adjacent
        (List(), [0, 0, 0, 1, 1, 1, 1], "[0]*3 + [1]*4"),
        # Mixed repeat and no repeat
        (List(), [0, 0, 0, 2, 1], "[0]*3 + [2, 1]"),
        (List(), [1, 2, 0, 0, 0], "[1, 2] + [0]*3"),
        (List(), [1, 2, 0, 0, 0, 2, 1], "[1, 2] + [0]*3 + [2, 1]"),
        # Custom formatters
        (List(formatter=Hex()), [1, 2, 3, 0, 0, 0], "[0x1, 0x2, 0x3] + [0x0]*3"),
        # Equality test is based on string value
        (List(formatter=Object()), [1, 2, 3, 0, 0, 0], "[<int>]*6"),
        # Custom repeat limit
        (
            List(min_run_length=2),
            [1, 2, 2, 3, 3, 3, 4, 4, 4, 4],
            "[1] + [2]*2 + [3]*3 + [4]*4",
        ),
    ],
)
def test_list(formatter, value, expectation):
    assert formatter(value) == expectation


@pytest.mark.parametrize(
    "formatter,value,expectation",
    [
        # Empty list
        (MultilineList(), [], ""),
        # Single-line values
        (MultilineList(), ["one", "two", "three"], "0: one\n1: two\n2: three"),
        # Multi-line values (no special treatment)
        (
            MultilineList(),
            ["one", "two\nlines", "three"],
            "0: one\n1: two\nlines\n2: three",
        ),
        # Custom formatter
        (MultilineList(formatter=Hex()), [1, 2, 3], "0: 0x1\n1: 0x2\n2: 0x3"),
        # Custom heading
        (MultilineList(heading="Foo"), ["a", "b"], "Foo\n  0: a\n  1: b"),
    ],
)
def test_multiline_list(formatter, value, expectation):
    assert formatter(value) == expectation
