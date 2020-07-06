r"""
The :py:mod:`vc2_conformance.bitstream` module implements facilities for
deserialising, displaying, manipulating and serialising VC-2 bitstreams,
including non-conformant streams, at a low-level.

This documentation begins with an overview of how bitstreams can be serialised,
deserialised and represented as Python data structures using this module. This
is followed by an in-depth description of how the serialiser and deserialisers
work internally.

How the serialiser/deserialiser module is used
----------------------------------------------

This module is used by various parts of the VC-2 conformance software, for
example:

* The :ref:`vc2-bitstream-viewer` utility uses this module to produce human
  readable, hierarchical descriptions of bitstreams.
* The test case generators in :py:mod:`vc2_conformance.test_cases` use this
  module to manipulate bitstreams, for example by tweaking values or filling
  padding bits with specific data.
* The VC-2 encoder in :py:mod:`vc2_conformance.encoder` produces deserialised
  bitstreams directly for later serialisation by this module.
* The conformance software's own test suite makes extensive use of this module.

.. note::

    This module is *not* used by the bitstream validator
    (:py:mod:`vc2_conformance.decoder`) which instead operates directly on the
    binary bitstream instead.

This module consists of two main parts: the
:py:mod:`~vc2_conformance.bitstream.serdes` framework for building serialisers
and deserialisers and a serialiser/deserialiser for VC-2.

The :py:mod:`~vc2_conformance.bitstream.serdes` framework allows serialisers
and deserialisers to be constructed *directly* from the VC-2 pseudocode,
ensuring a high chance of correctness.

The VC-2 serialiser/deserialiser, implemented using the
:py:mod:`~vc2_conformance.bitstream.serdes` framework defines a series of
Python data structures which may be used to describe a VC-2 bitstream.


Quick-start guide
-----------------

Before diving into the details, we'll briefly give few quick examples which
illustrate how this module is used below. We'll show how a small bitstream can
be explicitly described as a Python data structure, serialised and then
deserialised again. We'll skim over the details (and ignore a number of
important but minor features) in the process.


Deserialised bitstream data structures
``````````````````````````````````````

A VC-2 bitstream can be described hierarchically as a series of dictionaries
and lists. For example, the following structure describes a minimal VC-2
bitstream containing just a single end-of-sequence data unit::

    >>> from bitarray import bitarray

    >>> # A minimal bitstream...
    >>> bitstream_description = {
    ...     # ...consisting of a single sequence...
    ...     "sequences": [
    ...         {
    ...             # ...with a single data unit...
    ...             "data_units": [
    ...                 {
    ...                     # ...which is an end-of-sequence data unit
    ...                     "parse_info": {
    ...                         "padding": bitarray(),  # No byte alignment bits
    ...                         "parse_info_prefix": 0x42424344,
    ...                         "parse_code": 0x10,  # End of sequence
    ...                         "next_parse_offset": 0,
    ...                         "previous_parse_offset": 0,
    ...                     },
    ...                 },
    ...             ],
    ...         },
    ...     ],
    ... }

To make this somewhat clearer and more robust, a set of :py:mod:`fixeddicts
<vc2_conformance.fixeddict>` are provided which may be used instead of bare
Python dictionaries. The :py:mod:`vc2_data_tables` package also includes many
helpful constant definitions.  Together, these make it easier to see what's
going on while also eliminating simple mistakes like misspelling a field name.

.. note::

    :py:mod:`fixeddicts <vc2_conformance.fixeddict>` are subclasses of Python's
    native :py:class:`dict` type with the following extra features:

    * They allow only a permitted set of key names to be used.
    * The ``__str__`` implementation produces an easier to read pretty-printed
      format.

Using these types, our example now looks like::

    >>> from vc2_data_tables import PARSE_INFO_PREFIX, ParseCodes
    >>> from vc2_conformance.bitstream import Stream, Sequence, DataUnit, ParseInfo

    >>> bitstream_description = Stream(
    ...     sequences=[
    ...         Sequence(
    ...             data_units=[
    ...                 DataUnit(
    ...                     parse_info=ParseInfo(
    ...                         padding=bitarray(),  # No byte alignment bits
    ...                         parse_info_prefix=PARSE_INFO_PREFIX,
    ...                         parse_code=ParseCodes.end_of_sequence,
    ...                         next_parse_offset=0,
    ...                         previous_parse_offset=0,
    ...                     ),
    ...                 ),
    ...             ],
    ...         ),
    ...     ],
    ... )

See :ref:`bitstream-fixeddicts` for details of the expected hierarchy of a
deserialised bitstream (and the :py:mod:`~vc2_conformance.fixeddict` dictionary
types provided).


Serialising bitstreams
``````````````````````

To serialise our bitstream into binary form, we can use the following (which
we'll unpick afterwards)::

    >>> from vc2_conformance.bitstream import BitstreamWriter, Serialiser, parse_stream
    >>> from vc2_conformance.pseudocode import State

    >>> with open("/path/to/bitstream.vc2", "wb") as f:
    ...     with Serialiser(BitstreamWriter(f), bitstream_description) as ser:
    ...         parse_stream(ser, State())

In the example above, ``parse_stream`` is (a special version of) the
``parse_stream`` VC-2 pseudocode function provided by the
:py:mod:`vc2_conformance.bitstream` module. This pseudocode function would
normally decode a VC-2 stream (as per the VC-2 specification), however this
modified version may be used to serialise (or deserialise) a bitstream.  The
modified function takes an extra first argument, a
:py:class:`~vc2_conformance.bitstream.serdes.Serialiser` in this case, which it
will use to produce the serialised bitstream.

The :py:class:`~vc2_conformance.bitstream.serdes.Serialiser` class takes two
arguments in this example: a
:py:class:`~vc2_conformance.bitstream.io.BitstreamWriter` and the data
structure to serialise (``bitstream_description`` in our example).

The :py:class:`~vc2_conformance.bitstream.io.BitstreamWriter` is a wrapper for
file-like objects which provides additional bitwise I/O operations used during
serialisation.

The second argument to :py:class:`~vc2_conformance.bitstream.serdes.Serialiser`
is the deserialised data structure to be serialised. This may be an ordinary
Python :py:class:`dicts <dict>` or a :py:mod:`~vc2_conformance.fixeddict`.

.. note::

    It is possible to serialise (or deserialise) components of a bitstream in
    isolation by using other pseudocode functions in place of ``parse_stream``.
    In this case, the data structure provided to the
    :py:class:`~vc2_conformance.bitstream.serdes.Serialiser` must match the
    shape expected by the modified pseudocode function used. See
    :ref:`bitstream-fixeddicts` for an enumeration of the pseudocode functions
    available and the expected data structure.


Autofilling bitstream values
````````````````````````````

In the example above we explicitly spelt out every field in the bitstream --
including the empty padding field!  If we had omitted this field, the
serialiser will produce an error because it wouldn't know what padding bits we
wanted it to use in the stream. However, often we don't care about details such
as these and so the :py:class:`~vc2_conformance.bitstream.Serialiser` can
optionally 'autofill' certain values which weren't given in the deserialised
data structure.

The :py:class:`~vc2_conformance.bitstream.Serialiser` class takes an optional
third argument which it uses to autofill missing values. A sensible set of a
autofill values is provided in
:py:mod:`vc2_conformance.bitstream.vc2_default_values` allowing us to rewrite
our example like so::

    >>> from vc2_conformance.bitstream import vc2_default_values

    >>> concise_bitstream_description = Stream(
    ...     sequences=[
    ...         Sequence(
    ...             data_units=[
    ...                 DataUnit(
    ...                     parse_info=ParseInfo(
    ...                         parse_code=ParseCodes.end_of_sequence,
    ...                         next_parse_offset=0,
    ...                         previous_parse_offset=0,
    ...                     ),
    ...                 ),
    ...             ],
    ...         ),
    ...     ],
    ... )

    >>> with open("/path/to/bitstream.vc2", "wb") as f:
    ...     with Serialiser(
    ...         BitstreamWriter(f),
    ...         concise_bitstream_description,
    ...         vc2_default_values,
    ...     ) as ser:
    ...         parse_stream(ser, State())


This time we were able to omit the byte-alignment padding value and parse info
prefix which the serialiser autofilled with zeros and 0x42424344 respectively.

The default values for all fields are given in :ref:`bitstream-fixeddicts`.

Unfortunately, when using the mechanism above, autofill values are not provided
for every field in a bitstream (or for fields listed as autofilled with
``<AUTO>`` in the documentation). For instance, picture numbers and parse
offset values must still be calculated and specified explicitly. For a more
complete bitstream autofill solution the
:py:func:`vc2_conformance.bitstream.autofill_and_serialise_stream` utility
function is provided.

The :py:func:`~vc2_conformance.bitstream.autofill_and_serialise_stream`
function can autofill most values including picture numbers, and parse offset
fields (which marked as ``<AUTO>`` in the documentation). It also provides a
more concise wrapper around the serialisation process.

Using :py:func:`~vc2_conformance.bitstream.autofill_and_serialise_stream` our
example now becomes::

    >>> from vc2_conformance.bitstream import autofill_and_serialise_stream

    >>> very_concise_bitstream_description = Stream(
    ...     sequences=[
    ...         Sequence(
    ...             data_units=[
    ...                 DataUnit(
    ...                     parse_info=ParseInfo(
    ...                         parse_code=ParseCodes.end_of_sequence,
    ...                     ),
    ...                 ),
    ...             ],
    ...         ),
    ...     ],
    ... )

    >>> with open("/path/to/bitstream.vc2", "wb") as f:
    ...     autofill_and_serialise_stream(f, very_concise_bitstream_description)

Notice that this time we could omit all but the ``parse_code`` field.

.. note::

    The :py:func:`~vc2_conformance.bitstream.autofill_and_serialise_stream`
    function only supports serialisation of entire :py:class:`Streams
    <vc2_conformance.bitstream.Stream>` and cannot be used to serialise smaller
    pieces of a bitstream in isolation.


Deserialising bitstreams
````````````````````````

To deserialise a bitstream again, the process is similar::

    >>> from vc2_conformance.bitstream import BitstreamReader, Deserialiser

    >>> with open("/tmp/bitstream.vc2", "rb") as f:
    ...     with Deserialiser(BitstreamReader(f)) as des:
    ...         parse_stream(des, State())
    >>> deserialised_bitstream = des.context

This time, we pass a :py:class:`~vc2_conformance.bitstream.serdes.Deserialiser`
(which takes a :py:class:`~vc2_conformance.bitstream.io.BitstreamReader` as
argument) into ``parse_stream``. The deserialised bitstream is placed into
``des.``\ :py:attr:`~vc2_conformance.bitstream.serdes.Deserialiser.context` as a hierarchy
of :py:mod:`~vc2_conformance.fixeddicts`. We can then print or interact with the
deserialised data structure just like any other Python object::

    >>> # NB: Fixeddicts produce pretty-printed output when printed!
    >>> print(deserialised_bitstream)
    Stream:
      sequences:
        0: Sequence:
          data_units:
            0: DataUnit:
              parse_info: ParseInfo:
                padding: 0b
                parse_info_prefix: Correct (0x42424344)
                parse_code: end_of_sequence (0x10)
                next_parse_offset: 0
                previous_parse_offset: 0

    >>> data_unit = deserialised_bitstream["sequences"][0]["data_units"][0]
    >>> print(data_unit["parse_info"]["parse_code"])
    16


.. _bitstream-fixeddicts:

Deserialised VC-2 bitstream data types
--------------------------------------

Deserialised VC-2 bitstreams are described by a hierarchy of
:py:class:`fixeddicts <vc2_conformance.fixeddict>`, exported in
:py:mod:`vc2_conformance.bitstream`.  Each
:py:class:`~vc2_conformance.fixeddict` represents the data read by a particular
VC-2 pseudocode function. Special implementations of these functions are
provided in :py:mod:`vc2_conformance.bitstream` which may be used to serialise
and deserialise VC-2 bitstreams (or individual parts thereof).

..
    The following RST directives are implemented by
    ``docs/source/_ext/bitstream_fixeddicts.py``. These one-off directives
    generate a complete listing of:

    * The fixeddict types defined in
      :py:mod:`vc2_conformance.bitstream.vc2_fixeddicts`
    * The pseudocode functions defined in :py:mod:`vc2_conformance.bitstream.vc2`
    * The autofill values defined in
      :py:mod:`vc2_conformance.bitstream.vc2_autofill`

.. autobitstreamfixeddictstable::

.. autobitstreamfixeddicts::

:py:mod:`~vc2_conformance.bitstream.serdes`: A serialiser/deserialiser framework
--------------------------------------------------------------------------------

.. automodule:: vc2_conformance.bitstream.serdes


Low-level bitstream IO
----------------------

.. automodule:: vc2_conformance.bitstream.io

Fixeddicts and pseudocode
-------------------------

.. automodule:: vc2_conformance.bitstream.vc2_fixeddicts

.. automodule:: vc2_conformance.bitstream.vc2


Autofill
--------

.. automodule:: vc2_conformance.bitstream.vc2_autofill


Metadata
--------

.. automodule:: vc2_conformance.bitstream.metadata

"""

from vc2_conformance.bitstream.exceptions import *

# Exp-golomb code length calculators
from vc2_conformance.bitstream.exp_golomb import *

# Low-level bitwise file reading/writing
from vc2_conformance.bitstream.io import *

# Generic bitstream serialisation/deserialisation framework
from vc2_conformance.bitstream.serdes import *

# VC-2 specific parts
from vc2_conformance.bitstream.vc2 import *
from vc2_conformance.bitstream.vc2_fixeddicts import *
from vc2_conformance.bitstream.vc2_autofill import *

# Metadata for introspection purposes
from vc2_conformance.bitstream.metadata import *
