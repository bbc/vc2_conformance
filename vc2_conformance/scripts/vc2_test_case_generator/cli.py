"""
``vc2-test-case-generator``
===========================

This application generates test cases for VC-2 encoders and decoders.
"""

import os

import sys

import re

import logging

import json

from functools import partial

from collections import OrderedDict

from io import BytesIO

from argparse import ArgumentParser, FileType

from vc2_conformance import __version__

from vc2_conformance.codec_features import (
    read_codec_features_csv,
    InvalidCodecFeaturesError,
)

from vc2_conformance.encoder import UnsatisfiableCodecFeaturesError

from vc2_conformance._py2x_compat import (
    get_terminal_size,
    makedirs,
)

from vc2_conformance._string_utils import wrap_paragraphs

from vc2_conformance import file_format

from vc2_conformance.test_cases.decoder import static_grey

from vc2_conformance.bitstream import autofill_and_serialise_sequence

from vc2_conformance.state import State

from vc2_conformance.decoder import (
    init_io,
    parse_sequence,
    ConformanceError,
)

from vc2_conformance.test_cases import (
    ENCODER_TEST_CASE_GENERATOR_REGISTRY,
    DECODER_TEST_CASE_GENERATOR_REGISTRY,
)

from vc2_conformance.scripts.vc2_test_case_generator.worker import create_command


def regex(regex):
    try:
        return re.compile("^{}$".format(regex))
    except Exception as e:
        raise ValueError(str(e))


def parse_args(*args, **kwargs):
    """
    Parse a set of command line arguments. Returns a :py:mod:`argparse`
    ``args`` object.
    """
    parser = ArgumentParser(
        description="""
            Generate test inputs for VC-2 encoder and decoder implementations.
        """
    )

    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(__version__),
    )

    parser.add_argument(
        "codec_configurations",
        type=FileType("r"),
        help="""
            CSV file containing the set of codec configurations to generate
            test cases for.
        """,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="""
            Show additional status information during execution.
        """,
    )

    parser.add_argument(
        "--parallel",
        "-p",
        action="store_true",
        default=False,
        help="""
            If given, don't generate test cases but instead produce a series of
            commands on stdout which may be executed in parallel to generate
            the test cases.
        """,
    )

    parser.add_argument(
        "--output",
        "-o",
        default="./test_cases/",
        help="""
            Directory name to write test cases to. Will be created if it does
            not exist. Defaults to '%(default)s'.
        """,
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        default=False,
        help="""
            Force the test case generator to run even if the output directory
            is not empty.
        """,
    )

    encoder_decoder_only_group = parser.add_mutually_exclusive_group()

    encoder_decoder_only_group.add_argument(
        "--encoder-only",
        "-e",
        action="store_true",
        default=False,
        help="""
            If set, only generate test cases for VC-2 encoders.
        """,
    )

    encoder_decoder_only_group.add_argument(
        "--decoder-only",
        "-d",
        action="store_true",
        default=False,
        help="""
            If set, only generate test cases for VC-2 decoders.
        """,
    )

    parser.add_argument(
        "--codecs",
        "-c",
        type=regex,
        default=regex(r".*"),
        metavar="REGEX",
        help="""
            If given, a regular expression which selects which codec
            configurations to generate test cases for. If not given, test cases
            will be generated for all codec configurations.
        """,
    )

    return parser.parse_args(*args, **kwargs)


def load_codec_features(csv, name_re):
    """
    Load a set of codec features from the specified CSV, filtering just those
    matching the provided compiled regular expression.

    Returns an :py:class:`collections.OrderedDict` of
    :py:class:`vc2_conformance.codec_features.CodecFeatures` objects. Calls
    :py:func:`sys.exit` and prints an error to stderr upon any problems (e.g.
    invalid or empty file).
    """
    try:
        codec_feature_sets = read_codec_features_csv(csv)
    except InvalidCodecFeaturesError as e:
        sys.stderr.write("Error: Invalid codec features: {}\n".format(e))
        sys.exit(1)

    # Filter to just the specified codec features columns
    codec_feature_sets = OrderedDict(
        (name, codec_features)
        for name, codec_features in codec_feature_sets.items()
        if name_re.match(name)
    )
    if len(codec_feature_sets) == 0:
        sys.stderr.write("Error: No matching codec feature sets found.\n")
        sys.exit(2)
    logging.info(
        "Loaded %s matching codec feature sets: %s",
        len(codec_feature_sets),
        ", ".join(codec_feature_sets),
    )

    return codec_feature_sets


def check_output_directories_empty(
    output_root_dir, codec_feature_sets, check_encoder_tests, check_decoder_tests,
):
    """
    Check all output directories are empty (or don't yet exist).  Prints an
    error to stderr and calls :py:func:`sys.exit` if a non empty directory is
    encountered.
    """
    for codec_features_name in codec_feature_sets:
        base_path = os.path.join(output_root_dir, codec_features_name,)

        paths = []
        if check_encoder_tests:
            paths.append(os.path.join(base_path, "encoder"))
        if check_decoder_tests:
            paths.append(os.path.join(base_path, "decoder"))

        for path in paths:
            try:
                if len(os.listdir(path)) > 0:
                    sys.stderr.write(
                        (
                            "Error: Output directory {!r} is not empty. "
                            "(Use --force/-f to disable this check)\n"
                        ).format(path)
                    )
                    sys.exit(3)
            except OSError:
                # Directory does not exist, good!
                pass


