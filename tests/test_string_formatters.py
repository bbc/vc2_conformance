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
)

@pytest.mark.parametrize("formatter,number,expectation", [
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
])
def test_number(formatter, number, expectation):
    assert formatter(number) == expectation


@pytest.mark.parametrize("formatter,number,expectation", [
    (Hex(), 0x1234, "0x1234"),
    (Hex(8), 0x1234, "0x00001234"),
    (Hex(8, pad_digit=" "), 0x1234, "0x    1234"),
    (Hex(prefix=""), 0x1234, "1234"),
])
def test_hex(formatter, number, expectation):
    assert formatter(number) == expectation

@pytest.mark.parametrize("formatter,number,expectation", [
    (Dec(), 1234, "1234"),
    (Dec(8), 1234, "00001234"),
    (Dec(8, pad_digit=" "), 1234, "    1234"),
    (Dec(prefix="0d"), 1234, "0d1234"),
])
def test_hex(formatter, number, expectation):
    assert formatter(number) == expectation

@pytest.mark.parametrize("formatter,number,expectation", [
    (Oct(), 0o1234, "0o1234"),
    (Oct(8), 0o1234, "0o00001234"),
    (Oct(8, pad_digit=" "), 0o1234, "0o    1234"),
    (Oct(prefix=""), 0o1234, "1234"),
])
def test_bin(formatter, number, expectation):
    assert formatter(number) == expectation

@pytest.mark.parametrize("formatter,number,expectation", [
    (Bin(), 0b1001, "0b1001"),
    (Bin(8), 0b1001, "0b00001001"),
    (Bin(8, pad_digit=" "), 0b1001, "0b    1001"),
    (Bin(prefix=""), 0b1001, "1001"),
])
def test_bin(formatter, number, expectation):
    assert formatter(number) == expectation

@pytest.mark.parametrize("value,expectation", [
    (True, "True"),
    (1, "True"),
    (False, "False"),
    (0, "False"),
    (123, "True (123)"),
    (None, "False (None)"),
])
def test_bits(value, expectation):
    assert Bool()(value) == expectation

@pytest.mark.parametrize("formatter,number,expectation", [
    # Simple cases
    (Bits(), bitarray(), "0b"),
    (Bits(), bitarray("0"), "0b0"),
    (Bits(), bitarray("1001"), "0b1001"),
    # Test prefix
    (Bits(prefix=""), bitarray("101"), "101"),
    (Bits(prefix="!"), bitarray("101"), "!101"),
    # Test ellipsisation
    (Bits(), bitarray("0"*16), "0b0000...0000 (16 bits)"),
    (Bits(), bitarray("101" + "0"*16 + "101"), "0b1010000...0000101 (22 bits)"),
    (Bits(), bitarray("0"*6), "0b000000"),
    (Bits(min_length=4, context=1), bitarray("0"*6), "0b0...0"),
    # Test show length
    (Bits(show_length=True), bitarray(), "0b (0 bits)"),
    (Bits(show_length=True), bitarray("0"), "0b0 (1 bit)"),
    (Bits(show_length=True), bitarray("00"), "0b00 (2 bits)"),
    (Bits(show_length=3), bitarray("00"), "0b00"),
    (Bits(show_length=3), bitarray("000"), "0b000 (3 bits)"),
    (Bits(show_length=False), bitarray("0"*100), "0b0000...0000"),
])
def test_bits(formatter, number, expectation):
    assert formatter(number) == expectation

@pytest.mark.parametrize("formatter,number,expectation", [
    # Simple cases
    (Bytes(), b"", "0x"),
    (Bytes(), b"\x00", "0x00"),
    (Bytes(), b"\xAB\xCD\xEF", "0xAB_CD_EF"),
    # Test prefix
    (Bytes(prefix=""), b"\x00", "00"),
    (Bytes(prefix="!"), b"\x00", "!00"),
    # Ellipsise
    (Bytes(), b"\x00"*8, "0x00_00...00_00 (8 bytes)"),
    (Bytes(), b"\xAA" + b"\x00"*8 + b"\xBB", "0xAA_00_00...00_00_BB (10 bytes)"),
    (Bytes(), b"\x00"*3, "0x00_00_00"),
    (Bytes(context=1, min_length=1), b"\x00"*3, "0x00...00"),
    # Show length
    (Bytes(show_length=True), b"", "0x (0 bytes)"),
    (Bytes(show_length=True), b"\x00", "0x00 (1 byte)"),
    (Bytes(show_length=True), b"\x00\x00", "0x00_00 (2 bytes)"),
    (Bytes(show_length=3), b"\x00\x00", "0x00_00"),
    (Bytes(show_length=3), b"\x00\x00\x00", "0x00_00_00 (3 bytes)"),
    (Bytes(show_length=False), b"\x00"*100, "0x00_00...00_00"),
])
def test_bytes(formatter, number, expectation):
    assert formatter(number) == expectation
