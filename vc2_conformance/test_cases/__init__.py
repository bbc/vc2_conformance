r"""
:py:mod:`vc2_conformance.test_cases`: Test case generation routines for VC-2 codecs
==================================================================================

This module contains routines for generating test cases for VC-2 encoder and
decoder implementations.

Test cases are generated on-demand for specific sets of
:py:class:`~vc2_conformance.codec_features.CodecFeatures` by test
case generators. A test case generator is a function which takes a
:py:class:`~vc2_conformance.codec_features.CodecFeatures` as an
argument and returns or yields test pictures or bitstreams.

Test case generators are registered with one of two :py:class:`Registry`
objects:

.. autodata:: ENCODER_TEST_CASE_GENERATOR_REGISTRY

.. autodata:: DECODER_TEST_CASE_GENERATOR_REGISTRY

Test case generator functions are registered with these registries by
decorating them using the :py:func:`encoder_test_case_generator` and
:py:func:`decoder_test_case_generator` decorators.

.. autodata:: encoder_test_case_generator

.. autodata:: decoder_test_case_generator


Test case generators
--------------------

Test case generator functions are divided into encoder and decoder test cases.

Encoder test case generators take a
:py:class:`~vc2_conformance.codec_features.CodecFeatures` and
produce a :py:class:`EncoderTestSequence` object.

.. autoclass:: EncoderTestSequence

Decoder test case generators take a
:py:class:`~vc2_conformance.codec_features.CodecFeatures` and produce a
:py:class:`vc2_conformance.bitstream.Stream` dictionary.

In the simplest case, test case generator functions may be functions which
return a single :py:class:`EncoderTestSequence` or
:py:class:`~vc2_conformance.bitstream.Sequence` object (or None to indicate no
suitable test case is available).  Alternatively case generators may also
``yield`` a series of several related values.

Test cases are assigned a name based on the name of the function which produced
them. Where a test case generator generates several test cases, these are
automatically assigned sequential identifiers. Alternatively, test case
generators may wrap returned test cases in :py:class:`TestCase` objects in
which custom names are provided. Additionally, JSON-serialisable metadata may
be attached to a :py:class:`TestCase`.

.. autoclass:: TestCase

The :py:class:`normalise_test_case_generator` function is provided which
normalises a test case generator function into a generator function producing
:py:class:`TestCase` objects.

.. autofunction:: normalise_test_case_generator


Test case generator registries
------------------------------

The :py:class;`Registry` class implements a registry of test case generators.

.. autoclass:: Registry


"""

from types import GeneratorType

from functools import partial

from collections import namedtuple


__all__ = [
    "EncoderTestSequence",
    "TestCase",
    "ENCODER_TEST_CASE_GENERATOR_REGISTRY",
    "DECODER_TEST_CASE_GENERATOR_REGISTRY",
]


EncoderTestSequence = namedtuple(
    "TestPictureSequence", "pictures,video_parameters,picture_coding_mode"
)
"""
A sequence of pictures to be encoded by a VC-2 encoder under test.

Parameters
==========
pictures : [{"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}, ...]
    A :py:class:`list` of dictionaries containing raw picture data in 2D arrays
    for each picture component.
video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    The video parameters associated with the test sequence.
picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    The picture coding mode associated with the test sequence.
"""


class TestCase(object):
    def __init__(self, value, subcase_name=None, case_name=None, metadata=None):
        """
        A test case, produced by a test case generator function.

        Parameters
        ==========
        value : object
            A value containing the test case itself. (For example a bitstream
            or picture).
        subcase_name : str or None
            An identifier for the sub-case if this test case has several
            sub-cases.
        case_name : str or None
            The name of the test case. If None, the ``case_name`` will be
            populated automatically.
        metadata : object or None
            Optional JSON-serialisable metadata associated with this test case.
            The meaning and formatting of of this metadata is left to the
            individual test case to define.
        """
        self.value = value
        self.subcase_name = subcase_name
        self.case_name = case_name
        self.metadata = metadata

    @property
    def name(self):
        """
        A human-readable name for this test case
        """
        if self.subcase_name is None:
            return self.case_name
        else:
            return "{}[{}]".format(self.case_name, self.subcase_name)

    def __repr__(self):
        return "<{} {}>".format(type(self).__name__, self.name,)

    def __eq__(self, other):
        return (
            type(self) is type(other)
            and self.value == other.value
            and self.case_name == other.case_name
            and self.subcase_name == other.subcase_name
            and self.metadata == other.metadata
        )


def normalise_test_case_generator(f, *args, **kwargs):
    """
    Call a test case generator, f, and, regardless of its native output,
    produces a generator of :py:class:`TestCase` objects.

    If the function returns or yields :py:class:`TestCase` objects, their
    :py:attr:`TestCase.case_name` attributes will be populated with the
    function name, if not already defined. If the function returns or generates
    other values, these will be wrapped in :py:class:`TestCase` objects
    automatically. If the function returns or generates None, no test case will
    be emitted.
    """
    generator = f(*args, **kwargs)

    is_generator = isinstance(generator, GeneratorType)
    if not is_generator:
        generator = [generator]

    for i, value in enumerate(generator):
        if value is None:
            continue

        if not isinstance(value, TestCase):
            value = TestCase(value)

        if value.case_name is None:
            value.case_name = f.__name__

        if is_generator and value.subcase_name is None:
            value.subcase_name = str(i)

        yield value


class Registry(object):
    """
    A registry of test case generating functions.
    """

    def __init__(self):
        self._test_case_generators = []

    def register_test_case_generator(self, f):
        """
        Register a test case generator function with this registry.

        Returns the (unmodified) function allowing this method to be used as a
        decorator.
        """
        self._test_case_generators.append(f)
        return f

    def generate_test_cases(self, *args, **kwargs):
        """
        Run every test case generator registered with this registry, passing
        each generator the supplied arguments. Iterates over the generated
        :py:class:`TestCase` objects.
        """
        for test_case_generator in self._test_case_generators:
            for test_case in normalise_test_case_generator(
                test_case_generator, *args, **kwargs
            ):
                yield test_case

    def iter_independent_generators(self, *args, **kwargs):
        """
        Produce a series of generator functions which may be called in parallel
        (e.g. using :py:mod:`multiprocessing`), which generate test cases.
        """
        for test_case_generator in self._test_case_generators:
            yield partial(
                normalise_test_case_generator, test_case_generator, *args, **kwargs
            )

    def iter_registered_functions(self):
        """
        Iterates over the functions registered with this registry. Only
        intended for use during documentation generation.
        """
        for test_case_generator in self._test_case_generators:
            yield test_case_generator


ENCODER_TEST_CASE_GENERATOR_REGISTRY = Registry()
"""
:py:class:`Registry` singleton with which all VC-2 encoder test cases are
registered.
"""

encoder_test_case_generator = (
    ENCODER_TEST_CASE_GENERATOR_REGISTRY.register_test_case_generator
)
"""Decorator to use to register all encoder test case generators."""


DECODER_TEST_CASE_GENERATOR_REGISTRY = Registry()
"""
:py:class:`Registry` singleton with which all VC-2 decoder test cases are
registered.
"""

decoder_test_case_generator = (
    DECODER_TEST_CASE_GENERATOR_REGISTRY.register_test_case_generator
)
"""Decorator to use to register all decoder test case generators."""


# Import test case containing submodules to ensure they become registered with
# the above registries
from vc2_conformance.test_cases.encoder import *  # noqa: E402
from vc2_conformance.test_cases.decoder import *  # noqa: E402
