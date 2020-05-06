import os

import subprocess

import shlex

from vc2_conformance.scripts.vc2_test_case_generator.worker import (
    encode,
    decode,
    create_command,
)


def test_encode_decode(tmpdir):
    filename = str(tmpdir.join("test_file"))

    fn = decode(encode(open, filename, "wb"))

    assert not os.path.isfile(filename)
    fn()
    assert os.path.isfile(filename)


def test_roundtrip(tmpdir, capfd):
    filename = str(tmpdir.join("test_file"))

    command = create_command(open, filename, "wb")

    assert not os.path.isfile(filename)

    # Run command
    assert subprocess.Popen(shlex.split(command)).wait() == 0

    # Should have run the pickled function
    assert os.path.isfile(filename)

    # Should not have produced any extra output
    assert capfd.readouterr() == ("", "")
