r"""
The :py:mod:`vc2_conformance.test_cases` module contains routines for
generating test cases for VC-2 encoder and decoder implementations.

A description of each test case generator can be found in
:ref:`encoder-test-cases` and :ref:`decoder-test-cases` in the user guide.

Test case generators
--------------------

Test case generators are generator functions which take a
:py:class:`~vc2_conformance.codec_features.CodecFeatures` dictionary as their
only argument and produce picture sequences (for encoders) or bitstreams (for
decoders). Test case generators may take one of the following forms:

* Function which returns a single test case
* Function which returns a single test case or None (indicating no test case
  was produced)
* Generator function which yields multiple test cases.

A test case can be one of:

* For encoder test cases, a picture sequence in the form of an
  :py:class:`EncoderTestSequence` object.
* For decoder test cases, a bitstream in the form of a
  :py:class:`~vc2_conformance.bitstream.Stream` object which can be serialised
  using
  :py:func:`~vc2_conformance.bitstream.vc2_autofill.autofill_and_serialise_stream`.
* A :py:class:`TestCase` object containing one of the above as its
  :py:attr:`~TestCase.value`.

Test case generators may prefer to output :py:class:`TestCase` objects when
multiple test cases are produced so that each testcase can be given its own
'subcase' name. In addition, test cases may be accompanied by a freeform JSON
serialisable metadata object when :py:class:`TestCase` objects are produced.

.. autoclass:: TestCase
    :members:
    :undoc-members:

All test case generator functions are run via
:py:func:`normalise_test_case_generator` which normalises the function into the
form of a generator which yields :py:class:`TestCase` objects. This also
populates the :py:attr:`~TestCase.case_name` field of the generated
:py:class:`TestCase` automatically with the test case generator's function
name.

.. autofunction:: normalise_test_case_generator


Encoder test case generators
----------------------------

Encoder test case generators are located in
:py:mod:`vc2_conformance.test_cases.encoder` must be decorated with the
:py:data:`vc2_conformance.test_cases.encoder_test_case_generator` decorator,
take a :py:class:`~vc2_conformance.codec_features.CodecFeatures` and produce
:py:class:`EncoderTestSequence` objects.

.. autodata:: encoder_test_case_generator
    :annotation:

.. autoclass:: EncoderTestSequence

Decoder test case generators
----------------------------

Decoder test case generators are located in
:py:mod:`vc2_conformance.test_cases.decoder` must be decorated with the
:py:data:`vc2_conformance.test_cases.decoder_test_case_generator` decorator,
take a :py:class:`~vc2_conformance.codec_features.CodecFeatures` and produce
:py:class:`vc2_conformance.bitstream.Stream` dictionaries which can be
serialised using
:py:func:`~vc2_conformance.bitstream.vc2_autofill.autofill_and_serialise_stream`.

.. autodata:: decoder_test_case_generator
    :annotation:


Test case generator registries
------------------------------

All test case generators are registered (by the
:py:data:`encoder_test_case_generator` and
:py:data:`decoder_test_case_generator` decorators) with one of two
:py:class:`Registry` singletons:

.. autodata:: ENCODER_TEST_CASE_GENERATOR_REGISTRY
    :annotation:

.. autodata:: DECODER_TEST_CASE_GENERATOR_REGISTRY
    :annotation:

The :py:class:`Registry` class implements a registry of test case generators
which the :ref:`vc2-test-case-generator` script uses to generate a complete set
of test cases.

.. autoclass:: Registry
    :members:

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
    "EncoderTestSequence", "pictures,video_parameters,picture_coding_mode"
)
"""
A sequence of pictures to be encoded by a VC-2 encoder under test.

Parameters
==========
pictures : [{"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}, ...]
    A :py:class:`list` of dictionaries containing raw picture data in 2D arrays
    for each picture component.
video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    The video parameters associated with the test sequence.
picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    The picture coding mode associated with the test sequence.
"""


class TestCase(object):
    """
    A test case, produced by a test case generator function.

    Parameters
    ==========
    value : :py:class:`EncoderTestSequence` or :py:class:`~vc2_conformance.bitstream.Stream`
        A value containing the test case itself. An
        :py:class:`EncoderTestSequence` for encoder test cases or
        :py:class:`~vc2_conformance.bitstream.Stream` for decoder test cases.
    subcase_name : str or None
        An identifier for the sub-case if this test case has several
        sub-cases.
    case_name : str or None
        The name of the test case. If None, the ``case_name`` will be
        populated automatically with the name of the test case generator
        function which returned it.
    metadata : object or None
        Optional JSON-serialisable metadata associated with this test case.
        The meaning and formatting of of this metadata is left to the
        individual test case to define.
    """

    def __init__(self, value, subcase_name=None, case_name=None, metadata=None):
        self._value = value
        self._subcase_name = subcase_name
        self._case_name = case_name
        self._metadata = metadata

    @property
    def name(self):
        """
        The complete name of this test case. Constructed from the
        :py:attr:`case_name` and  :py:attr:`subcase_name` attributes.

        A string of the form ``"case_name"`` or ``"case_name[subcase_name]"``.
        """
        if self.subcase_name is None:
            return self.case_name
        else:
            return "{}[{}]".format(self.case_name, self.subcase_name)

    @property
    def case_name(self):
        return self._case_name

    @case_name.setter
    def case_name(self, value):
        self._case_name = value

    @property
    def subcase_name(self):
        return self._subcase_name

    @subcase_name.setter
    def subcase_name(self, value):
        self._subcase_name = value

    @property
    def value(self):
        return self._value

    @property
    def metadata(self):
        return self._metadata

    def __repr__(self):
        return "<{} {}>".format(
            type(self).__name__,
            self.name,
        )

    def __eq__(self, other):
        return (
            type(self) is type(other)
            and self.value == other.value
            and self.case_name == other.case_name
            and self.subcase_name == other.subcase_name
            and self.metadata == other.metadata
        )

    def __ne__(self, other):
        """Required under Python 2.x"""
        return not self.__eq__(other)


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
        each generator the supplied arguments. Generates all
        :py:class:`TestCase` objects.
        """
        for test_case_generator in self._test_case_generators:
            for test_case in normalise_test_case_generator(
                test_case_generator, *args, **kwargs
            ):
                yield test_case

    def iter_independent_generators(self, *args, **kwargs):
        """
        Produce a series of generator functions which may be called in
        parallel. Each returned zero-argument function should be called and
        will generate a series of :py:class:`TestCase` objects.
        """
        for test_case_generator in self._test_case_generators:
            yield partial(
                normalise_test_case_generator, test_case_generator, *args, **kwargs
            )

    def iter_registered_functions(self):
        """
        Iterates over the raw functions registered with this registry.

        Only intended for use during documentation generation.
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