def check_codec_features_valid(codec_feature_sets):
    """
    Verify that the codec features requested don't themselves violate the spec
    (e.g. violate a level constraint). This is done by generating then
    validating a bitstream containing a single mid-grey frame.

    Prints an error to stderr and calls :py:func:`sys.exit` if a problem is
    encountered.
    """
    logging.info("Checking codec feature sets are valid...")
    for name, codec_features in codec_feature_sets.items():
        logging.info("Checking %r...", name)
        f = BytesIO()

        # Generate a minimal bitstream
        try:
            autofill_and_serialise_sequence(f, static_grey(codec_features,))
        except UnsatisfiableCodecFeaturesError as e:
            sys.stderr.write(
                "Error: Codec configuration {!r} is invalid:\n".format(name)
            )
            terminal_width = get_terminal_size()[0]
            sys.stderr.write(wrap_paragraphs(e.explain(), terminal_width))
            sys.stderr.write("\n")
            sys.exit(4)
        f.seek(0)

        # Validate it meets the spec
        state = State()
        init_io(state, f)
        try:
            parse_sequence(state)
        except ConformanceError as e:
            sys.stderr.write(
                "Error: Codec configuration {!r} is invalid:\n".format(name)
            )
            terminal_width = get_terminal_size()[0]
            sys.stderr.write(wrap_paragraphs(e.explain(), terminal_width))
            sys.stderr.write("\n")
            sys.exit(4)


def output_encoder_test_case(output_dir, codec_features, test_case):
    """
    Write an encoder test case to disk.

    Parameters
    ==========
    output_dir : str
        Output directory to write test cases to.
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    test_case : :py:class:`~vc2_conformance.test_cases.TestCase`
    """
    # Write raw pictures
    for i, picture in enumerate(test_case.value.pictures):
        picture_directory = os.path.join(output_dir, test_case.name,)
        makedirs(picture_directory, exist_ok=True)
        file_format.write(
            picture,
            test_case.value.video_parameters,
            test_case.value.picture_coding_mode,
            os.path.join(picture_directory, "picture_{}.raw".format(i),),
        )
    # Write metadata
    if test_case.metadata is not None:
        with open(
            os.path.join(output_dir, "{}_metadata.json".format(test_case.name),), "w"
        ) as f:
            json.dump(test_case.metadata, f)

    logging.info(
        "Generated encoder test case %s for %s", test_case.name, codec_features["name"],
    )


def output_encoder_test_cases(output_dir, codec_features, generator_function):
    for test_case in generator_function():
        output_encoder_test_case(output_dir, codec_features, test_case)


def output_decoder_test_case(output_dir, codec_features, test_case):
    """
    Write a decoder test case to disk.

    Parameters
    ==========
    output_dir : str
        Output directory to write test cases to.
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    test_case : :py:class:`~vc2_conformance.test_cases.TestCase`
    """
    # Serialise bitstream
    bitstream_filename = os.path.join(output_dir, "{}.vc2".format(test_case.name),)
    with open(bitstream_filename, "wb") as f:
        autofill_and_serialise_sequence(f, test_case.value)

    # Decode model answer
    model_answer_directory = os.path.join(
        output_dir, "{}_expected".format(test_case.name),
    )
    makedirs(model_answer_directory, exist_ok=True)
    with open(bitstream_filename, "rb") as f:
        index = [0]

        def output_picture(picture, video_parameters):
            file_format.write(
                picture,
                video_parameters,
                codec_features["picture_coding_mode"],
                os.path.join(
                    model_answer_directory, "picture_{}.raw".format(index[0]),
                ),
            )
            index[0] += 1

        state = State(_output_picture_callback=output_picture)
        init_io(state, f)
        parse_sequence(state)

    # Write metadata
    if test_case.metadata is not None:
        with open(
            os.path.join(output_dir, "{}_metadata.json".format(test_case.name),), "w"
        ) as f:
            json.dump(test_case.metadata, f)

    logging.info(
        "Generated decoder test case %s for %s", test_case.name, codec_features["name"],
    )


def output_decoder_test_cases(output_dir, codec_features, generator_function):
    makedirs(output_dir, exist_ok=True)
    for test_case in generator_function():
        output_decoder_test_case(output_dir, codec_features, test_case)


def set_log_level_and_call(log_level, fn, *args, **kwargs):
    logging.basicConfig(level=log_level)
    return fn(*args, **kwargs)


def main(*args, **kwargs):
    args = parse_args(*args, **kwargs)

    log_level = logging.WARNING
    if args.verbose >= 2:
        log_level = logging.DEBUG
    elif args.verbose >= 1:
        log_level = logging.INFO
    logging.basicConfig(level=log_level)

    codec_feature_sets = load_codec_features(args.codec_configurations, args.codecs,)

    if not args.force:
        check_output_directories_empty(
            args.output,
            codec_feature_sets,
            not args.decoder_only,
            not args.encoder_only,
        )

    check_codec_features_valid(codec_feature_sets)

    to_call = []

    for name, codec_features in codec_feature_sets.items():
        if not args.decoder_only:
            output_dir = os.path.join(args.output, name, "encoder",)
            for (
                generator_function
            ) in ENCODER_TEST_CASE_GENERATOR_REGISTRY.iter_independent_generators(
                codec_features,
            ):
                to_call.append(
                    partial(
                        set_log_level_and_call,
                        log_level,
                        output_encoder_test_cases,
                        output_dir,
                        codec_features,
                        generator_function,
                    )
                )

        if not args.encoder_only:
            output_dir = os.path.join(args.output, name, "decoder",)
            for (
                generator_function
            ) in DECODER_TEST_CASE_GENERATOR_REGISTRY.iter_independent_generators(
                codec_features,
            ):
                to_call.append(
                    partial(
                        set_log_level_and_call,
                        log_level,
                        output_decoder_test_cases,
                        output_dir,
                        codec_features,
                        generator_function,
                    )
                )

    if args.parallel:
        for fn in to_call:
            print(create_command(fn))
    else:
        for fn in to_call:
            fn()

    return 0
