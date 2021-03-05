import pytest

from vc2_conformance.py2x_compat import (
    zip_longest,
    get_terminal_size,
    wraps,
    unwrap,
    zip,
    makedirs,
    FileType,
)

import os

from itertools import count


def test_zip_longest():
    # Sanity check as only renamed in Py 2.x
    assert list(zip_longest([1, 2, 3], [10, 20, 30, 40])) == [
        (1, 10),
        (2, 20),
        (3, 30),
        (None, 40),
    ]


def test_get_terminal_size():
    # Sanity check as fallback is crude
    rows, cols = get_terminal_size()
    assert isinstance(rows, int)
    assert isinstance(cols, int)


def test_wraps():
    def f():
        pass

    @wraps(f)
    def f_wrapper():
        pass

    assert f_wrapper.__wrapped__ is f


def test_unwrap():
    def f():
        pass

    @wraps(f)
    def f_wrapper():
        pass

    @wraps(f_wrapper)
    def f_wrapper_wrapper():
        pass

    assert unwrap(f_wrapper_wrapper) is f

    assert (
        unwrap(
            f_wrapper_wrapper,
            stop=lambda f: f is f_wrapper,
        )
        is f_wrapper
    )


def test_zip():
    # Check zip doesn't block on infinite iterators
    out = list(zip(range(3), zip(count(1), count(2))))
    assert out == [
        (0, (1, 2)),
        (1, (2, 3)),
        (2, (3, 4)),
    ]


def test_mkdirs(tmpdir):
    root = str(tmpdir)

    path = os.path.join(root, "foo", "bar")
    assert not os.path.isdir(path)
    makedirs(path, exist_ok=False)
    assert os.path.isdir(path)

    with pytest.raises(OSError):
        makedirs(path, exist_ok=False)

    path = os.path.join(root, "quo", "qux")
    assert not os.path.isdir(path)
    makedirs(path, exist_ok=True)
    assert os.path.isdir(path)
    makedirs(path, exist_ok=True)


class TestFileType(object):
    def test_no_encoding_write(self, tmpdir):
        text_filename = str(tmpdir.join("text_file"))
        binary_filename = str(tmpdir.join("binary_file"))

        tft = FileType("w")
        with tft(text_filename) as f:
            f.write("Hello!")
        assert open(text_filename, "r").read() == "Hello!"

        bft = FileType("wb")
        with bft(binary_filename) as f:
            f.write(b"\x00\xFF")
        assert open(binary_filename, "rb").read() == b"\x00\xFF"

    def test_no_encoding_read(self, tmpdir):
        text_filename = str(tmpdir.join("text_file"))
        binary_filename = str(tmpdir.join("binary_file"))

        with open(text_filename, "w") as f:
            f.write("Hello!")
        with open(binary_filename, "wb") as f:
            f.write(b"\x00\xFF")

        tft = FileType("r")
        assert tft(text_filename).read() == "Hello!"

        bft = FileType("rb")
        assert bft(binary_filename).read() == b"\x00\xFF"

    def test_with_encoding_read(self, tmpdir):
        text_filename = str(tmpdir.join("text_file"))

        with open(text_filename, "wb") as f:
            f.write(b"\xef\xbb\xbfHello!")  # With UTF-8 BOM

        ft = FileType("r")
        assert ft(text_filename).read() != "Hello!"

        sft = FileType("r", encoding="utf-8-sig")
        assert sft(text_filename).read() == "Hello!"
