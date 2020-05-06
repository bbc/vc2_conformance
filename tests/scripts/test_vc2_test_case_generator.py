import pytest

import os

import re

from functools import partial

from vc2_conformance._py2x_compat import makedirs

from vc2_conformance.codec_features import read_codec_features_csv

from vc2_conformance.scripts.vc2_test_case_generator.cli import (
    parse_args,
    load_codec_features,
    check_output_directories_empty,
    check_codec_features_valid,
    main,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES
from smaller_real_pictures import alternative_real_pictures

from vc2_conformance.test_cases import (
    ENCODER_TEST_CASE_GENERATOR_REGISTRY,
    DECODER_TEST_CASE_GENERATOR_REGISTRY,
)


CODEC_FEATURES_CSV = os.path.join(
    os.path.dirname(__file__), "..", "sample_codec_features.csv",
)

INVALID_CODEC_FEATURES_CSV = os.path.join(
    os.path.dirname(__file__), "..", "sample_codec_features_invalid.csv",
)


class TestParseArgs(object):
    @pytest.fixture
    def dummy_csv_filename(self, tmpdir):
        dummy = tmpdir.join("dummy.csv")
        dummy.write("")
        return str(dummy)

    def test_codecs_default(self, dummy_csv_filename):
        # Should return a regex object
        args = parse_args([dummy_csv_filename])
        assert args.codecs.match("foo")

    def test_codecs_valid_regex(self, dummy_csv_filename):
        # Should return a regex object
        args = parse_args([dummy_csv_filename, "-c", "f.*o"])
        assert args.codecs.match("foo")
        assert not args.codecs.match("bar")

        # Should be a whole-string match
        assert not args.codecs.match("xfoo")
        assert not args.codecs.match("foox")

    def test_codecs_invalid_regex(self, dummy_csv_filename):
        with pytest.raises(SystemExit):
            parse_args([dummy_csv_filename, "-c", "["])


class TestLoadCodecFeatures(object):
    @pytest.fixture
    def empty_csv_filename(self, tmpdir):
        dummy = tmpdir.join("dummy.csv")
        dummy.write("")
        return str(dummy)

    def test_empty(self, capsys, empty_csv_filename):
        with pytest.raises(SystemExit):
            load_codec_features(empty_csv_filename, re.compile(".*"))

        out, err = capsys.readouterr()
        assert "No matching codec" in err

    # Should fail regardless of whether we deselect the invalid configs or not
    @pytest.mark.parametrize("regex", [".*", "valid-config"])
    def test_invalid(self, capsys, regex):
        with pytest.raises(SystemExit):
            load_codec_features(open(INVALID_CODEC_FEATURES_CSV), re.compile(regex))

        out, err = capsys.readouterr()
        assert "invalid-config" in err
        assert "profile" in err
        assert "does_not_exist" in err

    @pytest.mark.parametrize(
        "regex,exp_names",
        [
            (".*", set(["hd", "minimal", "minimal-invalid"])),
            (".*h.*", set(["hd"])),
            (".*i.*", set(["minimal", "minimal-invalid"])),
        ],
    )
    def test_filtering(self, regex, exp_names):
        codec_feature_sets = load_codec_features(
            open(CODEC_FEATURES_CSV), re.compile(regex),
        )

        assert set(codec_feature_sets) == exp_names


@pytest.mark.parametrize(
    "exp_fail,files,check_encoder,check_decoder",
    [
        # No files
        (False, [], True, True),
        (False, [], False, True),
        (False, [], True, False),
        # Some empty encoder and decoder directories
        (False, ["foo/encoder", "bar/decoder"], True, True),
        (False, ["foo/encoder", "bar/decoder"], True, False),
        (False, ["foo/encoder", "bar/decoder"], False, True),
        # Some non-empty encoder directories
        (True, ["foo/encoder/hi.txt"], True, True),
        (True, ["foo/encoder/hi.txt"], True, False),
        (False, ["foo/encoder/hi.txt"], False, True),
        (True, ["foo/encoder/empty-subdir/"], True, True),
        (True, ["foo/encoder/empty-subdir/"], True, False),
        (False, ["foo/encoder/empty-subdir/"], False, True),
        # Some non-empty decoder directories
        (True, ["foo/decoder/hi.txt"], True, True),
        (False, ["foo/decoder/hi.txt"], True, False),
        (True, ["foo/decoder/hi.txt"], False, True),
        (True, ["foo/decoder/empty-subdir/"], True, True),
        (False, ["foo/decoder/empty-subdir/"], True, False),
        (True, ["foo/decoder/empty-subdir/"], False, True),
    ],
)
def test_check_output_directories_empty(
    capsys, tmpdir, exp_fail, files, check_encoder, check_decoder,
):
    # Create the specified files in the target directory
    for filename in files:
        filename = os.path.join(str(tmpdir), filename)
        makedirs(os.path.dirname(filename), exist_ok=True)
        if not filename.endswith("/"):
            with open(filename, "w"):
                pass

    fn = partial(
        check_output_directories_empty,
        str(tmpdir),
        {"foo": {}, "bar": {}},
        check_encoder,
        check_decoder,
    )

    if exp_fail:
        with pytest.raises(SystemExit):
            fn()
        out, err = capsys.readouterr()
        assert "not empty" in err
    else:
        fn()


# NB: This test is currently xfailing as impossible Level constraints are
# causing test case generation itself to be impossible (i.e. not just resulting
# in a non-conformant stream). Some rethinking of how level constraints are
# dealt with for test case generation needs doing...
@pytest.mark.parametrize(
    "name,exp_valid", [("minimal", True), ("minimal-invalid", False)],
)
def test_check_codec_features_valid(capsys, name, exp_valid):
    codec_feature_sets = read_codec_features_csv(open(CODEC_FEATURES_CSV))
    codec_feature_sets = {
        name: codec_feature_sets[name],
    }
    if exp_valid:
        check_codec_features_valid(codec_feature_sets)
    else:
        with pytest.raises(SystemExit):
            check_codec_features_valid(codec_feature_sets)
        out, err = capsys.readouterr()
        assert "minimal-invalid" in err
        assert "is invalid" in err


@pytest.fixture(scope="module")
def expected_files():
    """
    The (minimum) expected filenames which demonstrates all test cases were
    tried.
    """
    codec_feature_sets = {
        "minimal": MINIMAL_CODEC_FEATURES,
    }

    encoder_test_files = set()
    decoder_test_files = set()
    with alternative_real_pictures():
        for name, codec_features in codec_feature_sets.items():
            for test_case in ENCODER_TEST_CASE_GENERATOR_REGISTRY.generate_test_cases(
                codec_features
            ):
                encoder_test_files.add(
                    os.path.join(name, "encoder", test_case.name, "picture_0.raw",)
                )
                if test_case.metadata is not None:
                    encoder_test_files.add(
                        os.path.join(
                            name, "encoder", "{}_metadata.json".format(test_case.name),
                        )
                    )

            for test_case in DECODER_TEST_CASE_GENERATOR_REGISTRY.generate_test_cases(
                codec_features
            ):
                decoder_test_files.add(
                    os.path.join(name, "decoder", "{}.vc2".format(test_case.name),)
                )
                decoder_test_files.add(
                    os.path.join(
                        name,
                        "decoder",
                        "{}_expected".format(test_case.name),
                        "picture_0.raw",
                    )
                )
                if test_case.metadata is not None:
                    decoder_test_files.add(
                        os.path.join(
                            name, "decoder", "{}_metadata.json".format(test_case.name),
                        )
                    )

        return (encoder_test_files, decoder_test_files)


@pytest.mark.parametrize("extra_args,exp_fail", [([], True), (["--force"], False)])
def test_force(
    tmpdir, extra_args, exp_fail,
):
    with alternative_real_pictures():
        fn = partial(
            main,
            [CODEC_FEATURES_CSV, "--output", str(tmpdir), "--codecs", "minimal"]
            + extra_args,
        )

        # First time should always work
        fn()

        if exp_fail:
            with pytest.raises(SystemExit):
                fn()
        else:
            fn()


@pytest.mark.parametrize(
    "extra_args,exp_encoder,exp_decoder",
    [
        ([], True, True),
        # Should only produce required files
        (["--encoder-only"], True, False),
        (["--decoder-only"], False, True),
    ],
)
def test_completeness(
    tmpdir, extra_args, exp_encoder, exp_decoder, expected_files,
):
    with alternative_real_pictures():
        assert (
            main(
                [CODEC_FEATURES_CSV, "--output", str(tmpdir), "--codecs", "minimal"]
                + extra_args
            )
            == 0
        )

    generated_files = set(
        # Get relative paths within output dir
        os.path.abspath(os.path.join(root, filename))[
            len(os.path.abspath(str(tmpdir))) + 1 :
        ]
        for root, dirs, files in os.walk(str(tmpdir))
        for filename in files
    )

    if exp_encoder:
        assert expected_files[0].issubset(generated_files)
    else:
        assert expected_files[0].isdisjoint(generated_files)

    if exp_decoder:
        assert expected_files[1].issubset(generated_files)
    else:
        assert expected_files[1].isdisjoint(generated_files)


def test_parallel(tmpdir, expected_files, capsys):
    assert (
        main(
            [
                CODEC_FEATURES_CSV,
                "--parallel",
                "--encoder-only",
                "--output",
                str(tmpdir),
                "--codecs",
                "minimal",
            ]
        )
        == 0
    )
    out, err = capsys.readouterr()
    assert err == ""

    # Should not have generated any files yet
    assert [
        os.path.join(root, filename)
        for root, dirs, files in os.walk(str(tmpdir))
        for filename in files
    ] == []

    # Check that the commands could plausibly work by just running the first
    # one (which shouldn't be one which loads a very large real picture file
    # and so not take too long to run...)
    first_command = next(iter(filter(None, out.split("\n"))))

    os.system(first_command)

    generated_files = set(
        # Get relative paths within output dir
        os.path.abspath(os.path.join(root, filename))[
            len(os.path.abspath(str(tmpdir))) + 1 :
        ]
        for root, dirs, files in os.walk(str(tmpdir))
        for filename in files
    )

    assert expected_files[0].intersection(generated_files) != set()
    assert expected_files[1].intersection(generated_files) == set()
