import pytest

from vc2_conformance.bitstream.formatters import (
    Number,
    Hex,
    Dec,
    Oct,
    Bin,
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
